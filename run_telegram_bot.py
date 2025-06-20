# run_telegram_bot.py

"""
Punto de entrada principal para el servicio del cliente de Telegram.

Este módulo utiliza FastAPI para exponer una API interna que otros servicios
pueden usar para interactuar con Telegram (por ejemplo, para enviar notificaciones).

Utiliza el gestor de ciclo de vida (lifespan) de FastAPI para garantizar
que el bot de Telegram se inicie y se detenga de forma robusta y segura
junto con el servidor de la API.
"""

import logging
import asyncio
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from telegram.ext import Application

from core.config import settings
from telegram_client.bot_manager import bot_manager
from telegram_client.notification_scheduler import reschedule_pending_reminders
from core.database import create_tables

from telegram_client.handlers.command_handlers import register_command_handlers
from telegram_client.handlers.message_handlers import register_message_handlers
from telegram_client.handlers.callback_query_handler import register_callback_query_handler
from telegram_client.handlers.document_handlers import register_document_handlers
from telegram_client.handlers.admin_handlers import register_admin_handlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación de Telegram junto con FastAPI.

    Se encarga de la inicialización y el apagado ordenado del bot, evitando
    conflictos con el bucle de eventos de Uvicorn.
    """
    logger.info("🚀 Iniciando el ciclo de vida del servicio de Telegram...")
    
    try:
        await create_tables()
        logger.info("✅ Tablas de la base de datos verificadas/creadas.")
    except Exception as e:
        logger.error(f"❌ ERROR FATAL: No se pudieron crear las tablas de la DB. Error: {e}", exc_info=True)
        yield
        return

    if not settings.telegram_bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN no está configurado. El bot no se iniciará.")
        yield
        return

    # 1. Construir la aplicación de la forma estándar.
    #    Esto crea internamente una instancia de Updater y la asocia.
    ptb_app = Application.builder().token(settings.telegram_bot_token).build()
    bot_manager.initialize(ptb_app)
    
    # 2. Registrar todos los handlers.
    register_admin_handlers(ptb_app)
    register_document_handlers(ptb_app)
    register_message_handlers(ptb_app)
    register_command_handlers(ptb_app)
    register_callback_query_handler(ptb_app)
    
    # 3. Inicializar la aplicación. Prepara el bot, el dispatcher, etc.
    await ptb_app.initialize()
    
    # 4. Guardar la aplicación en el estado de FastAPI para usarla en el apagado.
    app.state.ptb_app = ptb_app
    
    # 5. Reprogramar recordatorios pendientes.
    await reschedule_pending_reminders(ptb_app)

    # --- LA CORRECCIÓN CLAVE ESTÁ AQUÍ ---
    def done_callback(task: asyncio.Task) -> None:
        """
        Función que se ejecuta cuando una tarea en segundo plano finaliza.
        Verifica si la tarea terminó con una excepción y la registra.
        """
        if task.cancelled():
            return
        if task.exception():
            logger.error(
                "❌ Excepción en una tarea de fondo de PTB:",
                exc_info=task.exception()
            )

    ptb_app = Application.builder().token(settings.telegram_bot_token).build()
    bot_manager.initialize(ptb_app)
    
    register_admin_handlers(ptb_app)
    register_document_handlers(ptb_app)
    register_message_handlers(ptb_app)
    register_command_handlers(ptb_app)
    register_callback_query_handler(ptb_app)
    
    await ptb_app.initialize()
    
    app.state.ptb_app = ptb_app
    
    await reschedule_pending_reminders(ptb_app)

    if ptb_app.updater:
        # Iniciar polling y añadir el callback síncrono.
        polling_task = asyncio.create_task(ptb_app.updater.start_polling(drop_pending_updates=True))
        polling_task.add_done_callback(done_callback)
        logger.info("✅ Tarea de polling de Telegram iniciada.")
        
        # Iniciar dispatcher y añadir el callback síncrono.
        dispatcher_task = asyncio.create_task(ptb_app.start())
        dispatcher_task.add_done_callback(done_callback)
        logger.info("✅ Tarea del dispatcher de PTB iniciada.")
        
        # Guardar las tareas para poder cancelarlas al apagar.
        app.state.background_tasks = [polling_task, dispatcher_task]

    yield # La API y el bot están ahora activos.

    # --- Lógica de Apagado ---
    logger.info("🔌 Apagando el cliente de Telegram...")
    ptb_to_shutdown = app.state.ptb_app
    if ptb_to_shutdown:
        if ptb_to_shutdown.running:
            await ptb_to_shutdown.stop()
            logger.info("✅ Dispatcher detenido.")
        
        if ptb_to_shutdown.updater and ptb_to_shutdown.updater.is_running():
            await ptb_to_shutdown.updater.stop()
            logger.info("✅ Polling detenido.")
            
        # Cancelar las tareas de fondo explícitamente.
        for task in app.state.get("background_tasks", []):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass # Es esperado

        await ptb_to_shutdown.shutdown()
        logger.info("✅ Cliente de Telegram completamente apagado.")

internal_api = FastAPI(lifespan=lifespan)


class SendMessageRequest(BaseModel):
    """Define la estructura de datos para una solicitud de envío de mensaje."""
    chat_id: int
    text: str


@internal_api.post("/internal/send-message")
async def send_message_endpoint(request: SendMessageRequest):
    """
    Endpoint de la API interna para enviar un mensaje a un chat de Telegram.
    """
    if not bot_manager.is_initialized():
        raise HTTPException(status_code=503, detail="El cliente de Telegram no está listo.")
    try:
        await bot_manager.bot.send_message(chat_id=request.chat_id, text=request.text, parse_mode='HTML')
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en endpoint interno /send-message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al enviar mensaje.")


if __name__ == "__main__":
    logger.info("Iniciando el servidor del cliente de Telegram en modo de desarrollo...")
    uvicorn.run(
        "run_telegram_bot:internal_api",
        host="0.0.0.0",
        port=9090,
        reload=True
    )