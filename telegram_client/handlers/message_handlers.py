# telegram_client/handlers/message_handlers.py

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
from typing import Optional
import httpx
from io import BytesIO
import uuid
import time

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

from core.config import settings
from core.database import get_or_create_account_from_platform_id, SessionLocal, AgendaEvent, ChatThread
from utils.db_session import DBSession
from telegram_client.bot_manager import bot_manager
#from utils.helpers import sanitize_html
from utils.paginator import Paginator, split_text_into_pages
from utils.image_generation import GENERATED_IMAGE_KEY
from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from tools.schedule_event_tool import EVENT_ID_FOR_SCHEDULING_KEY
from telegram_client.notification_scheduler import schedule_telegram_job
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Clave utilizada en context.user_data para almacenar un diccionario de sesiones
# de paginación activas para el usuario. Esto permite manejar múltiples instancias
# de paginación simultáneamente (ej., diferentes documentos o listas).
PAGINATOR_SESSIONS_KEY = "paginator_sessions"
API_BASE_URL = settings.api_server_url
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

async def handle_chat_response(update: Update, context: CallbackContext, response_text: str) -> None:
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
        return None

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # 1. Comprobar si hay una imagen generada para enviar (desde BytesIO)
    if GENERATED_IMAGE_KEY in context.user_data:
        image_bytesio = context.user_data.pop(GENERATED_IMAGE_KEY)
        logger.info(f"Enviando imagen generada al usuario {user_id} desde BytesIO...")
        image_bytesio.seek(0)
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=image_bytesio, caption=response_text)
            return None # Importante: Retornar None para detener la propagación.
        except Exception as e:
            logger.error(f"Error al enviar la imagen generada desde BytesIO: {e}", exc_info=True)
            # Si falla el envío de la imagen, enviamos el texto de todas formas (caerá al caso 4).

    # 2. Comprobar si hay una ruta de imagen generada para enviar (desde archivo temporal)
    if 'generated_image_path' in context.user_data:
        image_path = context.user_data.pop('generated_image_path')
        logger.info(f"Enviando imagen generada al usuario {user_id} desde archivo {image_path}...")
        try:
            with open(image_path, 'rb') as image_file:
                await context.bot.send_photo(chat_id=chat_id, photo=image_file, caption=response_text)
            return None # Importante: Retornar None para detener la propagación.
        except Exception as e:
            logger.error(f"Error al enviar la imagen generada desde archivo {image_path}: {e}", exc_info=True)
            # Si falla el envío de la imagen, enviamos el texto de todas formas (caerá al caso 5).

    # 2. Comprobar si hay un documento para paginar
    document_title = context.user_data.pop(DOCUMENT_NAME_KEY, None)
    if document_title:
        logger.info(f"Paginando el documento '{document_title}' para el usuario {user_id}...")
        chunks = split_text_into_pages(response_text, 3500) # Límite de caracteres para asegurar espacio de encabezado/pie.
        paginator = Paginator(
            chunks=chunks,
            title=document_title,
            parse_mode=ParseMode.HTML,
            prefix=f"doc_{uuid.uuid4().hex[:6]}" # Prefijo único para la sesión del paginador
        )
        if PAGINATOR_SESSIONS_KEY not in context.user_data:
            context.user_data[PAGINATOR_SESSIONS_KEY] = {}
        context.user_data[PAGINATOR_SESSIONS_KEY][paginator.session_id] = paginator
        first_page, markup = paginator.get_page()
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=first_page,
                reply_markup=markup,
                parse_mode=paginator.parse_mode,
                disable_web_page_preview=True
            )
            return None # Importante: Retornar None para detener la propagación.
        except Exception as e:
            logger.error(f"Error al enviar la primera página del documento paginado: {e}", exc_info=True)
            # Si falla el envío paginado, intentamos enviar como texto simple (caerá al caso 4).

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
        # No se retorna None aquí, porque la programación del job no impide enviar la respuesta de texto del agente.

    # 4. Si no hay nada de lo anterior o falló, enviar como texto simple.
    pages = split_text_into_pages(response_text, 4096) # Telegram tiene un límite de 4096 caracteres.
    for i, page in enumerate(pages):
        try:
            logger.info(f"[DEBUG TELEGRAM OUT] Texto enviado a Telegram (página {i+1}):\n{page}")
            await context.bot.send_message(chat_id=chat_id, text=page, disable_web_page_preview=True)
            if i < len(pages) - 1:
                await asyncio.sleep(0.5) # Pequeña pausa entre mensajes si hay múltiples páginas.
        except telegram_error.BadRequest as e:
            logger.warning(f"Error al enviar mensaje de texto plano: {e}")
            # Si falla, no reintentamos con otro formato.
    return None # Importante: Retornar None para detener la propagación después de enviar la respuesta final.

async def process_and_get_response(update: Update, context: CallbackContext, user_message: str, image_base64: Optional[str] = None) -> None:
    """
    Función central para procesar cualquier tipo de mensaje (texto, audio, etc.).

    Obtiene la identidad universal del usuario, gestiona el hilo de chat actual,
    empaqueta los datos y llama al backend (`/api/chat`) para obtener la
    respuesta de la IA.
    """
    if not update.message or not update.effective_user or not update.effective_chat:
        logger.warning("process_and_get_response fue llamada sin un contexto de mensaje/usuario/chat válido.")
        return None

    user = update.effective_user
    chat_id = update.effective_chat.id
    typing_stop_event = asyncio.Event()
    typing_task = asyncio.create_task(send_typing_heartbeat(context, chat_id, typing_stop_event))

    account = None
    current_thread_id = context.chat_data.get(CURRENT_CHAT_THREAD_ID_KEY)

    try:
        # 1. Obtener la identidad universal del usuario.
        result = await get_or_create_account_from_platform_id(
            platform='telegram',
            platform_user_id=str(user.id),
            first_name=user.first_name,
            username=user.username
        )
        if not result:
            error_msg = "Lo siento, tuve un problema al identificar tu cuenta. No puedo procesar tu solicitud."
            await update.message.reply_text(error_msg)
            return None
        account, _ = result
        account_id_str = str(account.id) # Convertir UUID a string para el payload.

        # 2. Gestionar el hilo de conversación.
        if not current_thread_id:
            logger.info(f"No hay hilo activo para la cuenta {account_id_str}. Creando uno nuevo...")
            # Llamar al endpoint /internal/bot-create-thread para que el bot cree un hilo interno.
            try:
                create_thread_url = f"{API_BASE_URL}/internal/bot-create-thread" # Endpoint para el bot
                internal_headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Internal-API-Key': settings.internal_api_key_for_bot # Clave API interna
                }
                # Enviar como formulario, no como JSON
                create_payload = {'account_id': account_id_str}
                async with httpx.AsyncClient() as client:
                    response = await client.post(create_thread_url, headers=internal_headers, data=create_payload, timeout=10)
                    response.raise_for_status()
                
                thread_data = response.json()
                logger.info(f"Respuesta de /internal/bot-create-thread: {thread_data}")
                if 'id' in thread_data:
                    current_thread_id = thread_data['id']
                elif 'thread_id' in thread_data:
                    current_thread_id = thread_data['thread_id']
                else:
                    logger.error(f"La respuesta no contiene 'id' ni 'thread_id'. Respuesta: {thread_data}")
                    await update.message.reply_text(f"No pude iniciar una nueva conversación. Respuesta inesperada del servidor: {thread_data}")
                    return None
                context.chat_data[CURRENT_CHAT_THREAD_ID_KEY] = current_thread_id
                logger.info(f"Nuevo hilo {current_thread_id} creado para la cuenta {account_id_str}.")
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json().get("detail", "Error del servidor al crear hilo.")
                logger.error(f"Error al crear hilo para la cuenta {account_id_str}: {error_detail}")
                await update.message.reply_text(f"No pude iniciar una nueva conversación. Problema: {error_detail}")
                return None
            except Exception as e:
                logger.error(f"Error inesperado al crear hilo para la cuenta {account_id_str}: {e}", exc_info=True)
                await update.message.reply_text("Ocurrió un error inesperado al iniciar la conversación.")
                return None
        
        # Verificar si ha habido inactividad por más de 10 minutos
        now = time.time()
        last_message_ts = context.chat_data.get(LAST_MESSAGE_TIMESTAMP_KEY)
        # Si hay hilo y hay timestamp, verificar inactividad
        if last_message_ts and current_thread_id:
            if now - last_message_ts > INACTIVITY_TIMEOUT_SECONDS:
                # Iniciar nuevo hilo por inactividad
                context.chat_data[CURRENT_CHAT_THREAD_ID_KEY] = None
                current_thread_id = None

        # 3. Construir el payload para la API central de chat.
        api_payload = {
            "account_id": account_id_str,
            "telegram_id": user.id, # telegram_id puede ser Optional[int] en el Pydantic BaseModel de la API
            "thread_id": current_thread_id,
            "user_message": user_message,
            "image_base64": image_base64,
        }
        
        # 4. Realizar la llamada a la API del agente.
        chat_api_url = f"{API_BASE_URL}/api/chat"
        # Obtener token JWT para el usuario (si no existe en chat_data, solicitarlo)
        jwt_token = context.chat_data.get("jwt_token")
        if not jwt_token:
            telegram_login_url = f"{API_BASE_URL}/api/auth/telegram/callback"
            auth_date = int(time.time())
            hash_value = calculate_telegram_login_hash(user, settings.telegram_bot_token, auth_date)
            telegram_login_payload = {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": getattr(user, "last_name", None),
                "username": getattr(user, "username", None),
                "photo_url": getattr(user, "photo_url", None),
                "auth_date": auth_date,
                "hash": hash_value
            }
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(telegram_login_url, json=telegram_login_payload, timeout=10)
                    resp.raise_for_status()
                    token_data = resp.json()
                    jwt_token = token_data.get("access_token")
                    context.chat_data["jwt_token"] = jwt_token
            except Exception as e:
                logger.error(f"No se pudo obtener el token JWT para el usuario {user.id}: {e}", exc_info=True)
                await update.message.reply_text("No se pudo autenticar tu sesión. Intenta de nuevo más tarde.")
                return None
        headers = {"Authorization": f"Bearer {jwt_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(chat_api_url, json=api_payload, headers=headers, timeout=300.0)
            response.raise_for_status()
        
        api_response = response.json()
        response_text = api_response.get("response_text", "No recibí una respuesta válida del servidor.")

        # 5. Pasar la respuesta a la función que la envía al usuario.
        # Antes de enviar la respuesta, esperar un breve momento para permitir que la imagen se almacene en user_data.
        await asyncio.sleep(2)  # Esperar 2 segundos para que la API de almacenamiento de imagen complete.
        await handle_chat_response(update, context, response_text)

    except httpx.HTTPStatusError as e:
        account_id_log = str(account.id) if account else "Desconocida"
        error_detail = "Error del servidor."
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except json.JSONDecodeError:
            error_detail = e.response.text
        logger.error(f"Error de API al procesar mensaje para la cuenta {account_id_log}: {error_detail}")
        error_msg = "No pude procesar tu mensaje. Hubo un problema con el servidor: {}".format(error_detail)
        await update.message.reply_text(error_msg)
    except Exception as e:
        account_id_log = str(account.id) if account else "Desconocida"
        logger.error(f"Error inesperado en process_and_get_response para la cuenta {account_id_log}: {e}", exc_info=True)
        error_msg = "Lo siento, ocurrió un error inesperado al procesar tu solicitud."
        logger.error(f"[DEBUG TELEGRAM OUT][ERROR] Mensaje escapado a enviar: {repr(error_msg)}")
        await update.message.reply_text(error_msg)
    finally:
        # Asegurarse de que el indicador "escribiendo..." siempre se detenga.
        typing_stop_event.set()
        await typing_task
    
    return None # Importante: Retornar None para detener la propagación.

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
    return None # Importante: Retornar None para detener la propagación.

async def text_message_handler(update: Update, context: CallbackContext) -> None:
    """Manejador principal para todos los mensajes de texto."""
    message = update.message
    if not message or not message.text or not message.from_user:
        return None
    
    if message.chat.type in ['group', 'supergroup']:
        bot_id = context.bot.id
        if not _should_respond_in_group(message, bot_id, bot_username=context.bot.username):
            return None # No responder en grupo si no cumple las condiciones.
    
    await process_and_get_response(update, context, user_message=message.text)
    # Después de procesar el mensaje, verificar si hay una imagen en user_data para enviar.
    if GENERATED_IMAGE_KEY in context.user_data:
        await handle_chat_response(update, context, response_text="¡Hecho! He generado la imagen.")
    return None # Importante: Retornar None para detener la propagación.

async def voice_message_handler(update: Update, context: CallbackContext) -> None:
    """Manejador para mensajes de voz."""
    message = update.message
    if not message or not message.voice or not message.from_user:
        return None
    
    if message.chat.type in ['group', 'supergroup']:
        bot_id = context.bot.id
        if not _should_respond_in_group(message, bot_id, bot_username=context.bot.username):
            return None # No responder en grupo si no cumple las condiciones.
    
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
    
    return None # Importante: Retornar None para detener la propagación.

async def photo_message_handler(update: Update, context: CallbackContext) -> None:
    """Manejador para mensajes que contienen una foto."""
    message = update.message
    if not message or not message.photo or not message.from_user:
        return None
    
    if message.chat.type in ['group', 'supergroup']:
        bot_id = context.bot.id
        if not _should_respond_in_group(message, bot_id, bot_username=context.bot.username):
            return None # No responder en grupo si no cumple las condiciones.
    
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
    
    return None # Importante: Retornar None para detener la propagación.

def register_message_handlers(application: Application) -> None:
    """Registra todos los manejadores de mensajes en la aplicación."""
    # Handlers específicos para tipos de mensaje que se envían al agente de IA.
    # Estos deben tener la PRIORIDAD MÁS ALTA (group=0) para que se procesen primero.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler), group=0)
    application.add_handler(MessageHandler(filters.VOICE, voice_message_handler), group=0)
    application.add_handler(MessageHandler(filters.PHOTO, photo_message_handler), group=0)

    # Handler genérico (comodín) para mensajes que no son de los tipos anteriores o comandos.
    # Este debe tener una PRIORIDAD MÁS BAJA (group=1) para que solo se active si los
    # handlers específicos NO procesaron el mensaje.
    # Su filtro es para 'todo' lo que no es TEXTO, VOZ, FOTO o COMANDO.
    application.add_handler(MessageHandler(filters.ALL & ~filters.TEXT & ~filters.VOICE & ~filters.PHOTO & ~filters.COMMAND, generic_message_handler_for_unsupported_types), group=1)
    logger.info("✅ Handlers de mensajes (texto, voz, foto y genérico) registrados.")

def calculate_telegram_login_hash(user, bot_token, auth_date):
    import hashlib
    import hmac
    data_check_arr = [
        f"auth_date={auth_date}",
        f"first_name={user.first_name}",
        f"id={user.id}"
    ]
    if getattr(user, "last_name", None):
        data_check_arr.append(f"last_name={user.last_name}")
    if getattr(user, "username", None):
        data_check_arr.append(f"username={user.username}")
    # photo_url no es obligatorio
    if getattr(user, "photo_url", None):
        data_check_arr.append(f"photo_url={user.photo_url}")
    data_check_arr.sort()
    data_check_string = '\n'.join(data_check_arr)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
