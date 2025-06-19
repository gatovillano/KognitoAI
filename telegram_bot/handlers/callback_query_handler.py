# telegram_bot/handlers/callback_query_handlers.py

"""
Manejador para los `CallbackQuery` generados por los botones en línea.

Este módulo se especializa en manejar las interacciones del usuario con los
botones que aparecen debajo de los mensajes (InlineKeyboards). Su principal
caso de uso en esta aplicación es la gestión de la paginación para respuestas
largas, como el contenido de un documento.

Aunque la lógica de paginación es principalmente una función de la interfaz
y no interactúa directamente con el backend central, sigue siendo crucial
identificar correctamente al usuario para acceder a su `user_data`, donde se
almacena el estado de la sesión de paginación.
"""

import logging

from telegram import Update, error as telegram_error
from telegram.ext import Application, CallbackQueryHandler, CallbackContext

# Importaciones del proyecto
from utils.paginator import Paginator
from telegram_bot.handlers.message_handlers import PAGINATOR_SESSIONS_KEY

logger = logging.getLogger(__name__)


async def pagination_callback_handler(update: Update, context: CallbackContext) -> None:
    """

    Maneja los callbacks de los botones de paginación.
    
    Interpreta el `callback_data` para determinar la acción (siguiente/anterior)
    y la sesión de paginación a la que pertenece. Luego, actualiza el mensaje
    con la página correspondiente.
    """
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return

    try:
        await query.answer()  # Responde al callback para que el cliente de Telegram no muestre un reloj.
    except telegram_error.BadRequest:
        logger.warning(f"No se pudo responder al callback query, probablemente ya había expirado. User: {query.from_user.id}")
        return

    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"Callback de paginación recibido de {user_id} con data: '{callback_data}'")

    try:
        # El formato del callback_data es "paginator:{session_id}:{action}"
        parts = callback_data.split(':')
        if len(parts) != 3 or parts[0] != 'paginator':
            logger.warning(f"Formato de callback_data de paginación inválido: {callback_data}")
            return
            
        session_id = parts[1]
        action = parts[2]

        # Recuperar la sesión de paginación del user_data
        paginator_sessions = context.user_data.get(PAGINATOR_SESSIONS_KEY, {})
        paginator_instance: Paginator = paginator_sessions.get(session_id)

        if not paginator_instance:
            logger.warning(f"No se encontró una sesión de paginación activa con ID '{session_id}' para el usuario {user_id}.")
            await query.edit_message_text(
                text=query.message.text + "\n\n(Esta sesión de paginación ha expirado)",
                reply_markup=None  # Elimina los botones
            )
            return

        # Actualizar la página actual según la acción
        if action == 'next':
            paginator_instance.next_page()
        elif action == 'prev':
            paginator_instance.previous_page()
        
        # Obtener el nuevo contenido y el nuevo teclado de botones
        new_text, new_markup = paginator_instance.get_page()

        # Editar el mensaje original con el nuevo contenido y botones
        await query.edit_message_text(
            text=new_text,
            reply_markup=new_markup,
            parse_mode=paginator_instance.parse_mode,
            disable_web_page_preview=True
        )

    except telegram_error.BadRequest as e:
        if "Message is not modified" in str(e):
            logger.debug(f"El mensaje no fue modificado para el usuario {user_id} (probablemente doble clic).")
        else:
            logger.error(f"Error de BadRequest al actualizar el mensaje paginado para {user_id}: {e}", exc_info=True)
            try:
                # Intentar notificar al usuario que algo salió mal sin crashear.
                await query.edit_message_text(text=query.message.text + "\n\n(Error al cargar esta página)")
            except Exception as inner_e:
                logger.error(f"Fallo al intentar notificar al usuario sobre el error de paginación: {inner_e}")
    except Exception as e:
        logger.error(f"Error inesperado en pagination_callback_handler para {user_id}: {e}", exc_info=True)


def register_callback_query_handler(application: Application) -> None:
    """
    Registra los manejadores de callback query en la aplicación.
    """
    # Se registra un handler general que filtra por el prefijo "paginator:"
    handler = CallbackQueryHandler(pagination_callback_handler, pattern="^paginator:")
    application.add_handler(handler)
    logger.info("✅ Handler para callbacks de paginación registrado.")
