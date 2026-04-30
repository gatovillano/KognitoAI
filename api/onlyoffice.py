# api/onlyoffice.py

import logging
import os
import uuid
import httpx
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import SessionLocal, Document, Account
from core.dependencies import get_db_session
from utils.security import get_current_account_id, check_workspace_permission
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Directorio para los documentos de OnlyOffice
DOCUMENTS_ROOT = os.path.join("/app/media", "documents")
os.makedirs(DOCUMENTS_ROOT, exist_ok=True)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(None),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Sube un documento para ser editado con OnlyOffice."""
    # Verificar permisos de workspace si se proporciona
    if workspace_id:
        if not await check_workspace_permission(current_account_id, workspace_id, db, required_roles=["owner", "editor"]):
            raise HTTPException(status_code=403, detail="No tienes permiso para subir documentos a este workspace.")

    account_id_uuid = uuid.UUID(current_account_id)
    
    # Obtener nombre y extensión
    filename = file.filename
    extension = filename.split('.')[-1].lower() if '.' in filename else ""
    
    # Validar extensiones soportadas por OnlyOffice (básico)
    supported = ['docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt', 'txt', 'csv']
    if extension not in supported:
        raise HTTPException(status_code=400, detail=f"Extensión .{extension} no soportada.")

    # Guardar archivo físicamente
    unique_filename = f"{uuid.uuid4()}.{extension}"
    user_dir = os.path.join(DOCUMENTS_ROOT, current_account_id)
    os.makedirs(user_dir, exist_ok=True)
    
    file_path = os.path.join(user_dir, unique_filename)
    
    try:
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        logger.error(f"Error al guardar archivo OnlyOffice: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar el archivo en el servidor.")
    
    # Guardar metadatos en la base de datos
    new_doc = Document(
        account_id=account_id_uuid,
        workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
        filename=filename,
        extension=extension,
        file_path=os.path.join(current_account_id, unique_filename)
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    
    return {"message": "Documento subido correctamente", "id": new_doc.id, "filename": filename}

@router.get("/list")
async def list_documents(
    workspace_id: Optional[str] = Query(None),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Lista los documentos editables del usuario o workspace."""
    stmt = select(Document).where(Document.account_id == uuid.UUID(current_account_id))
    if workspace_id:
        stmt = stmt.where(Document.workspace_id == uuid.UUID(workspace_id))
    else:
        stmt = stmt.where(Document.workspace_id == None)
        
    result = await db.execute(stmt)
    docs = result.scalars().all()
    
    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "extension": doc.extension,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            "workspace_id": str(doc.workspace_id) if doc.workspace_id else None
        }
        for doc in docs
    ]

@router.get("/config/{document_id}")
async def get_onlyoffice_config(
    document_id: uuid.UUID,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Genera la configuración necesaria para el editor OnlyOffice JavaScript."""
    doc = await db.get(Document, document_id)
    if not doc or str(doc.account_id) != current_account_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # URL del Document Server (Usamos el proxy de Next.js para simplificar el acceso externo)
    onlyoffice_api_url = os.getenv("ONLYOFFICE_URL", "/onlyoffice")
    
    # URL del Backend para que OnlyOffice (que está en el host/otro docker) descargue el archivo.
    # Debe ser una URL accesible por el servidor OnlyOffice.
    backend_url = settings.api_server_url.rstrip('/')
    
    file_url = f"{backend_url}/api/onlyoffice/download/{doc.id}"
    callback_url = f"{backend_url}/api/onlyoffice/callback/{doc.id}"
    
    # Generar una clave única para la sesión de edición basada en el ID y la última actualización
    from hashlib import md5
    key = md5(f"{doc.id}-{doc.updated_at.isoformat()}".encode()).hexdigest()
    
    config = {
        "document": {
            "fileType": doc.extension,
            "key": key,
            "title": doc.filename,
            "url": file_url,
        },
        "documentType": get_document_type(doc.extension),
        "editorConfig": {
            "callbackUrl": callback_url,
            "lang": "es",
            "mode": "edit",
            "user": {
                "id": current_account_id,
                "name": "Usuario"
            },
            "customization": {
                "forcesave": True,
                "chat": False,
                "comments": True,
                "help": False
            }
        }
    }
    
    return {"config": config, "onlyoffice_url": onlyoffice_api_url}

def get_document_type(ext: str) -> str:
    """Mapea extensiones a tipos de documentos de OnlyOffice."""
    ext = ext.lower()
    if ext in ['doc', 'docx', 'rtf', 'txt', 'odt']: return 'word'
    if ext in ['xls', 'xlsx', 'csv', 'ods']: return 'cell'
    if ext in ['ppt', 'pptx', 'odp']: return 'slide'
    return 'word'

@router.get("/download/{document_id}")
async def download_document(document_id: uuid.UUID):
    """Permite a OnlyOffice descargar el archivo actual."""
    # Nota: Este endpoint es público para que el servidor OnlyOffice pueda acceder.
    # En producción se debería usar un token secreto o validar la IP.
    async with SessionLocal() as db:
        doc = await db.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        file_full_path = os.path.join(DOCUMENTS_ROOT, doc.file_path)
        if not os.path.exists(file_full_path):
            raise HTTPException(status_code=404, detail="Archivo físico no encontrado")
            
        return FileResponse(file_full_path, filename=doc.filename)

@router.post("/callback/{document_id}")
async def onlyoffice_callback(document_id: uuid.UUID, request: Request):
    """Recibe las actualizaciones de OnlyOffice para guardar el archivo."""
    try:
        body = await request.json()
    except:
        return {"error": 1}
        
    status = body.get("status")
    logger.info(f"OnlyOffice Callback para {document_id}: Status {status}")
    
    # Status 2: El documento está listo para ser guardado
    # Status 6: El documento se está guardando forzadamente (forcesave)
    if status in [2, 6]:
        download_url = body.get("url")
        if not download_url:
            return {"error": 1}
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(download_url)
            if resp.status_code == 200:
                async with SessionLocal() as db:
                    doc = await db.get(Document, document_id)
                    if doc:
                        file_full_path = os.path.join(DOCUMENTS_ROOT, doc.file_path)
                        with open(file_full_path, "wb") as f:
                            f.write(resp.content)
                        
                        doc.updated_at = datetime.now()
                        await db.commit()
                        logger.info(f"Documento {document_id} guardado correctamente.")
                    else:
                        logger.error(f"Documento {document_id} no encontrado en DB durante callback.")
            else:
                logger.error(f"Error al descargar actualización de OnlyOffice: {resp.status_code}")
                return {"error": 1}
                        
    return {"error": 0}

@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Elimina un documento y su archivo físico."""
    doc = await db.get(Document, document_id)
    if not doc or str(doc.account_id) != current_account_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    file_full_path = os.path.join(DOCUMENTS_ROOT, doc.file_path)
    if os.path.exists(file_full_path):
        try:
            os.remove(file_full_path)
        except Exception as e:
            logger.error(f"Error al eliminar archivo físico: {e}")
        
    await db.delete(doc)
    await db.commit()
    return {"message": "Documento eliminado con éxito."}
