# telegram_gateway/handlers/document_handlers.py
import logging
import httpx
from io import BytesIO
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from telegram_gateway.config import config
from telegram_gateway.api_client import get_or_create_account, upload_document

logger = logging.getLogger(__name__)

async def document_message_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message or not message.from_user:
        return
    user = message.from_user
    document = message.document
    if not document:
        return
    logger.info(f"Documento recibido de {user.id}: {document.file_name}")
    try:
        auth_data = await get_or_create_account(
            platform_user_id=str(user.id),
            first_name=user.first_name,
            last_name=getattr(user, 'last_name', None),
            username=user.username
        )
        if not auth_data:
            await message.reply_text("Lo siento, no pude identificar tu cuenta.")
            return
        jwt_token = auth_data.get('access_token')
        context.chat_data['jwt_token'] = jwt_token

        await message.reply_text("📄 Recibido. Procesando documento...")
        file_bytes = bytes(await (await document.get_file()).download_as_bytearray())
        topic = message.caption if message.caption else "General"
        success = await upload_document(jwt_token, document.file_name, file_bytes, topic)
        if success:
            await message.reply_text("✅ ¡Documento procesado y añadido a tu base de conocimiento!")
        else:
            await message.reply_text("❌ Error al procesar el documento. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error en document_message_handler para {user.id}: {e}", exc_info=True)
        await message.reply_text("Lo siento, ocurrió un error inesperado.")

def register_document_handlers(application: Application) -> None:
    handler = MessageHandler(filters.Document.ALL & (~filters.UpdateType.EDITED_MESSAGE), document_message_handler)
    application.add_handler(handler, group=1)
    logger.info("✅ Manejador de documentos registrado.")
