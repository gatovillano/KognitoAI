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

# Usamos el nombre del servicio Docker y el puerto interno correcto.
TTS_SERVICE_URL = "http://openai-edge-tts:5050/v1/audio/speech"

from sqlalchemy import update, Integer, cast, func # Added cast # Added Integer # Added func


from utils.audio_transcriber import transcribe_audio_file, StreamingTranscriber, get_whisper_model
from utils.security import get_current_account_id, get_current_user, get_current_user_from_websocket_query_param, decode_access_token # Añadido decode_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.database import SessionLocal, ChatThread, settings, Workspace
from core.llm_manager import get_main_llm
from tools.add_web_to_rag_tool import AddWebToRAGTool
from tools.ddg_search_tool import create_ddg_search_tool
from core.websocket_manager import send_personal_message
from langchain_core.runnables import RunnableConfig # Importar RunnableConfig
from core.dependencies import get_db_session # Importar dependencia centralizada
from utils.db_session import DBSession # Importar DBSession para tareas en background

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# get_db eliminado en favor de core.dependencies.get_db_session

# --- Modelos para el Chat ---
class Source(BaseModel):
    """Define la estructura de datos para una fuente citada."""
    id: int
    title: str
    url: str
    snippet: str
    type: str = "web"  # "web", "document", "memory", etc.

class ChatRequest(BaseModel):
    """Define la estructura de datos para una solicitud de mensaje de chat al agente."""
    thread_id: str
    account_id: str
    telegram_id: Optional[int] = None  # Hacemos telegram_id opcional
    user_message: str
    image_base64: Optional[str] = None
    images_base64: Optional[List[str]] = None
    document_url: Optional[str] = None  # Campo para URL de documentos
    mode: Optional[str] = None
    rag_context: Optional[str] = None # Contexto RAG: [{'type': 'document', 'id': '...'}, {'type': 'collection', 'id': '...'}]
    workspace_id: Optional[str] = None  # Campo para el ID del workspace

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

class PaginatedChatMessagesResponse(BaseModel):
    total: int
    messages: List[Message]





class TextToSpeechRequest(BaseModel):
    """Define la estructura de datos para una solicitud de conversión de texto a voz."""
    text: str
    voice: Optional[str] = None  # Voz opcional para la conversión

class PinThreadRequest(BaseModel):
    """Define la estructura de datos para una solicitud de fijar/desfijar un hilo de chat."""
    isPinned: bool

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
            created_at=datetime.now(timezone.utc) # Asegurarse de que created_at se establece
        )
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        logger.info(f"Nuevo hilo creado: {new_thread.id} para la cuenta {current_account_id}")
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
    con opción de filtrar por workspace y con paginación.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)
        
        # Base query
        base_query = select(ChatThread).where(ChatThread.account_id == account_uuid)
        
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
                created_at=thread.created_at
            ) for thread in thread_list
        ]

        return PaginatedThreadsResponse(total=total_threads, threads=threads_response)

    except ValueError:
        raise HTTPException(status_code=400, detail="El ID de la cuenta o del workspace no es un UUID válido.")
    except Exception as e:
        logger.error(f"Error al obtener la lista de hilos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener la lista de hilos de chat.")

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
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=thread_id,
            table_name="langchain_chat_history",
        )
        
        all_messages = await chat_message_history.aget_messages()
        
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
                
                real_messages.append(Message(
                    text=text_content,
                    sender="user" if isinstance(msg, HumanMessage) else "ai",
                    created_at=msg.additional_kwargs.get("created_at", datetime.now(timezone.utc)),
                    image_base64=image_contents[0] if image_contents else None,
                    images_base64=image_contents if len(image_contents) > 1 else None,
                    sources=message_sources # Asignar las fuentes extraídas
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
                "thread_id": str(thread_id_str),
                "thread_title": thread_title,
                "content": text_content,
                "sender": sender,
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

@router.post("/text-to-speech", summary="Generar audio desde texto")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Recibe texto, lo envía al servicio interno de TTS y devuelve el audio como un stream.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")

    # Pre-procesar el texto para eliminar elementos no deseados
    text_to_speak = request.text
    # 1. Eliminar bloques de código cercados (```...```)
    text_to_speak = re.sub(r'```.*?```', '', text_to_speak, flags=re.DOTALL)
    # 2. Eliminar código en línea (`...`)
    # text_to_speak = re.sub(r'`[^`]*`', '', text_to_speak)
    # 3. Eliminar caracteres de puntuación que no se quieren leer
    # text_to_speak = re.sub(r'[[]{}()#*_]', '', text_to_speak)
    # 4. Limpiar espacios en blanco múltiples
    text_to_speak = re.sub(r'\s+', ' ', text_to_speak).strip()

    if not text_to_speak:
        return StreamingResponse(BytesIO(), media_type="audio/wav")

    # Parámetros para open-edgetts.
    tts_payload = {
        'input': text_to_speak,
        'voice': request.voice if request.voice else 'es-MX-DaliaNeural',
        'model': 'edge-tts',
        'speed': 1.0,
    }

    try:
        async with httpx.AsyncClient() as client:
            # Hacemos una petición POST al servicio de TTS
            response = await client.post(TTS_SERVICE_URL, json=tts_payload, timeout=30.0)     
            response.raise_for_status()
            # Devolvemos el contenido de audio directamente como un stream
            return StreamingResponse(BytesIO(response.content), media_type="audio/wav")

    except httpx.RequestError as e:
        logger.error(f"Error de red contactando el servicio TTS: {e}")
        raise HTTPException(status_code=503, detail="El servicio de voz no está disponible.")
    except httpx.HTTPStatusError as e:
        logger.error(f"El servicio TTS devolvió un error {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=502, detail="Error en el servicio de generación de voz.")

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

        if transcription is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo transcribir el audio.")

        return {"transcription": transcription}
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
    
    logger.debug(f"DEBUG (api/chat.py): Llamando create_and_run_agent_streaming con thread_id: {request.thread_id}") # <--- NUEVO LOG
    # Añadir la ejecución del agente como una tarea en segundo plano
    background_tasks.add_task(
        create_and_run_agent_streaming,
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
        workspace_id=workspace_id
    )
    
    # Devolver una respuesta inmediata
    return {"thread_id": request.thread_id, "taskId": task_id}

@router.post("/chat-form", status_code=status.HTTP_202_ACCEPTED, summary="Procesar Mensaje de Chat con FormData")
async def handle_chat_form(
    background_tasks: BackgroundTasks,
    thread_id: str = Form(...),
    account_id: str = Form(...),
    telegram_id: Optional[int] = Form(None),
    user_message: str = Form(...),
    image_base64: Optional[str] = Form(None),
    images_base64: Optional[List[str]] = Form(None),
    document_url: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
    rag_context: Optional[str] = Form(None),
    workspace_id: Optional[str] = Form(None),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Acepta una solicitud de chat con FormData, inicia una tarea en segundo plano para procesarla
    y devuelve inmediatamente una respuesta 202 Accepted. Los resultados se envían
    a través de WebSocket.
    """
    task_id = str(uuid.uuid4())
    
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
    
    logger.debug(f"DEBUG (api/chat.py): Llamando create_and_run_agent_streaming con thread_id: {thread_id}") # <--- NUEVO LOG
    # Añadir la ejecución del agente como una tarea en segundo plano
    background_tasks.add_task(
        create_and_run_agent_streaming,
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
        workspace_id=final_workspace_id
    )
    
    # Devolver una respuesta inmediata
    return {"thread_id": thread_id, "taskId": task_id}


async def create_and_run_agent_streaming(
    account_id: str,
    thread_id: str,
    task_id: str, # Nuevo taskId para seguimiento
    telegram_id: Optional[int],
    user_message: str,
    image_base64: Optional[str] = None,
    images_base64: Optional[List[str]] = None,
    document_url: Optional[str] = None,
    mode: Optional[str] = None,
    rag_context: Optional[List[Dict[str, str]]] = None,
    background_tasks: Optional[Any] = None,
    workspace_id: Optional[str] = None,
    k: int = 5
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
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=thread_id,
            table_name="langchain_chat_history",
        )
        history_messages = await chat_message_history.aget_messages()

        # El rag_context se pasará directamente al estado del agente, no se pre-procesa aquí.
        # El user_message se mantiene sin modificar aquí.

        # --- Construcción del Mensaje Multimodal ---
        # Langchain espera una lista de dicts o strings para el contenido multimodal.
        # Los dicts deben tener la estructura esperada por el modelo (e.g., {"type": "image_url", "image_url": {"url": "..."}})
        content_parts: List[Union[str, Dict[str, Any]]] = [{"type": "text", "text": user_message}]
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
        }

        # Asegurarse de que el historial de mensajes se inicialice con el mensaje del usuario
        # Sanitizar el contenido del mensaje antes de guardarlo
        sanitized_human_message = HumanMessage(
            content=sanitize_json_content(initial_human_message.content),
            additional_kwargs=initial_human_message.additional_kwargs
        )
        await chat_message_history.aadd_messages([sanitized_human_message])

        config: RunnableConfig = {"configurable": {"thread_id": thread_id}} # Castear a RunnableConfig
        final_graph_state = None
        async for chunk_data in agent_app.astream(initial_state, config=config):
            final_graph_state = chunk_data

        # El estado final es un diccionario con el nombre del último nodo ejecutado como clave.
        if not final_graph_state or "generateResponse" not in final_graph_state:
            logger.error("El grafo no produjo una salida de 'generateResponse' válida.")
            raise ValueError("El grafo no produjo una salida de 'generateResponse' válida.")

        final_node_output = final_graph_state.get("generateResponse", {})
        final_messages = final_node_output.get("messages", [])

        if not final_messages:
            logger.error("La salida final del grafo no contenía mensajes.")
            raise ValueError("La salida final del grafo no contenía mensajes.")

        # Buscar el último AIMessage en el historial del estado final
        final_ai_message = next((msg for msg in reversed(final_messages) if isinstance(msg, AIMessage)), None)

        if not final_ai_message:
            logger.error("El grafo no produjo un AIMessage en su estado final.")
            raise ValueError("El grafo no produjo un AIMessage en su estado final.")

        # Guardar el AIMessage final completo en el historial
        logger.info(f"DEBUG (create_and_run_agent_streaming): Guardando respuesta final en historial. thread_id: {thread_id}, task_id: {task_id}")
        # Sanitizar el contenido del mensaje antes de guardarlo
        sanitized_ai_message = AIMessage(
            content=sanitize_json_content(final_ai_message.content),
            tool_calls=final_ai_message.tool_calls,
            additional_kwargs=final_ai_message.additional_kwargs
        )
        await chat_message_history.aadd_messages([sanitized_ai_message])

        # El resto de la lógica para actualizar el título y enviar el evento final
        # Optimization: Calculate message count locally to avoid fetching all messages again
        if background_tasks:
            # updated_history = await chat_message_history.aget_messages() # Removed
            # real_messages = [m for m in updated_history if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
            
            # Estimate count: previous history + user message + AI message
            # We filter summary messages from history_messages first
            previous_real_messages = [m for m in history_messages if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
            message_count = len(previous_real_messages) + 2 # +1 User, +1 AI

            async with DBSession(SessionLocal) as db:
                thread = await db.get(ChatThread, uuid.UUID(thread_id))
                current_title = thread.title if thread else ""

            should_rename = (
                (current_title == "Nuevo Chat" and message_count >= 3) or
                (message_count >= 10 and message_count % 10 == 0)
            )

            if should_rename:
                from core.agent import force_update_thread_title
                logger.info(f"[AUTO-TÍTULO] Hilo {thread_id} cumple condición para nombrar/renombrar con {message_count} mensajes. Título actual: '{current_title}'")
                background_tasks.add_task(force_update_thread_title, thread_id)
        
        # --- Lógica de Extracción de Fuentes Finales ---
        # Las fuentes ya deberían estar correctamente priorizadas y procesadas en el AIMessage final
        # por la lógica en core/agent.py (específicamente en tool_node y call_model_node).
        # Aquí, simplemente extraemos las fuentes del AIMessage final.
        final_sources = final_ai_message.additional_kwargs.get("sources", [])
        
        logger.info(f"DEBUG (create_and_run_agent_streaming): Fuentes finales extraídas del AIMessage: {final_sources}")
        
        await send_personal_message(target_account_id, {
            "type": "stream_end",
            "thread_id": thread_id,
            "taskId": task_id,
            "sources": final_sources,
        }, connection_type=conn_type)

    except Exception as e:
        logger.error(f"Error en streaming agent LangGraph: {e}", exc_info=True)
        await send_personal_message(target_account_id, {
            "type": "error",
            "thread_id": thread_id,
            "taskId": task_id,
            "message": str(e)
        }, connection_type=conn_type)
