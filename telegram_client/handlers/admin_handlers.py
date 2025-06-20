# telegram_client/handlers/admin_handlers.py

"""
Manejador para los comandos de administración del bot.
"""

import logging
import httpx
import json

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, filters

from core.config import settings

logger = logging.getLogger(__name__)

# --- Estados para ConversationHandlers de Administración ---
# ¡CORREGIDO! Usamos un entero directamente en lugar de un objeto range.
PROMPT_INPUT = 0

# --- Filtro de Administrador ---
admin_filter = filters.User(user_id=[int(uid) for uid in settings.admin_telegram_ids])


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
    # ¡CORREGIDO! Ahora lee la URL desde la configuración centralizada.
    api_url = f"{settings.api_server_url}/api/admin/set-default-prompt"
    
    logger.info(f"Admin {update.effective_user.id} está actualizando el prompt por defecto.")

    try:
        async with httpx.AsyncClient() as client:
            # ¡CORREGIDO! Ahora lee el secreto desde la configuración centralizada.
            headers = {"X-Admin-Secret": settings.admin_secret}
            payload = {"default_prompt": new_prompt}
            
            response = await client.post(api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            api_response = response.json()
            await update.message.reply_text(f"✅ ¡Éxito! {api_response.get('message', 'Prompt actualizado.')}")

    except httpx.HTTPStatusError as e:
        error_detail = "Error del servidor."
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except json.JSONDecodeError:
            pass # Usar el mensaje por defecto si la respuesta no es JSON
        logger.error(f"Error de API al actualizar el prompt por defecto: {error_detail}")
        await update.message.reply_text(f"❌ Error al actualizar el prompt: {error_detail}")
    except Exception as e:
        logger.error(f"Error inesperado en receive_new_prompt: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error inesperado al contactar la API.")

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
    if not settings.admin_telegram_ids:
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
