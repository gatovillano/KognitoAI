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
from utils.scheduled_tools_manager import initialize_all_scheduled_tools
from utils.embeddings import initialize_embeddings

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

    # 6. Inicializar modelo de embeddings.
    try:
        await initialize_embeddings()
        logger.info("✅ Modelo de embeddings inicializado.")
    except Exception as e:
        logger.error(f"❌ Error al inicializar embeddings: {e}", exc_info=True)
        # No es fatal, el bot puede funcionar sin embeddings para algunas funciones

    # 7. Inicializar herramientas programadas automáticas.
    logger.info("Inicializando herramientas programadas...")
    await initialize_all_scheduled_tools()
    logger.info("✅ Herramientas programadas inicializadas.")

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

    if ptb_app.updater:
        # Iniciar polling y añadir el callback síncrono.
        polling_task = asyncio.create_task(ptb_app.updater.start_polling(drop_pending_updates=True, error_callback=done_callback))
        polling_task.add_done_callback(done_callback)
        logger.info("✅ Tarea de polling de Telegram iniciada.")
        
        # Iniciar dispatcher y añadir el callback síncrono.
        dispatcher_task = asyncio.create_task(ptb_app.start())
        dispatcher_task.add_done_callback(done_callback)
        logger.info("✅ Tarea del dispatcher de PTB iniciada.")
        
        # Guardar las tareas para poder cancelarlas al apagar.
        app.state.background_tasks = [polling_task, dispatcher_task]
        
        # Configurar reintentos para errores de red
        async def retry_on_network_error():
            while True:
                if not ptb_app.updater.running:
                    try:
                        await ptb_app.updater.start_polling(drop_pending_updates=True, error_callback=done_callback)
                        logger.info("✅ Polling reiniciado con éxito.")
                        break
                    except Exception as e:
                        logger.error(f"❌ Error de red en polling, reintentando en 5 segundos: {e}", exc_info=True)
                        await asyncio.sleep(5)
                else:
                    logger.info("✅ Updater ya está corriendo, no se necesita reintento.")
                    break

        # Iniciar tarea de reintento si es necesario
        app.state.retry_task = asyncio.create_task(retry_on_network_error())

    yield # La API y el bot están ahora activos.

    # --- Lógica de Apagado ---
    logger.info("🔌 Apagando el cliente de Telegram...")
    ptb_to_shutdown = app.state.ptb_app
    if ptb_to_shutdown:
        if ptb_to_shutdown.running:
            await ptb_to_shutdown.stop()
            logger.info("✅ Dispatcher detenido.")
        
        if ptb_to_shutdown.updater and ptb_to_shutdown.updater.running:
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
    bot_instance = bot_manager.bot
    if bot_instance is None:
        raise HTTPException(status_code=503, detail="El bot de Telegram no está inicializado.")
    try:
        await bot_instance.send_message(chat_id=request.chat_id, text=request.text, parse_mode='HTML')
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en endpoint interno /send-message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al enviar mensaje.")

class StoreUserDataRequest(BaseModel):
    """Define la estructura de datos para una solicitud de almacenamiento de datos de usuario."""
    user_id: int
    key: str
    data: str  # Datos en base64 para la imagen

class BotCreateThreadRequest(BaseModel):
    """Define la estructura de datos para una solicitud de creación de hilo de bot."""
    chat_id: int
    thread_name: str

@internal_api.post("/internal/store-user-data")
async def store_user_data_endpoint(request: StoreUserDataRequest):
    """
    Endpoint de la API interna para almacenar datos en user_data de un usuario de Telegram.
    """
    if not bot_manager.is_initialized():
        raise HTTPException(status_code=503, detail="El cliente de Telegram no está listo.")
    try:
        import base64
        from io import BytesIO
        user_data = bot_manager.get_user_data(request.user_id)
        # Decodificar datos base64 a BytesIO para la imagen
        image_data = base64.b64decode(request.data)
        user_data[request.key] = BytesIO(image_data)
        await bot_manager.flush_persistence()  # Asegura que se guarde el estado
        logger.info(f"Datos almacenados en user_data para el usuario {request.user_id} con clave {request.key}.")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en endpoint interno /store-user-data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al almacenar datos de usuario.")

@internal_api.post("/internal/bot-create-thread")
async def bot_create_thread_endpoint(request: BotCreateThreadRequest):
    """
    Endpoint de la API interna para crear un hilo de conversación desde el bot de Telegram.
    """
    if not bot_manager.is_initialized():
        raise HTTPException(status_code=503, detail="El cliente de Telegram no está listo.")
    bot_instance = bot_manager.bot
    if bot_instance is None:
        raise HTTPException(status_code=503, detail="El bot de Telegram no está inicializado.")
    try:
        # Aquí se implementaría la lógica para crear un hilo de conversación en Telegram
        # Por ahora, solo registramos la solicitud y devolvemos un estado de éxito simulado
        logger.info(f"Creando hilo de conversación en chat {request.chat_id} con nombre {request.thread_name}")
        return {"status": "ok", "thread_id": f"thread_{request.chat_id}_{request.thread_name}"}
    except Exception as e:
        logger.error(f"Error en endpoint interno /bot-create-thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al crear hilo de conversación.")


if __name__ == "__main__":
    logger.info("Iniciando el servidor del cliente de Telegram en modo de desarrollo...")
    uvicorn.run(
        "run_telegram_bot:internal_api",
        host="0.0.0.0",
        port=9090,
        reload=True
    )
