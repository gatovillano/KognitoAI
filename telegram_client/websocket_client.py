# telegram_client/websocket_client.py

import asyncio
import json
import logging
import websockets
from typing import Dict, Any
from datetime import datetime, timedelta
import jwt

from core.config import settings
from telegram_client.bot_manager import bot_manager
from utils.helpers import markdown_to_telegram_html
from utils.paginator import split_text_into_pages

logger = logging.getLogger(__name__)

class TelegramWebSocketClient:
    def __init__(self, account_id: str, token: str):
        self.account_id = account_id
        self.token = token
        self.uri = f"{settings.api_server_url.replace('http', 'ws')}/ws/{self.account_id}?token={self.token}"
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
                self.is_running = False

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
        except websockets.exceptions.ConnectionClosed:
            logger.warning("La conexión WebSocket se cerró. Se intentará reconectar.")

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
            if final_message:
                await self.send_message_to_telegram(final_message, thread_id)
        
        elif message_type == "error":
            error_message = data.get("error_message", "Error desconocido")
            logger.error(f"Error recibido del backend para thread_id: {thread_id}: {error_message}")
            await self.send_message_to_telegram(f"Lo siento, ocurrió un error: {error_message}", thread_id)

    async def send_message_to_telegram(self, text: str, thread_id: str):
        """Envía el mensaje final al chat de Telegram correspondiente."""
        logger.info(f"Intentando enviar mensaje a Telegram para thread_id: {thread_id}. Contenido: '{text[:100]}...'")
        # Necesitamos una forma de mapear thread_id a chat_id.
        # Por ahora, asumiremos que el thread_id es el chat_id.
        # Una solución más robusta sería almacenar este mapeo en la base de datos.
        try:
            chat_id = bot_manager.thread_id_to_chat_id_map.get(thread_id)
            if not chat_id:
                logger.error(f"No se encontró un chat_id para el thread_id '{thread_id}'.")
                return

            bot = bot_manager.bot
            if bot:
                if not text or not text.strip():
                    logger.warning(f"El texto para enviar a Telegram está vacío o solo contiene espacios en blanco para thread_id: {thread_id}. No se enviará el mensaje.")
                    return
                formatted_text = markdown_to_telegram_html(text)
                pages = split_text_into_pages(formatted_text, 4096)
                for i, page in enumerate(pages):
                    await bot.send_message(chat_id=chat_id, text=page, parse_mode='HTML', disable_web_page_preview=True)
                    if i < len(pages) - 1:
                        await asyncio.sleep(0.5)
            else:
                logger.error("bot_manager.bot no está inicializado. No se puede enviar el mensaje.")
        except Exception as e:
            logger.error(f"Error al enviar mensaje a Telegram: {e}", exc_info=True)

    def stop(self):
        """Detiene el cliente WebSocket."""
        self.is_running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Instancia única del cliente WebSocket para el bot
# Se inicializará en run_telegram_bot.py
telegram_ws_client: "TelegramWebSocketClient" = None

def _create_bot_jwt() -> str:
    """Crea un token JWT para el servicio del bot."""
    payload = {
        "sub": "telegram_bot_service",
        "account_id": "telegram_bot_service",
        "exp": datetime.utcnow() + timedelta(days=settings.jwt_expiry_days),
        "is_bot": True
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

async def start_telegram_ws_client():
    """Inicia el cliente WebSocket para el bot de Telegram."""
    global telegram_ws_client
    
    bot_account_id = "telegram_bot_service"
    bot_token = _create_bot_jwt()

    telegram_ws_client = TelegramWebSocketClient(account_id=bot_account_id, token=bot_token)
    asyncio.create_task(telegram_ws_client.connect())

def stop_telegram_ws_client():
    """Detiene el cliente WebSocket."""
    if telegram_ws_client:
        telegram_ws_client.stop()