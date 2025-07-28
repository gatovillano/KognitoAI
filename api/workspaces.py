# api/workspaces.py

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, AsyncGenerator, cast
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Depends, status, Query, Form, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select

from core.database import SessionLocal, Workspace, ChatThread
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.agent import create_thread_for_account, force_update_thread_title
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from core.config import settings
from core.memory_manager import list_user_collections, list_user_documents, process_document_for_rag # Importar process_document_for_rag

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:  # type: ignore
        try:
            yield session
        finally:
            await session.close()

# --- Modelos Pydantic para Workspaces ---
class WorkspaceResponse(BaseModel):
    id: str
    name: str
    system_prompt: Optional[str]
    created_at: datetime

class WorkspaceCreateRequest(BaseModel):
    name: str
    system_prompt: Optional[str] = None

class WorkspaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None

# --- Endpoints para Workspaces ---
@router.get("/workspaces", response_model=List[WorkspaceResponse], summary="Listar workspaces del usuario")
async def list_workspaces(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    stmt = select(Workspace).where(Workspace.account_id == uuid.UUID(current_account_id)).order_by(Workspace.created_at.desc())
    result = await db.execute(stmt)
    workspaces = result.scalars().all()
    return [WorkspaceResponse(id=str(w.id), name=w.name, system_prompt=w.system_prompt, created_at=w.created_at) for w in workspaces]  # type: ignore

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Obtener detalles de un workspace")
async def get_workspace(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, created_at=workspace.created_at)  # type: ignore

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo workspace")
async def create_workspace(request: WorkspaceCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    new_workspace = Workspace(
        account_id=uuid.UUID(current_account_id),
        name=request.name,
        system_prompt=request.system_prompt
    )
    db.add(new_workspace)
    await db.commit()
    await db.refresh(new_workspace)
    return WorkspaceResponse(id=str(new_workspace.id), name=new_workspace.name, system_prompt=new_workspace.system_prompt, created_at=new_workspace.created_at)  # type: ignore

@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Actualizar un workspace")
async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    
    if request.name is not None:
        setattr(workspace, 'name', request.name)
    if request.system_prompt is not None:
        setattr(workspace, 'system_prompt', request.system_prompt)
        
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, created_at=workspace.created_at)  # type: ignore

@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un workspace")
async def delete_workspace(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    
    await db.delete(workspace)
    await db.commit()
    return

# --- Modelos Pydantic para Colecciones ---
class CollectionResponse(BaseModel):
    id: str
    name: str
    document_count: int

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
@router.get("/collections/{collection_id}", response_model=CollectionResponse, summary="Obtener detalles de una colección")
async def get_collection_details(collection_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db), workspace_id: Optional[str] = Query(None)):
    logger.info(f"API: get_collection_details - collection_id: {collection_id}, account_id: {current_account_id}, workspace_id: {workspace_id}")
    
    decoded_collection_id = unquote(collection_id)
    logger.info(f"API: get_collection_details - decoded_collection_id: {decoded_collection_id}")
    
    collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
    logger.info(f"API: get_collection_details - collections found: {len(collections)}")
    
    collection = None
    for c in collections:
        if c.get('topic') == decoded_collection_id:
            collection = c
            break
            
    if not collection:
        logger.warning(f"API: get_collection_details - Colección '{decoded_collection_id}' no encontrada.")
        logger.warning(f"API: get_collection_details - Colección '{decoded_collection_id}' no encontrada para la cuenta {current_account_id} y workspace {workspace_id}.")
        raise HTTPException(status_code=404, detail=f"Colección '{decoded_collection_id}' no encontrada.")
    
    logger.info(f"API: get_collection_details - Returning collection: {collection}")
    return CollectionResponse(id=collection['topic'], name=collection['topic'], document_count=collection['document_count'])
 
@router.get("/collections/{collection_id}/documents", response_model=List[DocumentResponse], summary="Listar documentos de una colección")
async def list_collection_documents(collection_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db), workspace_id: Optional[str] = Query(None)):
    logger.info(f"API: list_collection_documents - collection_id: {collection_id}, account_id: {current_account_id}, workspace_id: {workspace_id}")
    try:
        decoded_collection_id = unquote(collection_id)
        logger.info(f"API: list_collection_documents - decoded_collection_id: {decoded_collection_id}")
 
        documents = await list_user_documents(account_id=current_account_id, workspace_id=workspace_id, topic=decoded_collection_id)
        logger.info(f"API: list_collection_documents - documents found: {len(documents)}")
        return [DocumentResponse(**doc) for doc in documents]
    except Exception as e:
        logger.error(f"API: Error listando documentos de la colección '{collection_id}' para workspace {workspace_id}: {e}", exc_info=True)
        # En lugar de 500, devolver una lista vacía si no hay documentos
        return []
@router.get("/collections", response_model=List[CollectionResponse], summary="Listar colecciones del usuario")
async def list_collections(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db), workspace_id: Optional[str] = Query(None)):
    logger.info(f"API: list_collections - Listando colecciones para account_id: {current_account_id}, workspace_id recibido: {workspace_id}")
    collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
    logger.info(f"API: list_collections - Collections retrieved from memory_manager: {collections}")
    return [CollectionResponse(id=c['topic'], name=c['topic'], document_count=c['document_count']) for c in collections]
 
@router.post("/collections", status_code=status.HTTP_201_CREATED, summary="Crear una nueva colección")
async def create_collection(request: CollectionCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)): # Eliminado Query(None) para workspace_id
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
    topic: str,
    file: UploadFile = File(...),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    workspace_id: Optional[str] = Query(None)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="El nombre del archivo no puede estar vacío.")

    logger.info(f"API: add_document_to_collection - topic: {topic}, file_name: {file.filename}, account_id: {current_account_id}, workspace_id: {workspace_id}")
    
    # Decodificar el topic si viene codificado en la URL
    decoded_topic = unquote(topic)

    # Leer el contenido del archivo
    file_content = await file.read()
    
    # Llamar a la función de procesamiento de documentos
    await process_document_for_rag(
        file_name=file.filename,
        extracted_text=file_content.decode('utf-8'), # Asumimos UTF-8, ajustar si es necesario
        account_id=current_account_id,
        topic=decoded_topic,
        workspace_id=workspace_id
    )
    logger.info(f"Documento '{file.filename}' subido y procesado exitosamente en la colección '{decoded_topic}' para el workspace '{workspace_id}'.")
    return {"message": f"Documento {file.filename} añadido a la colección '{decoded_topic}'."}

@router.put("/collections/{collection_id}", response_model=CollectionResponse, summary="Actualizar metadatos de una colección (renombrar)")
async def update_collection(
    collection_id: str,
    request: CollectionCreateRequest, # Reutilizar para new_topic y description
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    workspace_id: Optional[str] = Query(None)
):
    from core.memory_manager import update_collection_metadata
    
    decoded_collection_id = unquote(collection_id)
    
    success = await update_collection_metadata(
        account_id=current_account_id,
        old_topic_name=decoded_collection_id,
        new_topic_name=request.topic,
        new_description=request.description,
        workspace_id=workspace_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Colección no encontrada o no se pudo actualizar.")
        
    # Devolver la información actualizada de la colección
    collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
    collection = next((c for c in collections if c.get('topic') == request.topic), None)
    
    if not collection:
        raise HTTPException(status_code=500, detail="Error al recuperar la colección actualizada.")
        
    return CollectionResponse(id=collection['topic'], name=collection['topic'], document_count=collection['document_count'])

@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una colección")
async def delete_collection(
    collection_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    workspace_id: Optional[str] = Query(None)
):
    from core.memory_manager import delete_collection
    
    decoded_collection_id = unquote(collection_id)
    
    success = await delete_collection(
        account_id=current_account_id,
        topic_name=decoded_collection_id,
        workspace_id=workspace_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Colección no encontrada o no se pudo eliminar.")
    
    return

@router.put("/collections/{collection_id}", summary="Actualizar metadatos de una colección")
async def update_collection_api(
    collection_id: str,
    request: CollectionCreateRequest, # Reutilizamos CollectionCreateRequest para nombre y descripción
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    workspace_id: Optional[str] = Query(None)
):
    logger.info(f"PUT /collections/{collection_id} - Petición recibida. decoded_collection_id='{unquote(collection_id)}', workspace_id='{workspace_id}', new_topic_name='{request.topic}', new_description='{request.description}'")
    from core.memory_manager import update_collection_metadata
    decoded_collection_id = unquote(collection_id)
    
    success = await update_collection_metadata(
        account_id=current_account_id,
        old_topic_name=decoded_collection_id,
        new_topic_name=request.topic,
        new_description=request.description,
        workspace_id=workspace_id
    )
    logger.info(f"PUT /collections/{collection_id} - Resultado de update_collection_metadata: {success}")
    if not success:
        logger.warning(f"PUT /collections/{collection_id} - Falló la actualización. Colección no encontrada o no se pudo actualizar.")
        raise HTTPException(status_code=404, detail="Colección no encontrada o no se pudo actualizar.")
    
    logger.info(f"PUT /collections/{collection_id} - Colección actualizada con éxito.")
    # Devolver la información actualizada de la colección si la operación fue exitosa
    # Esto asegura que el frontend pueda actualizar su estado correctamente.
    collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
    collection = next((c for c in collections if c.get('topic') == request.topic), None)
    
    if not collection:
        logger.error(f"PUT /collections/{collection_id} - Error al recuperar la colección actualizada después de la actualización exitosa.")
        raise HTTPException(status_code=500, detail="Error al recuperar la colección actualizada.")
        
    return CollectionResponse(id=collection['topic'], name=collection['topic'], document_count=collection['document_count'])


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una colección")
async def delete_collection_api(
    collection_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    workspace_id: Optional[str] = Query(None)
):
    logger.info(f"DELETE /collections/{collection_id} - Petición recibida. decoded_collection_id='{unquote(collection_id)}', workspace_id='{workspace_id}'")
    from core.memory_manager import delete_collection
    decoded_collection_id = unquote(collection_id)
    
    success = await delete_collection(
        account_id=current_account_id,
        topic_name=decoded_collection_id,
        workspace_id=workspace_id
    )
    logger.info(f"DELETE /collections/{collection_id} - Resultado de delete_collection: {success}")
    if not success:
        logger.warning(f"DELETE /collections/{collection_id} - Falló la eliminación. Colección no encontrada o no se pudo eliminar.")
        raise HTTPException(status_code=404, detail="Colección no encontrada o no se pudo eliminar.")
    
    logger.info(f"DELETE /collections/{collection_id} - Colección eliminada con éxito.")
    return # Retorna 204 No Content por defecto si no hay HTTPException

# --- Modelos Pydantic para Hilos de Chat ---
class ThreadResponse(BaseModel):
    """Define la estructura de datos para la respuesta de un hilo de chat."""
    id: str
    title: str
    created_at: datetime
    workspace_id: Optional[str] = None

class MessageResponse(BaseModel):
    """Define la estructura de datos para un mensaje individual en el chat."""
    text: str  # antes 'content'
    sender: str  # antes 'type', valores: 'human' o 'ai'
    created_at: datetime
    image_base64: Optional[str] = None  # Campo para imágenes en base64
    document_url: Optional[str] = None  # Campo para URL de documentos

@router.get("/threads", response_model=List[ThreadResponse], summary="Listar hilos de chat del usuario")
async def list_chat_threads(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    workspace_id: Optional[str] = Query(None, description="ID del workspace para filtrar hilos. Si es 'global_context', se muestran hilos sin workspace. Si se omite, se muestran todos.")
):
    """
    Lista los hilos de chat de un usuario.
    - Si se proporciona workspace_id, filtra por ese workspace.
    - Si workspace_id es "global_context", muestra solo los hilos sin workspace.
    - Si no se proporciona workspace_id (default), muestra todos los hilos.
    """
    account_uuid = uuid.UUID(current_account_id)
    logger.info(f"Listando hilos para cuenta: {account_uuid}, workspace: {workspace_id}")
    
    stmt = select(ChatThread).where(ChatThread.account_id == account_uuid)
    
    if workspace_id == "global_context":
        stmt = stmt.where(ChatThread.workspace_id.is_(None))
    elif workspace_id:
        try:
            workspace_uuid = uuid.UUID(workspace_id)
            stmt = stmt.where(ChatThread.workspace_id == workspace_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="workspace_id inválido.")
    # Si workspace_id es None, no se añade filtro, mostrando todos los hilos.
        
    stmt = stmt.order_by(ChatThread.created_at.desc())
    result = await db.execute(stmt)
    threads = result.scalars().all()
    
    return [ThreadResponse(
        id=str(t.id),
        title=cast(str, t.title),
        created_at=cast(datetime, t.created_at),
        workspace_id=str(t.workspace_id) if t.workspace_id is not None else None
    ) for t in threads]

class ThreadCreateRequest(BaseModel):
    workspace_id: Optional[str] = None

@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo hilo de chat")
async def create_new_thread(
    request: ThreadCreateRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo hilo de chat para el usuario autenticado.
    """
    logger.info(f"Creando nuevo hilo de chat para la cuenta: {current_account_id} en workspace: {request.workspace_id}")
    try:
        account_uuid = uuid.UUID(current_account_id)
    except ValueError:
        logger.error(f"Invalid UUID for account_id: {current_account_id}")
        raise HTTPException(status_code=422, detail="Invalid account ID format.")

    workspace_uuid = None
    if request.workspace_id:
        try:
            workspace_uuid = uuid.UUID(request.workspace_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="workspace_id inválido.")

    new_thread = ChatThread(
        account_id=account_uuid,
        platform="web",
        workspace_id=workspace_uuid
    )
    db.add(new_thread)
    await db.commit()
    await db.refresh(new_thread)

    return ThreadResponse(
        id=str(new_thread.id),
        title=cast(str, new_thread.title),
        created_at=cast(datetime, new_thread.created_at),
        workspace_id=str(new_thread.workspace_id) if new_thread.workspace_id is not None else None
    )

@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse], summary="Obtener mensajes de un hilo de chat")
async def get_thread_messages(
    thread_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el historial de mensajes para un hilo de chat específico.
    """
    logger.info(f"Obteniendo mensajes para el hilo: {thread_id} de la cuenta: {current_account_id}")

    # Verificar que el hilo pertenzca a la cuenta actual
    thread_exists = await db.scalar(
        select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id))
    )
    if not thread_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hilo de chat no encontrado o no pertenece al usuario.")

    # Asegurarse de que database_url no es None antes de usar .replace()
    if settings.database_url is None:
        raise HTTPException(status_code=500, detail="Configuración de base de datos faltante.")

    db_sync_url = settings.database_url.replace("+psycopg", "")
    history = PostgresChatMessageHistory(
        connection_string=db_sync_url,
        session_id=thread_id,  # El session_id para LangChain es el thread_id
        table_name="langchain_chat_history",
    )

    try:
        # ¡CORRECCIÓN CLAVE! Usar aget_messages() y esperar directamente
        messages = await history.aget_messages()
        # Filtrar mensajes de resumen si los hay y mapear a MessageResponse
        response_messages = []
        for msg in messages:
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary":
                continue  # Ignorar mensajes de resumen internos

            msg_content = msg.content if hasattr(msg, 'content') else str(msg)
            image_base64 = None
            document_url = None
            
            # Manejar caso donde el contenido puede ser una lista o un objeto con imágenes o documentos
            if isinstance(msg_content, list):
                try:
                    msg_content = str(msg_content)
                except:
                    msg_content = "Mensaje con contenido no legible"
            elif isinstance(msg_content, dict):
                if 'text' in msg_content:
                    msg_content = msg_content.get('text', '')
                if 'image_base64' in msg_content:
                    image_base64 = msg_content.get('image_base64')
                if 'document_url' in msg_content:
                    document_url = msg_content.get('document_url')
                    
            # Determinar el sender de forma robusta
            if isinstance(msg, HumanMessage):
                sender = "user"
            elif isinstance(msg, AIMessage):
                sender = "ai"
            else:
                sender = "ai"  # fallback seguro

            # Usar datetime.now() directamente ya que los mensajes no tienen created_at
            msg_created_at = datetime.now(timezone.utc)

            response_messages.append(MessageResponse(
                text=msg_content,
                sender=sender,
                created_at=msg_created_at,
                image_base64=image_base64,
                document_url=document_url
            ))
        logger.info(f"Mensajes recuperados para el hilo {thread_id}.")
        return response_messages
    except Exception as e:
        logger.error(f"Error al obtener historial de chat para el hilo {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener mensajes del hilo: {e}")

@router.delete("/threads/{thread_id}", status_code=204, summary="Eliminar un hilo de chat")
async def delete_chat_thread(
    thread_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un hilo de chat si pertenece al usuario autenticado.
    """
    thread = await db.scalar(
        select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id))
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado o no pertenece al usuario.")
    await db.delete(thread)
    await db.commit()
    return

@router.get("/threads/{thread_id}", response_model=ThreadResponse, summary="Obtener un hilo de chat por ID")
async def get_thread_by_id(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado o no pertenece al usuario.")
    return ThreadResponse(id=str(thread.id), title=str(thread.title), created_at=thread.created_at.replace(tzinfo=timezone.utc))

class ThreadPinRequest(BaseModel):
    isPinned: bool

@router.put("/threads/{thread_id}/pin", response_model=ThreadResponse, summary="Actualizar estado de fijado de un hilo de chat")
async def update_thread_pin_status(thread_id: str, request: ThreadPinRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Actualiza el estado de fijado de un hilo de chat para el usuario autenticado.
    """
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado o no pertenece al usuario.")

    setattr(thread, 'is_pinned', request.isPinned)
    await db.commit()
    await db.refresh(thread)
    return ThreadResponse(id=str(thread.id), title=str(thread.title), created_at=thread.created_at.replace(tzinfo=timezone.utc))

@router.post("/threads/{thread_id}/generate-title", response_model=ThreadResponse, summary="Forzar la generación de un nuevo título para un hilo de chat")
async def force_generate_thread_title(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Fuerza la generación de un nuevo título para un hilo de chat específico.
    """
    await force_update_thread_title(thread_id)
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
    return ThreadResponse(id=str(thread.id), title=str(thread.title), created_at=thread.created_at.replace(tzinfo=timezone.utc))

@router.post("/internal/bot-create-thread")
async def bot_create_thread(account_id: str = Form(...), title: str = Form("Nuevo Chat")):
    """Permite al bot de Telegram crear un hilo de chat para una cuenta dada."""
    try:
        thread_id = await create_thread_for_account(account_id, title)
        return {"thread_id": thread_id}
    except Exception as e:
        logger.error(f"Error creando hilo para la cuenta {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
