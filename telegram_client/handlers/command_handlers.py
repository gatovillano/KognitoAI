# telegram_bot/handlers/command_handlers.py

"""
Manejador para los comandos explícitos del bot (ej. /start, /documentos).

Este módulo define las funciones que se ejecutan cuando un usuario envía un
comando que comienza con '/'.

Cambios Arquitectónicos Clave:
-   **Identidad Universal:** Todas las funciones de comando que interactúan con
    los datos del usuario ahora obtienen el `account_id` universal a través de
    `get_or_create_account_from_platform_id`.
-   **Integración con WebApp:** El comando `/documentos` ahora genera una URL
    segura para la WebApp del panel de control. Utiliza la lógica de validación
    de `initData` de Telegram para pasar la identidad del usuario de forma
    segura al `web_server.py`, que sirve el panel.
-   **Llamadas a la API Central:** Los comandos que desencadenan acciones de la
    IA (aunque en este archivo son principalmente de bienvenida o de interfaz)
    se comunican con el backend central a través de peticiones HTTP.
"""

import logging
import httpx
import json

from telegram import Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Importaciones de la nueva arquitectura y del proyecto
from core.config import settings
from core.database import SessionLocal
from core.repositories.account_repository import AccountRepository
from utils.db_session import DBSession
from core.database import Workspace, SessionLocal

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
        async with DBSession(SessionLocal) as session:
            repo = AccountRepository(session)
            result = await repo.get_or_create_account_from_platform_id(
                platform='telegram',
                platform_user_id=str(user.id),
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username
            )
        # Luego, comprobamos si el resultado es válido antes de desempaquetar.
        if not result:
            logger.error(f"No se pudo obtener/crear una cuenta en /start para {user.id}.")
            # No es necesario enviar un mensaje de error aquí, el saludo es suficiente.
            return
        
        # Ahora es seguro desempaquetar.
        account, created = result
        
        if created:
            logger.info(f"Nueva cuenta creada ({account.id}) para el usuario de Telegram {user.id}.")
            welcome_message = (
                f"¡Hola {user.first_name}! 👋 Soy Kognito, tu asistente de IA personal. "
                "Encantado de conocerte. Puedes empezar a chatear conmigo directamente, "
                "o usar /documentos para ver el panel de control."
            )
        else:
            welcome_message = (
                f"¡Hola de nuevo, {user.first_name}! 👋 Qué bueno verte por aquí. "
                "¿En qué puedo ayudarte hoy?"
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

    # Es crucial que el usuario esté registrado para poder abrir el panel.
    try:
        async with DBSession(SessionLocal) as session:
            repo = AccountRepository(session)
            account, _ = await repo.get_or_create_account_from_platform_id(
                platform='telegram',
                platform_user_id=str(user.id),
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
            )

        if not account:
            raise Exception("La cuenta no pudo ser creada o recuperada.")
    except Exception as e:
        logger.error(f"Error al obtener/crear cuenta en /documentos para {user.id}: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error al preparar el panel. Por favor, inténtalo de nuevo más tarde.")
        return

    # La URL de nuestra WebApp, que es servida por web_server.py.
    # El `web_server` debe estar configurado para servir el panel en la ruta raíz.
    # Esta URL debe ser la URL pública donde se despliega el web_server.
    web_app_url = settings.webapp_url
    if not web_app_url:
        logger.error("❌ WEB_APP_URL no está configurada en .env. No se puede abrir el panel.")
        await update.message.reply_text("La función del panel de control no está configurada en este momento.")
        return

    logger.info(f"Generando enlace a WebApp para {user.id} en la URL: {web_app_url}")

    # Crear el botón que abrirá la WebApp.
    # La clase WebAppInfo se encarga de gestionar la comunicación segura (initData).
    keyboard = [
        [InlineKeyboardButton("Abrir Panel de Control", web_app=WebAppInfo(url=web_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Haz clic en el botón de abajo para abrir tu panel de control personal.",
        reply_markup=reply_markup
    )


async def open_conversation(update: Update, context: CallbackContext) -> None:
    """
    Manejador para el comando /abrir_conversacion.
    Abre o crea un hilo de conversación con el nombre especificado.
    """
    if not update.message or not update.message.from_user:
        return

    user = update.message.from_user
    logger.info(f"Comando /abrir_conversacion recibido de {user.id} ({user.first_name})")

    try:
        # Obtener el nombre de la conversación del texto del comando
        command_text = update.message.text.split()
        if len(command_text) < 2:
            await update.message.reply_text("Por favor, proporciona un nombre para la conversación. Uso: /abrir_conversacion <nombre>")
            return

        conversation_name = " ".join(command_text[1:])
        
        # Obtener o crear la cuenta del usuario
        async with DBSession(SessionLocal) as session:
            repo = AccountRepository(session)
            result = await repo.get_or_create_account_from_platform_id(
                platform='telegram',
                platform_user_id=str(user.id),
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username
            )
        
        if not result:
            logger.error(f"No se pudo obtener/crear una cuenta en /abrir_conversacion para {user.id}.")
            await update.message.reply_text("Lo siento, ocurrió un error al procesar tu solicitud.")
            return
        
        account, _ = result
        
        # Buscar o crear el hilo de conversación con el nombre dado
        from core.database import SessionLocal, ChatThread
        from utils.db_session import DBSession
        
        async with DBSession(SessionLocal) as db:
            # Buscar si existe un hilo con ese nombre para este usuario
            thread = await db.query(ChatThread).filter(
                ChatThread.account_id == account.id,
                ChatThread.name == conversation_name
            ).first()
            
            if thread:
                # Si existe, establecerlo como el hilo activo
                context.chat_data['current_chat_thread_id'] = thread.id
                await update.message.reply_text(f"Conversación '{conversation_name}' abierta. Puedes continuar chateando aquí.")
            else:
                # Si no existe, crear un nuevo hilo con ese nombre
                thread = ChatThread(
                    account_id=account.id,
                    title=conversation_name,
                    platform='telegram'
                )
                db.add(thread)
                await db.commit()
                await db.refresh(thread)
                context.chat_data['current_chat_thread_id'] = thread.id
                await update.message.reply_text(f"Nueva conversación '{conversation_name}' creada y abierta. Puedes empezar a chatear.")
                
    except Exception as e:
        logger.error(f"Error en el handler /abrir_conversacion para el usuario {user.id}: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, ocurrió un error al procesar tu solicitud. Por favor, intenta de nuevo.")

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
        async with DBSession(SessionLocal) as session:
            repo = AccountRepository(session)
            account, _ = await repo.get_or_create_account_from_platform_id(
                platform='telegram',
                platform_user_id=str(user.id),
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
            )

            if not account:
                await update.message.reply_text("No pude encontrar tu cuenta. Intenta con /start primero.")
                return

            # Lógica para obtener workspaces (esto podría ser una llamada a la API interna en el futuro)
            from core.database import Workspace, WorkspacePermission
            from sqlalchemy.future import select

            permission_stmt = select(WorkspacePermission.workspace_id).where(WorkspacePermission.account_id == account.id)
            stmt = select(Workspace).where(Workspace.id.in_(permission_stmt)).order_by(Workspace.name)
            
            result = await session.execute(stmt)
            workspaces = result.scalars().all()

            if not workspaces:
                await update.message.reply_text("No tienes acceso a ningún workspace todavía. Puedes crear uno desde el panel web.")
                return

            keyboard = [
                [InlineKeyboardButton(ws.name, callback_data=f"workspace_select_{ws.id}")]
                for ws in workspaces
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text("Elige el workspace al que quieres cambiar:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error en el handler /workspace para el usuario {user.id}: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, ocurrió un error al intentar cambiar de workspace.")


async def workspace_callback_handler(update: Update, context: CallbackContext) -> None:
    """Maneja la selección de un workspace desde el teclado inline."""
    query = update.callback_query
    await query.answer()

    if not query.data or not query.data.startswith("workspace_select_"):
        return

    workspace_id = query.data.split("workspace_select_")[1]
    
    context.chat_data['current_workspace_id'] = workspace_id

    from core.database import Workspace
    from sqlalchemy.future import select
    
    async with DBSession(SessionLocal) as session:
        workspace = await session.get(Workspace, workspace_id)
        if workspace:
            await query.edit_message_text(text=f"Workspace cambiado a: {workspace.name}")
        else:
            await query.edit_message_text(text="Error: No se pudo encontrar el workspace seleccionado.")


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
    application.add_handler(CommandHandler("abrir_conversacion", open_conversation), group=group)
    application.add_handler(CommandHandler("workspace", switch_workspace), group=group)
    application.add_handler(CallbackQueryHandler(workspace_callback_handler, pattern="^workspace_select_"), group=group)
    logger.info("✅ Handlers de comandos registrados.")
