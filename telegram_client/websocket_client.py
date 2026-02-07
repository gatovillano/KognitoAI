# telegram_client/websocket_client.py

import asyncio
import os
import json
import logging
import websockets
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from io import BytesIO # Importar BytesIO

from telegram import Update, Chat, User # Importar Chat y User
from telegram.ext import Application, CallbackContext # Importar Application y CallbackContext

from core.config import settings
from telegram_client.bot_manager import bot_manager
from utils.helpers import markdown_to_telegram_html
from utils.paginator import split_text_into_pages
from telegram_client.handlers.message_handlers import send_agent_response, GENERATED_IMAGE_KEY, DOCUMENT_NAME_KEY, EVENT_ID_FOR_SCHEDULING_KEY, PAGINATOR_SESSIONS_KEY

logger = logging.getLogger(__name__)

class TelegramWebSocketClient:
    def __init__(self, account_id: str, token: str, application: Application):
        self.account_id = account_id
        self.token = token
        self.application = application # Guardar la instancia de Application
        
        # Forzar el uso de la dirección interna del contenedor 'core' en la red Docker
        # Esto evita problemas con proxies externos y errores 502.
        self.uri = f"ws://core:8000/ws/{self.account_id}?token={self.token}"
        logger.info(f"Configurando WebSocket URI interna: {self.uri}")
        
        self.websocket = None
        self.is_running = False
        self.accumulated_messages: Dict[str, str] = {}

    async def connect(self):
        """Establece la conexión WebSocket y la mantiene."""
        self.is_running = True
        while self.is_running:
            try:
                async with websockets.connect(self.uri) as websocket:
                    self.websocket = websocket
                    logger.info(f"Cliente WebSocket conectado a {self.uri}")
                    await self.listen_for_messages()
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidURI, ConnectionRefusedError) as e:
                logger.error(f"Error de conexión WebSocket: {e}. Reintentando en 5 segundos...")
                self.websocket = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error inesperado en el cliente WebSocket: {e}", exc_info=True)
                await asyncio.sleep(5) # Evitar bucle rápido en caso de error inesperado

    async def listen_for_messages(self):
        """Escucha los mensajes entrantes del WebSocket."""
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                if message == "ping":
                    await self.websocket.send("pong")
                    continue

                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("La conexión WebSocket se cerró. Lanzando excepción para reconexión.")
            raise e # Lanzar la excepción para que el bucle principal en connect() la maneje

    async def handle_message(self, data: Dict[str, Any]):
        """Procesa los mensajes recibidos del WebSocket."""
        message_type = data.get("type")
        thread_id = data.get("thread_id")
        task_id = data.get("taskId")

        if not thread_id:
            logger.warning(f"Mensaje WebSocket recibido sin thread_id: {data}")
            return

        if message_type == "stream_start":
            logger.info(f"Inicio de stream para thread_id: {thread_id}, taskId: {task_id}")
            self.accumulated_messages[thread_id] = ""
        
        elif message_type == "stream_chunk":
            chunk = data.get("chunk", "")
            if thread_id not in self.accumulated_messages:
                logger.warning(f"Recibido 'stream_chunk' para thread_id '{thread_id}' sin un 'stream_start' previo. Inicializando acumulador.")
                self.accumulated_messages[thread_id] = ""
            self.accumulated_messages[thread_id] += chunk
        
        elif message_type == "stream_end":
            logger.info(f"Fin de stream para thread_id: {thread_id}, taskId: {task_id}")
            final_message = self.accumulated_messages.pop(thread_id, "")
            
            # Extraer posibles datos adicionales del mensaje final
            image_base64_from_stream = data.get("image_base64")
            document_name_from_stream = data.get("document_name")
            event_id_from_stream = data.get("event_id")

            await self.send_message_to_telegram(
                final_message,
                thread_id,
                image_base64=image_base64_from_stream,
                document_name=document_name_from_stream,
                event_id=event_id_from_stream
            )
        
        elif message_type == "error":
            error_message = data.get("error_message", "Error desconocido")
            logger.error(f"Error recibido del backend para thread_id: {thread_id}: {error_message}")
            await self.send_message_to_telegram(f"Lo siento, ocurrió un error: {error_message}", thread_id)

    async def send_message_to_telegram(self, text: str, thread_id: str, image_base64: Optional[str] = None, document_name: Optional[str] = None, event_id: Optional[str] = None):
        """Envía el mensaje final al chat de Telegram correspondiente utilizando send_agent_response."""
        logger.info(f"Intentando enviar mensaje a Telegram para thread_id: {thread_id}.")
        
        chat_id = bot_manager.thread_id_to_chat_id_map.get(thread_id)
        if not chat_id:
            logger.error(f"No se encontró un chat_id para el thread_id '{thread_id}'.")
            return

        # Obtener user_data del persistence si está disponible
        user_data = {}
        if self.application.persistence:
            user_data = await self.application.persistence.get_user_data(chat_id)
        
        # Asegurarse de que user_data sea un diccionario
        if not isinstance(user_data, dict):
            user_data = {}

        # Inyectar los datos adicionales en user_data
        if image_base64:
            try:
                image_bytes = base64.b64decode(image_base64)
                user_data[GENERATED_IMAGE_KEY] = BytesIO(image_bytes)
                logger.info(f"Imagen base64 inyectada en user_data para thread_id: {thread_id}")
            except Exception as e:
                logger.error(f"Error al decodificar imagen base64 para thread_id {thread_id}: {e}", exc_info=True)
        
        if document_name:
            user_data[DOCUMENT_NAME_KEY] = document_name
            logger.info(f"Document name '{document_name}' inyectado en user_data para thread_id: {thread_id}")

        if event_id:
            user_data[EVENT_ID_FOR_SCHEDULING_KEY] = event_id
            logger.info(f"Event ID '{event_id}' inyectado en user_data para thread_id: {thread_id}")

        try:
            # Llamar a la nueva función de ayuda
            if bot_manager.bot is None:
                logger.error("El bot no está inicializado en bot_manager. No se puede enviar el mensaje desde WebSocket.")
                return
            await send_agent_response(bot_manager.bot, chat_id, chat_id, text, user_data)
            
            # Después de llamar a send_agent_response, guardar los cambios en persistence
            if self.application.persistence:
                await self.application.persistence.update_user_data(chat_id, user_data)

        except Exception as e:
            logger.error(f"Error al llamar a send_agent_response desde WebSocket para thread_id {thread_id}: {e}", exc_info=True)
            # En caso de error, enviar el texto simple como fallback
            try:
                formatted_text = markdown_to_telegram_html(text)
                pages = split_text_into_pages(formatted_text, 4096)
                for i, page in enumerate(pages):
                    if bot_manager.bot is None:
                        logger.error("Fallback: El bot no está inicializado en bot_manager.")
                        break
                    await bot_manager.bot.send_message(chat_id=chat_id, text=page, parse_mode='HTML', disable_web_page_preview=True)
                    if i < len(pages) - 1:
                        await asyncio.sleep(0.5)
            except Exception as fallback_e:
                logger.error(f"Error en fallback al enviar mensaje a Telegram para thread_id {thread_id}: {fallback_e}", exc_info=True)

    def stop(self):
        """Detiene el cliente WebSocket."""
        self.is_running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Instancia única del cliente WebSocket para el bot
# Se inicializará en run_telegram_bot.py
telegram_ws_client: Optional["TelegramWebSocketClient"] = None

def _create_bot_jwt() -> str:
    """Crea un token JWT para el servicio del bot."""
    payload = {
        "sub": "telegram_bot_service",
        "account_id": "telegram_bot_service",
        "exp": datetime.utcnow() + timedelta(days=settings.jwt_expiry_days),
        "is_bot": True
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

async def start_telegram_ws_client(application: Application):
    """Inicia el cliente WebSocket para el bot de Telegram."""
    global telegram_ws_client
    
    if telegram_ws_client and telegram_ws_client.is_running:
        logger.warning("El cliente WebSocket de Telegram ya está en ejecución. Omitiendo inicio.")
        return

    bot_account_id = "telegram_bot_service"
    bot_token = _create_bot_jwt()

    telegram_ws_client = TelegramWebSocketClient(account_id=bot_account_id, token=bot_token, application=application)
    telegram_ws_client.is_running = True # Marcar como corriendo inmediatamente para evitar condiciones de carrera
    asyncio.create_task(telegram_ws_client.connect())

async def stop_telegram_ws_client():
    """Detiene el cliente WebSocket de forma asíncrona."""
    global telegram_ws_client
    if telegram_ws_client:
        telegram_ws_client.stop()
        # Dar un pequeño margen para que la tarea de cierre se inicie
        await asyncio.sleep(0.1)