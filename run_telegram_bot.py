# run_telegram_bot.py

"""
Punto de Entrada Principal para el Servicio del Cliente de Telegram.
"""

import logging
import asyncio
import signal
import sys
import os

from telegram import Update
from telegram.ext import Application, CallbackContext, MessageHandler, filters, PicklePersistence

# --- ¡CAMBIOS CLAVE EN LAS IMPORTACIONES! ---
# Ahora apuntamos a las nuevas ubicaciones de los módulos.
from core.database import create_tables
from core.config import settings
from telegram_client.bot_manager import bot_manager
from core.agenda_manager import reschedule_pending_reminders
from core.reminders_manager import reschedule_simple_reminders

from telegram_client.handlers.command_handlers import register_command_handlers
from telegram_client.handlers.message_handlers import register_message_handlers
from telegram_client.handlers.document_handlers import register_document_handlers
from telegram_client.handlers.admin_handlers import register_admin_handlers
from telegram_client.handlers.callback_query_handlers import register_callback_query_handler

# --- El resto del código es igual, solo cambian las importaciones ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_diagnostic_callback(update: Update, context: CallbackContext):
    """
    Handler de diagnóstico opcional que se ejecuta para CADA actualización.
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
    """
    logger.info("🔧 Inicializando recursos del cliente de Telegram...")

    bot_manager.initialize(application)
    logger.info("✅ BotManager inicializado.")
    
    if settings.debug_mode:
        application.add_handler(MessageHandler(filters.ALL, update_diagnostic_callback), group=-1)

    register_admin_handlers(application)
    register_document_handlers(application)
    register_message_handlers(application)
    register_command_handlers(application)
    register_callback_query_handler(application)

    await reschedule_pending_reminders(application)
    await reschedule_simple_reminders(application)
    
    logger.info("✅ Todos los handlers y recursos del cliente han sido inicializados.")


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