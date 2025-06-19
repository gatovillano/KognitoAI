# telegram_bot/agenda_manager.py

"""
Gestor de Lógica de Negocio para la Agenda y los Recordatorios de Eventos.

Este módulo encapsula toda la lógica para programar, consultar y cancelar
eventos en la agenda de un usuario. Interactúa con la base de datos para la
persistencia de los eventos y con el `JobQueue` del bot de Telegram para
programar los recordatorios.

En la nueva arquitectura, las funciones principales han sido refactorizadas para
operar con el `account_id` universal del usuario. Sin embargo, para poder enviar
la notificación del recordatorio a través de Telegram, el sistema necesita
resolver el `telegram_id` asociado a esa cuenta en el momento de programar el job.

Este módulo es un excelente ejemplo de cómo la lógica de negocio (`account_id`)
se mantiene separada de la lógica de entrega de la notificación (`telegram_id`).
"""

import logging
import uuid
from datetime import datetime, timedelta
import pytz
import dateparser
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, delete
from telegram.ext import CallbackContext

# Importaciones del proyecto
from telegram_bot.database import SessionLocal, Account, AgendaEvent, PlatformIdentity
from utils.db_session import DBSession
from telegram_bot.bot_manager import bot_manager # Aún necesario para la JobQueue

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)


async def _send_reminder_callback(context: CallbackContext):
    """
    La función que ejecuta JobQueue para enviar un recordatorio de evento.
    Esta función sigue dependiendo del ecosistema de Telegram para la entrega.
    """
    job = context.job
    if not job or not job.data:
        logger.error("Job de recordatorio de evento ejecutado sin datos.")
        return

    # Extraer datos del job
    event_id = job.data.get("event_id")
    account_id = job.data.get("account_id")
    telegram_id = job.data.get("telegram_id")
    description = job.data.get("description")

    if not all([event_id, account_id, telegram_id, description]):
        logger.error(f"Faltan datos en el job del recordatorio de evento: {job.data}")
        return

    logger.info(f"Enviando recordatorio para el evento {event_id} (cuenta: {account_id}) al usuario de Telegram {telegram_id}")
    try:
        # Usamos el bot_manager para asegurar el acceso al bot y enviar el mensaje
        await bot_manager.bot.send_message(
            chat_id=telegram_id,
            text=f"⏰ ¡Recordatorio! Tienes un evento programado:\n\n<b>{description}</b>",
            parse_mode='HTML'
        )
        # Marcar el recordatorio como enviado en la BD para no reenviarlo
        async with DBSession(SessionLocal) as db:
            event = await db.get(AgendaEvent, event_id)
            if event:
                event.reminder_sent = True
                await db.commit()
                logger.info(f"Evento {event_id} marcado como 'reminder_sent=True'.")
    except Exception as e:
        logger.error(f"Error al enviar recordatorio para evento {event_id}: {e}", exc_info=True)


async def schedule_event(account_id: str, description: str, natural_language_datetime: str, telegram_id: int) -> Tuple[bool, str]:
    """
    Programa un nuevo evento y su recordatorio, usando `account_id` para la lógica
    y `telegram_id` para la notificación.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        description: La descripción del evento.
        natural_language_datetime: El texto con la fecha/hora.
        telegram_id: El ID de Telegram para la entrega del recordatorio.

    Returns:
        Una tupla (éxito, mensaje).
    """
    async with DBSession(SessionLocal) as db:
        try:
            # PASO 1: OBTENER LA CUENTA Y SU ZONA HORARIA
            account = await db.get(Account, uuid.UUID(account_id))
            if not account or not account.profile or not account.profile.timezone:
                logger.warning(f"Intento de programar evento para la cuenta {account_id} sin zona horaria configurada.")
                return False, "No tienes una zona horaria configurada. Por favor, configúrala primero."

            user_tz_str = account.profile.timezone
            user_tz = pytz.timezone(user_tz_str)
            
            # PASO 2: PARSEAR LA FECHA CON LA ZONA HORARIA DEL USUARIO
            date_settings = {'PREFER_DATES_FROM': 'future', 'TIMEZONE': user_tz_str}
            event_datetime_local = dateparser.parse(natural_language_datetime, settings=date_settings)

            if not event_datetime_local:
                logger.warning(f"Dateparser no pudo entender '{natural_language_datetime}' para la zona horaria {user_tz_str}.")
                return False, f"No pude entender la fecha y hora '{natural_language_datetime}'. Intenta ser más específico."

            if event_datetime_local.tzinfo is None:
                event_datetime_local = user_tz.localize(event_datetime_local)

            if event_datetime_local < datetime.now(user_tz):
                return False, "No puedo programar recordatorios en el pasado. Por favor, elige una fecha y hora futura."

            event_datetime_utc = event_datetime_local.astimezone(pytz.utc)

            # PASO 3: GUARDAR EL EVENTO EN LA BD
            new_event = AgendaEvent(
                account_id=uuid.UUID(account_id),
                description=description,
                event_datetime_utc=event_datetime_utc,
                user_timezone=user_tz_str,
            )
            db.add(new_event)
            await db.flush() # Para obtener el ID del nuevo evento

            # PASO 4: PROGRAMAR EL JOB DE RECORDATORIO
            job_name = f"reminder_{new_event.id}_{uuid.uuid4()}"
            new_event.job_name = job_name

            bot_manager.job_queue.run_once(
                _send_reminder_callback,
                when=event_datetime_utc,
                data={
                    "event_id": new_event.id,
                    "account_id": account_id,
                    "telegram_id": telegram_id, # Guardamos el ID de entrega
                    "description": description
                },
                name=job_name
            )

            await db.commit()
            formatted_local_time = event_datetime_local.strftime('%Y-%m-%d a las %H:%M:%S')
            logger.info(f"Evento programado para cuenta {account_id} en UTC: {event_datetime_utc}, local: {event_datetime_local}")
            return True, f"¡Evento programado! Te recordaré sobre '{description}' el {formatted_local_time} ({user_tz_str})."

        except Exception as e:
            logger.error(f"Error al programar evento para la cuenta {account_id}: {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al programar tu evento."


async def get_agenda_for_day(account_id: str, target_day: str) -> str:
    """
    Consulta la agenda para un día específico ('hoy', 'mañana', o una fecha).
    Opera exclusivamente con el `account_id`.
    """
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, uuid.UUID(account_id))
        if not account or not account.profile or not account.profile.timezone:
            return "Necesito que configures tu zona horaria para poder ver tu agenda."
        
        user_tz = pytz.timezone(account.profile.timezone)
        now_local = datetime.now(user_tz)

        # Determinar el rango de fechas a consultar
        if target_day.lower() == 'hoy':
            start_of_day_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            day_description = "hoy"
        elif target_day.lower() == 'mañana':
            start_of_day_local = (now_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_description = "mañana"
        else:
            parsed_date = dateparser.parse(target_day, settings={'TIMEZONE': account.profile.timezone, 'PREFER_DATES_FROM': 'future'})
            if not parsed_date:
                return f"No pude entender la fecha '{target_day}'. Intenta con 'hoy', 'mañana' o una fecha."
            start_of_day_local = user_tz.localize(parsed_date.replace(hour=0, minute=0, second=0, microsecond=0))
            day_description = f"el {start_of_day_local.strftime('%d de %B de %Y')}"

        end_of_day_local = start_of_day_local + timedelta(days=1)
        start_utc = start_of_day_local.astimezone(pytz.utc)
        end_utc = end_of_day_local.astimezone(pytz.utc)

        # Consultar los eventos en la base de datos
        stmt = select(AgendaEvent).where(
            AgendaEvent.account_id == uuid.UUID(account_id),
            AgendaEvent.event_datetime_utc >= start_utc,
            AgendaEvent.event_datetime_utc < end_utc
        ).order_by(AgendaEvent.event_datetime_utc)
        
        results = await db.execute(stmt)
        events = results.scalars().all()

        if not events:
            return f"No tienes nada programado para {day_description}."

        response_lines = [f"Esto es lo que tienes en tu agenda para {day_description}:"]
        for event in events:
            event_time_local = event.event_datetime_utc.astimezone(user_tz)
            response_lines.append(f"- A las {event_time_local.strftime('%H:%M')}: {event.description} (ID: {event.id})")
        
        return "\n".join(response_lines)


async def cancel_event(account_id: str, event_id: int) -> Tuple[bool, str]:
    """
    Cancela un evento programado y su recordatorio, usando `account_id`.
    """
    logger.info(f"Cuenta {account_id} intentando cancelar el evento ID: {event_id}")
    async with DBSession(SessionLocal) as db:
        try:
            stmt = select(AgendaEvent).where(
                AgendaEvent.id == event_id,
                AgendaEvent.account_id == uuid.UUID(account_id)
            )
            result = await db.execute(stmt)
            event_to_cancel = result.scalars().first()

            if not event_to_cancel:
                logger.warning(f"No se encontró el evento {event_id} para la cuenta {account_id}.")
                return False, f"No encontré ningún evento con el ID {event_id} en tu agenda."

            # Cancelar el job en la JobQueue
            if event_to_cancel.job_name:
                current_jobs = bot_manager.job_queue.get_jobs_by_name(event_to_cancel.job_name)
                if not current_jobs:
                    logger.warning(f"No se encontró el job '{event_to_cancel.job_name}' para el evento {event_id}.")
                else:
                    for job in current_jobs:
                        job.schedule_removal()
                    logger.info(f"Job '{event_to_cancel.job_name}' cancelado.")

            # Eliminar el evento de la base de datos
            description = event_to_cancel.description
            await db.delete(event_to_cancel)
            await db.commit()
            
            logger.info(f"Evento {event_id} ('{description}') eliminado de la DB para la cuenta {account_id}.")
            return True, f"¡Hecho! El evento '{description}' (ID: {event_id}) ha sido cancelado y eliminado de tu agenda."

        except Exception as e:
            logger.error(f"Error al cancelar el evento {event_id} para la cuenta {account_id}: {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al intentar cancelar el evento."


async def reschedule_pending_reminders(application):
    """
    Carga los recordatorios pendientes de la BD y los vuelve a programar al iniciar el bot.
    """
    logger.info("Re-programando recordatorios de agenda pendientes...")
    async with DBSession(SessionLocal) as db:
        now_utc = datetime.now(pytz.utc)
        stmt = select(AgendaEvent).where(
            AgendaEvent.reminder_sent == False,
            AgendaEvent.event_datetime_utc > now_utc
        )
        results = await db.execute(stmt)
        pending_events = results.scalars().all()

        count = 0
        for event in pending_events:
            if not event.job_name: continue

            # Necesitamos obtener el telegram_id para la entrega de la notificación
            identity_stmt = select(PlatformIdentity).where(
                PlatformIdentity.account_id == event.account_id,
                PlatformIdentity.platform == 'telegram'
            )
            identity_result = await db.execute(identity_stmt)
            identity = identity_result.scalars().first()

            if not identity:
                logger.warning(f"No se pudo encontrar una identidad de Telegram para la cuenta {event.account_id} del evento {event.id}. No se puede reprogramar.")
                continue

            application.job_queue.run_once(
                _send_reminder_callback,
                when=event.event_datetime_utc,
                data={
                    "event_id": event.id,
                    "account_id": str(event.account_id),
                    "telegram_id": identity.platform_user_id,
                    "description": event.description
                },
                name=event.job_name
            )
            count += 1
        logger.info(f"✅ {count} recordatorios de agenda han sido re-programados.")