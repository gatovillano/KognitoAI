# telegram_bot/main.py

"""
Punto de Entrada Principal para el Servicio del Bot de Telegram.

Este script es responsable de:
1.  Configurar el logging para toda la aplicación.
2.  Iniciar la conexión a la base de datos y crear las tablas si no existen (con
    la nueva estructura de Account/PlatformIdentity).
3.  Construir la instancia de la aplicación de `python-telegram-bot`.
4.  Inicializar el `bot_manager` para el acceso global a la aplicación.
5.  Registrar todos los handlers (comandos, mensajes, etc.) en grupos de prioridad.
6.  Volver a programar los recordatorios de agenda y simples que hayan quedado
    pendientes en la base de datos tras un reinicio.
7.  Manejar un apagado ordenado y seguro del bot (graceful shutdown).

Este módulo actúa como el "lanzador" del cliente de Telegram, que se comunica
con el backend central (`web_server.py`).
"""

import logging
import asyncio
import signal
import sys
import os

from telegram import Update
from telegram.ext import Application, CallbackContext, MessageHandler, filters, PicklePersistence

# --- Importaciones del proyecto ---
from telegram_bot.database import create_tables
from telegram_bot.config import settings
from telegram_bot.bot_manager import bot_manager
# ¡NUEVO! Importar las funciones de reprogramación de los managers refactorizados.
from telegram_bot.agenda_manager import reschedule_pending_reminders
from telegram_bot.reminders_manager import reschedule_simple_reminders

# --- Importar los módulos de registro de handlers ---
from telegram_bot.handlers.command_handlers import register_command_handlers
from telegram_bot.handlers.message_handlers import register_message_handlers, register_callback_query_handler
from telegram_bot.handlers.document_handlers import register_document_handlers
from telegram_bot.handlers.admin_handlers import register_admin_handlers

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_diagnostic_callback(update: Update, context: CallbackContext):
    """
    Handler de diagnóstico opcional que se ejecuta para CADA actualización.
    Es útil para depurar el flujo de updates y el estado de las conversaciones.
    """
    try:
        if update.message:
            logger.debug(f"DIAG: Message from {update.effective_user.id}. Text: {update.message.text[:50] if update.message.text else 'Non-text'}")
        elif update.callback_query:
            logger.debug(f"DIAG: Callback from {update.effective_user.id}. Data: {update.callback_query.data}")
    except Exception as e:
        logger.debug(f"DIAG: Error in diagnostic callback: {e}")


async def initialize_application_resources(application: Application):
    """
    Centraliza la inicialización de recursos y el registro de handlers.
    Se ejecuta una sola vez antes de que el bot empiece a recibir actualizaciones.
    """
    logger.info("🔧 Inicializando recursos de la aplicación...")

    bot_manager.initialize(application)
    logger.info("✅ BotManager inicializado.")
    
    # Grupos de prioridad: un número más bajo significa mayor prioridad.
    # Grupo -1: Diagnóstico.
    if settings.debug_mode:
        application.add_handler(MessageHandler(filters.ALL, update_diagnostic_callback), group=-1)

    # Grupo 0: Handlers de Administrador.
    register_admin_handlers(application)

    # Grupo 1: Handlers de Conversación de Usuario (documentos, notas, etc.).
    register_document_handlers(application)
    register_message_handlers(application)

    # Grupo 2: Handlers de Comandos y Callbacks no conversacionales.
    register_command_handlers(application)
    register_callback_query_handler(application)

    # ¡NUEVO! Llamar a las funciones de reprogramación al iniciar.
    await reschedule_pending_reminders(application)
    await reschedule_simple_reminders(application)
    
    logger.info("✅ Todos los handlers y recursos han sido inicializados.")


def main():
    """
    Función principal que configura y arranca el bot.
    """
    logger.info("🚀 Arrancando el servicio del Cliente de Telegram...")

    if not settings.telegram_bot_token:
        logger.error("❌ ERROR FATAL: TELEGRAM_BOT_TOKEN no está configurado. El bot no puede arrancar.")
        sys.exit(1)

    loop = asyncio.get_event_loop_policy().get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        # Se asegura de que las tablas (con la nueva estructura) existan.
        loop.run_until_complete(create_tables())
        logger.info("✅ Tablas de la base de datos verificadas/creadas exitosamente.")
    except Exception as e:
        logger.error(f"❌ ERROR FATAL: No se pudieron crear las tablas de la DB. El bot se detendrá. Error: {e}", exc_info=True)
        sys.exit(1)

    persistence_dir = "bot_data"
    os.makedirs(persistence_dir, exist_ok=True)
    persistence_file = os.path.join(persistence_dir, "bot_persistence.pickle")
    persistence = PicklePersistence(filepath=persistence_file, update_interval=30)
    logger.info(f"💾 Persistencia para ConversationHandlers configurada en: {persistence_file}")

    application = Application.builder().token(settings.telegram_bot_token).persistence(persistence).build()

    loop.run_until_complete(initialize_application_resources(application))

    stop_event = asyncio.Event()
    try:
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    except NotImplementedError:
        logger.warning("Manejadores de señales no soportados en este SO (ej. Windows).")
    
    polling_task = loop.create_task(application.run_polling(drop_pending_updates=True))
    
    try:
        logger.info("🤖 Cliente de Telegram iniciado y escuchando. Presiona Ctrl+C para detener.")
        loop.run_until_complete(stop_event.wait())
        logger.info("Señal de apagado recibida. Cerrando el bot...")
    except KeyboardInterrupt:
        logger.info("Interrupción de teclado recibida. Cerrando el bot...")
    finally:
        polling_task.cancel()
        try:
            loop.run_until_complete(asyncio.shield(polling_task))
        except asyncio.CancelledError:
            pass

        logger.info("💾 Guardando datos de persistencia antes de cerrar...")
        loop.run_until_complete(bot_manager.flush_persistence())
        loop.run_until_complete(application.shutdown())
        logger.info("✅ Aplicación de Telegram cerrada correctamente.")
        
        if not loop.is_closed():
            loop.close()
        
        logger.info("👋 Ejecución del bot finalizada.")
        sys.exit(0)

if __name__ == "__main__":
    main()