# api/documents.py

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, text

from core.database import SessionLocal, TeamMember
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, delete_document_chunks, get_full_document_content, update_document_metadata, list_user_collections, extract_titles_and_update_metadata
from utils.db_session import DBSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncSession:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.post("/upload-document")
async def upload_document_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    files: List[UploadFile] = File(...),
    topic: str = Form(...)  # El topic se recibe correctamente aquí
):
    account_id_uuid = uuid.UUID(current_account_id)
    processed_files = 0
    for file in files:
        try:
            content_bytes = await file.read()
            extracted_text, metadata = extract_text_and_metadata_from_document(file.filename, content_bytes)
            if not extracted_text:
                logger.warning(f"No se pudo extraer texto del archivo '{file.filename}'. Omitiendo.")
                continue

            await process_document_for_rag(
                account_id=str(account_id_uuid),
                file_name=file.filename,
                extracted_text=extracted_text,
                topic=topic,
                metadata={"original_filename": file.filename}
            )
            processed_files += 1
        except Exception as e:
            logger.error(f"Fallo al procesar el archivo {file.filename} para la cuenta {account_id_uuid}: {e}", exc_info=True)

    if processed_files == 0 and files:
        raise HTTPException(status_code=500, detail="No se pudo procesar ninguno de los archivos.")
    return {"message": f"{processed_files}/{len(files)} archivo(s) procesado(s) y añadido(s) a tu base de conocimiento en la categoría '{topic}'."}

@router.post("/upload-chat-file")
async def upload_chat_file_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    files: List[UploadFile] = File(...),
    thread_id: str = Form(...)
):
    """
    Endpoint para subir archivos al contexto de un hilo de chat específico.
    Los archivos se procesan para RAG pero se marcan como específicos del chat.
    """
    account_id_uuid = uuid.UUID(current_account_id)
    processed_files = 0
    for file in files:
        try:
            content_bytes = await file.read()
            extracted_text, metadata = extract_text_and_metadata_from_document(file.filename, content_bytes)
            if not extracted_text:
                logger.warning(f"No se pudo extraer texto del archivo '{file.filename}'. Omitiendo.")
                continue

            # Añadir metadato para indicar que es un documento de chat
            metadata['chat_context_only'] = True
            metadata['thread_id'] = thread_id

            await process_document_for_rag(
                account_id=str(account_id_uuid),
                file_name=file.filename,
                extracted_text=extracted_text,
                topic=f"chat_{thread_id}",
                metadata=metadata
            )
            logger.info(f"Archivo {file.filename} subido y procesado para RAG en el hilo {thread_id} por la cuenta {account_id_uuid}")
            processed_files += 1
        except Exception as e:
            logger.error(f"Fallo al procesar el archivo {file.filename} para el hilo {thread_id} de la cuenta {account_id_uuid}: {e}", exc_info=True)

    if processed_files == 0 and files:
        raise HTTPException(status_code=500, detail="No se pudo procesar ninguno de los archivos.")
    return {"message": f"{processed_files}/{len(files)} archivo(s) subido(s) y procesado(s) para el contexto del hilo {thread_id}."}

@router.post("/list-documents")  # Cambiado a POST porque el frontend web lo usa con FormData
async def list_documents_endpoint(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """Lista los documentos subidos por el usuario, incluyendo documentos compartidos con equipos. Protegido por JWT."""
    account_id_uuid = uuid.UUID(current_account_id)
    
    # Obtener documentos personales
    personal_docs = await list_user_documents(str(account_id_uuid))
    logger.info(f"Personal documents for account {current_account_id}: {len(personal_docs)} documents found")
    
    # Obtener equipos del usuario
    member_teams_result = await db.execute(
        select(TeamMember).where(TeamMember.account_id == account_id_uuid)
    )
    member_teams = member_teams_result.scalars().all()
    team_ids = [str(team.team_id) for team in member_teams]
    logger.info(f"Teams for account {current_account_id}: {team_ids}")
    
    # Obtener documentos de equipos
    team_docs = []
    for team_id in team_ids:
        team_docs_for_id = await list_user_documents(
            account_id=str(account_id_uuid),
            team_id=team_id
        )
        logger.info(f"Team documents for team {team_id} and account {current_account_id}: {len(team_docs_for_id)} documents found")
        team_docs.extend(team_docs_for_id)
    
    # Combinar documentos personales y de equipos, eliminando duplicados por file_name
    combined_docs = {doc['file_name']: doc for doc in personal_docs + team_docs}.values()
    logger.info(f"Total combined documents for account {current_account_id}: {len(combined_docs)} documents")
    return list(combined_docs)

@router.post("/delete-document")  # Cambiado a POST porque el frontend web lo usa con FormData
async def delete_document_endpoint(current_account_id: str = Depends(get_current_account_id), file_name: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Elimina documentos de la base de conocimiento del usuario. Protegido por JWT."""
    logger.info(f"Received delete request for file_name: '{file_name}' from account: {current_account_id}")
    if not file_name or file_name.strip() == "":
        logger.warning(f"Validation failed: file_name is empty for account: {current_account_id}")
        raise HTTPException(status_code=422, detail="El nombre del archivo no puede estar vacío.")
    account_id_uuid = uuid.UUID(current_account_id)
    success = await delete_document_chunks(str(account_id_uuid), file_name)
    if not success: raise HTTPException(status_code=404, detail="Documento no encontrado o ya eliminado.")
    return {"message": f"El documento '{file_name}' ha sido eliminado."}

class UpdateMetadataRequest(BaseModel):
    """Define la estructura de datos para actualizar los metadatos de un documento."""
    file_name: str
    new_title: Optional[str] = None
    new_topic: Optional[str] = None

@router.post("/update-document-metadata")
async def update_document_metadata_endpoint(
    request: UpdateMetadataRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza el título y/o la categoría de un documento del usuario."""
    account_id_uuid = uuid.UUID(current_account_id)
    # Usa los datos del objeto 'request'
    success = await update_document_metadata(
        str(account_id_uuid), 
        request.file_name, 
        request.new_title, 
        request.new_topic
    )
    if not success:
        raise HTTPException(status_code=404, detail="Documento no encontrado o no actualizado.")
    return {"message": "Metadatos actualizados correctamente."}

class DocumentContentRequest(BaseModel):
    file_name: str

@router.post("/get-document-content", summary="Obtener el contenido de un documento")
async def get_document_content_endpoint(
    request: DocumentContentRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Recupera el contenido textual completo de un documento específico.
    """
    content = await get_full_document_content(
        account_id=current_account_id,
        file_name=request.file_name
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado o sin contenido.")
    
    return {"content": content}

class ExtractTitleRequest(BaseModel):
    topic: Optional[str] = None
    file_name: Optional[str] = None

@router.post("/extract-title", summary="Extraer títulos de documentos y actualizar metadatos")
async def extract_titles_endpoint(request: ExtractTitleRequest, current_account_id: str = Depends(get_current_account_id)):
    """
    Activa la herramienta para extraer títulos de documentos y actualizar sus metadatos en la base de conocimiento del usuario.
    El proceso se ejecuta en segundo plano y devuelve una respuesta inmediata indicando que está en curso.
    Puede aplicarse a una colección completa (por tema) o a un documento individual (por nombre de archivo).
    """
    from tools.extract_document_titles_tool import ExtractDocumentTitlesTool
    import asyncio
    
    logger.info(f"Extrayendo títulos para la cuenta: {current_account_id}, tema: {request.topic}, archivo: {request.file_name}")
    try:
        tool = ExtractDocumentTitlesTool()
        if request.file_name:
            # Ejecutar el proceso en segundo plano para un documento específico
            asyncio.create_task(tool._arun(account_id=current_account_id, topic=request.topic, file_name=request.file_name))
            return {"message": f"El proceso de extracción de título para '{request.file_name}' ha comenzado. Recibirás una actualización una vez que finalice."}
        else:
            # Ejecutar el proceso en segundo plano para una colección o todos los documentos
            asyncio.create_task(tool._arun(account_id=current_account_id, topic=request.topic))
            return {"message": "El proceso de extracción de títulos ha comenzado. Recibirás una actualización una vez que finalice."}
    except Exception as e:
        logger.error(f"Error al iniciar la extracción de títulos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al iniciar la extracción de títulos: {str(e)}")

@router.post("/list-collections", summary="Listar las colecciones de conocimiento")
async def list_collections_endpoint(current_account_id: str = Depends(get_current_account_id)):
    """
    Devuelve una lista de todas las colecciones (temas) únicas de un usuario
    y el número de documentos en cada una.
    """
    collections = await list_user_collections(current_account_id)
    return collections

@router.get("/extract-title-status", summary="Consultar estado del proceso de extracción de títulos")
async def get_extract_title_status(current_account_id: str = Depends(get_current_account_id)):
    """
    Consulta el estado actual del proceso de extracción de títulos para el usuario.
    """
    async with DBSession(SessionLocal) as db:
        status_query = text("""
            SELECT status, progress, total, message, last_updated
            FROM process_status
            WHERE account_id = :account_id
        """)
        result = await db.execute(status_query, {"account_id": current_account_id})
        status_data = result.mappings().first()
        
        if not status_data:
            return {"status": "not_started", "progress": 0, "total": 0, "message": "No se ha iniciado ningún proceso de extracción de títulos."}
        
        return {
            "status": status_data["status"],
            "progress": status_data["progress"],
            "total": status_data["total"],
            "message": status_data["message"],
            "last_updated": status_data["last_updated"].isoformat() if status_data["last_updated"] else None
        }
