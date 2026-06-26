# telegram_gateway/handlers/admin_handlers.py

"""
Manejador para los comandos de administración del bot.
"""

import logging
import json

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, filters

from telegram_gateway.config import config
from telegram_gateway.api_client import set_default_prompt

logger = logging.getLogger(__name__)

# --- Estados para ConversationHandlers de Administración ---
# ¡CORREGIDO! Usamos un entero directamente en lugar de un objeto range.
PROMPT_INPUT = 0

# --- Filtro de Administrador ---
admin_filter = filters.User(user_id=[int(uid) for uid in config.admin_telegram_ids])


async def set_prompt_command(update: Update, context: CallbackContext) -> int:
    """
    Inicia la conversación para establecer el prompt de sistema por defecto.
    """
    if not update.message:
        return ConversationHandler.END

    await update.message.reply_text(
        "OK, envíame el nuevo prompt de sistema por defecto. "
        "Este prompt se usará para todos los usuarios que no tengan uno personalizado. "
        "Escribe /cancelar para abortar."
    )
    return PROMPT_INPUT


async def receive_new_prompt(update: Update, context: CallbackContext) -> int:
    """
    Recibe el nuevo prompt, lo envía a la API del backend y finaliza la conversación.
    """
    if not update.message or not update.message.text or not update.effective_user:
        return ConversationHandler.END

    new_prompt = update.message.text
    logger.info(f"Admin {update.effective_user.id} está actualizando el prompt por defecto.")

    success, message = await set_default_prompt(new_prompt)
    if success:
        await update.message.reply_text(f"✅ ¡Éxito! {message}")
    else:
        await update.message.reply_text(f"❌ Error al actualizar el prompt: {message}")

    return ConversationHandler.END


async def cancel_conversation(update: Update, context: CallbackContext) -> int:
    """
    Cancela la conversación actual.
    """
    if not update.message:
        return ConversationHandler.END
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END


def register_admin_handlers(application: Application) -> None:
    """
    Registra los manejadores de comandos de administración en la aplicación.
    """
    if not config.admin_telegram_ids:
        logger.warning("No se han definido ADMIN_TELEGRAM_IDS. Los comandos de administración no estarán disponibles.")
        return

    set_prompt_handler = ConversationHandler(
        entry_points=[CommandHandler("set_prompt", set_prompt_command, filters=admin_filter)],
        states={
            PROMPT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_prompt)]
        },
        fallbacks=[CommandHandler("cancelar", cancel_conversation, filters=admin_filter)],
    )

    application.add_handler(set_prompt_handler, group=0)
    logger.info("✅ Handlers de administración registrados.")
