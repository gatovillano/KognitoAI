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
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime, timezone # Importar datetime y timezone

# Usamos el nombre del servicio Docker y el puerto interno correcto.
TTS_SERVICE_URL = "http://openai-edge-tts:5050/v1/audio/speech"

from sqlalchemy import update, Integer, cast, func # Added cast # Added Integer # Added func


from utils.audio_transcriber import transcribe_audio_file
from utils.security import get_current_account_id
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
        threads_stmt = base_query.order_by(ChatThread.created_at.asc()).offset(skip).limit(limit)
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
                # Convertir el contenido a string si es una lista o un objeto
                content = msg.content
                if isinstance(content, list):
                    content = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in content])
                else:
                    content = str(content)

                real_messages.append(Message(
                    text=content,
                    sender="user" if isinstance(msg, HumanMessage) else "ai",
                    created_at=msg.additional_kwargs.get("created_at", datetime.now(timezone.utc))
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
    logger.info(f"Recibida solicitud para transcribir el archivo: {file.filename}")
    
    # Leer el contenido del archivo en memoria
    try:
        audio_bytes = await file.read()
        audio_file_io = BytesIO(audio_bytes)
    except Exception as e:
        logger.error(f"Error al leer el archivo cargado: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo leer el archivo de audio.")

    # Transcribir el audio
    transcription = await transcribe_audio_file(audio_file_io)

    if transcription is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo transcribir el audio.")

    return {"transcription": transcription}

@router.post("/chat", response_model=ChatResponse, summary="Procesar Mensaje de Chat")
async def handle_chat(
    background_tasks: BackgroundTasks,
    request: ChatRequest, # Use ChatRequest model for JSON body
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    Endpoint principal para procesar mensajes de chat con el agente de IA.
    Requiere autenticación JWT.
    """
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

    logger.info(f"Petición de chat recibida de la cuenta: {request.account_id} con modo: {request.mode}")
    
    # Obtener el workspace_id del ChatThread asociado
    workspace_id = None
    
    # Logs de depuración para verificar thread_id y account_id
    logger.info(f"DEBUG: Intentando recuperar ChatThread con thread_id: {request.thread_id} y account_id: {current_account_id}")
    
    thread = await db.scalar(select(ChatThread).where(  # type: ignore[arg-type]
        ChatThread.id == uuid.UUID(request.thread_id),
        ChatThread.account_id == uuid.UUID(current_account_id)
    ))
    if not thread:
        logger.warning(f"No se encontró el hilo {request.thread_id} para la cuenta {current_account_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hilo de chat con id {request.thread_id} no encontrado.")

    if thread.workspace_id:
        workspace_id = str(thread.workspace_id)
        logger.info(f"Recuperado workspace_id {workspace_id} para el hilo {request.thread_id}.")
    else:
        logger.info(f"El hilo {request.thread_id} no tiene un workspace_id asociado (opcional).")

    # Implementar la lógica principal del agente aquí y devolver la respuesta real
    final_agent_response = ""
    final_tool_code = None
    final_sources = []

    # Llamar a la función que ahora envía los mensajes por WebSocket
    await create_and_run_agent_streaming(
        account_id=request.account_id,
        thread_id=request.thread_id,
        telegram_id=request.telegram_id,
        user_message=request.user_message,
        image_base64=request.image_base64,
        document_url=request.document_url,
        mode=request.mode,
        rag_context=parsed_rag_context, # rag_context is now directly a list
        background_tasks=background_tasks,
        workspace_id=workspace_id
    )

    # Después de que el agente ha terminado y los mensajes se han guardado en el historial,
    # recuperamos el último mensaje del historial para devolverlo como respuesta final HTTP.
    db_sync_url = settings.database_url.replace("+psycopg", "")
    chat_message_history = PostgresChatMessageHistory(
        connection_string=db_sync_url,
        session_id=request.thread_id, # Changed to request.thread_id
        table_name="langchain_chat_history",
    )
    history_messages = await chat_message_history.aget_messages()
    
    if history_messages and isinstance(history_messages[-1], AIMessage):
        content = history_messages[-1].content
        if isinstance(content, list):
            # Convert list content to string, handling dicts if present
            final_agent_response = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in content])
        else:
            final_agent_response = str(content) # Ensure it's a string

        # Aquí podrías intentar extraer tool_code y sources si se guardan en additional_kwargs
        # o si tienes una forma de recuperarlos del historial.
        # Por ahora, los dejaremos como None/vacíos si no se guardan explícitamente en el historial.
        final_tool_code = history_messages[-1].additional_kwargs.get('tool_code')
        final_sources = history_messages[-1].additional_kwargs.get('sources', [])


    logger.info(f"DEBUG (handle_chat): Retornando ChatResponse con response_text: {final_agent_response[:100]}..., tool_code: {final_tool_code}, sources: {len(final_sources)} fuentes.")
    return ChatResponse(response_text=final_agent_response, tool_code=final_tool_code, sources=final_sources)


async def create_and_run_agent_streaming(
    account_id: str,
    thread_id: str,
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
    from core.agent import create_langgraph_agent, AgentState
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_community.chat_message_histories import PostgresChatMessageHistory
    from core.config import settings
    from core.database import LangchainPgEmbedding
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    from core.websocket_manager import send_personal_message # Asegurarse de que esté importado aquí también si es necesario

    logger.info(f"--- Iniciando agente LangGraph para account_id: {account_id}, thread_id: {thread_id} ---")

    llm_task_id = str(uuid.uuid4()) # Generar un ID único para esta tarea del LLM

    try:
        # Enviar mensaje de inicio del LLM
        await send_personal_message(account_id, {
            "type": "llm_start",
            "thread_id": thread_id,
            "task_id": llm_task_id,
            "message": "El agente está pensando..."
        })

        # --- Preparación del Contexto RAG ---
        context_text = ""
        if rag_context:
            logger.info(f"Enriqueciendo contexto con {len(rag_context)} item(s) de RAG.")
            document_ids_to_fetch = [item['id'] for item in rag_context if item.get('type') == 'document']
            
            if document_ids_to_fetch:
                async with SessionLocal() as session:
                    stmt = (
                        select(LangchainPgEmbedding)
                        .filter(LangchainPgEmbedding.cmetadata['document_id'].astext.in_(document_ids_to_fetch))
                        .order_by(cast(LangchainPgEmbedding.cmetadata['chunk_index'].astext, Integer))
                    )
                    result = await session.execute(stmt)
                    all_chunks = result.scalars().all()

                    docs_content = {}
                    for chunk in all_chunks:
                        doc_id = chunk.cmetadata.get('document_id')
                        if doc_id not in docs_content:
                            docs_content[doc_id] = {
                                'title': chunk.cmetadata.get('title', chunk.cmetadata.get('file_name')),
                                'chunks': []
                            }
                        docs_content[doc_id]['chunks'].append(chunk.document)

                    for doc_id, data in docs_content.items():
                        full_content = "".join(data['chunks'])
                        context_text += f"\n\n--- Contexto del Documento: {data['title']} ---\n"
                        context_text += f"Contenido: {full_content}\n"
                        context_text += "--- Fin del Contexto del Documento ---"

        if context_text:
            logger.info("Contexto RAG preparado para el LLM.")

        # --- Preparación Inicial ---
        agent_app = create_langgraph_agent()
        db_sync_url = settings.database_url.replace("+psycopg", "")
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=thread_id,
            table_name="langchain_chat_history",
        )
        history_messages = await chat_message_history.aget_messages()

        user_message_with_rag_context = HumanMessage(
            content=user_message,
            additional_kwargs={'rag_context': rag_context} if rag_context else {}
        )

        # Pre-procesar el user_message para incluir el contexto RAG si existe
        if context_text:
            user_message = f"{user_message}\n\n--- Contexto RAG ---\n{context_text}\n--- Fin Contexto RAG ---"

        initial_state: AgentState = { # Explicitly cast to AgentState
            "messages": history_messages + [HumanMessage(content=user_message)],
            "account_id": account_id,
            "telegram_id": telegram_id,
            "workspace_id": workspace_id,
            "rag_context": rag_context,
            "sources": [],
        }

        # Asegurarse de que el historial de mensajes se inicialice con el mensaje del usuario
        await chat_message_history.aadd_messages([HumanMessage(content=user_message)])

        config: RunnableConfig = {"configurable": {"thread_id": thread_id}} # Castear a RunnableConfig
        final_state = None
        full_response_content = "" # Inicializar aquí

        # Iterar sobre los chunks del astream
        async for chunk in agent_app.astream(initial_state, config=config):
            # LangGraph emite un diccionario con el nombre del nodo como clave
            # y el estado actualizado de ese nodo como valor.
            # Aquí, solo nos interesa el nodo 'generateResponse' y 'action'
            # para el streaming al cliente.

            if "generateResponse" in chunk:
                # Este es el nodo que genera la respuesta final del LLM
                # y contiene el AIMessage completo.
                # Extraemos el mensaje y lo enviamos caracter por caracter.
                final_response_message = chunk["generateResponse"]["messages"][-1]
                if isinstance(final_response_message, AIMessage):
                    # Asegurarse de que el contenido es un string o convertirlo
                    content_to_stream = final_response_message.content
                    if isinstance(content_to_stream, list):
                        # Si es una lista de partes de contenido (ej. para multimodal), unirlas
                        content_to_stream = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in content_to_stream])
                    else:
                        content_to_stream = str(content_to_stream)

                    # Si el AIMessage tiene tool_calls, enviarlos primero
                    if final_response_message.tool_calls:
                        tool_code_to_send = json.dumps([
                            {
                                "name": tc["name"],
                                "arguments": tc["args"],
                            }
                            for tc in final_response_message.tool_calls
                        ])
                        await send_personal_message(account_id, {
                            "type": "tool_code",
                            "thread_id": thread_id,
                            "task_id": llm_task_id,
                            "tool_code": tool_code_to_send
                        })
                        logger.info(f"DEBUG (create_and_run_agent_streaming): Enviado tool_code durante streaming: {tool_code_to_send}")

                    for char in content_to_stream:
                        full_response_content += char
                        await send_personal_message(account_id, {
                            "type": "llm_chunk",
                            "thread_id": thread_id,
                            "task_id": llm_task_id,
                            "chunk": char
                        })
                        await asyncio.sleep(0.001) # Pequeña pausa para simular streaming
                    final_state = chunk["generateResponse"] # Guardar el estado final

            elif "action" in chunk:
                # Este nodo representa la ejecución de una herramienta.
                # LangGraph devuelve el ToolMessage después de la ejecución.
                tool_message = chunk["action"]["messages"][-1]
                if isinstance(tool_message, ToolMessage):
                    # --- MODIFICACIÓN: No enviar el resultado crudo de la herramienta al frontend ---
                    # El resultado completo (tool_message.content) es para el LLM, no para el usuario.
                    # Solo notificamos que la herramienta terminó.
                    await send_personal_message(account_id, {
                        "type": "tool_status",
                        "thread_id": thread_id,
                        "task_id": llm_task_id,
                        "tool_name": tool_message.name or "herramienta",
                        "status": "end",
                        "message": f"Herramienta '{tool_message.name or 'herramienta'}' finalizada.",
                        # "result": tool_message.content # ELIMINADO
                    })
            
            # Otros estados intermedios del agente para notificaciones de "pensando"
            if "agent" in chunk: # El nodo 'agent' es el que llama al LLM para decidir
                # Podemos usar esto para enviar un estado de "pensando" o "analizando"
                if any(isinstance(msg, AIMessage) and msg.tool_calls for msg in chunk["agent"]["messages"]):
                     # El agente decidió usar una herramienta
                    tool_call_names = ", ".join([tc.get("name", "herramienta desconocida") for tc in chunk["agent"]["messages"][-1].tool_calls])
                    await send_personal_message(account_id, {"type": "llm_status", "thread_id": thread_id, "task_id": llm_task_id, "message": f"El agente está usando: {tool_call_names} 🛠️"})
                else:
                    # El agente está pensando en una respuesta
                    await send_personal_message(account_id, {"type": "llm_status", "thread_id": thread_id, "task_id": llm_task_id, "message": "El agente está pensando... 🤔"})

        # Al finalizar el bucle astream, debemos haber recolectado la respuesta final
        if not final_state:
            logger.error("El grafo no produjo un estado final válido.")
            raise ValueError("El grafo no produjo un estado final válido.")
        
        # Guardar el AIMessage final en el historial después de que se haya transmitido
        # Esto asegura que el historial refleje la conversación completa.
        final_ai_message_kwargs = {}
        if final_state and "generateResponse" in final_state and final_state["generateResponse"]["messages"]:
            last_ai_message = final_state["generateResponse"]["messages"][-1]
            if isinstance(last_ai_message, AIMessage):
                if last_ai_message.tool_calls:
                    final_ai_message_kwargs["tool_calls"] = last_ai_message.tool_calls
                if last_ai_message.additional_kwargs.get("sources"):
                    final_ai_message_kwargs["sources"] = last_ai_message.additional_kwargs["sources"]

        await chat_message_history.aadd_messages([AIMessage(content=full_response_content, additional_kwargs=final_ai_message_kwargs)])


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
        
        tool_code_to_send = None
        sources_to_send = []

        for msg in final_state["messages"]:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                tool_code_to_send = json.dumps([
                    {
                        "name": tc["name"],
                        "arguments": tc["args"],
                    }
                    for tc in msg.tool_calls
                ])
                logger.info(f"DEBUG (create_and_run_agent_streaming): Encontrado tool_code en AIMessage: {tool_code_to_send}")
                break

        await send_personal_message(account_id, {
            "type": "llm_end",
            "thread_id": thread_id,
            "task_id": llm_task_id,
            "message": "Respuesta completada",
            "tool_code": tool_code_to_send,
            "sources": sources_to_send
        })

    except Exception as e:
        logger.error(f"Error en streaming agent LangGraph: {e}", exc_info=True)
        await send_personal_message(account_id, {
            "type": "llm_error",
            "thread_id": thread_id,
            "task_id": llm_task_id,
            "message": str(e)
        })




@router.post("/chat/stream")
async def handle_chat_stream(
    background_tasks: BackgroundTasks,
    request: ChatRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para procesar mensajes de chat con el agente de IA y devolver un stream de eventos.
    """
    parsed_rag_context = None
    if request.rag_context:
        try:
            parsed_rag_context = json.loads(request.rag_context)
            if not isinstance(parsed_rag_context, list):
                raise ValueError("rag_context no es una lista válida.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error al parsear rag_context: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de rag_context inválido.")

    logger.info(f"Petición de chat stream recibida de la cuenta: {request.account_id} con modo: {request.mode}")

    thread = await db.scalar(select(ChatThread).where(
        ChatThread.id == uuid.UUID(request.thread_id),
        ChatThread.account_id == uuid.UUID(current_account_id)
    ))
    if not thread:
        logger.warning(f"No se encontró el hilo {request.thread_id} para la cuenta {current_account_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hilo de chat con id {request.thread_id} no encontrado.")

    workspace_id = str(thread.workspace_id) if thread.workspace_id else None

    async def stream_generator():
        from core.agent import create_langgraph_agent, AgentState
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        from langchain_community.chat_message_histories import PostgresChatMessageHistory
        from core.config import settings
        from core.database import LangchainPgEmbedding
        from sqlalchemy.future import select
        from sqlalchemy.orm import selectinload

        logger.info(f"--- Iniciando agente LangGraph para STREAM HTTP para account_id: {request.account_id}, thread_id: {request.thread_id} ---")

        llm_task_id = str(uuid.uuid4())

        try:
            yield json.dumps({
                "type": "llm_start",
                "thread_id": request.thread_id,
                "task_id": llm_task_id,
                "message": "El agente está pensando..."
            }) + "\n"

            # --- Preparación del Contexto RAG ---
            context_text = ""
            if parsed_rag_context:
                logger.info(f"Enriqueciendo contexto con {len(parsed_rag_context)} item(s) de RAG.")
                document_ids_to_fetch = [item['id'] for item in parsed_rag_context if item.get('type') == 'document']
                
                if document_ids_to_fetch:
                    async with SessionLocal() as session:
                        stmt = (
                            select(LangchainPgEmbedding)
                            .filter(LangchainPgEmbedding.cmetadata['document_id'].astext.in_(document_ids_to_fetch))
                            .order_by(cast(LangchainPgEmbedding.cmetadata['chunk_index'].astext, Integer))
                        )
                        result = await session.execute(stmt)
                        all_chunks = result.scalars().all()

                        docs_content = {}
                        for chunk in all_chunks:
                            doc_id = chunk.cmetadata.get('document_id')
                            if doc_id not in docs_content:
                                docs_content[doc_id] = {
                                    'title': chunk.cmetadata.get('title', chunk.cmetadata.get('file_name')),
                                    'chunks': []
                                }
                            docs_content[doc_id]['chunks'].append(chunk.document)

                        for doc_id, data in docs_content.items():
                            full_content = "".join(data['chunks'])
                            context_text += f"\n\n--- Contexto del Documento: {data['title']} ---"
                            context_text += f"\nContenido: {full_content}\n"
                            context_text += "--- Fin del Contexto del Documento ---"

            if context_text:
                logger.info("Contexto RAG preparado para el LLM.")

            # --- Preparación Inicial ---
            agent_app = create_langgraph_agent()
            db_sync_url = settings.database_url.replace("+psycopg", "")
            chat_message_history = PostgresChatMessageHistory(
                connection_string=db_sync_url,
                session_id=request.thread_id,
                table_name="langchain_chat_history",
            )
            history_messages = await chat_message_history.aget_messages()

            user_message_with_rag_context = HumanMessage(
                content=request.user_message,
                additional_kwargs={'rag_context': parsed_rag_context} if parsed_rag_context else {}
            )

            if context_text:
                user_message = f"{request.user_message}\n\n--- Contexto RAG ---\n{context_text}\n--- Fin Contexto RAG ---"
            else:
                user_message = request.user_message

            initial_state: AgentState = {
                "messages": history_messages + [HumanMessage(content=user_message)],
                "account_id": request.account_id,
                "telegram_id": request.telegram_id,
                "workspace_id": workspace_id,
                "rag_context": parsed_rag_context,
                "sources": [],
            }

            await chat_message_history.aadd_messages([HumanMessage(content=user_message)])

            config: RunnableConfig = {"configurable": {"thread_id": request.thread_id}}
            final_state = None
            full_response_content = ""

            async for chunk in agent_app.astream(initial_state, config=config):
                if "generateResponse" in chunk:
                    final_response_message = chunk["generateResponse"]["messages"][-1]
                    if isinstance(final_response_message, AIMessage):
                        content_to_stream = final_response_message.content
                        if isinstance(content_to_stream, list):
                            content_to_stream = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in content_to_stream])
                        else:
                            content_to_stream = str(content_to_stream)

                        if final_response_message.tool_calls:
                            tool_code_to_send = json.dumps([
                                {"name": tc["name"], "arguments": tc["args"]}
                                for tc in final_response_message.tool_calls
                            ])
                            yield json.dumps({
                                "type": "tool_code",
                                "thread_id": request.thread_id,
                                "task_id": llm_task_id,
                                "tool_code": tool_code_to_send
                            }) + "\n"

                        for char in content_to_stream:
                            full_response_content += char
                            yield json.dumps({
                                "type": "llm_chunk",
                                "thread_id": request.thread_id,
                                "task_id": llm_task_id,
                                "chunk": char
                            }) + "\n"
                            await asyncio.sleep(0.001)
                        final_state = chunk["generateResponse"]

                elif "action" in chunk:
                    tool_message = chunk["action"]["messages"][-1]
                    if isinstance(tool_message, ToolMessage):
                        yield json.dumps({
                            "type": "tool_status",
                            "thread_id": request.thread_id,
                            "task_id": llm_task_id,
                            "tool_name": tool_message.name or "herramienta",
                            "status": "end",
                            "message": f"Herramienta '{tool_message.name or 'herramienta'}' finalizada.",
                        }) + "\n"
                
                if "agent" in chunk:
                    if any(isinstance(msg, AIMessage) and msg.tool_calls for msg in chunk["agent"]["messages"]):
                        tool_call_names = ", ".join([tc.get("name", "herramienta desconocida") for tc in chunk["agent"]["messages"][-1].tool_calls])
                        yield json.dumps({"type": "llm_status", "thread_id": request.thread_id, "task_id": llm_task_id, "message": f"El agente está usando: {tool_call_names} 🛠️"}) + "\n"
                    else:
                        yield json.dumps({"type": "llm_status", "thread_id": request.thread_id, "task_id": llm_task_id, "message": "El agente está pensando... 🤔"}) + "\n"

            if not final_state:
                raise ValueError("El grafo no produjo un estado final válido.")
            
            final_ai_message_kwargs = {}
            if final_state and "generateResponse" in final_state and final_state["generateResponse"]["messages"]:
                last_ai_message = final_state["generateResponse"]["messages"][-1]
                if isinstance(last_ai_message, AIMessage):
                    if last_ai_message.tool_calls:
                        final_ai_message_kwargs["tool_calls"] = last_ai_message.tool_calls
                    if last_ai_message.additional_kwargs.get("sources"):
                        final_ai_message_kwargs["sources"] = last_ai_message.additional_kwargs["sources"]

            await chat_message_history.aadd_messages([AIMessage(content=full_response_content, additional_kwargs=final_ai_message_kwargs)])

            if background_tasks:
                updated_history = await chat_message_history.aget_messages()
                real_messages = [m for m in updated_history if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
                message_count = len(real_messages)

                async with SessionLocal() as db:
                    thread = await db.get(ChatThread, uuid.UUID(request.thread_id))
                    current_title = thread.title if thread else ""

                should_rename = (
                    (current_title == "Nuevo Chat" and message_count >= 3) or
                    (message_count >= 10 and message_count % 10 == 0)
                )

                if should_rename:
                    from core.agent import force_update_thread_title
                    background_tasks.add_task(force_update_thread_title, request.thread_id)
            
            tool_code_to_send = None
            sources_to_send = []

            for msg in final_state["messages"]:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    tool_code_to_send = json.dumps([
                        {"name": tc["name"], "arguments": tc["args"]}
                        for tc in msg.tool_calls
                    ])
                    break

            yield json.dumps({
                "type": "llm_end",
                "thread_id": request.thread_id,
                "task_id": llm_task_id,
                "message": "Respuesta completada",
                "tool_code": tool_code_to_send,
                "sources": sources_to_send
            }) + "\n"

        except Exception as e:
            logger.error(f"Error en streaming agent LangGraph (HTTP): {e}", exc_info=True)
            yield json.dumps({
                "type": "llm_error",
                "thread_id": request.thread_id,
                "task_id": llm_task_id,
                "message": str(e)
            }) + "\n"

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


@router.get("/threads", summary="Obtener lista de hilos de chat")
async def get_threads(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener la lista de todos los hilos de chat del usuario autenticado.
    """
    try:
        # MODIFICADO: Añadido .order_by() para ordenar por fecha de creación descendente
        threads = await db.execute(
            select(ChatThread)
            .where(ChatThread.account_id == uuid.UUID(current_account_id))
            .order_by(ChatThread.created_at.desc())
        )
        thread_list = threads.scalars().all()
        return [{"id": str(thread.id), "title": thread.title, "isPinned": thread.is_pinned, "platform": thread.platform, "workspace_id": str(thread.workspace_id) if thread.workspace_id else None} for thread in thread_list]
    except Exception as e:
        logger.error(f"Error al obtener la lista de hilos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener la lista de hilos de chat.")

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