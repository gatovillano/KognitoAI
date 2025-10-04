# api/documents.py

import logging
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from urllib.parse import unquote
import uuid

class ProfileLinkRequest(BaseModel):
    profile_id: uuid.UUID

class DeleteDocumentRequest(BaseModel):
    file_name: str
    topic: Optional[str] = None
    workspace_id: Optional[str] = None

from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile, Body, Query, Path, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, text, update
import asyncio

from core.database import SessionLocal, TeamMember, LangchainPgCollection, UploadTask, GitHubDocument, get_db_session
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, list_user_documents_all_teams, delete_document_chunks, get_full_document_content, update_document_metadata, list_user_collections, link_profile_to_collection, unlink_profile_from_collection, get_user_document_topic_by_name
from utils.db_session import DBSession
from tools.add_web_to_rag_tool import AddWebToRAGTool
from core.websocket_manager import send_personal_message
from core.tasks import process_upload_task, extract_titles_and_update_metadata, process_knowledge_graph

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

def decoded_topic(topic: str = Path(..., description="El tema de la colección, codificado en la URL")) -> str:
    return unquote(topic)




@router.post("/collections/{topic}/link-profile", summary="Vincular perfil a una colección")
async def link_profile_to_collection_endpoint(
    profile_link_request: ProfileLinkRequest,
    topic: str = Depends(decoded_topic),
    current_account_id: str = Depends(get_current_account_id),
    workspace_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None)
):
    """
    Vincula un perfil de contacto a una colección de documentos.
    """
    success = await link_profile_to_collection(
        account_id=current_account_id,
        topic_name=topic,
        profile_id=str(profile_link_request.profile_id), # Convertir a str
        workspace_id=workspace_id,
        team_id=team_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Colección o perfil no encontrado, o no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} vinculado a la colección {topic} correctamente."}

@router.post("/collections/{topic}/unlink-profile", summary="Desvincular perfil de una colección")
async def unlink_profile_from_collection_endpoint(
    profile_link_request: ProfileLinkRequest,
    topic: str = Depends(decoded_topic),
    current_account_id: str = Depends(get_current_account_id),
    workspace_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None)
):
    """
    Desvincula un perfil de contacto de una colección de documentos.
    """
    success = await unlink_profile_from_collection(
        account_id=current_account_id,
        topic_name=topic,
        profile_id=str(profile_link_request.profile_id), # Convertir a str
        workspace_id=workspace_id,
        team_id=team_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado, o colección/perfil no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} desvinculado de la colección {topic} correctamente."}


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

    # Añadir la tarea al fondo
    background_tasks.add_task(
        process_upload_task,
        str(new_task.id),
        current_account_id,
        file_data_list,
        topic,
        workspace_id
    )

    logger.info(f"Backend (process_upload_task): workspace_id = {workspace_id}")

    # Notificar al cliente que la subida ha comenzado
    await send_personal_message(
        current_account_id,
        {
            "type": "upload_started",
            "task_id": str(new_task.id),
            "file_names": file_names,
            "topic": topic,
            "created_at": new_task.created_at.isoformat()
        }
    )

    return {
        "task_id": str(new_task.id),
        "message": f"Subida de {len(files)} archivo(s) iniciada en segundo plano para la colección '{topic}'."
    }

@router.post("/upload-chat-document")
async def upload_chat_document_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(None),
):
    """
    Sube un documento para el contexto de un chat, lo procesa para RAG y lo devuelve.
    No se asigna a una colección (topic) específica, quedando como un documento flotante.
    """
    try:
        content_bytes = await file.read()
        file_name = file.filename or "documento_subido"

        # Extraer texto y metadatos
        extracted_text, metadata = extract_text_and_metadata_from_document(file_name, content_bytes)

        if not extracted_text:
            raise HTTPException(status_code=400, detail=f"No se pudo extraer texto del archivo '{file_name}'.")

        # Procesar para RAG sin un topic específico
        document_id = await process_document_for_rag(
            account_id=current_account_id,
            file_name=file_name,
            extracted_text=extracted_text,
            topic="chat",  # Usar un topic genérico para documentos de chat
            metadata={"original_filename": file_name},
            workspace_id=workspace_id
        )

        logger.info(f"Documento '{file_name}' (ID: {document_id}) subido al chat del workspace '{workspace_id}' por la cuenta {current_account_id}.")

        # Devolver la información necesaria para el frontend
        return {
            "id": document_id,
            "type": "document",
            "name": file_name,
            "title": file_name,
        }

    except Exception as e:
        logger.error(f"Error al subir documento de chat para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.get("/list-documents")
async def list_documents_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    topic: Optional[str] = Query(None), # Recibe el topic directamente
    workspace_id: Optional[str] = Query(None)
):
    """Lista los documentos subidos por el usuario, incluyendo documentos compartidos con equipos.
    Opcionalmente filtra por topic específico. Protegido por JWT."""
    account_id_uuid = uuid.UUID(current_account_id)
    topic_filter = topic # Ahora el topic ya viene directamente
    logger.info(f"DEBUG_API: list_documents_endpoint called with account_id={current_account_id}, topic_filter={topic_filter}, workspace_id={workspace_id}")
    
    # Usar list_user_documents para filtrar por workspace_id
    # Si workspace_id es None, list_user_documents listará documentos con workspace_id IS NULL
    # Si topic_filter es None, list_user_documents listará todos los topics para ese workspace_id
    
    documents = await list_user_documents(
        account_id=str(account_id_uuid),
        topic=topic_filter,
        workspace_id=workspace_id
    )
    
    logger.info(f"DEBUG_API: Documents found for account {current_account_id} (topic: {topic_filter}, workspace_id: {workspace_id}): {len(documents)} documents")
    
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
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session) # Añadido db dependency
):
    """
    Recupera el contenido textual completo de un documento específico.
    """
    # 1. Intentar recuperar de GitHubDocument primero
    try:
        query = select(GitHubDocument).where(
            GitHubDocument.account_id == uuid.UUID(current_account_id),
            GitHubDocument.file_path == request.file_name
        )
        result = await db.execute(query)
        github_doc = result.scalars().first()

        if github_doc:
            logger.info(f"Contenido de GitHubDocument encontrado para {request.file_name}.")
            return {"content": github_doc.content}
    except Exception as e:
        logger.error(f"Error al buscar en GitHubDocument para {request.file_name}: {e}", exc_info=True)
        # Continuar buscando en la base de datos vectorial si hay un error aquí

    # 2. Si no es un documento de GitHub o no se encontró, intentar recuperar de la base de datos vectorial
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

# --- Modelos Pydantic para Colecciones ---
class CollectionResponse(BaseModel):
    topic: str
    document_count: int
    description: Optional[str] = None
    team_shared: Optional[bool] = None
    has_knowledge_graph: Optional[bool] = None

class CollectionCreateRequest(BaseModel):
    topic: str
    description: Optional[str] = None
    workspaceId: Optional[str] = None # Añadido para recibir el workspaceId del frontend

class DocumentToCollectionRequest(BaseModel):
    document_id: str

class DocumentResponse(BaseModel):
    file_name: str
    topic: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    document_id: Optional[str] = None
    workspace_id: Optional[str] = None
    team_id: Optional[str] = None

# --- Endpoints para Colecciones ---
@router.get("/collections/{topic}/details", summary="Obtener detalles de una colección por nombre")
async def get_collection_details_by_name(
    current_account_id: str = Depends(get_current_account_id),
    topic: str = Depends(decoded_topic),
    workspace_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None)
):
    """
    Obtiene los detalles de una colección específica por su nombre, incluyendo los perfiles de contacto vinculados.
    """
    collection_details = await get_user_document_topic_by_name(
        account_id=current_account_id,
        topic_name=topic,
        workspace_id=workspace_id,
        team_id=team_id
    )
    if not collection_details:
        raise HTTPException(status_code=404, detail=f"Colección '{topic}' no encontrada o no autorizada.")
    return collection_details

@router.get("/collections/{collection_id}/documents", response_model=List[DocumentResponse], summary="Listar documentos de una colección")
async def list_collection_documents(collection_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db), workspace_id: Optional[str] = Query(None)):
    logger.info(f"API: list_collection_documents - collection_id: {collection_id}, account_id: {current_account_id}, workspace_id: {workspace_id}")
    try:
        decoded_collection_id = unquote(collection_id)
        logger.info(f"API: list_collection_documents - decoded_collection_id: {decoded_collection_id}")
 
        documents = await list_user_documents(account_id=current_account_id, workspace_id=workspace_id, topic=decoded_collection_id)
        logger.info(f"API: list_collection_documents - documents found: {len(documents)}")
        return [DocumentResponse(**doc) for doc in documents]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: list_collection_documents - Error al listar documentos de la colección '{decoded_collection_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al listar documentos de la colección.")

@router.get("/collections", response_model=List[CollectionResponse], summary="Listar colecciones del usuario")
async def list_collections(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db), workspace_id: Optional[str] = Query(None)):
    logger.info(f"API: list_collections - Listando colecciones para account_id: {current_account_id}, workspace_id recibido: {workspace_id}")
    try:
        collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
        logger.info(f"API: list_collections - Collections retrieved from memory_manager: {collections}")
        return [CollectionResponse(
            topic=c['topic'],
            document_count=c['document_count'],
            description=c.get('description'),
            team_shared=c.get('team_shared'),
            has_knowledge_graph=c.get('has_knowledge_graph')
        ) for c in collections]
    except Exception as e:
        logger.error(f"API: list_collections - Error al listar colecciones para account_id: {current_account_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor al listar colecciones.")
 
@router.post("/collections", status_code=status.HTTP_201_CREATED, summary="Crear una nueva colección")
async def create_collection(request: CollectionCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    logger.info(f"API: create_collection - Petición para crear colección: {request.topic}, description: {request.description}, workspaceId: {request.workspaceId}, account: {current_account_id}")
    from core.memory_manager import create_empty_collection
    success = await create_empty_collection(
        account_id=current_account_id,
        topic_name=request.topic,
        description=request.description,
        workspace_id=request.workspaceId
    )
    if not success:
        logger.error(f"API: create_collection - No se pudo crear la colección o ya existe: {request.topic}")
        raise HTTPException(status_code=400, detail="No se pudo crear la colección o ya existe.")
    logger.info(f"API: create_collection - Colección '{request.topic}' creada y asociada al workspace {request.workspaceId if request.workspaceId else 'global'} con éxito.")
    return {"message": f"Colección '{request.topic}' creada y lista para ser usada en el workspace {request.workspaceId if request.workspaceId else 'global'}."}
 
@router.post("/collections/{collection_id}/associate", status_code=status.HTTP_200_OK, summary="Asociar una colección existente a un workspace")
async def associate_collection_to_workspace(collection_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db), workspace_id: Optional[str] = Query(None)):
    logger.info(f"API: associate_collection_to_workspace - collection_id: {collection_id}, account_id: {current_account_id}, workspace_id: {workspace_id}")
    from core.memory_manager import update_collection_workspace
    
    if not workspace_id:
        logger.error("API: associate_collection_to_workspace - Se requiere un workspace_id para asociar una colección.")
        raise HTTPException(status_code=400, detail="Se requiere un workspace_id para asociar una colección.")
    
    decoded_collection_id = unquote(collection_id)
    logger.info(f"API: associate_collection_to_workspace - decoded_collection_id: {decoded_collection_id}")
    success = await update_collection_workspace(current_account_id, decoded_collection_id, workspace_id)
    if not success:
        logger.error(f"API: associate_collection_to_workspace - Colección no encontrada o no se pudo asociar al workspace: {decoded_collection_id}")
        raise HTTPException(status_code=404, detail="Colección no encontrada o no se pudo asociar al workspace.")
    
    logger.info(f"API: associate_collection_to_workspace - Colección '{decoded_collection_id}' asociada al workspace con éxito.")
    return {"message": f"Colección '{decoded_collection_id}' asociada al workspace con éxito.", "id": decoded_collection_id, "workspace_id": workspace_id}
 
@router.post("/collections/{topic}/documents", status_code=status.HTTP_201_CREATED, summary="Añadir un documento a una colección")
async def add_document_to_collection(
    file: UploadFile = File(...),
    topic: str = Depends(decoded_topic),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    workspace_id: Optional[str] = Query(None)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="El nombre del archivo no puede estar vacío.")
 
    logger.info(f"API: add_document_to_collection - topic: {topic}, file_name: {file.filename}, account_id: {current_account_id}, workspace_id: {workspace_id}")
    
    # Leer el contenido del archivo
    file_content = await file.read()
    
    # Llamar a la función de procesamiento de documentos
    await process_document_for_rag(
        file_name=file.filename,
        extracted_text=file_content.decode('utf-8'), # Asumimos UTF-8, ajustar si es necesario
        account_id=current_account_id,
        topic=topic,
        workspace_id=workspace_id
    )
    logger.info(f"Documento '{file.filename}' subido y procesado exitosamente en la colección '{topic}' para el workspace '{workspace_id}'.")
    return {"message": f"Documento {file.filename} añadido a la colección '{topic}'."}
 
@router.post("/extract-title", summary="Extraer títulos de documentos y actualizar metadatos")
async def extract_titles_endpoint(request: ExtractTitleRequest, background_tasks: BackgroundTasks, current_account_id: str = Depends(get_current_account_id)):
    """
    Activa la herramienta para extraer títulos de documentos y actualizar sus metadatos en la base de conocimiento del usuario.
    El proceso se ejecuta en segundo plano y devuelve una respuesta inmediata indicando que está en curso.
    Puede aplicarse a una colección completa (por tema) o a un documento individual (por nombre de archivo).
    """
    logger.info(f"Iniciando extracción de títulos para la cuenta: {current_account_id}, tema: {request.topic}, archivo: {request.file_name}.")
    try:
        background_tasks.add_task(
            extract_titles_and_update_metadata,
            account_id=current_account_id,
            topic=request.topic,
            workspace_id=None,
            team_id=None,
            file_name=request.file_name
        )
        return {"message": "El proceso de extracción de títulos ha comenzado en segundo plano. Recibirás una actualización una vez que finalice."}
    except Exception as e:
        logger.error(f"Error al iniciar la extracción de títulos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al iniciar la extracción de títulos: {str(e)}")
 
@router.post("/process-knowledge-graph")
async def process_knowledge_graph_endpoint(
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    topic: Optional[str] = None
):
    """Inicia el procesamiento de grafos de conocimiento en segundo plano."""
    try:
        background_tasks.add_task(
            process_knowledge_graph,
            account_id=current_account_id,
            topic=topic
        )
        return {
            "message": "Procesamiento de grafo de conocimiento iniciado en segundo plano.",
            "topic": topic or "todos"
        }
    except Exception as e:
        logger.error(f"Error al iniciar el procesamiento de grafo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al iniciar el procesamiento del grafo de conocimiento: {str(e)}")


class DeleteFolderRequest(BaseModel):
    repo_name: str
    folder_path: str
    repo_url: str # Añadido para identificar el repositorio de forma única
    workspace_id: Optional[str] = None

@router.post("/github/delete-folder")
async def delete_folder_endpoint(
    request: DeleteFolderRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Received delete folder request for repo: '{request.repo_name}', folder: '{request.folder_path}', workspace: '{request.workspace_id}' from account: {current_account_id}")

    account_id_uuid = uuid.UUID(current_account_id)
    
    folder_prefix = request.folder_path
    if folder_prefix and not folder_prefix.endswith('/'):
        folder_prefix += '/'

    # Importar delete_document_chunks desde core.memory_manager
    from core.memory_manager import delete_document_chunks

    success = await delete_document_chunks(
        account_id=str(account_id_uuid),
        file_name_prefix=folder_prefix, # Usar el nuevo parámetro
        workspace_id=request.workspace_id,
        repo_url=request.repo_url # Pasar el repo_url
    )

    if not success:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada o ya eliminada.")
    return {"message": f"La carpeta '{request.folder_path}' y sus contenidos han sido eliminados."}