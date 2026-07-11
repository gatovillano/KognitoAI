# telegram_gateway/websocket_client.py

import asyncio
import json
import logging
import websockets
import base64
import time
import zlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import jwt
from io import BytesIO

from telegram_gateway.config import config

# URL base del WebSocket del core. Configurable vía variable de entorno.
# Se deriva de config.core_ws_url para soportar tanto despliegues Docker
# (ws://core:8000) como el core corriendo localmente en el host (ej: ws://172.19.0.1:8000).
_CORE_WS_BASE_URL: str = config.core_ws_url

from telegram import Update, Chat, User
from telegram.ext import Application, CallbackContext
from telegram.error import RetryAfter

from telegram_gateway.bot_manager import bot_manager
from telegram_gateway.helpers import markdown_to_telegram_html, split_text_into_pages
from telegram_gateway.handlers.message_handlers import send_agent_response, GENERATED_IMAGE_KEY, DOCUMENT_NAME_KEY, EVENT_ID_FOR_SCHEDULING_KEY, PAGINATOR_SESSIONS_KEY, send_typing_heartbeat
from telegram.constants import ChatAction

logger = logging.getLogger(__name__)

class TelegramWebSocketClient:
    def __init__(self, account_id: str, token: str, application: Application):
        self.account_id = account_id
        self.token = token
        self.application = application  # Guardar la instancia de Application

        # URI del WebSocket del core. Se construye a partir de config.core_ws_url para
        # soportar tanto despliegues Docker (ws://core:8000) como el core corriendo
        # localmente en el host (ej: ws://172.19.0.1:8000).
        self.uri = f"{_CORE_WS_BASE_URL}/ws/{self.account_id}?token={self.token}"
        logger.info(f"Configurando WebSocket URI: {self.uri}")

        self.websocket = None
        self.is_running = False
        self.accumulated_messages: Dict[str, str] = {}
        self.last_draft_update_time: Dict[str, float] = {}
        self.draft_blocked_until: Dict[str, float] = {}
        self.typing_tasks: Dict[int, asyncio.Task] = {}
        self.typing_events: Dict[int, asyncio.Event] = {}
        self.tool_status_messages: Dict[str, int] = {}  # taskId -> message_id

    def _get_tool_icon(self, tool_name: str) -> str:
        icons = {
            "web_search": "🔍",
            "deep_research": "🧬",
            "comprehensive_web_analyzer": "📊",
            "web_scraper_tool": "🕸️",
            "knowledge_graph": "🕸️",
            "knowledge_search": "🧠",
            "add_note": "📝",
            "get_notes": "📚",
            "calendar": "📅",
            "terminal": "💻",
            "file_editor": "📝",
            "image_generation": "🎨"
        }
        return icons.get(tool_name, "⚙️")

    async def connect(self):
        """Establece la conexión WebSocket y la mantiene."""
        self.is_running = True
        while self.is_running:
            try:
                # Refrescar el token antes de cada intento de conexión
                self.token = _create_bot_jwt()
                self.uri = f"{_CORE_WS_BASE_URL}/ws/{self.account_id}?token={self.token}"
                logger.debug(f"Intentando conectar WebSocket con token actualizado a: {_CORE_WS_BASE_URL}")

                async with websockets.connect(self.uri) as websocket:
                    self.websocket = websocket
                    logger.info(f"Cliente WebSocket conectado satisfactoriamente.")
                    await self.listen_for_messages()
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidURI, ConnectionRefusedError) as e:
                logger.error(f"Error de conexión WebSocket: {e}. Reintentando en 5 segundos...")
                self.websocket = None
                await asyncio.sleep(5)
            except websockets.exceptions.InvalidStatus as e:
                if e.response.status_code == 403:
                    logger.error("Error 403: El servidor rechazó la conexión (probablemente token expirado o inválido).")
                else:
                    logger.error(f"Error de estado WebSocket: {e}")
                self.websocket = None
                await asyncio.sleep(5)
            except (TimeoutError, asyncio.TimeoutError) as e:
                logger.warning(f"Timeout durante la apertura de la conexión WebSocket (handshake): {e}. Reintentando en 5 segundos...")
                self.websocket = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error inesperado en el cliente WebSocket: {e}", exc_info=True)
                await asyncio.sleep(5)  # Evitar bucle rápido en caso de error inesperado

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
            raise e  # Lanzar la excepción para que el bucle principal en connect() la maneje

    async def handle_message(self, data: Dict[str, Any]):
        """Procesa los mensajes recibidos del WebSocket."""
        message_type = data.get("type")
        thread_id = data.get("thread_id")
        task_id = data.get("taskId")

        if not thread_id:
            logger.warning(f"Mensaje WebSocket recibido sin thread_id: {data}")
            return

        chat_id = bot_manager.thread_id_to_chat_id_map.get(thread_id)

        if message_type == "stream_start":
            logger.info(f"Inicio de stream para thread_id: {thread_id}, taskId: {task_id}")
            self.accumulated_messages[thread_id] = ""
            self.last_draft_update_time[thread_id] = 0.0
            self.draft_blocked_until[thread_id] = 0.0
            if chat_id:
                await self._start_typing(chat_id)

        elif message_type == "stream_chunk":
            chunk = data.get("chunk", "")
            if thread_id not in self.accumulated_messages:
                logger.warning(f"Recibido 'stream_chunk' para thread_id '{thread_id}' sin un 'stream_start' previo. Inicializando acumulador.")
                self.accumulated_messages[thread_id] = ""
                self.last_draft_update_time[thread_id] = 0.0
            self.accumulated_messages[thread_id] += chunk

            # Asegurar que el typing siga activo si recibimos chunks
            if chat_id:
                await self._start_typing(chat_id)

                # Realizar streaming nativo usando sendMessageDraft
                if bot_manager.bot:
                    draft_id = (zlib.crc32(thread_id.encode('utf-8')) & 0x7fffffff) or 1
                    now = time.time()
                    last_update = self.last_draft_update_time.get(thread_id, 0.0)
                    if now - last_update >= 1.5:
                        if now < self.draft_blocked_until.get(thread_id, 0.0):
                            return
                        self.last_draft_update_time[thread_id] = now
                        try:
                            # Enviamos como borrador temporal (sin parse_mode para evitar fallos de parseo por tags parciales)
                            await bot_manager.bot.send_message_draft(
                                chat_id=chat_id,
                                draft_id=draft_id,
                                text=self.accumulated_messages[thread_id]
                            )
                        except RetryAfter as e:
                            logger.warning(f"Flood control hit para thread_id {thread_id}. Bloqueado por {e.retry_after} segundos.")
                            self.draft_blocked_until[thread_id] = time.time() + e.retry_after
                        except Exception as e:
                            logger.warning(f"Error al enviar sendMessageDraft para thread_id {thread_id}: {e}")

        elif message_type == "tool_start":
            tool_name = data.get("tool_name", "herramienta")
            icon = self._get_tool_icon(tool_name)
            if chat_id:
                try:
                    await self._start_typing(chat_id)
                    msg = await bot_manager.bot.send_message(
                        chat_id=chat_id,
                        text=f"{icon} <i>Ejecutando {tool_name}...</i>",
                        parse_mode='HTML'
                    )
                    self.tool_status_messages[task_id] = msg.message_id
                except Exception as e:
                    logger.warning(f"No se pudo enviar mensaje de estado de herramienta: {e}")

        elif message_type == "tool_end":
            if task_id in self.tool_status_messages and chat_id:
                try:
                    # Borrar el mensaje de estado después de que la herramienta termine
                    await bot_manager.bot.delete_message(
                        chat_id=chat_id,
                        message_id=self.tool_status_messages.pop(task_id)
                    )
                except Exception as e:
                    logger.debug(f"No se pudo borrar mensaje de estado de herramienta: {e}")

        elif message_type == "stream_end":
            logger.info(f"Fin de stream para thread_id: {thread_id}, taskId: {task_id}")
            if chat_id: await self._stop_typing(chat_id)

            self.last_draft_update_time.pop(thread_id, None)
            self.draft_blocked_until.pop(thread_id, None)
            final_message = self.accumulated_messages.pop(thread_id, "")

            # Extraer posibles datos adicionales del mensaje final
            image_base64_from_stream = data.get("image_base64")
            document_name_from_stream = data.get("document_name")
            event_id_from_stream = data.get("event_id")
            sources = data.get("sources", [])

            await self.send_message_to_telegram(
                final_message,
                thread_id,
                image_base64=image_base64_from_stream,
                document_name=document_name_from_stream,
                event_id=event_id_from_stream,
                sources=sources
            )

        elif message_type == "error":
            error_message = data.get("error_message", "Error desconocido")
            logger.error(f"Error recibido del backend para thread_id: {thread_id}: {error_message}")
            if chat_id: await self._stop_typing(chat_id)
            self.last_draft_update_time.pop(thread_id, None)
            self.draft_blocked_until.pop(thread_id, None)
            self.accumulated_messages.pop(thread_id, None)
            await self.send_message_to_telegram(f"Lo siento, ocurrió un error: {error_message}", thread_id)

    async def _start_typing(self, chat_id: int):
        """Inicia el heartbeat de typing para un chat específico si no está activo."""
        if chat_id not in self.typing_tasks or self.typing_tasks[chat_id].done():
            stop_event = asyncio.Event()
            self.typing_events[chat_id] = stop_event
            task = asyncio.create_task(send_typing_heartbeat(self.application, chat_id, stop_event))
            self.typing_tasks[chat_id] = task
            logger.debug(f"Iniciado typing heartbeat para chat_id {chat_id}")

    async def _stop_typing(self, chat_id: int):
        """Detiene el heartbeat de typing para un chat específico."""
        if chat_id in self.typing_events:
            self.typing_events[chat_id].set()
            if chat_id in self.typing_tasks:
                try:
                    await self.typing_tasks[chat_id]
                except Exception: pass
                self.typing_tasks.pop(chat_id)
            self.typing_events.pop(chat_id)
            logger.debug(f"Detenido typing heartbeat para chat_id {chat_id}")

    async def send_message_to_telegram(self, text: str, thread_id: str, image_base64: Optional[str] = None, document_name: Optional[str] = None, event_id: Optional[str] = None, sources: Optional[List[Dict[str, Any]]] = None):
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

        # Formatear fuentes si existen
        if sources:
            sources_text = "\n\n**📚 Fuentes consultadas:**\n"
            seen_urls = set()
            count = 1
            for s in sources:
                url = s.get("url")
                title = s.get("title") or url
                if url and url not in seen_urls:
                    sources_text += f"{count}. [{title}]({url})\n"
                    seen_urls.add(url)
                    count += 1
            if count > 1:
                text += sources_text

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
            try:
                # Usar una tarea para cerrar sin bloquear el bucle
                asyncio.create_task(self.websocket.close())
            except Exception: pass

# Instancia única del cliente WebSocket para el bot
# Se inicializará en el punto de entrada del gateway
telegram_ws_client: Optional["TelegramWebSocketClient"] = None

def _create_bot_jwt() -> str:
    """Crea un token JWT para el servicio del bot."""
    payload = {
        "sub": "telegram_bot_service",
        "account_id": "telegram_bot_service",
        "is_bot": True
    }

    # Solo añadir expiración si es mayor a 0. Si es 0, el token no expira (según utils/security.py)
    if config.jwt_expiry_days > 0:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(days=config.jwt_expiry_days)

    return jwt.encode(payload, config.jwt_secret_key, algorithm="HS256")

async def start_telegram_ws_client(application: Application):
    """Inicia el cliente WebSocket para el bot de Telegram."""
    global telegram_ws_client

    if telegram_ws_client and telegram_ws_client.is_running:
        logger.warning("El cliente WebSocket de Telegram ya está en ejecución. Omitiendo inicio.")
        return

    bot_account_id = "telegram_bot_service"
    bot_token = _create_bot_jwt()

    telegram_ws_client = TelegramWebSocketClient(account_id=bot_account_id, token=bot_token, application=application)
    telegram_ws_client.is_running = True  # Marcar como corriendo inmediatamente para evitar condiciones de carrera
    asyncio.create_task(telegram_ws_client.connect())

async def stop_telegram_ws_client():
    """Detiene el cliente WebSocket de forma asíncrona."""
    global telegram_ws_client
    if telegram_ws_client:
        telegram_ws_client.stop()
        # Dar un pequeño margen para que la tarea de cierre se inicie
        await asyncio.sleep(0.1)
