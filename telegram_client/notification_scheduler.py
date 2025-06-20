# telegram_client/notification_scheduler.py

"""
Módulo de Programación de Notificaciones para Telegram.

Este módulo es el puente entre la lógica de negocio "pura" del `core` y la
funcionalidad específica de la plataforma de Telegram para enviar mensajes
programados (recordatorios).

Responsabilidades:
-   Definir la función de callback (`_send_reminder_callback`) que la `JobQueue`
    ejecutará para enviar un mensaje.
-   Proporcionar una función (`schedule_telegram_job`) que toma un evento de la
    base de datos y crea un job en la `JobQueue`.
-   Proporcionar una función de inicialización (`reschedule_pending_reminders`) que
    se llama al arrancar el bot para volver a programar todos los recordatorios
    activos que quedaron pendientes en la base de datos.
"""

import logging
import uuid
from datetime import datetime
import pytz

from sqlalchemy import select
from telegram.ext import CallbackContext

# Importaciones del proyecto
from core.database import SessionLocal, Account, AgendaEvent, PlatformIdentity
from utils.db_session import DBSession
from telegram_client.bot_manager import bot_manager

logger = logging.getLogger(__name__)


async def _send_event_reminder_callback(context: CallbackContext):
    """
    La función que ejecuta JobQueue para enviar el recordatorio de un evento.
    """
    job = context.job
    if not job or not job.data:
        logger.error("Job de recordatorio de evento sin datos.")
        return

    event_id = job.data.get("event_id")
    telegram_id = job.data.get("telegram_id")
    description = job.data.get("description")

    if not all([event_id, telegram_id, description]):
        logger.error(f"Faltan datos en el job del recordatorio de evento: {job.data}")
        return

    logger.info(f"Enviando recordatorio de evento {event_id} al usuario de Telegram {telegram_id}")
    try:
        await bot_manager.bot.send_message(
            chat_id=telegram_id,
            text=f"🔔⏰ ¡Recordatorio de Evento! ⏰🔔\n\n<b>{description}</b>",
            parse_mode='HTML'
        )
        # Marcar el evento como inactivo en la BD para que no se reprograme.
        async with DBSession(SessionLocal) as db:
            event = await db.get(AgendaEvent, event_id)
            if event:
                event.is_active = False
                await db.commit()
    except Exception as e:
        logger.error(f"Error al enviar recordatorio de evento {event_id}: {e}", exc_info=True)


async def schedule_telegram_job(event: AgendaEvent, telegram_id: int):
    """
    Programa un job en la JobQueue de Telegram para un evento específico.
    """
    if not bot_manager.job_queue:
        logger.error("JobQueue no está disponible en bot_manager. No se puede programar el job.")
        return

    # Crear un nombre de job único para poder cancelarlo si es necesario.
    job_name = f"event_reminder_{event.id}_{uuid.uuid4()}"
    
    # Guardar el job_name en el evento para futura referencia.
    async with DBSession(SessionLocal) as db:
        event.job_name = job_name
        db.add(event)
        await db.commit()

    bot_manager.job_queue.run_once(
        _send_event_reminder_callback,
        when=event.event_datetime_utc,
        data={
            "event_id": event.id,
            "telegram_id": telegram_id,
            "description": event.description
        },
        name=job_name
    )
    logger.info(f"Job programado en Telegram para el evento {event.id} con el nombre '{job_name}'.")


async def reschedule_pending_reminders(application):
    """
    Recarga los recordatorios de eventos pendientes de la BD y los vuelve a programar.
    Esta es la función que se importa y se llama desde `run_telegram_bot.py`.
    """
    logger.info("Re-programando recordatorios de eventos pendientes desde la base de datos...")
    async with DBSession(SessionLocal) as db:
        now_utc = datetime.now(pytz.utc)
        
        stmt = (
            select(AgendaEvent, PlatformIdentity.platform_user_id)
            .join(Account, AgendaEvent.account_id == Account.id)
            .join(PlatformIdentity, Account.id == PlatformIdentity.account_id)
            .where(
                AgendaEvent.is_active == True,
                AgendaEvent.event_datetime_utc > now_utc,
                PlatformIdentity.platform == 'telegram'
            )
        )
        
        results = await db.execute(stmt)
        pending_events = results.all()

        count = 0
        for event, telegram_id_str in pending_events:
            if not event.job_name:
                logger.warning(f"El evento {event.id} no tiene job_name, no se puede re-programar de forma segura.")
                continue

            try:
                telegram_id = int(telegram_id_str)
                application.job_queue.run_once(
                    _send_event_reminder_callback,
                    when=event.event_datetime_utc,
                    data={"event_id": event.id, "telegram_id": telegram_id, "description": event.description},
                    name=event.job_name
                )
                count += 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error al procesar el telegram_id '{telegram_id_str}' para el evento {event.id}: {e}")
        
        if count > 0:
            logger.info(f"✅ {count} recordatorio(s) de evento(s) han sido re-programados.")
        else:
            logger.info("ℹ️ No se encontraron recordatorios de eventos pendientes para re-programar.")