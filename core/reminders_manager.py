# telegram_bot/reminders_manager.py

"""
Gestor de Lógica de Negocio para Recordatorios Simples.

Este módulo se especializa en manejar recordatorios rápidos y, a menudo, relativos
en el tiempo (ej. "en 20 minutos"). Se diferencia del `agenda_manager` en que
estos recordatorios no se consideran "eventos" formales en la agenda, sino
alertas puntuales.

La arquitectura sigue el patrón establecido:
-   La lógica de negocio (`set_simple_reminder`) opera con el `account_id`
    universal para la persistencia en la base de datos.
-   Para la entrega de la notificación, que es específica de la plataforma,
    se resuelve y utiliza el `telegram_id` para interactuar con la `JobQueue`
    y la API de Telegram.
"""

import logging
import uuid
from datetime import datetime
import pytz
import dateparser
from typing import Tuple, Optional

from sqlalchemy import select

# Importaciones de la nueva arquitectura y del bot
from core.database import SessionLocal, Account, Recordatorio, PlatformIdentity
from utils.db_session import DBSession
from utils.telegram_api import send_telegram_message

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


async def _send_simple_reminder_callback(reminder_id: int, telegram_id: int, text: str):
    """
    La función que ejecuta APScheduler para enviar un recordatorio simple.
    Esta función es el punto final de la entrega de la notificación.
    """
    logger.info(f"Enviando recordatorio simple {reminder_id} al usuario de Telegram {telegram_id}")
    try:
        success = await send_telegram_message(
            telegram_id=telegram_id,
            text=f"🔔⏰ ¡Recordatorio! ⏰🔔 \n\nMe pediste que te recordara esto: <b>{text}</b>"
        )
        if not success:
            raise ValueError("No se pudo enviar el mensaje via Telegram gateway.")
            
        # Marcar el recordatorio como inactivo en la BD para que no se reprograme.
        async with DBSession(SessionLocal) as db:
            reminder = await db.get(Recordatorio, reminder_id)
            if reminder:
                reminder.is_active = False
                await db.commit()
    except Exception as e:
        logger.error(f"Error al enviar recordatorio simple {reminder_id}: {e}", exc_info=True)


async def set_simple_reminder(
    account_id: str, 
    telegram_id: int, 
    text: str, 
    natural_language_time: str,
    workspace_id: Optional[str] = None,
    thread_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Programa un nuevo recordatorio simple.
    """
    async with DBSession(SessionLocal) as db:
        try:
            # Para recordatorios relativos ('en 20 minutos'), no necesitamos la
            # zona horaria del usuario. dateparser los interpreta correctamente en UTC.
            date_settings = {'RETURN_AS_TIMEZONE_AWARE': True, 'TO_TIMEZONE': 'UTC'}
            due_datetime_utc = dateparser.parse(natural_language_time, **date_settings)

            if not due_datetime_utc:
                logger.warning(f"Dateparser no pudo entender '{natural_language_time}'.")
                return False, f"No pude entender el tiempo '{natural_language_time}'. Intenta con 'en 20 minutos', 'en 1 hora', 'a las 10pm', etc."

            # Asegurarse de que la fecha/hora no está en el pasado.
            now_utc = datetime.now(pytz.utc)
            if due_datetime_utc < now_utc:
                return False, "No puedo programar recordatorios en el pasado. Por favor, elige una fecha y hora futura."

            # Crear la nueva entrada en la tabla de recordatorios, asociada al account_id.
            new_reminder = Recordatorio(
                account_id=account_id,
                workspace_id=workspace_id,
                thread_id=thread_id,
                message=text,
                due_datetime=due_datetime_utc,
                is_active=True
            )
            db.add(new_reminder)
            await db.flush()  # Para obtener el ID del nuevo recordatorio

            # Crear un nombre de job único para poder cancelarlo si es necesario.
            job_name = f"simple_reminder_{new_reminder.id}_{uuid.uuid4()}"
            new_reminder.job_name = job_name

            # Programar el job en APScheduler.
            from utils.tool_scheduler import tool_scheduler
            tool_scheduler.scheduler.add_job(
                _send_simple_reminder_callback,
                'date',
                run_date=due_datetime_utc,
                args=[new_reminder.id, telegram_id, text],
                id=job_name
            )

            await db.commit()
            
            # Formatear una respuesta amigable para el usuario.
            account = await db.get(Account, account_id)
            user_tz_str = account.timezone if account else None
            
            display_time_str = ""
            if user_tz_str:
                try:
                    user_tz = pytz.timezone(user_tz_str)
                    display_time = due_datetime_utc.astimezone(user_tz)
                    display_time_str = f" a las {display_time.strftime('%H:%M:%S del %d-%m-%Y')} ({user_tz_str})"
                except pytz.UnknownTimeZoneError:
                    display_time_str = f" a las {due_datetime_utc.strftime('%H:%M:%S UTC del %d-%m-%Y')}"
            else:
                display_time_str = f" a las {due_datetime_utc.strftime('%H:%M:%S UTC del %d-%m-%Y')}"

            return True, f"¡Entendido! Te recordaré '{text}'{display_time_str}."

        except Exception as e:
            logger.error(f"Error al programar recordatorio simple para la cuenta '{account_id}': {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al programar tu recordatorio."
        

async def reschedule_simple_reminders():
    """
    Recarga los recordatorios simples pendientes de la BD y los vuelve a programar en APScheduler.
    """
    logger.info("Re-programando recordatorios simples pendientes desde la base de datos...")
    from utils.tool_scheduler import tool_scheduler
    async with DBSession(SessionLocal) as db:
        now_utc = datetime.now(pytz.utc)
        
        stmt = (
            select(Recordatorio, PlatformIdentity.platform_user_id)
            .join(Account, Recordatorio.account_id == Account.id)
            .join(PlatformIdentity, Account.id == PlatformIdentity.account_id)
            .where(
                Recordatorio.is_active == True,
                Recordatorio.due_datetime > now_utc,
                PlatformIdentity.platform == 'telegram'
            )
        )
        
        results = await db.execute(stmt)
        pending_reminders = results.all()

        count = 0
        for reminder, telegram_id_str in pending_reminders:
            if not reminder.job_name:
                continue

            try:
                telegram_id = int(telegram_id_str)
                tool_scheduler.scheduler.add_job(
                    _send_simple_reminder_callback,
                    'date',
                    run_date=reminder.due_datetime,
                    args=[reminder.id, telegram_id, reminder.message],
                    id=reminder.job_name
                )
                count += 1
            except Exception as e:
                logger.error(f"Error al re-programar recordatorio {reminder.id}: {e}")
        
        if count > 0:
            logger.info(f"✅ {count} recordatorio(s) simple(s) han sido re-programados en APScheduler.")
        else:
            logger.info("ℹ️ No se encontraron recordatorios simples pendientes para re-programar.")
