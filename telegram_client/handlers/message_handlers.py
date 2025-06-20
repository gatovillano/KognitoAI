# telegram_client/handlers/message_handlers.py

"""
Manejadores para mensajes de texto, fotos, audio y la lógica de respuesta.

Este módulo ha sido refactorizado para actuar como un cliente ligero de la API
central. Su responsabilidad es recibir las interacciones del usuario, obtener la
identidad universal, empaquetar la información, enviarla al backend y luego
procesar la respuesta final, incluyendo la programación de notificaciones de
eventos, el envío de imágenes o la paginación de texto.
"""

import logging
import re
import asyncio
import tempfile
import os
import base64
import json
import httpx
from io import BytesIO
import uuid

from telegram import Update, Message, error as telegram_error
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler,
    CommandHandler,
)
from telegram.constants import ChatAction, ParseMode

# Importaciones de la nueva arquitectura y del proyecto
from core.config import settings
from core.database import get_or_create_account_from_platform_id, SessionLocal, AgendaEvent
from utils.db_session import DBSession
from telegram_client.bot_manager import bot_manager
from utils.helpers import sanitize_html
from utils.paginator import Paginator, split_text_into_pages
from utils.image_generation import GENERATED_IMAGE_KEY
from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from faster_whisper import WhisperModel

# ¡NUEVO! Importaciones para la programación de notificaciones
from telegram_client.notification_scheduler import schedule_telegram_job
from tools.schedule_event_tool import EVENT_ID_FOR_SCHEDULING_KEY


logger = logging.getLogger(__name__)

# --- Constantes y Configuración ---
PAGINATOR_SESSIONS_KEY = "paginator_sessions"
API_BASE_URL = settings.api_server_url

# --- Modelo para Whisper (transcripción de audio) ---
WHISPER_MODEL_SIZE = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
_whisper_model = None


async def get_whisper_model():
    """Carga y devuelve el modelo de transcripción, inicializándolo solo una vez."""
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"🗣️ Cargando modelo Faster Whisper: {WHISPER_MODEL_SIZE}...")
        try:
            loop = asyncio.get_event_loop()
            _whisper_model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
            )
            logger.info("✅ Modelo Faster Whisper cargado.")
        except Exception as e:
            logger.error(f"❌ Error cargando el modelo Faster Whisper: {e}", exc_info=True)
            _whisper_model = None
    return _whisper_model


async def send_typing_heartbeat(context: CallbackContext, chat_id: int, stop_event: asyncio.Event):
    """Envía una acción 'typing' cada 4 segundos para indicar que el bot está procesando."""
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
        except (asyncio.CancelledError, telegram_error.NetworkError):
            break
        except Exception as e:
            logger.warning(f"No se pudo enviar la acción de 'typing': {e}")
            break
def _should_respond_in_group(message: Message, bot_id: int, bot_username: str | None) -> bool:
    """
    Determina si el bot debe responder a un mensaje en un chat grupal.
    """
    if message.chat.type == 'private':
        return True
    if message.text and bot_username and f"@{bot_username}" in message.text:
        return True
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot_id:
        return True
    return False


# ...dentro de message_handlers.py

async def handle_chat_response(update: Update, context: CallbackContext, response_text: str):
    """
    Función de ayuda para enviar la respuesta final al usuario.

    Ahora incluye la lógica para:
    1. Enviar imágenes generadas.
    2. Paginar contenido de documentos.
    3. Programar los jobs de recordatorio de eventos.
    4. Enviar respuestas de texto simples.
    """
    if not update or not update.effective_chat or not update.effective_user:
        logger.warning("handle_chat_response fue llamada sin un contexto de usuario/chat válido.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # 1. Comprobar si hay una imagen generada para enviar
    if GENERATED_IMAGE_KEY in context.user_data:
        image_bytesio = context.user_data.pop(GENERATED_IMAGE_KEY)
        logger.info(f"Enviando imagen generada al usuario {user_id}...")
        image_bytesio.seek(0)
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=image_bytesio, caption=response_text)
            return
        except Exception as e:
            logger.error(f"Error al enviar la imagen generada: {e}", exc_info=True)
            # Si falla el envío de la imagen, enviamos el texto de todas formas.

    # 2. Comprobar si hay un documento para paginar
    document_title = context.user_data.pop(DOCUMENT_NAME_KEY, None)
    if document_title:
        logger.info(f"Paginando el documento '{document_title}' para el usuario {user_id}...")
        
        # ¡CORREGIDO! Primero dividimos el texto en chunks.
        chunks = split_text_into_pages(response_text, 3500)
        
        # Y luego pasamos los chunks al Paginator.
        paginator = Paginator(
            chunks=chunks, 
            title=document_title,
            parse_mode=ParseMode.HTML,
            prefix=f"doc_{uuid.uuid4().hex[:6]}" # Prefijo único
        )
        
        if PAGINATOR_SESSIONS_KEY not in context.user_data:
            context.user_data[PAGINATOR_SESSIONS_KEY] = {}
        context.user_data[PAGINATOR_SESSIONS_KEY][paginator.session_id] = paginator
        
        first_page, markup = paginator.get_page()
        await context.bot.send_message(
            chat_id=chat_id, 
            text=first_page, 
            reply_markup=markup, 
            parse_mode=paginator.parse_mode, 
            disable_web_page_preview=True
        )
        return

    # 3. Comprobar si hay un evento para programar su notificación
    event_id_to_schedule = context.user_data.pop(EVENT_ID_FOR_SCHEDULING_KEY, None)
    if event_id_to_schedule:
        logger.info(f"Se ha detectado el evento ID {event_id_to_schedule} para programar su notificación al usuario {user_id}.")
        async with DBSession(SessionLocal) as db:
            event = await db.get(AgendaEvent, event_id_to_schedule)
            if event and event.is_active:
                await schedule_telegram_job(event, telegram_id=user_id)
            else:
                logger.warning(f"Se intentó programar un job para el evento {event_id_to_schedule}, pero no se encontró o está inactivo.")

    # 4. Si no hay nada de lo anterior, enviar como texto simple.
    pages = split_text_into_pages(response_text, 4096)
    for i, page in enumerate(pages):
        try:
            await context.bot.send_message(chat_id=chat_id, text=page, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            if i < len(pages) - 1:
                await asyncio.sleep(0.5)
        except telegram_error.BadRequest as e:
            if "can't parse entities" in str(e):
                logger.warning(f"Error de parseo HTML, reintentando como texto plano. Error: {e}")
                await context.bot.send_message(chat_id=chat_id, text=page)
            else:
                raise e


    # ... (resto de la lógica sin cambios)
            
# ...dentro de message_handlers.py

async def process_and_get_response(update: Update, context: CallbackContext, user_message: str, image_base64: str | None = None):
    """
    Función central para procesar cualquier tipo de mensaje (texto, audio, etc.).

    Obtiene la identidad universal del usuario, empaqueta los datos y llama al
    backend (`/api/chat`) para obtener la respuesta de la IA. Luego, pasa esa
    respuesta a `handle_chat_response` para su correcta visualización.
    """
    if not update.message or not update.effective_user or not update.effective_chat:
        logger.warning("process_and_get_response fue llamada sin un contexto de mensaje/usuario/chat válido.")
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    
    typing_stop_event = asyncio.Event()
    typing_task = asyncio.create_task(send_typing_heartbeat(context, chat_id, typing_stop_event))

    account = None
    try:
        # ¡CORREGIDO! Aplicamos el patrón de desempaquetado seguro.
        result = await get_or_create_account_from_platform_id(
            platform='telegram', 
            platform_user_id=str(user.id),  # <-- Add missing comma here
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username
        )
        if not result:
            logger.error(f"No se pudo obtener/crear una cuenta para el usuario de Telegram {user.id}.")
            await update.message.reply_text("Lo siento, tuve un problema al identificar tu cuenta.")
            return
            
        account, _ = result
        
        api_payload = {
            "account_id": str(account.id),
            "telegram_id": user.id,
            "user_message": user_message,
            "image_base64": image_base64,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{settings.api_server_url}/api/chat", json=api_payload, timeout=300.0)
            response.raise_for_status()
            api_response = response.json()
            response_text = api_response.get("response_text", "No recibí una respuesta válida del servidor.")

        await handle_chat_response(update, context, response_text)

    except httpx.HTTPStatusError as e:
        account_id_log = str(account.id) if account else "Desconocida"
        error_detail = "Error del servidor."
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except json.JSONDecodeError:
            error_detail = e.response.text
        logger.error(f"Error de API al procesar mensaje para la cuenta {account_id_log}: {error_detail}")
        await update.message.reply_text(f"No pude procesar tu mensaje. Hubo un problema con el servidor: {error_detail}")
    except Exception as e:
        account_id_log = str(account.id) if account else "Desconocida"
        logger.error(f"Error inesperado en process_and_get_response para la cuenta {account_id_log}: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, ocurrió un error inesperado al procesar tu solicitud.")
    finally:
        typing_stop_event.set()
        await typing_task

async def text_message_handler(update: Update, context: CallbackContext):
    """
    Manejador principal para todos los mensajes de texto.
    """
    message = update.message
    if not message or not message.text or not message.from_user:
        return

    bot_id = context.bot.id
    bot_username = context.bot.username

    if message.chat.type != 'private':
        if not _should_respond_in_group(message, bot_id, bot_username):
            return
        
        # Eliminar la mención del bot del mensaje para que el agente no se confunda.
        user_message = re.sub(rf'@{bot_username}\b', '', message.text, flags=re.IGNORECASE).strip()
    else:
        user_message = message.text

    await process_and_get_response(update, context, user_message)


async def voice_message_handler(update: Update, context: CallbackContext):
    """

    Manejador para los mensajes de voz. Los transcribe a texto y los procesa.
    """
    message = update.message
    if not message or not message.voice or not message.from_user:
        return

    logger.info(f"Mensaje de voz recibido de {message.from_user.id}. Transcribiendo...")
    
    try:
        # Descargar el archivo de voz
        voice_file = await message.voice.get_file()
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio_file:
            await voice_file.download_to_drive(custom_path=temp_audio_file.name)
            temp_audio_path = temp_audio_file.name

        # Transcribir el audio a texto
        whisper_model = await get_whisper_model()
        if not whisper_model:
            await message.reply_text("Lo siento, el servicio de transcripción de audio no está disponible en este momento.")
            return

        segments, _ = whisper_model.transcribe(temp_audio_path, beam_size=5)
        transcribed_text = " ".join(segment.text for segment in segments).strip()

        # Limpiar el archivo temporal
        os.remove(temp_audio_path)
        
        if not transcribed_text:
            await message.reply_text("No pude entender el audio. ¿Podrías intentarlo de nuevo?")
            return

        logger.info(f"Texto transcrito: '{transcribed_text}'")
        await message.reply_text(f'<i>(Voz transcrita: "{transcribed_text}")</i>', parse_mode=ParseMode.HTML)
        
        # Procesar el texto transcrito como un mensaje normal.
        await process_and_get_response(update, context, transcribed_text)

    except Exception as e:
        logger.error(f"Error al procesar el mensaje de voz: {e}", exc_info=True)
        await message.reply_text("Lo siento, ocurrió un error al procesar tu mensaje de voz.")


async def photo_message_handler(update: Update, context: CallbackContext):
    """
    Manejador para los mensajes que contienen una foto.
    Extrae la imagen en formato base64 y el texto del caption.
    """
    message = update.message
    if not message or not message.photo or not message.from_user:
        return

    logger.info(f"Foto recibida de {message.from_user.id}. Procesando...")
    
    try:
        # Descargar la foto de mayor calidad
        photo_file = await message.photo[-1].get_file()
        
        # Descargar la imagen a un buffer en memoria
        image_buffer = BytesIO()
        await photo_file.download_to_memory(image_buffer)
        image_buffer.seek(0)
        
        # Codificar la imagen en base64
        image_base64 = base64.b64encode(image_buffer.read()).decode('utf-8')
        
        user_message = message.caption if message.caption else "Analiza esta imagen."
        
        await process_and_get_response(update, context, user_message, image_base64)
        
    except Exception as e:
        logger.error(f"Error al procesar la foto: {e}", exc_info=True)
        await message.reply_text("Lo siento, ocurrió un error al procesar la imagen.")


def register_message_handlers(application: Application) -> None:
    """Registra todos los manejadores de mensajes en la aplicación."""
    
    # El handler de texto es el más común. Se le da una prioridad más baja (1)
    # para que los ConversationHandlers tengan prioridad.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler), group=1)
    
    # Handlers para otros tipos de media.
    application.add_handler(MessageHandler(filters.VOICE, voice_message_handler), group=1)
    application.add_handler(MessageHandler(filters.PHOTO, photo_message_handler), group=1)
    
    logger.info("✅ Handlers de mensajes (texto, voz, foto) registrados.")
