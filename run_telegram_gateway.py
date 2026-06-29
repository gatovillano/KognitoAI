# run_telegram_gateway.py

"""
Punto de entrada para el servicio telegram_gateway.

Servicio ultraligero que maneja SOLO la integración con Telegram.
No importa nada del core/, no usa langchain, no requiere ML.
Toda la lógica de negocio se delega al Core API via HTTP/WebSocket.

Para ejecutar:
    PYTHONPATH=. ./venv_host/bin/python run_telegram_gateway.py

O agregado al start_local.sh para correr junto al backend y frontend.
"""

import logging
import asyncio
import sys
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configuración de logging inmediata
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Silenciar librerías ruidosas
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from telegram.ext import Application

from telegram_gateway.config import config
from telegram_gateway.bot_manager import bot_manager
from telegram_gateway.notification_scheduler import reschedule_pending_reminders
from telegram_gateway.websocket_client import start_telegram_ws_client, stop_telegram_ws_client

from telegram_gateway.handlers.command_handlers import register_command_handlers
from telegram_gateway.handlers.message_handlers import register_message_handlers
from telegram_gateway.handlers.callback_query_handler import register_callback_query_handler
from telegram_gateway.handlers.document_handlers import register_document_handlers
from telegram_gateway.handlers.admin_handlers import register_admin_handlers
from telegram_gateway.handlers.workspace_handler import register_workspace_handlers

# Actualizar nivel de logging según config
logging.getLogger().setLevel(config.log_level)

MAX_IMAGE_BASE64_SIZE_MB = 500
MAX_IMAGE_BASE64_BYTES = MAX_IMAGE_BASE64_SIZE_MB * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida del gateway de Telegram."""
    logger.info("🚀 Iniciando telegram_gateway...")

    if not config.telegram_bot_token:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN no configurado. El gateway iniciará en modo sin bot (solo health check).")
        yield
        return

    # Construir la aplicación de Telegram
    ptb_app = Application.builder().token(config.telegram_bot_token).build()
    bot_manager.initialize(ptb_app)

    # Registrar handlers
    register_admin_handlers(ptb_app)
    register_document_handlers(ptb_app)
    register_message_handlers(ptb_app)
    register_command_handlers(ptb_app)
    register_callback_query_handler(ptb_app)
    register_workspace_handlers(ptb_app)

    # Inicializar la aplicación PTB
    await ptb_app.initialize()
    app.state.ptb_app = ptb_app

    # Configurar los comandos para el autocompletado en Telegram
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Iniciar conversación y registrar cuenta"),
        BotCommand("help", "Mostrar la guía de ayuda y comandos"),
        BotCommand("documentos", "Abrir el panel de control (notas, documentos, agenda)"),
        BotCommand("workspace", "Cambiar el workspace activo")
    ]
    try:
        await ptb_app.bot.set_my_commands(commands)
        logger.info("✅ Autocompletado de comandos registrado con éxito en Telegram.")
    except Exception as e:
        logger.error(f"❌ No se pudieron registrar los comandos de autocompletado en Telegram: {e}")

    # Re-programar recordatorios pendientes (API-based, no DB directa)
    await reschedule_pending_reminders(ptb_app)

    def done_callback(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        if task.exception():
            logger.error("❌ Excepción en tarea de fondo PTB:", exc_info=task.exception())

    if ptb_app.updater:
        logger.info("Iniciando polling de Telegram...")
        await ptb_app.start()
        polling_task = asyncio.create_task(
            ptb_app.updater.start_polling(drop_pending_updates=True, error_callback=done_callback)
        )
        polling_task.add_done_callback(done_callback)
        logger.info("✅ Polling iniciado.")

        logger.info("Iniciando cliente WebSocket hacia el core...")
        try:
            await start_telegram_ws_client(ptb_app)
            logger.info("✅ Cliente WebSocket iniciado.")
        except Exception as ws_err:
            logger.error(f"❌ Error al iniciar WebSocket: {ws_err}", exc_info=True)

        app.state.background_tasks = [polling_task]

    logger.info(f"🚀 telegram_gateway listo. Core API: {config.core_api_url}")
    logger.info(f"   WebSocket Core: {config.core_ws_url}")

    try:
        yield
    finally:
        logger.info("🔌 Apagando telegram_gateway...")

        await stop_telegram_ws_client()
        logger.info("✅ WebSocket detenido.")

        if hasattr(app.state, 'ptb_app') and app.state.ptb_app.updater and app.state.ptb_app.updater.running:
            await app.state.ptb_app.updater.stop()
            await app.state.ptb_app.stop()
            logger.info("✅ Bot detenido.")

        if hasattr(app.state, 'background_tasks'):
            for task in app.state.background_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*app.state.background_tasks, return_exceptions=True)


gateway_api = FastAPI(
    title="Telegram Gateway",
    description="Servicio ultraligero de integración con Telegram: http://localhost:9091",
    lifespan=lifespan
)


class SendMessageRequest(BaseModel):
    chat_id: int
    text: str


class StoreUserDataRequest(BaseModel):
    user_id: int
    key: str
    data: Any


@gateway_api.post("/internal/send-message")
async def send_message_endpoint(request: SendMessageRequest):
    """Endpoint interno para enviar mensajes a Telegram."""
    if not bot_manager.is_initialized() or bot_manager.bot is None:
        raise HTTPException(status_code=503, detail="Bot no inicializado.")
    try:
        await bot_manager.bot.send_message(
            chat_id=request.chat_id,
            text=request.text,
            parse_mode='HTML'
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en /internal/send-message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al enviar mensaje.")


@gateway_api.post("/internal/store-user-data")
async def store_user_data_endpoint(request: StoreUserDataRequest):
    """
    Endpoint de la API interna para almacenar datos en user_data de un usuario de Telegram.
    """
    if not bot_manager.is_initialized():
        raise HTTPException(status_code=503, detail="El cliente de Telegram no está listo.")
    try:
        user_data = bot_manager.get_user_data(request.user_id)
        if request.key == "generated_image":
            if isinstance(request.data, str) and len(request.data) > MAX_IMAGE_BASE64_BYTES:
                logger.warning(f"Intento de almacenar imagen demasiado grande para el usuario {request.user_id}.")
                raise HTTPException(status_code=413, detail=f"La imagen excede el tamaño máximo permitido.")
            import base64
            from io import BytesIO
            image_data = base64.b64decode(request.data)
            user_data[request.key] = BytesIO(image_data)
        else:
            user_data[request.key] = request.data
            
        await bot_manager.flush_persistence()
        logger.info(f"Datos almacenados en user_data para el usuario {request.user_id} con clave {request.key}.")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint interno /store-user-data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al almacenar datos de usuario.")


@gateway_api.get("/health")
async def health_check():
    """Health check del gateway."""
    return {
        "status": "ok",
        "bot_initialized": bot_manager.is_initialized(),
        "core_api_url": config.core_api_url,
        "core_ws_url": config.core_ws_url,
    }



if __name__ == "__main__":
    logger.info("🚀 Iniciando telegram_gateway...")
    try:
        uvicorn.run(
            "run_telegram_gateway:gateway_api",
            host="0.0.0.0",
            port=9091,
            reload=False,
            workers=1,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO: {e}", exc_info=True)
        sys.exit(1)
