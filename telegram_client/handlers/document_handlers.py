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
        return  # No debería ocurrir si el filtro es correcto, pero es una buena práctica.

    logger.info(f"Documento recibido de {user.id} ({user.first_name}): {document.file_name}")

    try:
        # Obtener la identidad universal del usuario.
        account = await get_or_create_account_from_platform_id(
            platform='telegram',
            platform_user_id=str(user.id),
       
        )
        if not account:
            await message.reply_text("No pude identificarte en el sistema. Por favor, intenta de nuevo.")
            return

        # Informar al usuario que el proceso ha comenzado.
        processing_message = await message.reply_text(
            f"He recibido tu documento '{document.file_name}'. Lo procesaré ahora, dame un momento..."
        )

        # Descargar el archivo a un objeto en memoria (BytesIO).
        file = await document.get_file()
        file_bytes_io = BytesIO()
        await file.download_to_memory(file_bytes_io)
        file_bytes_io.seek(0)  # Rebobinar el puntero al inicio del archivo en memoria.

        # Preparar los datos y archivos para la petición a la API.
        # El tema se puede tomar del caption del mensaje.
        topic = message.caption or "Documento General"
        
        payload = {
            "topic": topic,
            "account_id": str(account.id),
            "telegram_id": user.id
        }
        
        files_to_upload = {
            'files': (document.file_name, file_bytes_io, document.mime_type)
        }

        # Realizar la llamada a la API central para procesar el documento.
        api_url = f"{settings.api_server_url}/api/upload-document"
        async with httpx.AsyncClient(timeout=300.0) as client: # Timeout generoso para subidas grandes.
            api_response = await client.post(api_url, data=payload, files=files_to_upload)
            api_response.raise_for_status()  # Lanza una excepción para errores 4xx/5xx.
        
        response_data = api_response.json()
        await processing_message.edit_text(response_data.get("message", "Documento procesado con éxito."))

    except httpx.HTTPStatusError as e:
        error_detail = "Error desconocido"
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except Exception:
            pass
        logger.error(f"Error de API al subir documento para {user.id}: {error_detail}", exc_info=True)
        await message.reply_text(f"Hubo un error al procesar tu documento: {error_detail}")
    except Exception as e:
        logger.error(f"Error inesperado en document_message_handler para {user.id}: {e}", exc_info=True)
        await message.reply_text("Ocurrió un error inesperado al procesar tu documento. Por favor, inténtalo de nuevo más tarde.")


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