# api/documents.py

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile, Body
from pydantic import BaseModel
from sqlalchemy import select, text

from core.database import SessionLocal, TeamMember, LangchainPgCollection
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, list_user_documents_all_teams, delete_document_chunks, get_full_document_content, update_document_metadata, list_user_collections, extract_titles_and_update_metadata
from utils.db_session import DBSession
from tools.add_web_to_rag_tool import AddWebToRAGTool

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

@router.post("/list-documents")
async def list_documents_endpoint(
    request: Optional[ListDocumentsRequest] = Body(None),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Lista los documentos subidos por el usuario, incluyendo documentos compartidos con equipos.
    Opcionalmente filtra por topic específico. Protegido por JWT."""
    account_id_uuid = uuid.UUID(current_account_id)
    topic_filter = request.topic if request else None
    
    # Obtener TODOS los documentos del usuario (incluyendo compartidos y no compartidos)
    # Para la vista personal, el usuario debe ver todos sus documentos independientemente del team_id
    all_user_docs = await list_user_documents_all_teams(str(account_id_uuid), topic=topic_filter)
    logger.info(f"All user documents for account {current_account_id} (topic: {topic_filter}): {len(all_user_docs)} documents found")

    combined_docs_list = all_user_docs
    
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

class UpdateCollectionRequest(BaseModel):
    """Define la estructura para actualizar una colección específica."""
    old_topic: str
    new_topic: Optional[str] = None
    new_description: Optional[str] = None
    workspace_id: Optional[str] = None
    team_id: Optional[str] = None

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

@router.post("/update-collection", summary="Actualizar metadatos de una colección")
async def update_collection_endpoint(
    request: UpdateCollectionRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza los metadatos de una colección (nombre y/o descripción).
    """
    try:
        from core.memory_manager import update_collection_metadata

        success = await update_collection_metadata(
            account_id=current_account_id,
            old_topic_name=request.old_topic,
            new_topic_name=request.new_topic,
            new_description=request.new_description,
            workspace_id=request.workspace_id,
            team_id=request.team_id
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"La colección '{request.old_topic}' no se encontró o no se pudo actualizar.")

        return {"message": f"Colección actualizada exitosamente."}
    except Exception as e:
        logger.error(f"Error al actualizar la colección para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar la colección.")

@router.post("/list-collections", summary="Listar las colecciones de conocimiento")
async def list_collections_endpoint(current_account_id: str = Depends(get_current_account_id)):
    """
    Devuelve una lista de todas las colecciones (temas) únicas de un usuario
    y el número de documentos en cada una.
    """
    collections = await list_user_collections(current_account_id)
    return collections

@router.post("/list-general-collections", summary="Listar solo las colecciones del contexto general")
async def list_general_collections_endpoint(current_account_id: str = Depends(get_current_account_id)):
    """
    Devuelve una lista de las colecciones del contexto general (sin workspace_id)
    que pueden ser asociadas a workspaces.
    """
    # Obtener solo colecciones del contexto general (sin workspace_id)
    collections = await list_user_collections(current_account_id, workspace_id=None)

    # Filtrar para asegurar que solo devolvemos colecciones sin workspace_id
    general_collections = []
    for collection in collections:
        # Verificar que la colección realmente no tenga workspace_id en la base de datos
        if collection.get('document_count', 0) > 0:  # Solo colecciones con documentos
            general_collections.append(collection)

    return general_collections

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

class AddWebRequest(BaseModel):
    url: str
    topic: str
    workspace_id: Optional[str] = None
    custom_title: Optional[str] = None

@router.post("/add-web-to-rag", summary="Añadir contenido web a la base de conocimiento")
async def add_web_to_rag_endpoint(
    request: AddWebRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Endpoint para añadir contenido de una URL directamente a la base de conocimiento del usuario.
    Extrae el contenido web, lo procesa y lo almacena en la base vectorial.
    """
    try:
        # Crear instancia de la herramienta
        tool = AddWebToRAGTool()

        # Ejecutar la herramienta
        result = await tool._arun(
            url=request.url,
            topic=request.topic,
            account_id=current_account_id,
            workspace_id=request.workspace_id,
            custom_title=request.custom_title
        )

        # Verificar si fue exitoso
        if result.startswith("✅"):
            return {"success": True, "message": result}
        else:
            return {"success": False, "message": result}

    except Exception as e:
        logger.error(f"Error en add_web_to_rag_endpoint para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar la URL: {str(e)}")
