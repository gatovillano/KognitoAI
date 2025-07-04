from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
import logging

from core.config import settings
import requests

router = APIRouter()
logger = logging.getLogger(__name__)

class SendMessageRequest(BaseModel):
    """Define la estructura de datos para una solicitud de envío de mensaje."""
    chat_id: int
    text: str

class StoreUserDataRequest(BaseModel):
    """Define la estructura de datos para una solicitud de almacenamiento de datos de usuario."""
    user_id: int
    key: str
    data: str  # Datos en base64 para la imagen

class BotCreateThreadRequest(BaseModel):
    """Define la estructura de datos para una solicitud de creación de hilo de bot."""
    chat_id: int
    thread_name: str

@router.post("/internal/send-message", status_code=status.HTTP_200_OK)
async def send_message(request: SendMessageRequest):
    """
    Endpoint interno para enviar un mensaje a un chat de Telegram.
    """
    try:
        # Aquí se implementaría la lógica para enviar un mensaje a través del cliente de Telegram
        # Por ahora, solo registramos la solicitud y devolvemos un estado de éxito simulado
        logger.info(f"Enviando mensaje a chat {request.chat_id}: {request.text}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error al enviar mensaje: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al enviar mensaje")

@router.post("/internal/store-user-data", status_code=status.HTTP_200_OK)
async def store_user_data(request: StoreUserDataRequest):
    """
    Endpoint interno para almacenar datos en user_data de un usuario de Telegram.
    """
    try:
        # Aquí se implementaría la lógica para almacenar datos en user_data
        # Por ahora, solo registramos la solicitud y devolvemos un estado de éxito simulado
        logger.info(f"Almacenando datos para usuario {request.user_id} con clave {request.key}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error al almacenar datos de usuario: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al almacenar datos de usuario")

@router.post("/internal/bot-create-thread", status_code=status.HTTP_200_OK)
async def bot_create_thread(request: dict):
    """
    Endpoint interno para crear un hilo de conversación desde el bot de Telegram.
    Maneja diferentes formatos de entrada para mayor flexibilidad.
    """
    try:
        chat_id = None
        thread_name = "default_thread"
        
        # Intentar extraer datos del cuerpo de la solicitud
        if isinstance(request, dict):
            chat_id = request.get('chat_id')
            thread_name = request.get('thread_name', thread_name)
        else:
            # Si no es un diccionario, intentar parsear como cadena
            body_str = str(request)
            if 'chat_id=' in body_str:
                parts = body_str.split('chat_id=')
                if len(parts) > 1:
                    chat_id_part = parts[1].split('&')[0] if '&' in parts[1] else parts[1]
                    chat_id = int(chat_id_part) if chat_id_part.isdigit() else None
        
        if chat_id is None:
            raise ValueError("No se pudo extraer chat_id de la solicitud")
            
        # Generar un UUID válido para el thread_id
        import uuid
        thread_id = str(uuid.uuid4())
        logger.info(f"Creando hilo de conversación en chat {chat_id} con nombre {thread_name}, thread_id: {thread_id}")
        return {"status": "ok", "thread_id": thread_id}
    except Exception as e:
        logger.error(f"Error al crear hilo de conversación: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear hilo de conversación")
