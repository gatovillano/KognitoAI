# api/chat.py

import logging
import uuid
import re
import json
import asyncio
import os
import pickle
from typing import Optional, AsyncGenerator, Any, List, Dict
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
from utils.security import get_current_account_id, decode_access_token # Añadido decode_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.database import SessionLocal, ChatThread, settings, Workspace
from core.llm_manager import get_main_llm
from tools.deep_research_tool import DeepResearchTool
from tools.add_web_to_rag_tool import AddWebToRAGTool
from tools.ddg_search_tool import create_ddg_search_tool
from core.websocket_manager import send_personal_message
from langchain_core.runnables import RunnableConfig # Importar RunnableConfig

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
    document_url: Optional[str] = None  # Campo para URL de documentos
    mode: Optional[str] = None
    rag_context: Optional[str] = None # Contexto RAG: [{'type': 'document', 'id': '...'}, {'type': 'collection', 'id': '...'}]

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
    document_url: Optional[str] = None

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
    title: Optional[str] = "Nuevo Chat"
    platform: Optional[str] = "web"
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db),
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
            if workspace_id.lower() == "none":
                base_query = base_query.where(ChatThread.workspace_id == None)
            else:
                base_query = base_query.where(ChatThread.workspace_id == uuid.UUID(workspace_id))

        # Consulta para el total de hilos
        total_stmt = select(func.count()).select_from(base_query.alias())
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
    db: AsyncSession = Depends(get_db),
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
                image_content = None
                
                if isinstance(msg.content, list):
                    # Handle multimodal content
                    for part in msg.content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                text_content += part.get("text", "")
                            elif part.get("type") == "image_url":
                                image_url_data = part.get("image_url")
                                if isinstance(image_url_data, dict):
                                    image_content = image_url_data.get("url")
                        else:
                            text_content += str(part)
                else:
                    text_content = str(msg.content)

                real_messages.append(Message(
                    text=text_content,
                    sender="user" if isinstance(msg, HumanMessage) else "ai",
                    created_at=msg.additional_kwargs.get("created_at", datetime.now(timezone.utc)),
                    image_base64=image_content
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

@router.get("/threads/{thread_id}", summary="Obtener detalles de un hilo de chat")
async def get_thread(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
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
async def pin_thread(thread_id: str, request: PinThreadRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
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
async def delete_thread(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
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
async def generate_thread_title(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
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
        'voice': request.voice if request.voice else 'es-MX-JorgeNeural',
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

@router.post("/chat", status_code=status.HTTP_202_ACCEPTED, summary="Procesar Mensaje de Chat en Segundo Plano")
async def handle_chat(
    background_tasks: BackgroundTasks,
    request: ChatRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
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
        document_url=request.document_url,
        mode=request.mode,
        rag_context=parsed_rag_context,
        background_tasks=background_tasks,
        workspace_id=workspace_id
    )

    # Devolver una respuesta inmediata
    return {"thread_id": request.thread_id, "taskId": task_id}


async def create_and_run_agent_streaming(
    account_id: str,
    thread_id: str,
    task_id: str, # Nuevo taskId para seguimiento
    telegram_id: Optional[int],
    user_message: str,
    image_base64: Optional[str] = None,
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
    from core.agent import create_langgraph_agent
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_community.chat_message_histories import PostgresChatMessageHistory
    from core.config import settings
    from core.database import LangchainPgEmbedding
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    from core.websocket_manager import send_personal_message # Asegurarse de que esté importado aquí también si es necesario

    logger.info(f"--- Iniciando agente LangGraph para account_id: {account_id}, thread_id: {thread_id} ---")

    try:
        # Enviar mensaje de inicio de stream
        await send_personal_message(account_id, {
            "type": "stream_start",
            "thread_id": thread_id,
            "taskId": task_id,
        })

        # --- Preparación Inicial ---
        agent_app = create_langgraph_agent()
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
        content_parts = [{"type": "text", "text": user_message}]
        if image_base64:
            # Asumimos que image_base64 es una data URL (p.ej., "data:image/jpeg;base64,...")
            # y la pasamos directamente. Los modelos de Google aceptan este formato.
            logger.info("Adjuntando imagen al mensaje para el LLM.")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": image_base64},
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
        await chat_message_history.aadd_messages([initial_human_message])

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
        await chat_message_history.aadd_messages([final_ai_message])

        # El resto de la lógica para actualizar el título y enviar el evento final
        if background_tasks:
            updated_history = await chat_message_history.aget_messages()
            real_messages = [m for m in updated_history if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
            message_count = len(real_messages)

            async with SessionLocal() as db:
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
        
        await send_personal_message(account_id, {
            "type": "stream_end",
            "thread_id": thread_id,
            "taskId": task_id,
        })

    except Exception as e:
        logger.error(f"Error en streaming agent LangGraph: {e}", exc_info=True)
        await send_personal_message(account_id, {
            "type": "error",
            "thread_id": thread_id,
            "taskId": task_id,
            "message": str(e)
        })

@router.websocket("/ws-transcribe/{account_id}")
async def websocket_transcribe(websocket: WebSocket, account_id: str):
    logger.debug(f"DEBUG: Entrando a websocket_transcribe para account_id: {account_id}")
    await websocket.accept() # Aceptar la conexión primero para poder enviar mensajes de error
    
    token = websocket.url.query_params.get("token")
    logger.info(f"DEBUG WS Transcribe Backend: Token recibido (parcial): {token[:30]}...")
    logger.info(f"DEBUG WS Transcribe Backend: account_id de la URL: {account_id}")
    payload = decode_access_token(token)
    logger.info(f"DEBUG WS Transcribe Backend: Payload decodificado: {payload}")
    authenticated_account_id = payload.get("sub")
    logger.info(f"DEBUG WS Transcribe Backend: authenticated_account_id del token: {authenticated_account_id}")
    if not token:
        logger.warning(f"Intento de conexión de transcripción sin token para account_id: {account_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token de autenticación no proporcionado")
        return

    try:
        # Verificar el token de autenticación
        try:
            # --- INICIO DE LOS LOGS AÑADIDOS EN EL BACKEND ---
            logger.info(f"DEBUG WS Transcribe Backend: Token recibido (parcial): {token[:30]}...")
            logger.info(f"DEBUG WS Transcribe Backend: account_id de la URL: {account_id}")
            # --- FIN DE LOS LOGS AÑADIDOS EN EL BACKEND ---

            payload = decode_access_token(token)
            authenticated_account_id = payload.get("sub")

            # --- INICIO DE LOS LOGS AÑADIDOS EN EL BACKEND ---
            logger.info(f"DEBUG WS Transcribe Backend: Payload decodificado: {payload}")
            logger.info(f"DEBUG WS Transcribe Backend: authenticated_account_id del token: {authenticated_account_id}")
            # --- FIN DE LOS LOGS AÑADIDOS EN EL BACKEND ---

            if authenticated_account_id != account_id:
                logger.warning(f"Intento de conexión de transcripción no autorizado para account_id: {account_id} con token de {authenticated_account_id}. Razón: Conflicto de ID de usuario.")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No autorizado: Conflicto de ID de usuario")
                return
        except HTTPException as e:
            logger.error(f"Error de autenticación de token en WebSocket de transcripción para la cuenta {account_id}: {e.detail}. Razón: {e.detail}")
            await websocket.close(code=e.status_code, reason=f"Error de autenticación: {e.detail}")
            return
        except Exception as e:
            logger.error(f"Error inesperado al decodificar token en WebSocket de transcripción para la cuenta {account_id}: {e}", exc_info=True)
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Error interno del servidor")
            return

        logger.info(f"WebSocket de transcripción conectado y autenticado para la cuenta: {account_id}")
    except HTTPException as e:
        logger.error(f"Error de autenticación en WebSocket de transcripción para la cuenta {account_id}: {e.detail}")
        await websocket.close(code=e.status_code, reason=e.detail)
        return
    except Exception as e:
        logger.error(f"Error inesperado al establecer conexión WebSocket de transcripción para la cuenta {account_id}: {e}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Error interno del servidor")
        return

    # Conectar el WebSocket al manager
    await websocket_manager.connect(websocket, account_id, "transcribe")

    whisper_model = await get_whisper_model()
    if not whisper_model:
        logger.error("Modelo de Whisper no disponible para transcripción en streaming.")
        await websocket.send_json({"type": "error", "message": "Modelo de transcripción no disponible."})
        await websocket_manager.disconnect(websocket, account_id, "transcribe") # Desconectar en caso de error
        return

    transcriber = StreamingTranscriber(whisper_model)

    try:
        while True:
            data = await websocket.receive_bytes()
            
            # Asumimos que el frontend envía el formato de archivo junto con el audio
            # Por ahora, lo hardcodeamos a "webm" ya que es lo que esperamos del frontend
            file_format = "webm" 

            transcript_chunk = await transcriber.process_audio_chunk(data, file_format)
            if transcript_chunk:
                await websocket.send_json({"type": "transcript_chunk", "text": transcript_chunk})

    except WebSocketDisconnect:
        logger.info(f"WebSocket de transcripción desconectado para la cuenta: {account_id}")
        final_transcript = await transcriber.finalize_transcription()
        if final_transcript:
            await websocket.send_json({"type": "final_transcript", "text": final_transcript})
    except Exception as e:
        logger.error(f"Error en WebSocket de transcripción para la cuenta {account_id}: {e}", exc_info=True)
        await websocket.send_json({"type": "error", "message": f"Error en la transcripción: {e}"})
    finally:
        logger.info(f"Cerrando conexión WebSocket de transcripción para {account_id}")
        websocket_manager.disconnect(websocket, account_id, "transcribe") # Asegurarse de desconectar