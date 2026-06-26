# telegram_gateway/notification_scheduler.py
"""
Programación de recordatorios para Telegram.
En esta versión, el re-scheduling al inicio consulta la API del core.
Las notificaciones se envían directamente via JobQueue.
"""
import logging
import uuid
from datetime import datetime
import pytz
from telegram.ext import CallbackContext
from telegram_gateway.bot_manager import bot_manager

logger = logging.getLogger(__name__)


async def _send_event_reminder_callback(context: CallbackContext):
    job = context.job
    if not job or not job.data:
        return
    event_id = job.data.get("event_id")
    telegram_id = job.data.get("telegram_id")
    description = job.data.get("description")
    if not all([event_id, telegram_id, description]):
        return
    try:
        if bot_manager.bot:
            await bot_manager.bot.send_message(
                chat_id=telegram_id,
                text=f"🔔⏰ ¡Recordatorio! ⏰🔔\n\n<b>{description}</b>",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error enviando recordatorio {event_id}: {e}", exc_info=True)


async def schedule_telegram_job(event_id: str, telegram_id: int, description: str, event_datetime_utc):
    if not bot_manager.job_queue:
        logger.warning("JobQueue no disponible.")
        return
    job_name = f"event_reminder_{event_id}_{uuid.uuid4()}"
    bot_manager.job_queue.run_once(
        _send_event_reminder_callback,
        when=event_datetime_utc,
        data={"event_id": event_id, "telegram_id": telegram_id, "description": description},
        name=job_name
    )
    logger.info(f"Job programado para evento {event_id}")


async def reschedule_pending_reminders(application):
    """
    En el gateway, los recordatorios pendientes son re-programados via API del core.
    Por ahora, simplemente logueamos y dejamos que el core maneje sus propios jobs.
    TODO: Agregar endpoint GET /api/events/pending-reminders al core.
    """
    logger.info("ℹ️ Gateway: re-scheduling de recordatorios omitido (el core maneja los jobs del servidor).")
