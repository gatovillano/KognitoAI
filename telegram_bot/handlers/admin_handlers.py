# telegram_bot/handlers/admin_handlers.py

"""
Manejador para los comandos de administración del bot.

Este módulo define las funciones que solo pueden ser ejecutadas por los
usuarios cuyo ID de Telegram se encuentra en la lista `ADMIN_TELEGRAM_IDS`
definida en la configuración.

En la nueva arquitectura, estos handlers actúan como clientes de una API de
administración segura en el `web_server.py`. Esto centraliza la lógica de
administración y la hace accesible desde diferentes interfaces.
"""

import logging
import httpx
import json

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, filters

from telegram_bot.config import settings

logger = logging.getLogger(__name__)

# --- Estados para ConversationHandlers de Administración ---
PROMPT_INPUT = range(200, 201)  # Usar un rango alto para evitar colisiones.

# --- Filtro de Administrador ---
# Crea un filtro personalizado para proteger los comandos de administrador.
admin_filter = filters.User(user_id=[int(uid) for uid in settings.admin_telegram_ids])


async def set_prompt_command(update: Update, context: CallbackContext) -> int:
    """
    Inicia la conversación para establecer el prompt de sistema por defecto.
    """
    if not update.message: return ConversationHandler.END
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
    if not update.message or not update.message.text: return ConversationHandler.END

    new_prompt = update.message.text
    api_url = f"{settings.api_server_url}/api/admin/set-default-prompt"
    
    logger.info(f"Admin {update.message.from_user.id} está actualizando el prompt por defecto.")

    try:
        async with httpx.AsyncClient() as client:
            headers = {"X-Admin-Secret": settings.admin_secret}
            payload = {"default_prompt": new_prompt}
            
            response = await client.post(api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            api_response = response.json()
            await update.message.reply_text(f"✅ ¡Éxito! {api_response.get('message', 'Prompt actualizado.')}")

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", e.response.text)
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
    if not update.message: return ConversationHandler.END
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END


def register_admin_handlers(application: Application) -> None:
    """
    Registra los manejadores de comandos de administración en la aplicación.
    """
    if not settings.admin_telegram_ids:
        logger.warning("No se han definido ADMIN_TELEGRAM_IDS. Los comandos de administración no estarán disponibles.")
        return

    # Conversación para establecer el prompt del sistema.
    set_prompt_handler = ConversationHandler(
        entry_points=[CommandHandler("set_prompt", set_prompt_command, filters=admin_filter)],
        states={
            PROMPT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_prompt)]
        },
        fallbacks=[CommandHandler("cancelar", cancel_conversation, filters=admin_filter)],
    )

    application.add_handler(set_prompt_handler, group=0) # Grupo 0 para máxima prioridad.
    logger.info("✅ Handlers de administración registrados.")
