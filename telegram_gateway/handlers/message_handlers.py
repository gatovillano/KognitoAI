# telegram_gateway/handlers/message_handlers.py

"""
Manejadores para mensajes de texto, fotos, audio y la lógica de respuesta para Telegram.

Este módulo es inherentemente dependiente del módulo 'telegram' (python-telegram-bot)
ya que su función es interpretar y responder a los eventos específicos de la API de Telegram.
Sin embargo, la lógica de negocio subyacente (gestión de hilos, identificación de usuarios,
interacción con el agente de IA, gestión de datos del usuario) se mantiene agnóstica a la plataforma,
delegando en el servidor API central (run_api.py) y operando con el 'account_id' universal.

Soporta:
- Mensajes de texto: Envía la consulta al agente de IA.
- Mensajes de voz: Transcribe a texto usando Faster Whisper y envía al agente de IA.
- Mensajes de foto: Codifica a Base64 y envía al agente de IA junto con el caption.
- Respuestas especiales del agente: Envío de imágenes generadas, paginación de documentos,
  programación de recordatorios de eventos.
- Gestión de hilos de conversación: Mantiene un seguimiento del hilo de chat activo con el backend.
- Respuestas en grupos: Responde solo a menciones o respuestas directas al bot.
"""

import logging
import re
import asyncio
import tempfile
import os
import base64
import json
from typing import List, Optional, Dict, Any, Union, Generator
import httpx
from io import BytesIO
import uuid
import time

import telegram
from telegram import Update, Message
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    ApplicationHandlerStop,
)
from telegram.constants import ChatAction, ParseMode

from telegram_gateway.config import config
from telegram_gateway.helpers import (
    markdown_to_telegram_html,
    Paginator,
    split_text_into_pages,
)
from telegram_gateway.bot_manager import bot_manager
from telegram_gateway.api_client import get_or_create_account, create_thread, send_chat_message
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Constants defined locally (no core/skills dependency)
GENERATED_IMAGE_KEY = "generated_image"
DOCUMENT_NAME_KEY = "document_name"
EVENT_ID_FOR_SCHEDULING_KEY = "event_id_for_scheduling"

# Clave utilizada en context.user_data para almacenar un diccionario de sesiones
# de paginación activas para el usuario. Esto permite manejar múltiples instancias
# de paginación simultáneamente (ej., diferentes documentos o listas).
PAGINATOR_SESSIONS_KEY = "paginator_sessions"
API_BASE_URL = config.core_api_url
CURRENT_CHAT_THREAD_ID_KEY = "current_chat_thread_id"
INACTIVITY_TIMEOUT_SECONDS = 600  # 10 minutos
LAST_MESSAGE_TIMESTAMP_KEY = "last_message_timestamp"

WHISPER_MODEL_SIZE = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
_whisper_model: Optional[WhisperModel] = None

async def get_whisper_model() -> Optional[WhisperModel]:
    """Carga y devuelve el modelo de transcripción, inicializándolo solo una vez."""
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Cargando modelo Faster Whisper: {WHISPER_MODEL_SIZE}...")
        try:
            loop = asyncio.get_event_loop()
            _whisper_model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
            )
            logger.info("Modelo Faster Whisper cargado.")
        except Exception as e:
            logger.error(f"Error cargando el modelo Faster Whisper: {e}", exc_info=True)
            _whisper_model = None
    return _whisper_model

async def send_typing_heartbeat(application_or_context: Union[Application, CallbackContext], chat_id: int, stop_event: asyncio.Event):
    """Envía una acción 'typing' cada 4 segundos para indicar que el bot está procesando."""
    bot = application_or_context.bot if hasattr(application_or_context, 'bot') else getattr(application_or_context, 'bot', None)

    # Si recibimos un application directamente (vía WebSocket client)
    if not bot and hasattr(application_or_context, 'bot'):
        bot = application_or_context.bot

    while not stop_event.is_set():
        try:
            if bot:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
        except (asyncio.CancelledError, telegram.error.NetworkError):
            break
        except Exception as e:
            logger.warning(f"No se pudo enviar la acción de 'typing': {e}")
            break

def _should_respond_in_group(message: Message, bot_id: int, bot_username: Optional[str]) -> bool:
    """
    Determina si el bot debe responder a un mensaje en un grupo.
    Responde solo a menciones explícitas, si no está en modo privacidad, o si es un comando.
    """
    if message.chat.type == "private":
        return True

    if bot_username:
        # Si es una respuesta directa al bot
        if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot_id:
            return True
        # Si se menciona al bot en el texto del mensaje
        if message.text and f"@{bot_username.lower()}" in message.text.lower():
            return True
        # Si es un comando dirigido al bot (ej. /comando@botname)
        if message.text and message.text.startswith('/') and f"@{bot_username.lower()}" in message.text.lower():
            return True

    # Por defecto, si no es chat privado y no hay mención/respuesta, no responder en grupos
    logger.debug(f"Mensaje en grupo de {message.from_user.id} ignorado (no mención/privado).")
    return False

async def send_agent_response(bot, chat_id, user_id, text, user_data):
    """
    Función de ayuda para enviar la respuesta final del agente al usuario,
    sin depender de Update o CallbackContext.
    """
    # 1. Comprobar si hay una imagen generada para enviar (desde BytesIO)
    if GENERATED_IMAGE_KEY in user_data:
        image_bytesio = user_data.pop(GENERATED_IMAGE_KEY)
        logger.info(f"Enviando imagen generada al usuario {user_id} desde BytesIO...")
        image_bytesio.seek(0)
        try:
            await bot.send_photo(chat_id=chat_id, photo=image_bytesio, caption=text)
            return
        except Exception as e:
            logger.error(f"Error al enviar la imagen generada desde BytesIO: {e}", exc_info=True)

    # 2. Comprobar si hay una ruta de imagen generada para enviar (desde archivo temporal)
    if 'generated_image_path' in user_data:
        image_path = user_data.pop('generated_image_path')
        logger.info(f"Enviando imagen generada al usuario {user_id} desde archivo {image_path}...")
        try:
            with open(image_path, 'rb') as image_file:
                await bot.send_photo(chat_id=chat_id, photo=image_file, caption=text)
            return
        except Exception as e:
            logger.error(f"Error al enviar la imagen generada desde archivo {image_path}: {e}", exc_info=True)

    # 3. Comprobar si hay un documento para paginar
    document_title = user_data.pop(DOCUMENT_NAME_KEY, None)
    if document_title:
        logger.info(f"Paginando el documento '{document_title}' para el usuario {user_id}...")
        formatted_text = markdown_to_telegram_html(text)
        chunks = split_text_into_pages(formatted_text, 3500)
        paginator = Paginator(
            chunks=chunks,
            title=document_title,
            parse_mode=ParseMode.HTML,
            prefix=f"doc_{uuid.uuid4().hex[:6]}"
        )
        if PAGINATOR_SESSIONS_KEY not in user_data:
            user_data[PAGINATOR_SESSIONS_KEY] = {}
        user_data[PAGINATOR_SESSIONS_KEY][paginator.session_id] = paginator
        first_page, markup = paginator.get_page()
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=first_page,
                reply_markup=markup,
                parse_mode=paginator.parse_mode,
                disable_web_page_preview=True
            )
            return
        except Exception as e:
            logger.error(f"Error al enviar la primera página del documento paginado: {e}", exc_info=True)

    # 4. Comprobar si hay un evento para programar su notificación
    event_id_to_schedule = user_data.pop(EVENT_ID_FOR_SCHEDULING_KEY, None)
    if event_id_to_schedule:
        logger.info(f"Se ha detectado el evento ID {event_id_to_schedule} para programar su notificación al usuario {user_id}.")
        # En el gateway no accedemos directamente a la DB ni al scheduler de core.
        # El core maneja la programación de eventos server-side.
        logger.info(f"Evento {event_id_to_schedule} detectado. El recordatorio se gestionará via WebSocket.")

    # 5. Si no hay nada de lo anterior o falló, enviar como texto simple con formato HTML.
    formatted_text = markdown_to_telegram_html(text)
    # Usamos 4000 en lugar de 4096 para dejar margen a las etiquetas HTML que añaden bytes.
    pages = split_text_into_pages(formatted_text, 4000)
    for i, page in enumerate(pages):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=page,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            if i < len(pages) - 1:
                await asyncio.sleep(0.5)
        except telegram.error.BadRequest as e:
            logger.warning(f"Error al enviar mensaje con formato HTML (BadRequest): {e}. Reintentando como texto plano...")
            try:
                # Fallback: enviar el texto sin ningún formato si el HTML falla
                import re
                plain_text = re.sub(r'<[^>]+>', '', page)
                plain_pages = split_text_into_pages(plain_text, 4000)
                for j, plain_page in enumerate(plain_pages):
                    await bot.send_message(
                        chat_id=chat_id,
                        text=plain_page,
                        disable_web_page_preview=True
                    )
                    if j < len(plain_pages) - 1:
                        await asyncio.sleep(0.5)
            except Exception as fallback_e:
                logger.error(f"Error definitivo al enviar mensaje como texto plano: {fallback_e}", exc_info=True)

async def handle_chat_response(update: Update, context: CallbackContext, response_text: str) -> None:
    """
    Función de ayuda para enviar la respuesta final al usuario.
    Ahora delega en send_agent_response.
    """
    if not update or not update.effective_chat or not update.effective_user:
        logger.warning("handle_chat_response fue llamada sin un contexto de usuario/chat válido.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_data: Dict[str, Any] = context.user_data if context.user_data is not None else {}

    await send_agent_response(context.bot, chat_id, user_id, response_text, user_data)

async def _create_new_thread(account_id_str: str, chat_id: int, workspace_id: Optional[str],
                             update: Update) -> Optional[str]:
    """Helper interno para crear un nuevo hilo via api_client."""
    thread_id = await create_thread(account_id_str, chat_id, workspace_id)
    if not thread_id:
        logger.error(f"No se pudo crear un hilo para la cuenta {account_id_str}.")
        await update.message.reply_text("No pude iniciar una nueva conversación. Por favor, intenta de nuevo.")
        return None
    logger.info(f"Nuevo hilo {thread_id} creado para la cuenta {account_id_str}.")
    return thread_id

async def process_and_get_response(update: Update, context: CallbackContext, user_message: str, image_base64: Optional[str] = None) -> None:
    """
    Función central para procesar cualquier tipo de mensaje (texto, audio, etc.).

    Obtiene la identidad universal del usuario via API, gestiona el hilo de chat actual,
    empaqueta los datos y llama al backend (`/api/chat`) para obtener la
    respuesta de la IA.

    Flujo:
    1. Llama a get_or_create_account() desde api_client → obtiene account_id y jwt_token
    2. Si no hay hilo activo, llama a create_thread() desde api_client
    3. Mapea thread_id a chat_id en bot_manager.thread_id_to_chat_id_map
    4. Llama a send_chat_message() desde api_client
    5. La respuesta llega vía WebSocket (no hay polling)
    """
    if not update.message or not update.effective_user or not update.effective_chat:
        logger.warning("process_and_get_response fue llamada sin un contexto de mensaje/usuario/chat válido.")
        return None

    user = update.effective_user
    chat_id = update.effective_chat.id
    typing_stop_event = None
    typing_task = None

    from telegram_gateway.websocket_client import telegram_ws_client
    if telegram_ws_client:
        await telegram_ws_client._start_typing(chat_id)
    else:
        typing_stop_event = asyncio.Event()
        typing_task = asyncio.create_task(send_typing_heartbeat(context, chat_id, typing_stop_event))

    account_id_str = None
    jwt_token = None
    current_thread_id = context.chat_data.get(CURRENT_CHAT_THREAD_ID_KEY)

    try:
        # 1. Obtener la identidad universal del usuario via API.
        auth_data = await get_or_create_account(
            platform_user_id=str(user.id),
            first_name=user.first_name,
            last_name=getattr(user, 'last_name', None),
            username=user.username
        )
        if not auth_data:
            error_msg = "Lo siento, tuve un problema al identificar tu cuenta. No puedo procesar tu solicitud."
            await update.message.reply_text(error_msg)
            return None

        account_id_str = auth_data.get('account_id')
        jwt_token = auth_data.get('access_token')
        # Guardar el token JWT en chat_data para reutilizarlo
        context.chat_data['jwt_token'] = jwt_token

        # 2. Gestionar el hilo de conversación.
        workspace_id = context.chat_data.get('current_workspace_id')

        if not current_thread_id:
            logger.info(f"No hay hilo activo para la cuenta {account_id_str}. Creando uno nuevo...")
            current_thread_id = await _create_new_thread(account_id_str, chat_id, workspace_id, update)
            if not current_thread_id:
                return None
            context.chat_data[CURRENT_CHAT_THREAD_ID_KEY] = current_thread_id
        else:
            # Verificar si ha habido inactividad por más de 10 minutos
            now = time.time()
            last_message_ts = context.chat_data.get(LAST_MESSAGE_TIMESTAMP_KEY)
            if last_message_ts and (now - last_message_ts > INACTIVITY_TIMEOUT_SECONDS):
                context.chat_data[CURRENT_CHAT_THREAD_ID_KEY] = None
                current_thread_id = None
                logger.info(f"Hilo anterior inactivo para la cuenta {account_id_str}. Creando uno nuevo por inactividad...")
                current_thread_id = await _create_new_thread(account_id_str, chat_id, workspace_id, update)
                if not current_thread_id:
                    return None
                context.chat_data[CURRENT_CHAT_THREAD_ID_KEY] = current_thread_id

        # 3. Registrar el mapeo thread_id → chat_id para que el WebSocket sepa dónde entregar la respuesta.
        if current_thread_id:
            bot_manager.thread_id_to_chat_id_map[current_thread_id] = chat_id

        # Actualizar el timestamp del último mensaje
        context.chat_data[LAST_MESSAGE_TIMESTAMP_KEY] = time.time()

        # 4. Enviar el mensaje al agente via api_client.
        response_data = await send_chat_message(
            jwt_token=jwt_token,
            account_id=account_id_str,
            thread_id=current_thread_id,
            user_message=user_message,
            image_base64=image_base64,
            workspace_id=workspace_id,
            telegram_id=chat_id
        )

        if response_data:
            task_id = response_data.get("taskId")
            thread_id_from_api = response_data.get("thread_id")
            logger.info(f"Solicitud de chat enviada. Thread ID: {thread_id_from_api}, Task ID: {task_id}. Esperando respuesta vía WebSocket.")
            logger.debug(f"Respuesta completa de /api/chat: {response_data}")
        else:
            logger.error(f"Error al enviar el mensaje al agente para la cuenta {account_id_str}.")
            await update.message.reply_text("No pude procesar tu mensaje. Por favor, intenta de nuevo.")

        # No hay más procesamiento aquí, la respuesta vendrá por WebSocket.

    except Exception as e:
        account_id_log = account_id_str if account_id_str else "Desconocida"
        logger.error(f"Error inesperado en process_and_get_response para la cuenta {account_id_log}: {e}", exc_info=True)
        error_msg = "Lo siento, ocurrió un error inesperado al procesar tu solicitud."
        await update.message.reply_text(error_msg)
    finally:
        # Si NO se pudo enviar el mensaje con éxito, detenemos el typing
        if 'task_id' not in locals():
            from telegram_gateway.websocket_client import telegram_ws_client
            if telegram_ws_client:
                await telegram_ws_client._stop_typing(chat_id)
            elif typing_stop_event and typing_task:
                typing_stop_event.set()
                await typing_task

    return None  # Importante: Retornar None para detener la propagación.

async def generic_message_handler_for_unsupported_types(update: Update, context: CallbackContext) -> None:
    """
    Un handler "comodín" para capturar mensajes que no son manejados por los
    handlers específicos (ej. emojis, stickers, archivos no soportados, o tipos nuevos).
    Simplemente informa al usuario que el tipo de mensaje no es compatible,
    sin intentar procesarlo con el agente de IA.
    """
    if not update.message or not update.message.from_user or not update.effective_chat:
        logger.warning("generic_message_handler_for_unsupported_types recibió una actualización inválida.")
        return None

    user = update.message.from_user
    chat_id = update.effective_chat.id

    # Loguear el mensaje completo para depuración, así sabemos qué tipo de mensaje llegó.
    logger.info(f"Handler genérico capturó un mensaje no soportado del usuario {user.id}. Tipo de chat: {update.message.chat.type}. Mensaje: {update.message.text or update.message.caption or 'Otros contenidos'}")

    # Solo informar al usuario, NO llamar a process_and_get_response aquí.
    await context.bot.send_message(
        chat_id=chat_id,
        text="Lo siento, este tipo de mensaje (como stickers, documentos sin texto, etc.) aún no es compatible. Por favor, intenta con texto, una foto o un mensaje de voz."
    )
    return None  # Importante: Retornar None para detener la propagación.

async def text_message_handler(update: Update, context: CallbackContext) -> None:
    """Manejador principal para todos los mensajes de texto."""
    message = update.message
    if not message or not message.text or not message.from_user:
        return None

    if message.chat.type in ['group', 'supergroup']:
        bot_id = context.bot.id
        if not _should_respond_in_group(message, bot_id, bot_username=context.bot.username):
            return None  # No responder en grupo si no cumple las condiciones.

    await process_and_get_response(update, context, user_message=message.text)
    # Después de procesar el mensaje, verificar si hay una imagen en user_data para enviar.
    # Asegurarse de que context.user_data es un diccionario
    user_data: Dict[str, Any] = context.user_data if context.user_data is not None else {}
    if GENERATED_IMAGE_KEY in user_data:
        await handle_chat_response(update, context, response_text="¡Hecho! He generado la imagen.")
    raise ApplicationHandlerStop()  # Importante: Retornar ApplicationHandlerStop para detener la propagación.

async def voice_message_handler(update: Update, context: CallbackContext) -> None:
    """Manejador para mensajes de voz."""
    message = update.message
    if not message or not message.voice or not message.from_user:
        return None

    if message.chat.type in ['group', 'supergroup']:
        bot_id = context.bot.id
        if not _should_respond_in_group(message, bot_id, bot_username=context.bot.username):
            return None  # No responder en grupo si no cumple las condiciones.

    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        voice_file = await message.voice.get_file()
        voice_bytes_io = BytesIO()
        await voice_file.download_to_memory(voice_bytes_io)
        voice_bytes_io.seek(0)

        model = await get_whisper_model()
        if not model:
            await message.reply_text("Lo siento, el servicio de transcripción de voz no está disponible.")
            return None

        segments, info = model.transcribe(voice_bytes_io)
        transcribed_text = " ".join([segment.text for segment in segments])

        if not transcribed_text.strip():
            await message.reply_text("No pude entender lo que dijiste. ¿Puedes repetirlo o escribirlo?")
            return None

        logger.info(f"Voz transcrita de {message.from_user.id}: {transcribed_text[:50]}...")
        await process_and_get_response(update, context, user_message=transcribed_text)

    except Exception as e:
        logger.error(f"Error procesando mensaje de voz de {message.from_user.id}: {e}", exc_info=True)
        await message.reply_text("Hubo un error al procesar tu mensaje de voz. Por favor, intenta de nuevo.")

    raise ApplicationHandlerStop()  # Importante: Retornar ApplicationHandlerStop para detener la propagación.

async def photo_message_handler(update: Update, context: CallbackContext) -> None:
    """Manejador para mensajes que contienen una foto."""
    message = update.message
    if not message or not message.photo or not message.from_user:
        return None

    if message.chat.type in ['group', 'supergroup']:
        bot_id = context.bot.id
        if not _should_respond_in_group(message, bot_id, bot_username=context.bot.username):
            return None  # No responder en grupo si no cumple las condiciones.

    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        photo_file = await message.photo[-1].get_file()
        photo_bytes_io = BytesIO()
        await photo_file.download_to_memory(photo_bytes_io)
        photo_bytes_io.seek(0)
        image_base64 = base64.b64encode(photo_bytes_io.read()).decode('utf-8')
        user_message = message.caption if message.caption else "Imagen sin descripción."
        await process_and_get_response(update, context, user_message=user_message, image_base64=image_base64)

    except Exception as e:
        logger.error(f"Error procesando foto de {message.from_user.id}: {e}", exc_info=True)
        await message.reply_text("Hubo un error al procesar tu imagen. Por favor, intenta de nuevo.")

    raise ApplicationHandlerStop()  # Importante: Retornar ApplicationHandlerStop para detener la propagación.

def register_message_handlers(application: Application) -> None:
    """Registra todos los manejadores de mensajes en la aplicación."""
    # Handlers específicos para tipos de mensaje que se envían al agente de IA.
    # Estos deben tener la PRIORIDAD MÁS ALTA (group=0) para que se procesen primero.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler), group=0)
    application.add_handler(MessageHandler(filters.VOICE, voice_message_handler), group=0)
    application.add_handler(MessageHandler(filters.PHOTO, photo_message_handler), group=0)

    # Handler genérico (comodín) para mensajes que no son de los tipos anteriores o comandos.
    # Este debe tener una PRIORIDAD MENOR (group=1) para que se ejecute solo si los anteriores no capturan el mensaje.
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, generic_message_handler_for_unsupported_types), group=1)

def calculate_telegram_login_hash(user, bot_token, auth_date):
    import hashlib
    import hmac

    data_check_string = []
    if user.id:
        data_check_string.append(f"id={user.id}")
    if user.first_name:
        data_check_string.append(f"first_name={user.first_name}")
    if user.last_name:
        data_check_string.append(f"last_name={user.last_name}")
    if user.username:
        data_check_string.append(f"username={user.username}")
    if getattr(user, "photo_url", None):
        data_check_string.append(f"photo_url={user.photo_url}")

    data_check_string.append(f"auth_date={auth_date}")

    data_check_string_sorted = sorted(data_check_string)
    data_check_string_joined = "\n".join(data_check_string_sorted)

    secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
    hmac_hash = hmac.new(secret_key, data_check_string_joined.encode('utf-8'), hashlib.sha256).hexdigest()

    return hmac_hash
