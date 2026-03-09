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
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configuración de logs inmediata
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Límite máximo para el tamaño de la imagen en base64 (5MB)
# Aproximadamente, 5MB de texto base64 equivalen a ~3.6MB de datos binarios.
# Este límite ayuda a prevenir el consumo excesivo de recursos por imágenes muy grandes.
MAX_IMAGE_BASE64_SIZE_MB = 5
MAX_IMAGE_BASE64_BYTES = MAX_IMAGE_BASE64_SIZE_MB * 1024 * 1024

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
from telegram_client.handlers.workspace_handler import register_workspace_handlers
from telegram_client.websocket_client import start_telegram_ws_client, stop_telegram_ws_client

logging.basicConfig(level=settings.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Mantener httpx en WARNING para evitar ruido excesivo de librerías de terceros
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
    register_workspace_handlers(ptb_app)
    
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
        # Iniciar la aplicación y el procesamiento de mensajes
        logger.info("Iniciando aplicación de Telegram (ptb_app.start())...")
        await ptb_app.start()

        # Iniciar polling y añadir el callback síncrono.
        logger.info("Iniciando updater.start_polling()...")
        polling_task = asyncio.create_task(ptb_app.updater.start_polling(drop_pending_updates=True, error_callback=done_callback))
        polling_task.add_done_callback(done_callback)
        logger.info("✅ Tarea de polling de Telegram iniciada.")
        
        # Iniciar cliente WebSocket
        logger.info("Iniciando start_telegram_ws_client()...")
        try:
            await start_telegram_ws_client(ptb_app) # Pasar la instancia de ptb_app
            logger.info("✅ Cliente WebSocket de Telegram iniciado.")
        except Exception as ws_err:
            logger.error(f"❌ Error crítico al iniciar el cliente WebSocket: {ws_err}", exc_info=True)

        # Guardar la tarea de polling para poder cancelarla al apagar.
        app.state.background_tasks = [polling_task]
        

    logger.info("🚀 Bot de Telegram y API interna listos y funcionando.")
    try:
        yield
    finally:
        # --- Lógica de Apagado Única y Limpia ---
        logger.info("🔌 Apagando el cliente de Telegram...")
        
        # 1. Detener el WebSocket
        await stop_telegram_ws_client()
        logger.info("✅ Cliente WebSocket de Telegram detenido.")

        # 2. Detener el polling si está activo
        if hasattr(app.state, 'ptb_app') and app.state.ptb_app.updater and app.state.ptb_app.updater.running:
            logger.info("Deteniendo polling de Telegram...")
            await app.state.ptb_app.updater.stop()
            logger.info("✅ Polling de Telegram detenido.")
            logger.info("Deteniendo aplicación de Telegram (ptb_app.stop())...")
            await app.state.ptb_app.stop()
            logger.info("✅ Aplicación de Telegram detenida.")
        
        # 3. Cancelar tareas en segundo plano
        if hasattr(app.state, 'background_tasks') and app.state.background_tasks:
            for task in app.state.background_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
            logger.info("✅ Tareas en segundo plano canceladas.")


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
    account_id: str
    chat_id: int
    workspace_id: Optional[str] = None

@internal_api.post("/internal/store-user-data")
async def store_user_data_endpoint(request: StoreUserDataRequest):
    """
    Endpoint de la API interna para almacenar datos en user_data de un usuario de Telegram.
    """
    if not bot_manager.is_initialized():
        raise HTTPException(status_code=503, detail="El cliente de Telegram no está listo.")
    try:
        if len(request.data) > MAX_IMAGE_BASE64_BYTES:
            logger.warning(f"Intento de almacenar imagen demasiado grande para el usuario {request.user_id}. Tamaño: {len(request.data)} bytes.")
            raise HTTPException(status_code=413, detail=f"La imagen excede el tamaño máximo permitido de {MAX_IMAGE_BASE64_SIZE_MB}MB.")

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
        from core.database import ChatThread, SessionLocal
        from utils.db_session import DBSession
        import uuid

        async with DBSession(SessionLocal) as session:
            new_thread = ChatThread(
                account_id=uuid.UUID(request.account_id),
                workspace_id=uuid.UUID(request.workspace_id) if request.workspace_id else None,
                title=f"Chat de Telegram - {request.chat_id}",
                platform="telegram"
            )
            session.add(new_thread)
            await session.commit()
            await session.refresh(new_thread)
            
            logger.info(f"Nuevo hilo {new_thread.id} creado para la cuenta {request.account_id} en el workspace {request.workspace_id}")
            return {"status": "ok", "id": str(new_thread.id)}

    except Exception as e:
        logger.error(f"Error en endpoint interno /bot-create-thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al crear hilo de conversación.")


if __name__ == "__main__":
    # Iniciar Uvicorn para la API interna. El bot se iniciará mediante el lifespan.
    logger.info("🚀 Iniciando servidor de Telegram (API interna + Bot)...")
    try:
        uvicorn.run(
            "run_telegram_bot:internal_api",
            host="0.0.0.0",
            port=9090,
            reload=False,
            workers=1,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO al iniciar el servicio: {e}", exc_info=True)
        sys.exit(1)

