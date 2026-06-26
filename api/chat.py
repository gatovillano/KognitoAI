# api/chat.py

import logging
import uuid
import re
import json
import asyncio
import os
import pickle
from typing import Annotated, Optional, AsyncGenerator, Any, List, Dict, Union
from io import BytesIO
import httpx
from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile, Query
from fastapi import BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime, timezone # Importar datetime y timezone

from sqlalchemy import update, Integer, cast, func, text


from utils.audio_transcriber import (
    transcribe_audio_file,
    StreamingTranscriber,
    get_whisper_model,
    AudioTranscriptionError,
    InvalidAudioFileError,
)
from core.tts_manager import generate_speech_streaming, get_tts_client # Importar desde el nuevo módulo
from utils.security import get_current_account_id, get_current_user, get_current_user_from_websocket_query_param, decode_access_token # Añadido decode_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.database import SessionLocal, ChatThread, settings, Workspace, Account, ChatTask
from core.llm_manager import get_main_llm
from skills.rag_skill.scripts.add_web_to_rag_tool import AddWebToRAGTool
from skills.search_and_research_skill.scripts.ddg_search_tool import create_ddg_search_tool
from core.websocket_manager import send_personal_message
from langchain_core.runnables import RunnableConfig # Importar RunnableConfig
from core.dependencies import get_db_session # Importar dependencia centralizada
from utils.db_session import DBSession # Importar DBSession para tareas en background

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# Global registry for active chat tasks to allow cancellation
active_chat_tasks: Dict[str, Dict[str, Any]] = {}

# get_db eliminado en favor de core.dependencies.get_db_session

# --- Modelos para el Chat ---
class Source(BaseModel):
    """Define la estructura de datos para una fuente citada."""
    id: Union[int, str]
    title: str
    url: str
    snippet: str
    type: str = "web"  # "web", "document", "memory", etc.
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    """Define la estructura de datos para una solicitud de mensaje de chat al agente."""
    thread_id: str
    account_id: str
    telegram_id: Optional[int] = None  # Hacemos telegram_id opcional
    user_message: Optional[str] = None
    image_base64: Optional[str] = None
    images_base64: Optional[List[str]] = None
    document_url: Optional[str] = None  # Campo para URL de documentos
    mode: Optional[str] = None
    rag_context: Optional[str] = None # Contexto seleccionado por el usuario: [{'type': 'document', 'id': '...', 'name': '...', 'file_name': '...'}]
    workspace_id: Optional[str] = None  # Campo para el ID del workspace
    context: Optional[Dict[str, Any]] = None # Contexto específico: {"type": "table", "id": "...", "snapshot": {...}}

class ToolExecutionRequest(BaseModel):
    tool_name: str
    query: str
    account_id: str
    workspace_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Define la estructura de datos para la respuesta del agente de chat."""
    response_text: str
    sources: Optional[List[Source]] = None  # Lista de fuentes citadas
    image_base64: Optional[str] = None  # Campo para imágenes en base64
    document_url: Optional[str] = None  # Campo para URL de documentos
    tool_code: Optional[str] = None
    rag_context: Optional[List[Dict[str, str]]] = None

class Message(BaseModel):
    text: str
    sender: str
    created_at: datetime # Cambiado a datetime
    image_base64: Optional[str] = None
    images_base64: Optional[List[str]] = None
    document_url: Optional[str] = None
    sources: Optional[List[Source]] = None # Añadido para incluir las fuentes
    reasoning: Optional[str] = None # Añadido para persistir el pensamiento del LLM
    model_name: Optional[str] = None
    content_parts: Optional[List[Dict[str, Any]]] = None
    pty_session: Optional[Dict[str, Any]] = None

class PaginatedChatMessagesResponse(BaseModel):
    total: int
    messages: List[Message]





class TextToSpeechRequest(BaseModel):
    """Define la estructura de datos para una solicitud de conversión de texto a voz."""
    text: str
    voice: Optional[str] = None  # Voz opcional para la conversión
    provider: str = "google" # Nuevo campo para el proveedor de TTS
    speed: Optional[float] = None  # Velocidad del habla
    model: Optional[str] = None  # Modelo opcional para la conversión (OpenAI/Compatible)
    region: Optional[str] = None  # Región para Azure TTS

class PinThreadRequest(BaseModel):
    """Define la estructura de datos para una solicitud de fijar/desfijar un hilo de chat."""
    isPinned: bool

class DeleteThreadMessageRequest(BaseModel):
    """Define la estructura para eliminar un mensaje individual de un hilo."""
    sender: str
    created_at: Optional[str] = None
    text: Optional[str] = None
    allow_fallback_latest: bool = True

class CreateThreadRequest(BaseModel):
    """Define la estructura de datos para crear un nuevo hilo de chat."""
    title: str = "Nuevo Chat"
    platform: str = "web"
    workspace_id: Optional[str] = None



class ChatThreadResponse(BaseModel):
    id: str
    title: str
    isPinned: bool
    platform: Optional[str]
    workspace_id: Optional[str]
    created_at: Optional[datetime]
    hidden_from_sidebar: Optional[bool] = False

class PaginatedThreadsResponse(BaseModel):
    total: int
    threads: List[ChatThreadResponse]


@router.post("/threads", summary="Crear un nuevo hilo de chat")
async def create_thread(
    request: CreateThreadRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint para crear un nuevo hilo de chat.
    """
    try:
        new_thread_id = uuid.uuid4()
        new_thread = ChatThread(
            id=new_thread_id,
            title=request.title,
            account_id=uuid.UUID(current_account_id),
            platform=request.platform,
            workspace_id=uuid.UUID(request.workspace_id) if request.workspace_id else None,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        logger.info(f"Nuevo hilo creado: {new_thread.id} para la cuenta {current_account_id}")
        # Nota: NO lanzamos generación de título aquí porque el thread recién creado
        # no tiene mensajes. El título se generará automáticamente tras el primer
        # intercambio de mensajes (condición: título == 'Nuevo Chat' y message_count >= 3).
        return {"id": str(new_thread.id), "title": new_thread.title, "isPinned": new_thread.is_pinned, "platform": new_thread.platform, "workspace_id": str(new_thread.workspace_id) if new_thread.workspace_id else None}
    except ValueError:
        logger.error(f"El account_id o workspace_id proporcionado no es un UUID válido.")
        raise HTTPException(status_code=400, detail="El account_id o workspace_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al crear un nuevo hilo para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al crear el hilo de chat.")

@router.get("/threads", response_model=PaginatedThreadsResponse, summary="Obtener lista de hilos de chat con paginación")
async def get_threads(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session),
    workspace_id: Optional[str] = Query(None, description="Filtrar hilos por workspace ID"),
    skip: int = Query(0, ge=0, description="Número de hilos a omitir"),
    limit: int = Query(8, ge=1, le=100, description="Número máximo de hilos a devolver")
):
    """
    Endpoint para obtener la lista de hilos de chat del usuario autenticado,
    con opción de filtrar por workspace y con paginación. Excluye hilos ocultos y del sistema.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)
        
        # Base query — excluir hilos de sistema (heartbeat/system) y ocultos del sidebar
        base_query = select(ChatThread).where(
            ChatThread.account_id == account_uuid,
            ChatThread.platform != "heartbeat",
            ChatThread.platform != "system",
            ChatThread.hidden_from_sidebar == False
        )
        
        # Filter by workspace_id if provided
        if workspace_id:
            if str(workspace_id).lower() == "none":
                base_query = base_query.where(ChatThread.workspace_id == None)
            else:
                base_query = base_query.where(ChatThread.workspace_id == uuid.UUID(str(workspace_id)))

        # Consulta para el total de hilos
        total_stmt = select(func.count(ChatThread.id)).select_from(base_query.alias()) # Corregido: func.count(ChatThread.id)
        total_result = await db.execute(total_stmt)
        total_threads = total_result.scalar_one()

        # Consulta para los hilos paginados
        threads_stmt = base_query.order_by(ChatThread.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(threads_stmt)
        thread_list = result.scalars().all()
        
        # Format response
        threads_response = [
            ChatThreadResponse(
                id=str(thread.id),
                title=thread.title,
                isPinned=thread.is_pinned,
                platform=thread.platform,
                workspace_id=str(thread.workspace_id) if thread.workspace_id else None,
                created_at=thread.created_at,
                hidden_from_sidebar=thread.hidden_from_sidebar
            ) for thread in thread_list
        ]

        return PaginatedThreadsResponse(total=total_threads, threads=threads_response)

    except ValueError:
        raise HTTPException(status_code=400, detail="El ID de la cuenta o del workspace no es un UUID válido.")
    except Exception as e:
        logger.error(f"Error al obtener la lista de hilos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener la lista de hilos de chat.")


@router.get("/threads/system", response_model=PaginatedThreadsResponse, summary="Obtener hilos de sistema (heartbeats) con paginación")
async def get_system_threads(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0, description="Número de hilos a omitir"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de hilos a devolver")
):
    """
    Endpoint para obtener la lista de hilos de sistema (heartbeats) del usuario autenticado,
    con paginación.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)
        
        # Base query — obtener solo hilos de sistema (heartbeats)
        base_query = select(ChatThread).where(
            ChatThread.account_id == account_uuid,
            ChatThread.platform == "system",
        )
        
        # Consulta para el total de hilos
        total_stmt = select(func.count(ChatThread.id)).select_from(base_query.alias())
        total_result = await db.execute(total_stmt)
        total_threads = total_result.scalar_one()

        # Consulta para los hilos paginados
        threads_stmt = base_query.order_by(ChatThread.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(threads_stmt)
        thread_list = result.scalars().all()
        
        # Format response
        threads_response = [
            ChatThreadResponse(
                id=str(thread.id),
                title=thread.title,
                isPinned=thread.is_pinned,
                platform=thread.platform,
                workspace_id=str(thread.workspace_id) if thread.workspace_id else None,
                created_at=thread.created_at,
                hidden_from_sidebar=thread.hidden_from_sidebar
            ) for thread in thread_list
        ]

        return PaginatedThreadsResponse(total=total_threads, threads=threads_response)

    except ValueError:
        raise HTTPException(status_code=400, detail="El ID de la cuenta no es un UUID válido.")
    except Exception as e:
        logger.error(f"Error al obtener la lista de hilos de sistema para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener la lista de hilos de sistema.")

@router.get("/threads/{thread_id}/messages", response_model=PaginatedChatMessagesResponse, summary="Obtener mensajes de un hilo de chat con paginación")
async def get_messages_for_thread(
    thread_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0, description="Número de mensajes a omitir"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de mensajes a devolver")
):
    try:
        # Verificar que el hilo existe y pertenece al usuario
        thread = await db.scalar(select(ChatThread).where(
            ChatThread.id == uuid.UUID(thread_id),
            ChatThread.account_id == uuid.UUID(current_account_id)
        ))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")

        db_sync_url = settings.database_url.replace("+psycopg", "")
        
        # Robustez: Intentar inicializar el historial con reintentos
        chat_message_history = None
        for attempt in range(3):
            try:
                chat_message_history = PostgresChatMessageHistory(
                    connection_string=db_sync_url,
                    session_id=thread_id,
                    table_name="langchain_chat_history",
                )
                all_messages = await chat_message_history.aget_messages()
                break
            except Exception as e:
                logger.warning(f"⚠️ Intento {attempt + 1} fallido al obtener mensajes del hilo {thread_id}: {e}")
                if attempt == 2:
                    logger.error(f"❌ No se pudo conectar con el historial del hilo {thread_id}: {e}")
                    raise HTTPException(status_code=500, detail="Error al recuperar el historial de mensajes.")
                await asyncio.sleep(1)

        
        # Filtrar mensajes que no son de tipo "summary"
        real_messages = []
        for msg in all_messages:
            if not (hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary"):
                text_content = ""
                image_contents = []
                
                if isinstance(msg.content, list):
                    # Handle multimodal content
                    for part in msg.content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                text_content += part.get("text", "")
                            elif part.get("type") == "image_url":
                                image_url_data = part.get("image_url")
                                if isinstance(image_url_data, dict):
                                    image_contents.append(image_url_data.get("url"))
                        else:
                            text_content += str(part)
                else:
                    text_content = str(msg.content)
                
                # Extraer sources si existen en additional_kwargs
                message_sources = msg.additional_kwargs.get("sources", [])
                message_model_name = msg.additional_kwargs.get("model_name")
                message_content_parts = msg.additional_kwargs.get("content_parts")
                message_pty_session = msg.additional_kwargs.get("pty_session")
                
                real_messages.append(Message(
                    text=text_content,
                    sender="user" if isinstance(msg, HumanMessage) else "ai",
                    created_at=msg.additional_kwargs.get("created_at", datetime.now(timezone.utc)),
                    image_base64=image_contents[0] if image_contents else None,
                    images_base64=image_contents if len(image_contents) > 1 else None,
                    sources=message_sources, # Asignar las fuentes extraídas
                    reasoning=msg.additional_kwargs.get("reasoning") or msg.additional_kwargs.get("think"), # Extraer razonamiento
                    model_name=message_model_name,
                    content_parts=message_content_parts,
                    pty_session=message_pty_session
                ))

        # Sort messages by created_at in ascending order
        real_messages.sort(key=lambda msg: msg.created_at)

        total_messages = len(real_messages)
        paginated_messages = real_messages[skip : skip + limit]

        return PaginatedChatMessagesResponse(total=total_messages, messages=paginated_messages)

    except ValueError:
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no es un UUID válido.")
    except Exception as e:
        logger.error(f"Error al obtener mensajes para el hilo {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener los mensajes del chat.")

async def search_chat_messages(
    query: str,
    account_id: str,
    db: AsyncSession,
    workspace_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Busca en los títulos de los hilos y en los mensajes de chat de un usuario.
    """
    logger.info(f"Buscando '{query}' en chats para la cuenta {account_id} y workspace {workspace_id}")
    results = []
    
    # Optimization: Use direct SQL queries instead of iterating over all threads and messages
    
    # 1. Search in thread titles
    thread_query = select(ChatThread).where(
        ChatThread.account_id == uuid.UUID(account_id),
        ChatThread.title.ilike(f"%{query}%")
    )
    if workspace_id:
        if str(workspace_id).lower() == "none":
            thread_query = thread_query.where(ChatThread.workspace_id == None)
        else:
            thread_query = thread_query.where(ChatThread.workspace_id == uuid.UUID(str(workspace_id)))
            
    thread_results = await db.execute(thread_query)
    threads = thread_results.scalars().all()
    
    for thread in threads:
        results.append({
            "type": "chat_thread",
            "id": str(thread.id),
            "title": thread.title,
            "created_at": thread.created_at.isoformat() if thread.created_at else None
        })

    # 2. Search in messages (joining with ChatThread for permission)
    # We use raw SQL because langchain_chat_history is not a mapped model in our codebase
    # We cast message to text to search within the JSONB
    message_sql = """
        SELECT ct.id, ct.title, lch.message
        FROM langchain_chat_history lch
        JOIN chat_threads ct ON lch.session_id = ct.id::text
        WHERE ct.account_id = :account_id
        AND lch.message::text ILIKE :query
    """
    params = {"account_id": account_id, "query": f"%{query}%"}
    
    if workspace_id:
        if str(workspace_id).lower() == "none":
             message_sql += " AND ct.workspace_id IS NULL"
        else:
             message_sql += " AND ct.workspace_id = :workspace_id"
             params["workspace_id"] = workspace_id

    message_results = await db.execute(text(message_sql), params)
    rows = message_results.fetchall()
    
    for row in rows:
        thread_id_str, thread_title, message_json = row
        
        # Parse message content
        # message_json is a dict (JSONB)
        text_content = ""
        sender = "unknown"
        created_at = datetime.now(timezone.utc)
        
        try:
            if isinstance(message_json, str):
                 message_data = json.loads(message_json)
            else:
                 message_data = message_json
            
            # LangChain message structure: {"type": "human", "data": {"content": ...}} or direct keys
            msg_type = message_data.get("type")
            if msg_type == "human":
                sender = "user"
            elif msg_type == "ai":
                sender = "ai"
            
            # Extract content
            if "data" in message_data and isinstance(message_data["data"], dict):
                content = message_data["data"].get("content")
                additional_kwargs = message_data["data"].get("additional_kwargs", {})
            else:
                content = message_data.get("content")
                additional_kwargs = message_data.get("additional_kwargs", {})

            if additional_kwargs:
                 created_at_str = additional_kwargs.get("created_at")
                 if created_at_str:
                     try:
                         created_at = datetime.fromisoformat(created_at_str)
                     except:
                         pass

            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_content += part.get("text", "")
            else:
                text_content = str(content) if content else ""
                
        except Exception as e:
            logger.warning(f"Error parsing message for search: {e}")
            continue

        # Double check query match in extracted text (since SQL match was on raw JSON)
        if query.lower() in text_content.lower():
            results.append({
                "type": "chat_message",
                "id": str(thread_id_str),  # Added for frontend compatibility
                "thread_id": str(thread_id_str),
                "thread_title": thread_title,
                "content": text_content,
                "sender": sender,
                "reasoning": additional_kwargs.get("reasoning") or additional_kwargs.get("think"),
                "created_at": created_at.isoformat()
            })

    # Aplicar paginación a los resultados finales
    return results[skip : skip + limit]

@router.get("/threads/{thread_id}", summary="Obtener detalles de un hilo de chat")
async def get_thread(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    """
    Endpoint para obtener los detalles de un hilo de chat específico.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        return {"id": str(thread.id), "title": thread.title, "isPinned": thread.is_pinned, "platform": thread.platform, "workspace_id": str(thread.workspace_id) if thread.workspace_id else None}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Error al obtener detalles del hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener los detalles del hilo de chat.")


@router.put("/threads/{thread_id}/pin", summary="Fijar o desfijar un hilo de chat")
async def pin_thread(thread_id: str, request: PinThreadRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    """
    Endpoint para fijar o desfijar un hilo de chat específico.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        await db.execute(update(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)).values(is_pinned=request.isPinned))
        await db.commit()
        return {"id": str(thread.id), "isPinned": request.isPinned}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al actualizar el estado de fijado del hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al actualizar el estado de fijado del hilo de chat.")

@router.delete("/threads/{thread_id}", summary="Eliminar un hilo de chat")
async def delete_thread(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    """
    Endpoint para eliminar un hilo de chat específico.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        await db.delete(thread)
        await db.commit()
        return {"id": thread_id, "deleted": True}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al eliminar el hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al eliminar el hilo de chat.")

@router.delete("/threads/{thread_id}/messages", summary="Eliminar un mensaje individual de un hilo")
async def delete_thread_message(
    thread_id: str,
    request: DeleteThreadMessageRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina un mensaje específico de `langchain_chat_history` dentro del hilo indicado.
    Busca por `sender` y opcionalmente `created_at` y `text`, eliminando el match más reciente.
    """
    try:
        # Verificar que el hilo existe y pertenece al usuario autenticado
        thread = await db.scalar(select(ChatThread).where(
            ChatThread.id == uuid.UUID(thread_id),
            ChatThread.account_id == uuid.UUID(current_account_id)
        ))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")

        sender_normalized = (request.sender or "").strip().lower()
        sender_to_message_type = {
            "user": "human",
            "human": "human",
            "ai": "ai",
            "assistant": "ai",
        }
        message_type = sender_to_message_type.get(sender_normalized)
        if not message_type:
            raise HTTPException(status_code=400, detail="Sender inválido. Use 'user' o 'ai'.")

        filters = [
            "session_id = :session_id",
            "message->>'type' = :message_type",
        ]
        params: Dict[str, Any] = {
            "session_id": thread_id,
            "message_type": message_type,
        }

        if request.created_at:
            filters.append(
                "COALESCE(message #>> '{data,additional_kwargs,created_at}', message #>> '{additional_kwargs,created_at}', '') = :created_at"
            )
            params["created_at"] = request.created_at

        if request.text is not None:
            filters.append("COALESCE(message #>> '{data,content}', message #>> '{content}', '') = :message_text")
            params["message_text"] = request.text

        where_clause = " AND ".join(filters)
        select_stmt = text(f"""
            SELECT id
            FROM langchain_chat_history
            WHERE {where_clause}
            ORDER BY id DESC
            LIMIT 1
        """)
        result = await db.execute(select_stmt, params)
        row = result.first()

        if not row and request.allow_fallback_latest:
            logger.warning(
                f"⚠️ No se encontró coincidencia exacta para borrar mensaje en hilo {thread_id}. "
                "Aplicando fallback al mensaje más reciente del mismo remitente."
            )
            fallback_result = await db.execute(
                text("""
                    SELECT id
                    FROM langchain_chat_history
                    WHERE session_id = :session_id
                      AND message->>'type' = :message_type
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {
                    "session_id": thread_id,
                    "message_type": message_type,
                },
            )
            row = fallback_result.first()

        if not row:
            raise HTTPException(status_code=404, detail="No se encontró un mensaje que coincida con los criterios.")

        message_id = row[0]
        await db.execute(text("DELETE FROM langchain_chat_history WHERE id = :message_id"), {"message_id": message_id})
        await db.commit()

        return {
            "deleted": True,
            "thread_id": thread_id,
            "message_id": message_id,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar mensaje del hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al eliminar el mensaje.")

@router.post("/threads/{thread_id}/generate-title", summary="Generar un título para un hilo de chat")
async def generate_thread_title(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    """
    Endpoint para generar un título para un hilo de chat específico basado en su contenido.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        from core.agent import force_update_thread_title
        await force_update_thread_title(thread_id)
        updated_thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)))
        if not updated_thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        return {"id": thread_id, "title": updated_thread.title}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al generar título para el hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al generar el título del hilo de chat.")

@router.post("/threads/generate-all-titles", summary="Generar títulos para todos los hilos de chat")
async def generate_all_thread_titles(
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Inicia una tarea en segundo plano para generar títulos para todos los hilos de chat del usuario.
    """
    try:
        from core.agent import force_update_all_thread_titles
        logger.info(f"Iniciando tarea en segundo plano para generar todos los títulos para la cuenta {current_account_id}")
        background_tasks.add_task(force_update_all_thread_titles, current_account_id)
        return {"message": "El proceso de nombrar todas las conversaciones ha comenzado en segundo plano."}
    except Exception as e:
        logger.error(f"Error al iniciar la generación de todos los títulos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al iniciar el proceso.")

def _split_text_into_chunks(text: str, max_length: int = 1500) -> List[str]:
    """
    Splits a long text into smaller chunks of a maximum length.
    Tries to split at natural sentence breaks like '.', '?', '!', or newlines.
    """
    if not text or not text.strip():
        return []

    if len(text) <= max_length:
        return [text]

    chunks = []
    while len(text) > 0:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find the best split point by searching backwards from max_length
        split_pos = -1
        # Prioritize sentence-ending punctuation
        for delimiter in ['.', '?', '!']:
            pos = text.rfind(delimiter, 0, max_length)
            if pos != -1:
                split_pos = pos + 1
                break
        
        # If not found, try newlines or other punctuation
        if split_pos == -1:
            for delimiter in ['\n', ';', ',']:
                pos = text.rfind(delimiter, 0, max_length)
                if pos != -1:
                    split_pos = pos + 1
                    break

        # If still no natural break found, hard split at a space
        if split_pos == -1:
            pos = text.rfind(' ', 0, max_length)
            if pos != -1:
                split_pos = pos + 1
            else:
                # Absolute last resort: hard split at max_length
                split_pos = max_length
        
        chunk = text[:split_pos]
        text = text[split_pos:]
        chunks.append(chunk)

    return [c.strip() for c in chunks if c.strip()]


@router.post("/text-to-speech", summary="Generar audio desde texto")
async def text_to_speech(
    request: TextToSpeechRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Recibe texto, lo envía al servicio TTS configurado (del usuario o por defecto)
    y devuelve el audio como un stream. Maneja textos largos dividiéndolos en
    fragmentos y utiliza caché para evitar regeneraciones.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")

    # Cargar configuración por defecto del usuario
    account = await db.get(Account, uuid.UUID(current_account_id))
    
    # Valores de la solicitud (si vienen) o de la cuenta (si existen) o valores por defecto
    effective_provider = request.provider
    effective_voice = request.voice
    effective_speed = request.speed
    effective_model = request.model
    effective_region = request.region
    effective_api_base = None

    if account:
        if not effective_provider:
            effective_provider = account.tts_provider or "google"
            logger.info(f"🎤 [TTS Trace] Provider en cuenta: {account.tts_provider}, Usando efectivo: {effective_provider}")
        if not effective_voice:
            effective_voice = account.tts_voice
        if effective_speed is None: # Comprobar None específicamente porque 0.0 es un valor válido aunque raro
            effective_speed = account.tts_speed if account.tts_speed is not None else 1.0
        if not effective_region:
            effective_region = account.tts_region
        if not effective_model:
            effective_model = account.tts_model
        effective_api_base = account.tts_api_base
        logger.info(f"🎤 [TTS Trace] Config: voice={effective_voice}, model={effective_model}, base={effective_api_base}")
    else:
        # Fallback total si no hay cuenta ni datos en request
        effective_provider = effective_provider or "google"
        effective_speed = effective_speed if effective_speed is not None else 1.0

    # Asegurarnos de que tenemos una voz por defecto si sigue siendo None
    if not effective_voice:
        effective_voice = 'es-MX-DaliaNeural'
    
    # Pre-procesar el texto para eliminar elementos no deseados
    text_to_speak = request.text
    # 1. Eliminar bloques de código cercados (```...```)
    text_to_speak = re.sub(r'```.*?```', '', text_to_speak, flags=re.DOTALL)
    # 2. Eliminar código en línea (`...`)
    text_to_speak = re.sub(r'`[^`]*`', '', text_to_speak)
    # 3. Eliminar encabezados de markdown (#, ##, etc.)
    text_to_speak = re.sub(r'#+\s*', '', text_to_speak)
    # 4. Limpiar enlaces de markdown: [texto](url) -> texto
    text_to_speak = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text_to_speak)
    # 5. Eliminar otros caracteres de puntuación de markdown (*, _, ~, >)
    text_to_speak = re.sub(r'[*_~>]', '', text_to_speak)
    # 6. Limpiar espacios en blanco múltiples
    text_to_speak = re.sub(r'\s+', ' ', text_to_speak).strip()

    if not text_to_speak:
        return StreamingResponse(BytesIO(), media_type="audio/mpeg")

    # Para Kokoro y Coqui, no dividimos el texto en fragmentos porque devuelven WAV.
    # Concatenar múltiples WAVs con cabeceras rompe la reproducción en el navegador.
    if effective_provider.lower() in ["kokoro", "coquitts", "coqui"]:
        text_chunks = [text_to_speak]
    else:
        text_chunks = _split_text_into_chunks(text_to_speak)

    async def generate_audio_stream():
        """Genera el stream de audio usando el servicio TTS configurado para cada fragmento."""
        try:
            async for audio_chunk in generate_speech_streaming(
                text_chunks=text_chunks,
                provider=effective_provider,
                voice=effective_voice if effective_voice else 'es-MX-DaliaNeural',
                speaking_rate=effective_speed,
                audio_format="mp3",
                use_cache=True,
                region=effective_region,  # Pasar la región para Azure TTS
                account_id=uuid.UUID(current_account_id), # Pasar account_id para recuperar secretos
                api_base=effective_api_base, # Pasar la URL base para servicios TTS locales/OpenAI
                model=effective_model # Pasar el modelo para servicios compatibles
            ):
                yield audio_chunk
        except Exception as e:
            logger.error(f"❌ Error generando audio con el proveedor {effective_provider} TTS: {e}")
            # Si el error es un NameError sobre 'model', registramos más detalles para depuración
            if "name 'model' is not defined" in str(e):
                logger.error(f"DEBUG TTS: provider={effective_provider}, model_val={effective_model}")
            raise HTTPException(status_code=500, detail=f"Error al generar audio: {str(e)}")

    # Determinar el tipo de medio según el proveedor
    media_type = "audio/mpeg"
    if effective_provider.lower() in ["coquitts", "coqui", "kokoro"]:
        media_type = "audio/wav"

    return StreamingResponse(generate_audio_stream(), media_type=media_type)


@router.get("/text-to-speech/cache-stats", summary="Obtener estadísticas del caché de TTS")
async def get_tts_cache_stats(provider: str = Query("google", description="Proveedor de TTS para obtener estadísticas del caché")):
    """
    Endpoint para obtener estadísticas del caché de audios TTS para un proveedor específico.
    """
    try:
        client = get_tts_client(provider=provider)
        stats = client.get_cache_stats()
        
        if stats:
            return {
                "success": True,
                "stats": stats
            }
        else:
            return {
                "success": True,
                "message": "El caché está deshabilitado o no disponible para este proveedor",
                "stats": None
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas del caché TTS para el proveedor {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")


@router.post("/text-to-speech/clear-cache", summary="Limpiar caché de TTS")
async def clear_tts_cache(provider: str = Query("google", description="Proveedor de TTS para limpiar el caché")):
    """
    Endpoint para limpiar las entradas expiradas del caché de TTS para un proveedor específico.
    """
    try:
        client = get_tts_client(provider=provider)
        client.clear_cache()
        
        return {
            "success": True,
            "message": f"Caché de TTS para {provider} limpiado exitosamente"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error limpiando caché TTS para el proveedor {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al limpiar caché: {str(e)}")

@router.get("/text-to-speech/models", summary="Obtener modelos disponibles para un proveedor")
async def get_tts_models(
    provider: str = Query(..., description="Proveedor de TTS"),
    api_base: Optional[str] = Query(None, description="URL base opcional")
):
    """
    Intenta obtener la lista de modelos disponibles para un proveedor de TTS.
    Útil para OpenAI-compatible APIs locales.
    """
    if provider not in ["openai", "openai-compatible", "kokoro", "coquitts"]:
        # Por ahora solo soportamos descubrimiento automático para OpenAI/Compatibles/Kokoro/Coqui
        return {"models": []}
    
    if not api_base:
        if provider == "kokoro":
            # Para Kokoro, intentar detectar si estamos en Docker
            import os
            if os.path.exists("/.dockerenv"):
                url = "http://kokoro-tts:8011"
            else:
                url = "http://localhost:8011"
        else:
            url = "https://api.openai.com/v1"
    else:
        url = api_base
    
    # Si estamos en Docker y el usuario pone localhost, lo traducimos a host.docker.internal
    if "localhost" in url or "127.0.0.1" in url:
        import os
        if os.path.exists("/.dockerenv"):
            url = url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            logger.info(f"🔄 Traduciendo localhost/127.0.0.1 a host.docker.internal para descubrimiento de modelos TTS: {url}")
    
    if not url.endswith("/"):
        url += "/"
    
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            # Probamos varios endpoints e incluyendo varios niveles de profundidad
            model_endpoints = ["models", "v1/models"]
            for endpoint in model_endpoints:
                try:
                    full_url = f"{url}{endpoint}"
                    logger.info(f"Intentando obtener modelos de: {full_url}")
                    response = await client.get(full_url, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        # El servidor Kokoro devuelve {"models": [...]}
                        models = data.get("models", [])
                        if not models:
                            # Si no hay "models", probar "data" (OpenAI style)
                            items = data.get("data", []) if isinstance(data, dict) else data
                            models = [m["id"] if isinstance(m, dict) else m for m in items if isinstance(m, (dict, str))]
                        
                        # Filtrar modelos que parezcan TTS
                        tts_models = [m for m in models if "tts" in str(m).lower() or "kokoro" in str(m).lower()]
                        
                        if tts_models:
                            return {"models": tts_models}
                        elif models:
                            return {"models": models}
                except Exception as e:
                    logger.debug(f"Error en endpoint de modelos {endpoint}: {e}")
                    continue
            
            # Si no se encontraron modelos pero el api_base sugiere Kokoro o es local,
            # devolver "kokoro" como fallback si al menos responde /voices (verificado en frontend)
            return {"models": ["kokoro"]}
    except Exception as e:
        logger.error(f"Error conectando con {url} para obtener modelos: {e}")
        return {"models": []}

@router.get("/text-to-speech/voices", summary="Obtener voces disponibles para un proveedor")
async def get_tts_voices(
    provider: str = Query(..., description="Proveedor de TTS"),
    api_base: Optional[str] = Query(None, description="URL base opcional")
):
    """
    Intenta obtener la lista de voces disponibles para un proveedor de TTS.
    Útil para Kokoro u otras APIs locales.
    """
    if provider not in ["openai", "openai-compatible", "kokoro", "coquitts"]:
        return {"voices": []}
    
    if not api_base:
        if provider == "kokoro":
            # Para Kokoro, intentar detectar si estamos en Docker
            import os
            if os.path.exists("/.dockerenv"):
                url = "http://kokoro-tts:8011"
            else:
                url = "http://localhost:8011"
        else:
            url = "https://api.openai.com/v1"
    else:
        url = api_base
    
    # Si estamos en Docker y el usuario pone localhost, lo traducimos a host.docker.internal
    if "localhost" in url or "127.0.0.1" in url:
        import os
        if os.path.exists("/.dockerenv"):
            url = url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            logger.info(f"🔄 Traduciendo localhost/127.0.0.1 a host.docker.internal para descubrimiento de voces: {url}")
    
    if not url.endswith("/"):
        url += "/"
    
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            # Intentar llamar al endpoint de voces (común en implementaciones locales como Kokoro)
            # Probamos varios endpoints comunes
            voice_endpoints = ["voices", "v1/voices"]
            
            for endpoint in voice_endpoints:
                try:
                    full_url = f"{url}{endpoint}"
                    logger.info(f"Intentando obtener voces de: {full_url}")
                    response = await client.get(full_url, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        # Kokoro-fastapi o este servidor Kokoro suelen devolver {"voices": [...]}
                        if isinstance(data, dict):
                            if "voices" in data:
                                return {"voices": data["voices"]}
                            elif "speakers" in data:
                                return {"voices": data["speakers"]}
                            elif "data" in data:
                                return {"voices": data["data"]}
                        elif isinstance(data, list):
                            return {"voices": data}
                        
                        logger.warning(f"Formato de respuesta de voces no reconocido de {full_url}: {data}")
                except Exception as inner_e:
                    logger.debug(f"Error al intentar endpoint {endpoint}: {inner_e}")
                    continue
            
            return {"voices": []}
    except Exception as e:
        logger.error(f"Error conectando con {url} para obtener voces: {e}")
        return {"voices": []}

@router.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Endpoint para transcribir un archivo de audio utilizando Faster Whisper.
    """
    try:
        audio_file_io = BytesIO(await file.read())
        
        # Extraer el formato del nombre del archivo
        file_format = file.filename.split('.')[-1] if file.filename else "webm"
        
        logger.info(f"Recibida solicitud para transcribir el archivo: {file.filename}")
        transcription = await transcribe_audio_file(audio_file_io, file_format)

        return {"transcription": transcription}
    except InvalidAudioFileError as e:
        logger.warning(f"Archivo de audio inválido recibido para transcripción: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AudioTranscriptionError as e:
        logger.error(f"Error controlado en la transcripción de audio: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo transcribir el audio.")
    except Exception as e:
        logger.error(f"Error en la transcripción de audio: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error interno del servidor: {e}")

class SystemMessageRequest(BaseModel):
    text: str
    created_at: Optional[datetime] = None

@router.post("/threads/{thread_id}/messages/system", status_code=status.HTTP_201_CREATED, summary="Guardar un mensaje de sistema/AI en el historial de chat")
async def save_system_message(
    thread_id: str,
    request: SystemMessageRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint para guardar un mensaje de sistema o de la IA en el historial de chat.
    Esto permite que mensajes generados por el frontend (como notificaciones de vectorización)
    sean persistidos y considerados por el LLM en futuras interacciones.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(
            ChatThread.id == uuid.UUID(thread_id),
            ChatThread.account_id == uuid.UUID(current_account_id)
        ))
        if not thread:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hilo de chat no encontrado.")

        db_sync_url = settings.database_url.replace("+psycopg", "")
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=thread_id,
            table_name="langchain_chat_history",
        )

        # Crear un AIMessage para guardar en el historial
        ai_message = AIMessage(
            content=sanitize_json_content(request.text),
            additional_kwargs={"created_at": request.created_at or datetime.now(timezone.utc)}
        )
        await chat_message_history.aadd_messages([ai_message])
        logger.info(f"Mensaje de sistema guardado en el hilo {thread_id}: {request.text}")
        return {"message": "Mensaje de sistema guardado exitosamente."}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El thread_id proporcionado no es un UUID válido.")
    except Exception as e:
        logger.error(f"Error al guardar mensaje de sistema en el hilo {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocurrió un error al guardar el mensaje de sistema.")

@router.post("/chat", status_code=status.HTTP_202_ACCEPTED, summary="Procesar Mensaje de Chat en Segundo Plano")
async def handle_chat(
    background_tasks: BackgroundTasks,
    request: ChatRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Acepta una solicitud de chat, inicia una tarea en segundo plano para procesarla
    y devuelve inmediatamente una respuesta 202 Accepted. Los resultados se envían
    a través de WebSocket.
    """
    task_id = str(uuid.uuid4())
    
    # Parse rag_context if provided
    parsed_rag_context = None
    if request.rag_context:
        try:
            parsed_rag_context = json.loads(request.rag_context)
            if not isinstance(parsed_rag_context, list):
                raise ValueError("rag_context no es una lista válida.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error al parsear rag_context: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de rag_context inválido.")
    
    logger.info(f"Petición de chat recibida de la cuenta: {request.account_id} con modo: {request.mode}. Task ID: {task_id}")
    
    # Obtener el workspace_id del payload si está presente, de lo contrario obtenerlo del hilo
    workspace_id = request.workspace_id if request.workspace_id else None
    
    if not workspace_id:
        # Si no se proporcionó workspace_id en el payload, obtenerlo del hilo
        thread = await db.scalar(select(ChatThread).where(
            ChatThread.id == uuid.UUID(request.thread_id),
            ChatThread.account_id == uuid.UUID(current_account_id)
        ))
        if not thread:
            logger.warning(f"No se encontró el hilo {request.thread_id} para la cuenta {current_account_id}.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hilo de chat con id {request.thread_id} no encontrado.")
        workspace_id = str(thread.workspace_id) if thread.workspace_id else None

    # Crear registro de ChatTask para seguimiento de cancelación
    try:
        chat_task = ChatTask(
            id=uuid.UUID(task_id),
            account_id=uuid.UUID(current_account_id),
            thread_id=uuid.UUID(request.thread_id),
            cancelled=False,
            status="running"
        )
        db.add(chat_task)
        await db.commit()
    except Exception as e:
        logger.error(f"Error creando ChatTask: {e}")
        await db.rollback()
        # Continuar de todos modos, la cancelación vía DB no funcionará pero el chat puede continuar

    logger.debug(f"DEBUG (api/chat.py): Llamando create_and_run_agent_streaming con thread_id: {request.thread_id}") # <--- NUEVO LOG
    # Crear y registrar la tarea para permitir cancelación
    task = asyncio.create_task(
        create_and_run_agent_streaming(
            account_id=request.account_id,
            thread_id=request.thread_id,
            task_id=task_id,
            telegram_id=request.telegram_id,
            user_message=request.user_message,
            image_base64=request.image_base64,
            images_base64=request.images_base64,
            document_url=request.document_url,
            mode=request.mode,
            rag_context=parsed_rag_context,
            background_tasks=background_tasks,
            workspace_id=workspace_id,
            context=request.context # Pasar el contexto
        )
    )
    # Registrar la tarea
    active_chat_tasks[task_id] = {
        "task": task,
        "account_id": request.account_id,
        "thread_id": request.thread_id
    }
    # Limpiar registro cuando la tarea termine
    task.add_done_callback(lambda t: active_chat_tasks.pop(task_id, None))

    # Devolver una respuesta inmediata
    return {"thread_id": request.thread_id, "taskId": task_id}

@router.post("/chat-form", status_code=status.HTTP_202_ACCEPTED, summary="Procesar Mensaje de Chat con FormData")
async def handle_chat_form(
    background_tasks: BackgroundTasks,
    thread_id: str = Form(...),
    account_id: str = Form(...),
    telegram_id: Optional[int] = Form(None),
    user_message: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None),
    images_base64: Optional[List[str]] = Form(None),
    document_url: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
    rag_context: Optional[str] = Form(None),
    workspace_id: Optional[str] = Form(None),
    context: Optional[str] = Form(None), # Nuevo campo en FormData
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Acepta una solicitud de chat con FormData, inicia una tarea en segundo plano para procesarla
    y devuelve inmediatamente una respuesta 202 Accepted. Los resultados se envían
    a través de WebSocket.
    """
    task_id = str(uuid.uuid4())
    
    # Parse context if provided
    parsed_context = None
    if context:
        try:
            parsed_context = json.loads(context)
        except json.JSONDecodeError:
            logger.error(f"Error al parsear context JSON: {context}")
    
    # Parse rag_context if provided
    parsed_rag_context = None
    if rag_context:
        try:
            parsed_rag_context = json.loads(rag_context)
            if not isinstance(parsed_rag_context, list):
                raise ValueError("rag_context no es una lista válida.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error al parsear rag_context: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de rag_context inválido.")
    
    logger.info(f"Petición de chat recibida de la cuenta: {account_id} con modo: {mode}. Task ID: {task_id}")
    
    # Obtener el workspace_id del payload si está presente, de lo contrario obtenerlo del hilo
    final_workspace_id = workspace_id if workspace_id else None
    
    if not final_workspace_id:
        # Si no se proporcionó workspace_id en el payload, obtenerlo del hilo
        thread = await db.scalar(select(ChatThread).where(
            ChatThread.id == uuid.UUID(thread_id),
            ChatThread.account_id == uuid.UUID(current_account_id)
        ))
        if not thread:
            logger.warning(f"No se encontró el hilo {thread_id} para la cuenta {current_account_id}.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hilo de chat con id {thread_id} no encontrado.")
        final_workspace_id = str(thread.workspace_id) if thread.workspace_id else None

    # Crear registro de ChatTask para seguimiento de cancelación
    try:
        chat_task = ChatTask(
            id=uuid.UUID(task_id),
            account_id=uuid.UUID(current_account_id),
            thread_id=uuid.UUID(thread_id),
            cancelled=False,
            status="running"
        )
        db.add(chat_task)
        await db.commit()
    except Exception as e:
        logger.error(f"Error creando ChatTask: {e}")
        await db.rollback()
        # Continuar de todos modos, la cancelación vía DB no funcionará pero el chat puede continuar

    logger.debug(f"DEBUG (api/chat.py): Llamando create_and_run_agent_streaming con thread_id: {thread_id}") # <--- NUEVO LOG
    # Crear y registrar la tarea para permitir cancelación
    task = asyncio.create_task(
        create_and_run_agent_streaming(
            account_id=account_id,
            thread_id=thread_id,
            task_id=task_id,
            telegram_id=telegram_id,
            user_message=user_message,
            image_base64=image_base64,
            images_base64=images_base64,
            document_url=document_url,
            mode=mode,
            rag_context=parsed_rag_context,
            background_tasks=background_tasks,
            workspace_id=final_workspace_id,
            context=parsed_context # Pasar el contexto parseado
        )
    )
    active_chat_tasks[task_id] = {
        "task": task,
        "account_id": account_id,
        "thread_id": thread_id
    }
    task.add_done_callback(lambda t: active_chat_tasks.pop(task_id, None))

    # Devolver una respuesta inmediata
    return {"thread_id": thread_id, "taskId": task_id}


async def create_and_run_agent_streaming(
    account_id: str,
    thread_id: str,
    task_id: str, # Nuevo taskId para seguimiento
    telegram_id: Optional[int],
    user_message: Optional[str],
    image_base64: Optional[str] = None,
    images_base64: Optional[List[str]] = None,
    document_url: Optional[str] = None,
    mode: Optional[str] = None,
    rag_context: Optional[List[Dict[str, str]]] = None,
    background_tasks: Optional[Any] = None,
    workspace_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None, # Nuevo parámetro
    k: int = 5,
    db_session: Optional[Any] = None  # DB session opcional para actualización de estado
):
    """
    Ejecuta el agente LangGraph y transmite los resultados a través de WebSockets.
    """
    from core.agent import AgentState, get_langgraph_agent, sanitize_json_content # Usar versión cacheada
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_community.chat_message_histories import PostgresChatMessageHistory
    from core.config import settings
    from core.database import LangchainPgEmbedding
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    from core.websocket_manager import send_personal_message # Asegurarse de que esté importado aquí también si es necesario

    logger.info(f"--- Iniciando agente LangGraph para account_id: {account_id}, thread_id: {thread_id} ---")

    should_check_cancellation = db_session is not None
    chunk_count = 0
    cancellation_check_interval = 10  # Check every 10 chunks to avoid DB overload

    try:
        # Determinar el destinatario y el tipo de conexión
        target_account_id = "telegram_bot_service" if telegram_id else account_id
        conn_type = "chat" if telegram_id else None # El cliente de Telegram se conecta como 'chat'

        # Enviar mensaje de inicio de stream
        await send_personal_message(target_account_id, {
            "type": "stream_start",
            "thread_id": thread_id,
            "taskId": task_id,
        }, connection_type=conn_type)

        # --- Preparación Inicial ---
        # Optimization: Usar grafo cacheado en lugar de recrearlo
        agent_app = get_langgraph_agent()
        db_sync_url = settings.database_url.replace("+psycopg", "")
        
        # Robustez: Intentar inicializar el historial con reintentos en caso de fallo de conexión
        chat_message_history = None
        for attempt in range(3):
            try:
                chat_message_history = PostgresChatMessageHistory(
                    connection_string=db_sync_url,
                    session_id=thread_id,
                    table_name="langchain_chat_history",
                )
                # Forzar una pequeña operación para verificar la conexión
                history_messages = await chat_message_history.aget_messages()
                break
            except Exception as e:
                logger.warning(f"⚠️ Intento {attempt + 1} fallido al conectar con el historial de chat: {e}")
                if attempt == 2:
                    logger.error(f"❌ No se pudo inicializar el historial de chat tras 3 intentos: {e}")
                    raise HTTPException(status_code=500, detail="Error de conexión con la base de datos de historial.")
                await asyncio.sleep(1)


        # Si rag_context no viene en la request, intentar recuperarlo del hilo (persistent_rag_context)
        if not rag_context:
            try:
                from core.database import ChatThread
                from sqlalchemy import select
                async with SessionLocal() as db_ctx:
                    thread_obj = await db_ctx.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)))
                    if thread_obj and thread_obj.persistent_rag_context:
                        rag_context = thread_obj.persistent_rag_context
                        logger.info(f"Cargado persistent_rag_context del hilo: {len(rag_context)} items.")
            except Exception as e:
                logger.warning(f"Error al cargar persistent_rag_context: {e}")

        # Inyección Automática de Contexto de OnlyOffice
        # Leemos el contenido actualizado del documento y lo inyectamos directamente en el rag_context
        # Esto permite que el agente "vea" el documento en cada turno, incluyendo los cambios que acaba de hacer.
        if rag_context:
            onlyoffice_docs = [item for item in rag_context if item.get('type') == 'document' and 'OnlyOffice' in (item.get('topic') or item.get('name') or '')]
            if onlyoffice_docs:
                try:
                    from skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool import ReadOnlyOfficeDocumentTool
                    reader = ReadOnlyOfficeDocumentTool(account_id=account_id)
                    
                    # Crear una copia del rag_context para modificarlo en memoria sin afectar la DB
                    new_rag_context = list(rag_context)
                    
                    for doc_to_inject in onlyoffice_docs:
                        logger.info(f"Cargando contenido en vivo del documento OnlyOffice: {doc_to_inject.get('id')}")
                        doc_content = await reader._arun(document_id=doc_to_inject['id'])
                        
                        if doc_content and "--- CONTENIDO" in doc_content:
                            # Reemplazar el ítem en la nueva lista con el contenido inyectado
                            idx = new_rag_context.index(doc_to_inject)
                            new_doc = dict(doc_to_inject)
                            new_doc['content'] = f"DOCUMENTO ACTUAL ABIERTO POR EL USUARIO:\n\n{doc_content}\n\nRECUERDA: Tienes herramientas para editar este documento directamente si el usuario lo pide."
                            new_rag_context[idx] = new_doc
                    
                    rag_context = new_rag_context
                    logger.info("Contenido de los documentos inyectado exitosamente en rag_context.")
                except Exception as e:
                    logger.error(f"Error en la inyección automática de documento en vivo: {e}")

        # El user_message se mantiene sin modificar aquí.

        # --- Construcción del Mensaje Multimodal ---
        # Langchain espera una lista de dicts o strings para el contenido multimodal.
        # Los dicts deben tener la estructura esperada por el modelo (e.g., {"type": "image_url", "image_url": {"url": "..."}})
        # Asegurarse de que el mensaje no sea None para evitar errores de validación en LangChain
        safe_user_message = user_message if user_message is not None else ""
        content_parts: List[Union[str, Dict[str, Any]]] = [{"type": "text", "text": safe_user_message}]
        if image_base64:
            logger.info("Adjuntando imagen al mensaje para el LLM.")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": image_base64},
            })
        if images_base64:
            logger.info(f"Adjuntando {len(images_base64)} imágenes al mensaje para el LLM.")
            for image in images_base64:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": image},
                })
        
        initial_human_message = HumanMessage(content=content_parts)
        # --- Fin Construcción ---

        initial_state: AgentState = {
            "messages": history_messages + [initial_human_message],
            "account_id": account_id,
            "task_id": task_id,
            "telegram_id": telegram_id,
            "workspace_id": workspace_id,
            "rag_context": rag_context,
            "sources": [],
            "thread_id": thread_id, # Añadir thread_id al estado inicial
            "context": context, # Inyectar el contexto
            "loop_count": 0, # Inicializar contador de bucles
        }

        # Asegurarse de que el historial de mensajes se inicialice con el mensaje del usuario
        # Sanitizar el contenido del mensaje antes de guardarlo
        sanitized_human_message = HumanMessage(
            content=sanitize_json_content(initial_human_message.content),
            additional_kwargs=initial_human_message.additional_kwargs
        )
        await chat_message_history.aadd_messages([sanitized_human_message])

        config: RunnableConfig = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100} # Castear a RunnableConfig con límite aumentado
        final_graph_state = None
        full_response_text = ""
        
        async for chunk_data in agent_app.astream(initial_state, config=config):
            final_graph_state = chunk_data
            # Las actualizaciones de streaming (stream_chunk) ahora se manejan directamente 
            # desde los nodos en core/agent.py para mayor tiempo real y evitar duplicaciones.
            
            # Periodic cancellation check
            if should_check_cancellation:
                chunk_count += 1
                if chunk_count % cancellation_check_interval == 0:
                    try:
                        # Query the ChatTask to check cancelled flag
                        stmt = select(ChatTask).where(ChatTask.id == uuid.UUID(task_id))
                        result = await db_session.execute(stmt)
                        chat_task = result.scalars().first()
                        if chat_task and chat_task.cancelled:
                            logger.info(f"Chat task {task_id} cancelled via DB flag.")
                            raise asyncio.CancelledError()
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"Error checking cancellation status: {e}")
                        # Continue processing; don't fail just because cancellation check failed


        # El estado final es un diccionario con el nombre del último nodo ejecutado como clave.
        if not final_graph_state or "generateResponse" not in final_graph_state:
            logger.error("El grafo no produjo una salida de 'generateResponse' válida.")
            raise ValueError("El grafo no produjo una salida de 'generateResponse' válida.")

        final_node_output = final_graph_state.get("generateResponse", {})
        final_messages = final_node_output.get("messages", [])

        if not final_messages:
            logger.error("La salida final del grafo no contenía mensajes.")
            raise ValueError("La salida final del grafo no contenía mensajes.")

        def _extract_text_content(message: AIMessage) -> str:
            if isinstance(message.content, str):
                return message.content
            if isinstance(message.content, list):
                text = ""
                for part in message.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text += part.get("text", "")
                return text
            return ""

        # Buscar primero el último AIMessage con contenido textual para evitar respuestas finales vacías.
        final_ai_message = next(
            (
                msg
                for msg in reversed(final_messages)
                if isinstance(msg, AIMessage) and _extract_text_content(msg).strip()
            ),
            None,
        )

        # Fallback: si ninguno tiene texto, usar el último AIMessage disponible.
        if not final_ai_message:
            final_ai_message = next((msg for msg in reversed(final_messages) if isinstance(msg, AIMessage)), None)

        if not final_ai_message:
            logger.error("El grafo no produjo un AIMessage en su estado final.")
            raise ValueError("El grafo no produjo un AIMessage en su estado final.")

        # Extraer el texto final para el evento stream_end
        full_response_text = _extract_text_content(final_ai_message)

        # Guardar el AIMessage final completo en el historial
        logger.info(f"DEBUG (create_and_run_agent_streaming): Guardando respuesta final en historial. thread_id: {thread_id}, task_id: {task_id}")
        
        # Reconstruir content_parts para persistencia en base de datos
        ai_content_parts: List[Dict[str, Any]] = []
        
        # 1. Extraer razonamiento si existe
        reasoning_text = final_ai_message.additional_kwargs.get("reasoning") or final_ai_message.additional_kwargs.get("think")
        if reasoning_text:
            ai_content_parts.append({
                "type": "reasoning",
                "content": reasoning_text
            })
            
        # 2. Identificar el último HumanMessage para procesar solo el turno actual
        last_human_idx = -1
        for idx in range(len(final_messages) - 1, -1, -1):
            if isinstance(final_messages[idx], HumanMessage):
                last_human_idx = idx
                break
                
        # 3. Extraer mensajes intermedios del turno actual
        intermediate_messages = []
        if last_human_idx != -1:
            intermediate_messages = final_messages[last_human_idx + 1 : -1]
            
        # 4. Agrupar resultados de herramientas
        tool_results = {}
        for msg in intermediate_messages:
            if isinstance(msg, ToolMessage):
                tool_results[msg.tool_call_id] = msg
                
        # 5. Parsear llamadas de herramientas
        for msg in intermediate_messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_call_id = tool_call.get("id")
                    tool_name = tool_call.get("name")
                    
                    tool_msg = tool_results.get(tool_call_id)
                    status = "end"
                    content = f"Usando {tool_name}..."
                    pty_session = None
                    
                    if tool_msg:
                        content = str(tool_msg.content)
                        if tool_name == "terminal_executor":
                            import re
                            match = re.search(r'data-session-id="([^"]+)"', content)
                            if match:
                                pty_session = {"session_id": match.group(1)}
                                match_cmd = re.search(r'data-cmd="([^"]+)"', content)
                                if match_cmd:
                                    import html
                                    pty_session["command"] = html.unescape(match_cmd.group(1))
                    else:
                        status = "error"
                        
                    ai_content_parts.append({
                        "type": "tool_call",
                        "content": content,
                        "tool_name": tool_name,
                        "status": status,
                        "pty_session": pty_session,
                        "id": tool_call_id
                    })
                    
        # 6. Extraer texto final del AI
        final_text = _extract_text_content(final_ai_message)
        if final_text:
            ai_content_parts.append({
                "type": "text",
                "content": final_text
            })
            
        # 7. Obtener la sesión PTY para el nivel raíz si aplica
        root_pty_session = None
        for part in ai_content_parts:
            if part.get("type") == "tool_call" and part.get("pty_session"):
                root_pty_session = part["pty_session"]
                break
                
        # 8. Modificar additional_kwargs
        additional_kwargs = dict(final_ai_message.additional_kwargs)
        additional_kwargs["content_parts"] = ai_content_parts
        if root_pty_session:
            additional_kwargs["pty_session"] = root_pty_session

        # Sanitizar el contenido del mensaje antes de guardarlo
        sanitized_ai_message = AIMessage(
            content=sanitize_json_content(final_ai_message.content),
            tool_calls=final_ai_message.tool_calls,
            additional_kwargs=additional_kwargs
        )
        await chat_message_history.aadd_messages([sanitized_ai_message])

        # El resto de la lógica para actualizar el título y enviar el evento final
        # Optimization: Calculate message count locally to avoid fetching all messages again
        # Calcular si corresponde renombrar el hilo (aplica siempre, con o sin background_tasks)
        previous_real_messages = [m for m in history_messages if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
        message_count = len(previous_real_messages) + 2  # +1 User, +1 AI

        async with DBSession(SessionLocal) as db:
            thread = await db.get(ChatThread, uuid.UUID(thread_id))
            current_title = thread.title if thread else ""

        should_rename = (
            (current_title == "Nuevo Chat" and message_count >= 2) or
            (message_count >= 10 and message_count % 10 == 0)
        )

        if should_rename:
            from core.agent import force_update_thread_title
            logger.info(f"[AUTO-TÍTULO] Hilo {thread_id} cumple condición para nombrar/renombrar con {message_count} mensajes. Título actual: '{current_title}'")
            # Siempre usar asyncio.create_task ya que esta función corre dentro de un asyncio.Task
            # (background_tasks de FastAPI puede no ser válido en este contexto)
            import asyncio as _asyncio
            _asyncio.create_task(force_update_thread_title(thread_id))
        
        # --- Lógica de Extracción de Fuentes Finales ---
        # Las fuentes ya deberían estar correctamente priorizadas y procesadas en el AIMessage final
        # por la lógica en core/agent.py (específicamente en tool_node y call_model_node).
        # Aquí, simplemente extraemos las fuentes del AIMessage final.
        final_sources = final_ai_message.additional_kwargs.get("sources", [])
        final_reasoning = final_ai_message.additional_kwargs.get("reasoning", "")
        final_model_name = final_ai_message.additional_kwargs.get("model_name")
        
        logger.info(f"DEBUG (create_and_run_agent_streaming): Fuentes finales extraídas del AIMessage: {final_sources}")
        
        await send_personal_message(target_account_id, {
            "type": "stream_end",
            "thread_id": thread_id,
            "taskId": task_id,
            "text": full_response_text,
            "reasoning": final_reasoning,
            "sources": final_sources,
            "model_name": final_model_name,
        }, connection_type=conn_type)

    except asyncio.CancelledError:
        logger.info(f"Chat task {task_id} cancelled by user. Guardando mensaje parcial.")
        try:
            from core.websocket_manager import partial_task_messages, partial_task_reasoning
            from core.agent import sanitize_json_content
            from langchain_core.messages import AIMessage
            
            partial_text = partial_task_messages.pop(task_id, "")
            partial_reasoning = partial_task_reasoning.pop(task_id, "")
            
            if partial_text or partial_reasoning:
                final_kwargs = {"status": "cancelled"}
                if partial_reasoning:
                    final_kwargs["reasoning"] = partial_reasoning
                    
                sanitized_ai_message = AIMessage(
                    content=sanitize_json_content(partial_text),
                    additional_kwargs=final_kwargs
                )
                if 'chat_message_history' in locals() and chat_message_history:
                    await chat_message_history.aadd_messages([sanitized_ai_message])
        except Exception as save_err:
            logger.error(f"Error salvando mensaje parcial: {save_err}")
            
        raise  # Re-raise to ensure task is marked as cancelled
    except Exception as e:
        logger.error(f"Error en streaming agent LangGraph: {e}", exc_info=True)
        try:
            from core.websocket_manager import partial_task_messages, partial_task_reasoning
            from core.agent import sanitize_json_content
            from langchain_core.messages import AIMessage
            
            partial_text = partial_task_messages.pop(task_id, "")
            partial_reasoning = partial_task_reasoning.pop(task_id, "")
            
            if partial_text or partial_reasoning:
                final_kwargs = {"status": "error"}
                if partial_reasoning:
                    final_kwargs["reasoning"] = partial_reasoning
                    
                sanitized_ai_message = AIMessage(
                    content=sanitize_json_content(partial_text),
                    additional_kwargs=final_kwargs
                )
                if 'chat_message_history' in locals() and chat_message_history:
                    await chat_message_history.aadd_messages([sanitized_ai_message])
        except Exception as save_err:
            logger.error(f"Error salvando mensaje parcial tras excepcion: {save_err}")
            
        await send_personal_message(target_account_id, {
            "type": "error",
            "thread_id": thread_id,
            "taskId": task_id,
            "message": str(e)
        }, connection_type=conn_type)

@router.post("/tasks/{task_id}/cancel")
async def cancel_chat_task(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Cancela una tarea de chat en ejecución.
    """
    if task_id not in active_chat_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = active_chat_tasks[task_id]
    if task_info["account_id"] != current_account_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")

    task = task_info["task"]
    if task.done():
        raise HTTPException(status_code=400, detail="Task already completed")

    task.cancel()
    # The task's done callback will clean up the registry
    return {"status": "cancelled", "task_id": task_id}
