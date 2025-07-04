# api/documents.py

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, text

from core.database import SessionLocal, TeamMember, LangchainPgCollection
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
    topic: str = Form(...),
    workspace_id: Optional[str] = Form(None)  # Añadir parámetro para workspace_id
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
                metadata={"original_filename": file.filename},
                workspace_id=workspace_id  # Pasar workspace_id a la función
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
    Los archivos se procesan para RAG pero se marcan como específicos del chat y no se guardan en colecciones permanentes.
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

            # Añadir metadato para indicar que es un documento de chat y no debe guardarse en colecciones permanentes
            metadata['chat_context_only'] = True
            metadata['thread_id'] = thread_id
            metadata['temporary'] = True  # Marca para indicar que es temporal y solo para el contexto del chat

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

class ListDocumentsRequest(BaseModel):
    """Define la estructura para filtrar documentos opcionalmente por topic."""
    topic: Optional[str] = None

@router.post("/list-documents")  # Cambiado a POST porque el frontend web lo usa con FormData
async def list_documents_endpoint(
    request: Optional[ListDocumentsRequest] = None,
    current_account_id: str = Depends(get_current_account_id), 
    db: AsyncSession = Depends(get_db)
):
    """Lista los documentos subidos por el usuario, incluyendo documentos compartidos con equipos. 
    Opcionalmente filtra por topic específico. Protegido por JWT."""
    account_id_uuid = uuid.UUID(current_account_id)
    topic_filter = request.topic if request else None
    
    # Obtener documentos personales (con filtro opcional por topic)
    personal_docs = await list_user_documents(str(account_id_uuid), topic=topic_filter)
    logger.info(f"Personal documents for account {current_account_id} (topic: {topic_filter}): {len(personal_docs)} documents found")
    
    # Obtener equipos del usuario (optimizado)
    member_teams_result = await db.execute(
        select(TeamMember).where(TeamMember.account_id == account_id_uuid)
    )
    member_teams = member_teams_result.scalars().all()
    team_ids = [str(team.team_id) for team in member_teams]
    
    # Solo log si hay equipos
    if team_ids:
        logger.info(f"⚠️ TEAMS: Usuario {current_account_id} pertenece a {len(team_ids)} equipos: {team_ids}")
    else:
        logger.info(f"✅ NO TEAMS: Usuario {current_account_id} no pertenece a ningún equipo")
    
    # Obtener documentos de equipos solo si los hay
    team_docs = []
    if team_ids:
        for team_id in team_ids:
            team_docs_for_id = await list_user_documents(
                account_id=str(account_id_uuid),
                team_id=team_id,
                topic=topic_filter
            )
            if team_docs_for_id:  # Solo log si hay documentos
                logger.info(f"Team documents for team {team_id}: {len(team_docs_for_id)} documents found")
            team_docs.extend(team_docs_for_id)
    
    # Combinar documentos personales y de equipos, eliminando duplicados por file_name
    combined_docs = {doc['file_name']: doc for doc in personal_docs + team_docs}.values()
    combined_docs_list = list(combined_docs)
    
    # Debug logging para investigar problema de filtrado
    logger.info(f"🔍 DEBUG: Total combined documents for account {current_account_id}: {len(combined_docs_list)} documents")
    for doc in combined_docs_list:
        logger.info(f"🔍 DEBUG: Documento - file_name: '{doc.get('file_name')}', topic: '{doc.get('topic')}'")
    
    return combined_docs_list

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

@router.post("/create-collection", summary="Crear una nueva colección vacía")
async def create_collection_endpoint(
    request: dict,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea una nueva colección vacía usando la tabla UserDocumentTopic.
    """
    topic = request.get("topic")
    description = request.get("description")
    team_id = request.get("teamId")
    workspace_id = request.get("workspaceId")
    
    if not topic or not isinstance(topic, str) or len(topic.strip()) < 3:
        raise HTTPException(status_code=400, detail="El nombre de la colección debe ser una cadena de al menos 3 caracteres.")

    try:
        from core.memory_manager import create_empty_collection
        
        success = await create_empty_collection(
            account_id=current_account_id,
            topic_name=topic.strip(),
            description=description,
            workspace_id=workspace_id,
            team_id=team_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=f"La colección '{topic}' ya existe o no se pudo crear.")
        
        return {"message": f"Colección '{topic}' creada exitosamente."}
    except Exception as e:
        logger.error(f"Error al crear la colección para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear la colección.")

@router.post("/list-collections", summary="Listar las colecciones de conocimiento")
async def list_collections_endpoint(current_account_id: str = Depends(get_current_account_id)):
    """
    Devuelve una lista de todas las colecciones (temas) únicas de un usuario
    y el número de documentos en cada una.
    """
    collections = await list_user_collections(current_account_id)
    return collections

class DeleteCollectionRequest(BaseModel):
    """Define la estructura para eliminar una colección específica."""
    topic: str

@router.post("/delete-collection", summary="Eliminar una colección específica")
async def delete_collection_endpoint(
    request: DeleteCollectionRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina una colección específica y todos sus documentos asociados.
    """
    try:
        from core.memory_manager import delete_collection

        success = await delete_collection(
            account_id=current_account_id,
            topic_name=request.topic
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"La colección '{request.topic}' no se encontró o ya fue eliminada.")

        return {"message": f"Colección '{request.topic}' y todos sus documentos han sido eliminados."}
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Error al eliminar la colección '{request.topic}' para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al eliminar la colección.")

# TODO: Implementar endpoint específico para documentos por topic
# class ListDocumentsByTopicRequest(BaseModel):
#     """Define la estructura para obtener documentos de una colección específica."""
#     topic: str

# @router.post("/list-documents-by-topic", summary="Listar documentos de una colección específica")
# async def list_documents_by_topic_endpoint(
#     request: ListDocumentsByTopicRequest,
#     current_account_id: str = Depends(get_current_account_id),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Lista los documentos de una colección (topic) específica del usuario.
#     """
#     try:
#         documents = await list_documents_by_topic(current_account_id, request.topic)
#         return documents
#     except Exception as e:
#         logger.error(f"Error al listar documentos del topic '{request.topic}' para cuenta {current_account_id}: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error al obtener documentos de la colección.")

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
