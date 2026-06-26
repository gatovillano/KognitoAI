# telegram_gateway/handlers/workspace_handler.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from telegram_gateway.config import config
from telegram_gateway.api_client import get_or_create_account, get_workspaces

logger = logging.getLogger(__name__)

async def leave_workspace(update: Update, context: CallbackContext) -> None:
    """
    Manejador para el comando /leave_workspace.
    Permite al usuario salir del workspace actual.
    """
    if not update.message or not update.message.from_user:
        return

    user = update.message.from_user
    logger.info(f"Comando /leave_workspace recibido de {user.id} ({user.first_name})")

    # Eliminar el workspace_id del contexto para salir del workspace
    if 'current_workspace_id' in context.chat_data:
        del context.chat_data['current_workspace_id']
        await update.message.reply_text("✅ Has salido del workspace. Tu próxima conversación no tendrá un contexto de workspace específico.")
    else:
        await update.message.reply_text("📝 No estás en ningún workspace actualmente.")

    # Forzar la creación de un nuevo hilo en el próximo mensaje eliminando el ID del hilo actual.
    if 'current_chat_thread_id' in context.chat_data:
        del context.chat_data['current_chat_thread_id']


async def switch_workspace(update: Update, context: CallbackContext) -> None:
    """
    Manejador para el comando /workspace.
    Permite al usuario cambiar el workspace activo.
    """
    if not update.message or not update.message.from_user:
        return

    user = update.message.from_user
    logger.info(f"Comando /workspace recibido de {user.id} ({user.first_name})")

    try:
        auth_data = await get_or_create_account(
            platform_user_id=str(user.id),
            first_name=user.first_name,
            last_name=getattr(user, 'last_name', None),
            username=user.username,
        )
        if not auth_data:
            await update.message.reply_text("No pude encontrar tu cuenta. Intenta con /start primero.")
            return

        jwt_token = auth_data.get('access_token')
        context.chat_data['jwt_token'] = jwt_token

        workspaces = await get_workspaces(jwt_token)

        keyboard = [
            [InlineKeyboardButton(
                ws.get('name', f"Workspace {ws.get('id', '?')}"),
                callback_data=f"workspace_select_{ws.get('id')}"
            )]
            for ws in workspaces
        ]

        if not workspaces:
            # Mostrar mensaje con instrucciones y opción de comando
            help_message = "No tienes acceso a ningún workspace todavía. Puedes crear uno desde el panel web.\n\n"
            help_message += "💡 <b>Opciones disponibles:</b>\n"
            help_message += "• /leave_workspace - Salir del workspace actual\n"
            await update.message.reply_text(help_message, parse_mode='HTML')
            return

        # Agregar opción para salir del workspace
        keyboard.append([InlineKeyboardButton("🚪 Salir del workspace", callback_data="workspace_exit")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Elige el workspace al que quieres cambiar:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error en el handler /workspace para el usuario {user.id}: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, ocurrió un error al intentar cambiar de workspace.")


async def workspace_callback_handler(update: Update, context: CallbackContext) -> None:
    """Maneja la selección de un workspace desde el teclado inline."""
    query = update.callback_query
    await query.answer()

    if not query.data:
        return

    if query.data.startswith("workspace_select_"):
        workspace_id = query.data.split("workspace_select_")[1]

        # Guardar el workspace_id seleccionado en el contexto del chat.
        context.chat_data['current_workspace_id'] = workspace_id

        # Forzar la creación de un nuevo hilo en el próximo mensaje eliminando el ID del hilo actual.
        if 'current_chat_thread_id' in context.chat_data:
            del context.chat_data['current_chat_thread_id']

        # No consultamos la DB para el nombre - mostramos mensaje genérico
        await query.edit_message_text(text="✅ Workspace activado. Tu próxima conversación usará este contexto.")

    elif query.data == "workspace_exit":
        # Eliminar el workspace_id del contexto para salir del workspace
        if 'current_workspace_id' in context.chat_data:
            del context.chat_data['current_workspace_id']

        # Forzar la creación de un nuevo hilo en el próximo mensaje eliminando el ID del hilo actual.
        if 'current_chat_thread_id' in context.chat_data:
            del context.chat_data['current_chat_thread_id']

        await query.edit_message_text(text="✅ Has salido del workspace. Tu próxima conversación no tendrá un contexto de workspace específico.")

def register_workspace_handlers(application, group: int = 2):
    """Registra los manejadores de workspace."""
    application.add_handler(CommandHandler("workspace", switch_workspace), group=group)
    application.add_handler(CommandHandler("leave_workspace", leave_workspace), group=group)
    application.add_handler(CallbackQueryHandler(workspace_callback_handler, pattern="^workspace_"), group=group)
    logger.info("✅ Handlers de workspace registrados.")
