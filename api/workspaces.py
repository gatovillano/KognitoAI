# api/workspaces.py

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import unquote

from fastapi import File, UploadFile

from fastapi import APIRouter, HTTPException, Depends, status, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, desc, update, or_, and_

from core.database import SessionLocal, Account, Workspace, ChatThread, LangchainPgCollection
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.agent import create_thread_for_account, force_update_thread_title
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from core.config import settings
from core.memory_manager import list_user_collections, process_document_for_rag, list_user_documents

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
    return [WorkspaceResponse(id=str(w.id), name=w.name, system_prompt=w.system_prompt, created_at=w.created_at) for w in workspaces]

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Obtener detalles de un workspace")
async def get_workspace(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, created_at=workspace.created_at)

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
    return WorkspaceResponse(id=str(new_workspace.id), name=new_workspace.name, system_prompt=new_workspace.system_prompt, created_at=new_workspace.created_at)

@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Actualizar un workspace")
async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    
    if request.name is not None:
        workspace.name = request.name
    if request.system_prompt is not None:
        workspace.system_prompt = request.system_prompt
        
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, created_at=workspace.created_at)

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
@router.get("/workspaces/{workspace_id}/collections/{collection_id}", response_model=CollectionResponse, summary="Obtener detalles de una colección de un workspace")
async def get_collection_details(workspace_id: str, collection_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    
    decoded_collection_id = unquote(collection_id)
    
    # Lógica más robusta para encontrar la colección
    collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
    logger.info(f"Buscando colección '{decoded_collection_id}' en {len(collections)} colecciones del workspace.")
    
    collection = None
    for c in collections:
        if c.get('topic') == decoded_collection_id:
            collection = c
            break
            
    if not collection:
        logger.warning(f"Colección '{decoded_collection_id}' no encontrada. Colecciones disponibles: {[c.get('topic') for c in collections]}")
        raise HTTPException(status_code=404, detail=f"Colección '{decoded_collection_id}' no encontrada en este workspace.")
        
    return CollectionResponse(id=collection['topic'], name=collection['topic'], document_count=collection['document_count'])

@router.get("/workspaces/{workspace_id}/collections/{collection_id}/documents", response_model=List[DocumentResponse], summary="Listar documentos de una colección de un workspace")
async def list_collection_documents(workspace_id: str, collection_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    
    documents = await list_user_documents(account_id=current_account_id, workspace_id=workspace_id, topic=collection_id)
    return [DocumentResponse(**doc) for doc in documents]
@router.get("/workspaces/{workspace_id}/collections", response_model=List[CollectionResponse], summary="Listar colecciones de un workspace")
async def list_collections(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    
    collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
    return [CollectionResponse(id=c['topic'], name=c['topic'], document_count=c['document_count']) for c in collections]

@router.post("/workspaces/{workspace_id}/collections", status_code=status.HTTP_201_CREATED, summary="Crear una nueva colección en un workspace")
async def create_collection(workspace_id: str, request: CollectionCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    
    # La creación de la colección es implícita al subir el primer documento.
    # Este endpoint puede servir para asociar un topic a un workspace.
    # O simplemente para validar que el nombre es válido.
    # Por ahora, solo devolvemos un mensaje de éxito.
    return {"message": f"Colección '{request.topic}' lista para ser usada en el workspace."}

@router.post("/workspaces/{workspace_id}/collections/{collection_id}/associate", status_code=status.HTTP_200_OK, summary="Asociar una colección existente a un workspace")
async def associate_collection_to_workspace(workspace_id: str, collection_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    from core.memory_manager import update_collection_workspace
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    
    decoded_collection_id = unquote(collection_id)
    success = await update_collection_workspace(current_account_id, decoded_collection_id, workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Colección no encontrada o no se pudo asociar al workspace.")
    
    return {"message": f"Colección '{decoded_collection_id}' asociada al workspace con éxito.", "id": decoded_collection_id, "workspace_id": workspace_id}

@router.post("/workspaces/{workspace_id}/collections/{topic}/documents", status_code=status.HTTP_201_CREATED, summary="Añadir un documento a una colección de un workspace")
async def add_document_to_collection(workspace_id: str, topic: str, request: DocumentToCollectionRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    
    # Aquí iría la lógica para asociar un documento existente a esta colección/workspace.
    # Esto podría implicar actualizar los metadatos del documento.
    # Por ahora, solo devolvemos un mensaje de éxito.
    return {"message": f"Documento {request.document_id} añadido a la colección '{topic}' en el workspace."}

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
    workspace_id: Optional[str] = Query(None)
):
    """
    Lista los hilos de chat de un usuario.
    - Si se proporciona workspace_id, filtra por ese workspace.
    - Si no se proporciona workspace_id, muestra solo los hilos sin workspace.
    """
    account_uuid = uuid.UUID(current_account_id)
    logger.info(f"Listando hilos para cuenta: {account_uuid}, workspace: {workspace_id}")
    
    stmt = select(ChatThread).where(ChatThread.account_id == account_uuid)
    
    if workspace_id:
        try:
            workspace_uuid = uuid.UUID(workspace_id)
            stmt = stmt.where(ChatThread.workspace_id == workspace_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="workspace_id inválido.")
    else:
        stmt = stmt.where(ChatThread.workspace_id.is_(None))
        
    stmt = stmt.order_by(ChatThread.created_at.desc())
    result = await db.execute(stmt)
    threads = result.scalars().all()
    
    return [ThreadResponse(id=str(t.id), title=t.title, created_at=t.created_at, workspace_id=str(t.workspace_id) if t.workspace_id else None) for t in threads]

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
        workspace_id=workspace_uuid
    )
    db.add(new_thread)
    await db.commit()
    await db.refresh(new_thread)

    return ThreadResponse(
        id=str(new_thread.id),
        title=new_thread.title,
        created_at=new_thread.created_at,
        workspace_id=str(new_thread.workspace_id) if new_thread.workspace_id else None
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
                    msg_content = msg_content['text']
                if 'image_base64' in msg_content:
                    image_base64 = msg_content['image_base64']
                if 'document_url' in msg_content:
                    document_url = msg_content['document_url']
                    
            # Determinar el sender de forma robusta
            if isinstance(msg, HumanMessage):
                sender = "user"
            elif isinstance(msg, AIMessage):
                sender = "ai"
            else:
                sender = "ai"  # fallback seguro
            msg_created_at = datetime.now(timezone.utc)  # Placeholder si no hay un 'created_at' en BaseMessage

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
    return ThreadResponse(id=str(thread.id), title=thread.title, created_at=thread.created_at)

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
    thread.is_pinned = request.isPinned
    await db.commit()
    await db.refresh(thread)
    return ThreadResponse(id=str(thread.id), title=thread.title, created_at=thread.created_at)

@router.post("/threads/{thread_id}/generate-title", response_model=ThreadResponse, summary="Forzar la generación de un nuevo título para un hilo de chat")
async def force_generate_thread_title(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Fuerza la generación de un nuevo título para un hilo de chat específico.
    """
    await force_update_thread_title(thread_id)
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
    return ThreadResponse(id=str(thread.id), title=thread.title, created_at=thread.created_at)

@router.post("/internal/bot-create-thread")
async def bot_create_thread(account_id: str = Form(...), title: str = Form("Nuevo Chat")):
    """Permite al bot de Telegram crear un hilo de chat para una cuenta dada."""
    try:
        thread_id = await create_thread_for_account(account_id, title)
        return {"thread_id": thread_id}
    except Exception as e:
        logger.error(f"Error creando hilo para la cuenta {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
