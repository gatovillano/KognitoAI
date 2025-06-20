# telegram_bot/handlers/document_handlers.py

"""
Manejador para la recepción de documentos enviados directamente al chat.

Este módulo se encarga de interceptar los mensajes que contienen archivos
(documentos, PDFs, etc.). En la nueva arquitectura, su función principal es
actuar como un cliente del endpoint de subida de archivos del backend central.

Flujo de Trabajo:
1.  Recibe el mensaje con el documento.
2.  Obtiene la identidad universal del usuario (`account_id`) a través de la
    base de datos.
3.  Descarga el contenido del archivo en memoria.
4.  Empaqueta el archivo, el `account_id`, el `telegram_id` y cualquier
    metadato (como el 'topic' en el caption) en una petición `multipart/form-data`.
5.  Envía la petición al endpoint `/api/upload-document` del `web_server.py`.
6.  Informa al usuario del resultado de la operación.
"""

import logging
import httpx
import asyncio
from io import BytesIO

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Importaciones de la nueva arquitectura y del proyecto
from core.config import settings
from core.database import get_or_create_account_from_platform_id

logger = logging.getLogger(__name__)


async def document_message_handler(update: Update, context: CallbackContext) -> None:
    """
    Maneja los mensajes que contienen un documento.
    """
    message = update.message
    if not message or not message.from_user:
        logger.warning("document_message_handler recibió una actualización sin mensaje o usuario.")
        return

    user = message.from_user
    document = message.document
    if not document:
        return

    logger.info(f"Documento recibido de {user.id} ({user.first_name}): {document.file_name}")

    account = None
    try:
        # ¡CORREGIDO! Aplicamos el patrón de desempaquetado seguro.
        result = await get_or_create_account_from_platform_id(
            platform='telegram',
            platform_user_id=str(user.id),
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username
        )
        if not result:
            logger.error(f"No se pudo obtener/crear una cuenta para el usuario de Telegram {user.id} en document_handler.")
            await message.reply_text("Lo siento, tuve un problema al identificar tu cuenta. No puedo procesar el documento.")
            return
            
        account, _ = result
        account_id = str(account.id)
        
        await message.reply_text("He recibido tu documento. Lo estoy procesando, esto puede tardar un momento...")
        
        file_bytes = await (await document.get_file()).download_as_bytearray()
        
        # El caption del mensaje puede contener el tema del documento.
        topic = message.caption if message.caption else "General"

        api_url = f"{settings.api_server_url}/api/upload-document"
        files = {'files': (document.file_name, BytesIO(file_bytes), document.mime_type)}
        data = {'topic': topic}
        
        # Aquí no podemos usar `initData` porque no viene de una WebApp.
        # En una arquitectura de producción real, necesitaríamos un token de API
        # para que el bot se autentique con el backend. Por ahora, lo omitimos
        # y el backend confiará en el bot.

        async with httpx.AsyncClient() as client:
            # ¡IMPORTANTE! El endpoint /api/upload-document espera `user_id` de `initData`.
            # Necesitamos un endpoint alternativo o modificar el existente para aceptar
            # una llamada directa con el `account_id`.
            # Por ahora, crearemos un payload JSON y lo enviaremos a un endpoint hipotético.
            # Este es un punto a refactorizar en el futuro.
            # Vamos a asumir que el endpoint /api/upload-document puede manejarlo.
            # El endpoint actual está protegido por `get_validated_user_id`, lo cual fallará.
            # Esto requerirá un cambio en `run_api.py`.
            # **Parche Temporal:** Por ahora, vamos a simular que el endpoint funciona
            # y que la lógica del lado del bot es correcta.
            # La solución real es crear un endpoint `/api/internal/upload` en run_api.py
            # que no requiera `initData`.
            
            # --- Lógica con un endpoint ideal (futuro) ---
            # data['account_id'] = account_id
            # response = await client.post(api_url_internal, data=data, files=files, timeout=120.0)
            
            # --- Simulación (para que el código actual no falle) ---
            # Vamos a comentar la llamada a la API por ahora, ya que el endpoint
            # actual no está preparado para esta llamada.
            logger.warning("La llamada a la API desde document_handler está deshabilitada temporalmente hasta que se cree un endpoint interno.")
            
            # await message.reply_text("✅ ¡Documento procesado y añadido a tu base de conocimiento!")
            await message.reply_text("He recibido tu documento. La funcionalidad de procesamiento desde el chat está en desarrollo.")


    except Exception as e:
        account_id_log = str(account.id) if account else "Desconocida"
        logger.error(f"Error al procesar documento para la cuenta {account_id_log}: {e}", exc_info=True)
        await message.reply_text("Lo siento, ocurrió un error inesperado al procesar tu documento.")



def register_document_handlers(application: Application) -> None:
    """

    Registra los manejadores de documentos en la aplicación de Telegram.
    """
    # Usamos `filters.Document.ALL` para capturar cualquier tipo de documento.
    # El `~filters.UpdateType.EDITED_MESSAGE` evita que el handler se active
    # si se edita el caption de un documento ya enviado.
    handler = MessageHandler(filters.Document.ALL & (~filters.UpdateType.EDITED_MESSAGE), document_message_handler)
    application.add_handler(handler, group=1)
    logger.info("✅ Manejador de documentos registrado.")