# telegram_gateway/handlers/command_handlers.py

"""
Manejador para los comandos explícitos del bot (ej. /start, /documentos).

Este módulo define las funciones que se ejecutan cuando un usuario envía un
comando que comienza con '/'.

Versión gateway: todas las llamadas a base de datos han sido reemplazadas
por llamadas HTTP al Core API via api_client.
"""

import logging

from telegram import Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

from telegram_gateway.config import config
from telegram_gateway.api_client import get_or_create_account

logger = logging.getLogger(__name__)


async def start(update: Update, context: CallbackContext) -> None:
    """
    Manejador para el comando /start. Saluda al usuario y registra su cuenta.
    """
    if not update.message or not update.message.from_user:
        return

    user = update.message.from_user
    logger.info(f"Comando /start recibido de {user.id} ({user.first_name})")

    try:
        auth_data = await get_or_create_account(
            platform_user_id=str(user.id),
            first_name=user.first_name,
            last_name=getattr(user, 'last_name', None),
            username=user.username
        )
        if not auth_data:
            logger.error(f"No se pudo obtener/crear una cuenta en /start para {user.id}.")
            await update.message.reply_text("Lo siento, ocurrió un error al registrar tu cuenta. Por favor, intenta de nuevo.")
            return

        # Guardar el token para uso futuro
        jwt_token = auth_data.get('access_token')
        if jwt_token:
            context.chat_data['jwt_token'] = jwt_token

        welcome_message = (
            f"¡Hola {user.first_name}! 👋 Soy Kognito, tu asistente de IA personal. "
            "Puedes empezar a chatear conmigo directamente, "
            "o usar /documentos para ver el panel de control."
        )

        await update.message.reply_text(welcome_message)

    except Exception as e:
        logger.error(f"Error en el handler /start para el usuario {user.id}: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, ocurrió un error al procesar tu inicio. Por favor, intenta de nuevo.")


async def help_command(update: Update, context: CallbackContext) -> None:
    """
    Manejador para el comando /help. Muestra una lista de comandos útiles.
    """
    if not update.message:
        return

    logger.info(f"Comando /help recibido de {update.effective_user.id}")

    help_text = (
        "Aquí tienes una lista de cosas que puedes hacer:\n\n"
        "<b>Comandos Principales:</b>\n"
        "/start - Inicia una conversación conmigo.\n"
        "/documentos - Abre el panel de control para gestionar tus documentos, notas, agenda y personalidad.\n"
        "/workspace - Cambia el workspace activo.\n"
        "/help - Muestra este mensaje de ayuda.\n\n"
        "<b>Ejemplos de Conversación:</b>\n"
        "• 'Recuérdame llamar a Juan mañana a las 10am.'\n"
        "• 'Añade una nota: la idea para el proyecto es...'\n"
        "• '¿Qué tengo para hoy en mi agenda?'\n"
        "• 'Crea una imagen de un gato astronauta.'\n\n"
        "Simplemente envíame un mensaje y haré lo mejor para ayudarte."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


async def open_documents_panel(update: Update, context: CallbackContext) -> None:
    """
    Manejador para el comando /documentos.
    Abre la WebApp del panel de control.
    """
    if not update.message or not update.message.from_user:
        return

    user = update.message.from_user
    logger.info(f"Comando /documentos recibido de {user.id} ({user.first_name})")

    # Asegurar que el usuario tenga una cuenta/token antes de abrir el panel.
    try:
        auth_data = await get_or_create_account(
            platform_user_id=str(user.id),
            first_name=user.first_name,
            last_name=getattr(user, 'last_name', None),
            username=user.username,
        )
        if not auth_data:
            raise Exception("La cuenta no pudo ser creada o recuperada.")

        # Guardar el token para uso futuro
        jwt_token = auth_data.get('access_token')
        if jwt_token:
            context.chat_data['jwt_token'] = jwt_token

    except Exception as e:
        logger.error(f"Error al obtener/crear cuenta en /documentos para {user.id}: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error al preparar el panel. Por favor, inténtalo de nuevo más tarde.")
        return

    # La URL de nuestra WebApp.
    web_app_url = config.webapp_url
    if not web_app_url:
        logger.error("❌ TELEGRAM_WEBAPP_URL no está configurada en .env. No se puede abrir el panel.")
        await update.message.reply_text("La función del panel de control no está configurada en este momento.")
        return

    logger.info(f"Generando enlace a WebApp para {user.id} en la URL: {web_app_url}")

    # Crear el botón que abrirá la WebApp.
    keyboard = [
        [InlineKeyboardButton("Abrir Panel de Control", web_app=WebAppInfo(url=web_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Haz clic en el botón de abajo para abrir tu panel de control personal.",
        reply_markup=reply_markup
    )


def register_command_handlers(application: Application, group: int = 2):
    """
    Registra todos los manejadores de comandos en la aplicación de Telegram.

    Args:
        application: La instancia de la aplicación de `python-telegram-bot`.
        group: El grupo de prioridad para los handlers.
    """
    application.add_handler(CommandHandler("start", start), group=group)
    application.add_handler(CommandHandler("help", help_command), group=group)
    application.add_handler(CommandHandler("documentos", open_documents_panel), group=group)
    logger.info("✅ Handlers de comandos registrados.")
