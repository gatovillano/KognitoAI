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
    Crea un thread real en la base de datos marcado como platform='telegram'.
    """
    try:
        from core.database import SessionLocal, ChatThread
        from utils.db_session import DBSession
        import uuid

        account_id = request.get('account_id')
        chat_id = request.get('chat_id')
        thread_name = request.get('thread_name', 'Chat de Telegram')

        if not account_id:
            raise ValueError("account_id es requerido")
        if not chat_id:
            raise ValueError("chat_id es requerido")

        # Crear el thread en la base de datos
        async with DBSession(SessionLocal) as db:
            new_thread = ChatThread(
                account_id=uuid.UUID(account_id),
                title=thread_name,
                platform='telegram'
            )
            db.add(new_thread)
            await db.commit()
            await db.refresh(new_thread)

            thread_id = str(new_thread.id)
            logger.info(f"Hilo de Telegram creado: {thread_id} para cuenta {account_id} en chat {chat_id}")
            return {"status": "ok", "thread_id": thread_id, "id": thread_id}

    except Exception as e:
        logger.error(f"Error al crear hilo de conversación: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear hilo de conversación")
