# api/documents.py

import logging
import uuid
from typing import List, Optional
from pydantic import BaseModel # Importar BaseModel

class DeleteDocumentRequest(BaseModel):
    file_name: str
    topic: Optional[str] = None
    workspace_id: Optional[str] = None


from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile, Body, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, text, update
import asyncio

from core.database import SessionLocal, TeamMember, LangchainPgCollection, UploadTask
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, list_user_documents_all_teams, delete_document_chunks, get_full_document_content, update_document_metadata, list_user_collections, extract_titles_and_update_metadata
from utils.db_session import DBSession
from tools.add_web_to_rag_tool import AddWebToRAGTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

from typing import AsyncGenerator
# ...
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def process_upload_task(task_id: str, account_id: str, file_data_list: List[dict], topic: str, workspace_id: Optional[str] = None):
    """Función que procesa la subida de documentos en segundo plano."""
    async with SessionLocal() as db_session:
        try:
            # 1. Marcar la tarea como 'processing'
            stmt_processing = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                status="processing",
                progress=0
            )
            await db_session.execute(stmt_processing)
            await db_session.commit()

            logger.info(f"Iniciando procesamiento de subida para tarea {task_id}...")

            processed_files = 0
            total_files = len(file_data_list)

            for i, file_data in enumerate(file_data_list):
                try:
                    # Actualizar progreso
                    progress = int((i / total_files) * 90)  # Hasta 90% durante el procesamiento
                    stmt_progress = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                        progress=progress
                    )
                    await db_session.execute(stmt_progress)
                    await db_session.commit()

                    # Procesar el archivo
                    file_name_str = file_data['filename'] if file_data['filename'] is not None else "unknown_file"
                    extracted_text, metadata = extract_text_and_metadata_from_document(
                        file_name_str,
                        file_data['content']
                    )

                    if not extracted_text:
                        logger.warning(f"No se pudo extraer texto del archivo '{file_data['filename']}'. Omitiendo.")
                        continue

                    await process_document_for_rag(
                        account_id=account_id,
                        file_name=file_name_str,
                        extracted_text=extracted_text,
                        topic=topic,
                        metadata={"original_filename": file_name_str},
                        workspace_id=workspace_id
                    )
                    processed_files += 1

                except Exception as e:
                    logger.error(f"Error al procesar archivo {file_data['filename']}: {e}", exc_info=True)

            # 2. Marcar la tarea como completada
            result_payload = {
                "processed_files": processed_files,
                "total_files": total_files,
                "topic": topic,
                "message": f"{processed_files}/{total_files} archivo(s) procesado(s) y añadido(s) a la colección '{topic}'."
            }

            stmt_completed = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                status="completed",
                progress=100,
                result_payload=result_payload
            )
            await db_session.execute(stmt_completed)
            await db_session.commit()

            logger.info(f"Tarea de subida {task_id} completada exitosamente.")

        except Exception as e:
            logger.error(f"Error en la tarea de subida {task_id}: {e}", exc_info=True)
            # Marcar la tarea como fallida
            stmt_failed = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                status="failed",
                error_message=str(e)
            )
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/upload-document")
async def upload_document_endpoint(
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    files: List[UploadFile] = File(...),
    topic: str = Form(...),
    workspace_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Inicia una tarea de subida de documentos y devuelve un ID de tarea."""
    account_id_uuid = uuid.UUID(current_account_id)

    # Leer y almacenar los datos de los archivos
    file_data_list = []
    file_names = []

    for file in files:
        try:
            content_bytes = await file.read()
            file_data_list.append({
                'filename': file.filename,
                'content': content_bytes
            })
            file_names.append(file.filename)
        except Exception as e:
            logger.error(f"Error al leer archivo {file.filename}: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Error al leer archivo {file.filename}")

    if not file_data_list:
        raise HTTPException(status_code=400, detail="No se pudieron leer los archivos.")

    # Crear la tarea de subida
    new_task = UploadTask(
        account_id=account_id_uuid,
        file_names=file_names,
        topic=topic,
        workspace_id=workspace_id,
        status="pending",
        progress=0
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Iniciar la tarea en segundo plano
    background_tasks.add_task(
        process_upload_task,
        str(new_task.id),
        current_account_id,
        file_data_list,
        topic,
        workspace_id
        
    )

    logger.info(f"Backend (process_upload_task): workspace_id = {workspace_id}")

    return {
        "task_id": str(new_task.id),
        "message": f"Subida de {len(files)} archivo(s) iniciada en segundo plano para la colección '{topic}'."
    }

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
            file_name_str = file.filename if file.filename is not None else "unknown_file"
            extracted_text, metadata = extract_text_and_metadata_from_document(file_name_str, content_bytes)
            if not extracted_text:
                logger.warning(f"No se pudo extraer texto del archivo '{file.filename}'. Omitiendo.")
                continue

            # Añadir metadato para indicar que es un documento de chat y no debe guardarse en colecciones permanentes
            metadata['chat_context_only'] = True
            metadata['thread_id'] = thread_id
            metadata['temporary'] = True  # Marca para indicar que es temporal y solo para el contexto del chat

            await process_document_for_rag(
                account_id=str(account_id_uuid),
                file_name=file_name_str,
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

@router.post("/list-documents")
async def list_documents_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    topic: Optional[str] = Body(None), # Recibe el topic directamente
    workspace_id: Optional[str] = Body(None)
):
    """Lista los documentos subidos por el usuario, incluyendo documentos compartidos con equipos.
    Opcionalmente filtra por topic específico. Protegido por JWT."""
    account_id_uuid = uuid.UUID(current_account_id)
    topic_filter = topic # Ahora el topic ya viene directamente
    logger.info(f"list_documents_endpoint called with account_id={current_account_id}, topic_filter={topic_filter}, workspace_id={workspace_id}")
    
    # Usar list_user_documents para filtrar por workspace_id
    # Si workspace_id es None, list_user_documents listará documentos con workspace_id IS NULL
    # Si topic_filter es None, list_user_documents listará todos los topics para ese workspace_id
    
    documents = await list_user_documents(
        account_id=str(account_id_uuid),
        topic=topic_filter,
        workspace_id=workspace_id
    )
    
    logger.info(f"Documents found for account {current_account_id} (topic: {topic_filter}, workspace_id: {workspace_id}): {len(documents)} documents")
    
    return documents

@router.post("/list-all-user-documents")
async def list_all_user_documents_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Lista TODOS los documentos subidos por el usuario, ignorando el workspace_id y el topic.
    Protegido por JWT. Utiliza list_user_documents_all_teams."""
    account_id_uuid = uuid.UUID(current_account_id)
    logger.info(f"list_all_user_documents_endpoint called for account_id={current_account_id}")
    
    all_user_docs = await list_user_documents_all_teams(str(account_id_uuid))
    logger.info(f"All user documents for account {current_account_id}: {len(all_user_docs)} documents found")

    return all_user_docs

@router.post("/delete-document")
async def delete_document_endpoint(
    request: DeleteDocumentRequest, # Cambiado a Request Body
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Elimina documentos de la base de conocimiento del usuario. Protegido por JWT."""
    logger.info(f"Received delete request for file_name: '{request.file_name}', topic: '{request.topic}', workspace_id: '{request.workspace_id}' from account: {current_account_id}")
    logger.info(f"Delete request parameters (from JSON): file_name='{request.file_name}', topic='{request.topic}', workspace_id='{request.workspace_id}'")
    if not request.file_name or request.file_name.strip() == "":
        logger.warning(f"Validation failed: file_name is empty for account: {current_account_id}")
        raise HTTPException(status_code=422, detail="El nombre del archivo no puede estar vacío.")
    account_id_uuid = uuid.UUID(current_account_id)
    success = await delete_document_chunks(
        account_id=str(account_id_uuid),
        file_name=request.file_name,
        topic=request.topic, # Pasado a delete_document_chunks
        workspace_id=request.workspace_id # Pasado a delete_document_chunks
    )
    if not success: raise HTTPException(status_code=404, detail="Documento no encontrado o ya eliminado.")
    return {"message": f"El documento '{request.file_name}' ha sido eliminado."}

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
        tool = ExtractDocumentTitlesTool(account_id=current_account_id)
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

    # Devolver todas las colecciones del contexto general (incluidas las vacías)
    # Las colecciones vacías también pueden ser útiles para asociar a workspaces
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
        tool = AddWebToRAGTool(account_id=current_account_id)

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

@router.get("/upload-tasks")
async def get_upload_tasks_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene todas las tareas de subida del usuario."""
    try:
        stmt = select(UploadTask).where(UploadTask.account_id == uuid.UUID(current_account_id)).order_by(UploadTask.created_at.desc())
        result = await db.execute(stmt)
        tasks = result.scalars().all()

        return [
            {
                "id": str(task.id),
                "status": task.status,
                "file_names": task.file_names,
                "topic": task.topic,
                "workspace_id": task.workspace_id,
                "progress": task.progress,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            }
            for task in tasks
        ]
    except Exception as e:
        logger.error(f"Error al obtener tareas de subida para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener las tareas de subida.")

@router.get("/upload-task/{task_id}")
async def get_upload_task_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el estado de una tarea de subida específica."""
    try:
        task = await db.get(UploadTask, uuid.UUID(task_id))
        if not task or str(task.account_id) != current_account_id:
            raise HTTPException(status_code=404, detail="Tarea no encontrada.")

        return {
            "id": str(task.id),
            "status": task.status,
            "file_names": task.file_names,
            "topic": task.topic,
            "workspace_id": task.workspace_id,
            "progress": task.progress,
            "result": task.result_payload,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de tarea inválido.")
    except Exception as e:
        logger.error(f"Error al obtener tarea de subida {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener la tarea de subida.")

@router.post("/process-knowledge-graph")
async def process_knowledge_graph_endpoint(
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    topic: Optional[str] = None
):
    """Procesa todos los documentos del usuario para crear grafos de conocimiento con Cognee."""
    try:
        from tools.cognee_knowledge_graph_tool import CogneeKnowledgeGraphTool
        from core.memory_manager import list_user_documents

        # Obtener documentos del usuario
        if topic:
            documents = await list_user_documents(current_account_id, topic=topic)
        else:
            documents = await list_user_documents(current_account_id)

        if not documents:
            return {"message": "No se encontraron documentos para procesar."}

        # Preparar documentos para Cognee
        cognee_documents = []
        for doc in documents:
            cognee_documents.append({
                "content": doc.get("content", ""),
                "title": doc.get("file_name", "Documento sin título"),
                "metadata": {
                    "file_name": doc.get("file_name"),
                    "topic": doc.get("topic"),
                    "account_id": current_account_id
                }
            })

        # Ejecutar procesamiento en segundo plano
        async def process_in_background():
            try:
                tool = CogneeKnowledgeGraphTool(account_id=current_account_id)
                import json
                tool_input = {
                    "action": "process_documents",
                    "documents": cognee_documents,
                    "dataset_name": f"kognito_{current_account_id}"
                }
                result = await tool._arun(
                    tool_input_json=json.dumps(tool_input)
                )
                logger.info(f"Procesamiento de grafo completado para {current_account_id}: {result}")
            except Exception as e:
                logger.error(f"Error en procesamiento de grafo para {current_account_id}: {e}", exc_info=True)

        background_tasks.add_task(process_in_background)

        return {
            "message": f"Procesamiento de grafo de conocimiento iniciado para {len(cognee_documents)} documentos.",
            "documents_count": len(cognee_documents),
            "topic": topic or "todos"
        }

    except Exception as e:
        logger.error(f"Error al iniciar procesamiento de grafo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al iniciar el procesamiento del grafo de conocimiento.")
