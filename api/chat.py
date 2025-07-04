# api/chat.py

import logging
import uuid
import re
from typing import Optional
from io import BytesIO
import httpx
from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Usamos el nombre del servicio Docker y el puerto interno correcto.
TTS_SERVICE_URL = "http://openai-edge-tts:5050/v1/audio/speech"

from sqlalchemy import update

from core.agent import create_and_run_agent
from utils.audio_transcriber import transcribe_audio_file
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import SessionLocal, ChatThread

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

# --- Modelos para el Chat ---
class ChatRequest(BaseModel):
    """Define la estructura de datos para una solicitud de mensaje de chat al agente."""
    thread_id: str
    account_id: str
    telegram_id: Optional[int] = None  # Hacemos telegram_id opcional
    user_message: str
    image_base64: Optional[str] = None
    document_url: Optional[str] = None  # Campo para URL de documentos
    mode: Optional[str] = None

class ChatResponse(BaseModel):
    """Define la estructura de datos para la respuesta del agente de chat."""
    response_text: str
    image_base64: Optional[str] = None  # Campo para imágenes en base64
    document_url: Optional[str] = None  # Campo para URL de documentos

class TextToSpeechRequest(BaseModel):
    """Define la estructura de datos para una solicitud de conversión de texto a voz."""
    text: str
    voice: Optional[str] = None  # Voz opcional para la conversión

class PinThreadRequest(BaseModel):
    """Define la estructura de datos para una solicitud de fijar/desfijar un hilo de chat."""
    isPinned: bool

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
    text_to_speak = re.sub(r'`[^`]*`', '', text_to_speak)
    # 3. Eliminar caracteres de puntuación que no se quieren leer
    text_to_speak = re.sub(r'[\[\]{}()#*_]', '', text_to_speak)
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
async def handle_chat(request: ChatRequest, background_tasks: BackgroundTasks, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)) -> ChatResponse:
    """
    Endpoint principal para procesar mensajes de chat con el agente de IA.
    Requiere autenticación JWT.
    """
    try:
        account_id_uuid = uuid.UUID(request.account_id)
        if str(account_id_uuid) != current_account_id:  # Validar que el account_id coincida con el del token
            logger.error(f"El account_id proporcionado ({request.account_id}) no coincide con el token de autenticación ({current_account_id})")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El account_id proporcionado no coincide con el token de autenticación.")
    except ValueError:
        logger.error(f"El account_id proporcionado no es un UUID válido: {request.account_id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El account_id proporcionado no tiene un formato válido.")

    logger.info(f"Petición de chat recibida de la cuenta: {request.account_id} con modo: {request.mode}")
    
    # Obtener el workspace_id del ChatThread asociado
    workspace_id = None
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(request.thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if thread and thread.workspace_id:
        workspace_id = str(thread.workspace_id)
        logger.info(f"Recuperado workspace_id {workspace_id} para el hilo {request.thread_id}.")
    else:
        logger.info(f"No se encontró workspace_id para el hilo {request.thread_id}.")

    try:
        final_response_text = await create_and_run_agent(
            account_id=request.account_id,
            thread_id=request.thread_id,
            telegram_id=request.telegram_id,  # telegram_id ahora es Optional[int]
            user_message=request.user_message,
            image_base64=request.image_base64,
            document_url=request.document_url,  # Añadir soporte para documentos
            mode=request.mode,
            background_tasks=background_tasks,
            workspace_id=workspace_id
        )
        return ChatResponse(response_text=final_response_text)
    except Exception as e:
        logger.error(f"Error al procesar petición de la cuenta {request.account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error interno al procesar tu solicitud.")

@router.get("/threads", summary="Obtener lista de hilos de chat")
async def get_threads(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener la lista de todos los hilos de chat del usuario autenticado.
    """
    try:
        threads = await db.execute(select(ChatThread).where(ChatThread.account_id == uuid.UUID(current_account_id)))
        thread_list = threads.scalars().all()
        return [{"id": str(thread.id), "title": thread.title, "isPinned": thread.is_pinned, "workspace_id": str(thread.workspace_id) if thread.workspace_id else None} for thread in thread_list]
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
        return {"id": str(thread.id), "title": thread.title, "isPinned": thread.is_pinned, "workspace_id": str(thread.workspace_id) if thread.workspace_id else None}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Error al obtener detalles del hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener los detalles del hilo de chat.")

@router.post("/threads", summary="Crear un nuevo hilo de chat")
async def create_thread(request: dict = {}, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para crear un nuevo hilo de chat para el usuario autenticado.
    """
    try:
        workspace_id = request.get('workspace_id')
        new_thread = ChatThread(
            account_id=uuid.UUID(current_account_id),
            title="Nuevo Chat",
            workspace_id=uuid.UUID(workspace_id) if workspace_id else None
        )
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        return {"id": str(new_thread.id), "title": new_thread.title, "isPinned": new_thread.is_pinned, "workspace_id": str(new_thread.workspace_id) if new_thread.workspace_id else None}
    except ValueError:
        logger.error(f"El workspace_id proporcionado no es un UUID válido: {workspace_id}")
        raise HTTPException(status_code=400, detail="El workspace_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al crear un nuevo hilo para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al crear un nuevo hilo de chat.")

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
        return {"id": thread_id, "title": updated_thread.title}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al generar título para el hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al generar el título del hilo de chat.")
