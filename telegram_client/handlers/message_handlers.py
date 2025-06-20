# telegram_bot/handlers/message_handlers.py

"""
Manejadores para mensajes de texto, fotos, audio y callbacks de la interfaz de Telegram.

Este módulo ha sido refactorizado para actuar como un "cliente ligero" de la API
central. Su principal responsabilidad es recibir las interacciones del usuario,
identificar al usuario en el sistema universal de cuentas, empaquetar la
información y enviarla al backend (`web_server.py`) para su procesamiento.

Cambio Arquitectónico Clave:
En lugar de solo usar el `telegram_id`, este módulo ahora llama a la función
`get_or_create_account_from_platform_id` para obtener el `account_id` universal
del usuario. Luego, pasa tanto el `account_id` como el `telegram_id` a la API
central, permitiendo que el backend opere de forma agnóstica a la plataforma
mientras sigue pudiendo interactuar con sistemas de sesión específicos de Telegram.
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

from telegram import Update, Message, error as telegram_error
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    CommandHandler,
)
from telegram.constants import ChatAction, ParseMode

# Importaciones de la nueva arquitectura y del proyecto
from core.config import settings
from core.database import get_or_create_account_from_platform_id
from telegram_client.bot_manager import bot_manager
from utils.helpers import sanitize_html
from utils.paginator import Paginator, split_text_into_pages
from utils.image_generation import GENERATED_IMAGE_KEY
from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# --- Constantes y Configuración ---
PAGINATOR_SESSIONS_KEY = "paginator_sessions"
PAGINATOR_CHUNKS_KEY = "chunks"
PAGINATOR_PAGE_KEY = "current_page"
# settings.api_server_url no existe, usar settings.webapp_url si es para la webapp
API_BASE_URL = settings.webapp_url

# --- Estados de Conversación para acciones rápidas ---
(WAITING_FOR_NOTE_CONTENT, WAITING_FOR_EVENT_DETAILS) = range(100, 102)

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


def _should_respond_in_group(message: Message, bot_id: int, bot_username: str) -> bool:
    """Determina si el bot debe responder a un mensaje en un chat grupal."""
    if message.chat.type == "private":
        return True
    if message.text and f"@{bot_username}" in message.text:
        return True
    if message.reply_to_message and message.reply_to_message.from_user.id == bot_id:
        return True
    return False


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


async def handle_text_and_photo(update: Update, context: CallbackContext) -> None:
    """
    Manejador principal para mensajes de texto y fotos.
    Este es el punto de entrada para la mayoría de las interacciones del usuario.
    """
    if not update.message or not update.effective_user:
        return

    if not _should_respond_in_group(update.message, context.bot.id, context.bot.username):
        return

    logger.info(f"Procesando mensaje de texto/foto del usuario {update.effective_user.id}")

    stop_heartbeat = asyncio.Event()
    heartbeat_task = asyncio.create_task(send_typing_heartbeat(context, update.effective_chat.id, stop_heartbeat))

    image_base64 = None
    user_message = update.message.text or update.message.caption or ""

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image_base64 = base64.b64encode(photo_bytes).decode('utf-8')

    try:
        # --- Lógica de Identidad Universal ---
        telegram_id = update.effective_user.id
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name or ""
        
        account = await get_or_create_account_from_platform_id(
            platform='telegram',
            platform_user_id=str(telegram_id),
            platform_user_name=first_name
        )
        if not account:
            raise Exception("No se pudo obtener o crear una cuenta de usuario.")
        account_id = str(account.id) if account else None
        # --- Fin Lógica de Identidad ---

        api_payload = {
            "telegram_id": telegram_id,
            "account_id": account_id,
            "user_message": user_message,
            "image_base64": image_base64,
            "author_user_name": update.effective_user.first_name,
            "chat_id": update.effective_chat.id,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{API_BASE_URL}/api/chat", json=api_payload)
            response.raise_for_status()
            api_response_data = response.json()
            final_response = api_response_data.get("response_text", "No recibí una respuesta clara.")

        await process_and_send_response(update, context, final_response)

    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP al contactar la API: {e.response.status_code} - {e.response.text}", exc_info=True)
        error_detail = e.response.json().get("detail", "Error del servidor.")
        await update.message.reply_text(f"Hubo un problema de comunicación con mi cerebro: {error_detail}")
    except Exception as e:
        logger.error(f"Error en handle_text_and_photo: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, ocurrió un error inesperado al procesar tu mensaje.")
    finally:
        stop_heartbeat.set()
        await heartbeat_task


async def handle_audio(update: Update, context: CallbackContext) -> None:
    """Manejador para mensajes de voz, los transcribe y los procesa como texto."""
    if not update.message or not update.message.voice:
        return
    logger.info(f"Procesando mensaje de voz del usuario {update.effective_user.id}")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        voice_file = await update.message.voice.get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
            await voice_file.download_to_drive(custom_path=temp_audio_file.name)
            temp_audio_path = temp_audio_file.name

        whisper_model = await get_whisper_model()
        if not whisper_model:
            raise Exception("El modelo de transcripción no está disponible.")

        segments, _ = await asyncio.to_thread(whisper_model.transcribe, temp_audio_path, beam_size=5)
        transcribed_text = " ".join([segment.text for segment in segments]).strip()
        os.remove(temp_audio_path)

        if not transcribed_text:
            await update.message.reply_text("No pude entender el audio, ¿podrías repetirlo?")
            return
        
        # --- Lógica de Identidad Universal ---
        telegram_id = update.effective_user.id
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name or ""
        account = await get_or_create_account_from_platform_id(
            platform='telegram',
            platform_user_id=str(telegram_id),
            platform_user_name=first_name
        )
        if not account:
            raise Exception("No se pudo obtener o crear una cuenta de usuario.")
        account_id = str(account.id) if account else None
        # --- Fin Lógica de Identidad ---

        await update.message.reply_text(f"<i>(Transcripción: «{transcribed_text}»)</i>", parse_mode=ParseMode.HTML)

        api_payload = {
            "telegram_id": telegram_id,
            "account_id": account_id,
            "user_message": transcribed_text,
            "author_user_name": update.effective_user.first_name,
            "chat_id": update.effective_chat.id,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{API_BASE_URL}/api/chat", json=api_payload)
            response.raise_for_status()
            api_response_data = response.json()
            final_response = api_response_data.get("response_text", "No recibí una respuesta clara.")

        await process_and_send_response(update, context, final_response)

    except Exception as e:
        logger.error(f"Error en handle_audio: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, hubo un problema al procesar tu mensaje de voz.")


async def process_and_send_response(update: Update, context: CallbackContext, response_text: str):
    """
    Centraliza el envío de la respuesta final al usuario, manejando paginación
    y el envío de imágenes generadas.
    """
    chat_id = update.effective_chat.id
    user_data = context.user_data or {}
    
    # 1. Enviar imagen generada, si existe
    if GENERATED_IMAGE_KEY in user_data:
        image_bytesio = user_data[GENERATED_IMAGE_KEY]
        image_bytesio.seek(0)
        await context.bot.send_photo(chat_id=chat_id, photo=image_bytesio, caption=response_text)
        del user_data[GENERATED_IMAGE_KEY]
        return

    # 2. Manejar paginación de documentos largos
    document_name_to_paginate = user_data.get(DOCUMENT_NAME_KEY)
    if document_name_to_paginate:
        del user_data[DOCUMENT_NAME_KEY]
        title = f"Contenido de: {document_name_to_paginate}"
        pages = split_text_into_pages(response_text)
        paginator = Paginator(pages, title=title)
        
        paginator_key = f"paginator_{chat_id}_{update.message.message_id if update.message else 'cb'}"
        context.chat_data[paginator_key] = paginator

        message_text, keyboard = paginator.get_page()
        await context.bot.send_message(chat_id, text=message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return
        
    # 3. Enviar respuesta de texto simple
    await context.bot.send_message(chat_id, text=response_text, parse_mode=ParseMode.HTML)


def register_message_handlers(application: Application):
    """Registra todos los manejadores de mensajes en la aplicación."""
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_and_photo))
    application.add_handler(MessageHandler(filters.PHOTO, handle_text_and_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_audio))

# --- ConversationHandlers para notas rápidas (ejemplo) ---
# Esta lógica podría moverse a su propio módulo si crece.
async def start_add_note_from_button(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ok, ¿cuál es el contenido de la nota que quieres añadir?")
    return WAITING_FOR_NOTE_CONTENT

async def add_note_content_received(update: Update, context: CallbackContext) -> int:
    """
    Recibe el contenido de la nota del usuario, lo procesa y finaliza la conversación.
    """
    # ¡CORREGIDO! Añadimos guardas para asegurar que los objetos existen antes de usarlos.
    if not update.message or not update.message.text or not update.effective_user:
        logger.warning("add_note_content_received recibió una actualización inválida.")
        # Si no podemos continuar, es mejor terminar la conversación.
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Ocurrió un error inesperado. Por favor, intenta de nuevo."
        )
        return ConversationHandler.END

    note_content = update.message.text
    user = update.effective_user

    try:
        # Obtener la identidad universal del usuario.
        account = await get_or_create_account_from_platform_id(
            platform='telegram',
            platform_user_id=str(user.id),

        )
        if not account:
            logger.error(f"No se pudo obtener o crear una cuenta para el usuario de Telegram {user.id}.")
            await update.message.reply_text("Lo siento, no pude identificar tu cuenta en mi sistema. Por favor, intenta de nuevo más tarde.")
            return ConversationHandler.END

        # El account_id es un UUID, lo convertimos a string para el payload JSON.
        account_id_str = str(account.id)

        # Preparamos el payload para enviar a nuestra API central.
        api_payload = {
            "account_id": account_id_str,
            "telegram_id": user.id,
            "content": note_content
            # Podríamos añadir "title" y "category" si quisiéramos pedirlos en la conversación.
        }

        # La URL del endpoint en nuestro `run_api.py`.
        # ¡Importante! Este endpoint debe existir.
        api_url = f"{API_BASE_URL}/api/add-note"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=api_payload, timeout=20)
            response.raise_for_status() # Lanza una excepción para errores HTTP 4xx/5xx.
        
        await update.message.reply_text(f"¡Nota guardada exitosamente!")

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", "Error del servidor.")
        logger.error(f"Error de API al añadir nota para la cuenta {account_id_str}: {error_detail}")
        await update.message.reply_text(f"No pude guardar la nota. Hubo un problema con el servidor: {error_detail}")
    except Exception as e:
        logger.error(f"Error inesperado en add_note_content_received: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, ocurrió un error inesperado al intentar guardar tu nota.")

    return ConversationHandler.END

async def cancel_conversation(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

# def register_quick_action_conversations(application: Application):
#     conv_handler = ConversationHandler(
#         entry_points=[CallbackQueryHandler(start_add_note_from_button, pattern='^add_note$')],
#         states={
#             WAITING_FOR_NOTE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note_content_received)],
#         },
#         fallbacks=[CommandHandler('cancel', cancel_conversation)],
#     )
#     application.add_handler(conv_handler, group=1)