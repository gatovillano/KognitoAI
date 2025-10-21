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
from core.memory_manager import process_document_for_rag
from utils.document_parser import extract_text_and_metadata_from_document


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
        extracted_text, metadata = extract_text_and_metadata_from_document(
        document.file_name,
        bytes(file_bytes),
    )
        # Procesamos el documento en memoria usando process_document_for_rag
        try:
            await process_document_for_rag(
                file_name=document.file_name,
                extracted_text=extracted_text,
                metadata=metadata,
                account_id=account_id,
                topic=topic,
            )
            await message.reply_text("✅ ¡Documento procesado y añadido a tu base de conocimiento!")
        except Exception as e:
            logger.error(f"Error al procesar documento para RAG: {e}", exc_info=True)
            await message.reply_text("❌ Ocurrió un error al procesar tu documento. Intenta de nuevo más tarde.")



    except Exception as e:
        account_id_log = str(account.id) if account else "Desconocida"
        logger.error(f"Error al procesar documento para la cuenta {account_id_log}: {e}", exc_info=True)
        await message.reply_text("Lo siento, ocurrió un error inesperado al procesar tu documento.")
    



        await message.reply_text("✅ ¡Documento procesado y añadido a tu base de conocimiento!")
    
    

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