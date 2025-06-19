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
from typing import Tuple

from sqlalchemy import select
from telegram.ext import CallbackContext

# Importaciones de la nueva arquitectura y del bot
from telegram_bot.database import SessionLocal, Account, Recordatorio, PlatformIdentity
from utils.db_session import DBSession
from telegram_bot.bot_manager import bot_manager

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


async def _send_simple_reminder_callback(context: CallbackContext):
    """
    La función que ejecuta JobQueue para enviar un recordatorio simple.
    Esta función es el punto final de la entrega de la notificación.
    """
    job = context.job
    # Extraer los datos necesarios del job
    reminder_id = job.data.get("reminder_id")
    telegram_id = job.data.get("telegram_id")
    text = job.data.get("text")

    if not all([reminder_id, telegram_id, text]):
        logger.error(f"Faltan datos en el job del recordatorio simple: {job.data}")
        return

    logger.info(f"Enviando recordatorio simple {reminder_id} al usuario de Telegram {telegram_id}")
    try:
        # Usa el bot_manager para asegurar el acceso al objeto bot
        await bot_manager.bot.send_message(
            chat_id=telegram_id,
            text=f"🔔⏰ ¡Recordatorio! ⏰🔔 \n\nMe pediste que te recordara esto: <b>{text}</b>",
            parse_mode='HTML'
        )
        # Marcar el recordatorio como inactivo en la BD para que no se reprograme.
        async with DBSession(SessionLocal) as db:
            reminder = await db.get(Recordatorio, reminder_id)
            if reminder:
                reminder.is_active = False
                await db.commit()
    except Exception as e:
        logger.error(f"Error al enviar recordatorio simple {reminder_id}: {e}", exc_info=True)


async def set_simple_reminder(account_id: str, telegram_id: int, text: str, natural_language_time: str) -> Tuple[bool, str]:
    """
    Programa un nuevo recordatorio simple.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        telegram_id: El ID de Telegram, necesario para la JobQueue y la zona horaria.
        text: El contenido del recordatorio.
        natural_language_time: La descripción en lenguaje natural del tiempo.

    Returns:
        Una tupla (bool, str) indicando éxito y un mensaje para el usuario.
    """
    async with DBSession(SessionLocal) as db:
        try:
            # Para recordatorios relativos ('en 20 minutos'), no necesitamos la
            # zona horaria del usuario. dateparser los interpreta correctamente en UTC.
            # Le indicamos que el resultado debe estar en UTC.
            date_settings = {'RETURN_AS_TIMEZONE_AWARE': True, 'TO_TIMEZONE': 'UTC'}
            due_datetime_utc = dateparser.parse(natural_language_time, settings=date_settings)

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
                text=text,
                due_datetime=due_datetime_utc,
                is_active=True
            )
            db.add(new_reminder)
            await db.flush()  # Para obtener el ID del nuevo recordatorio

            # Crear un nombre de job único para poder cancelarlo si es necesario.
            job_name = f"simple_reminder_{new_reminder.id}_{uuid.uuid4()}"
            new_reminder.job_name = job_name

            # Programar el job en la JobQueue de Telegram.
            bot_manager.job_queue.run_once(
                _send_simple_reminder_callback,
                when=due_datetime_utc,
                data={"reminder_id": new_reminder.id, "telegram_id": telegram_id, "text": text},
                name=job_name
            )

            await db.commit()
            
            # Formatear una respuesta amigable para el usuario.
            # Si el usuario tiene una zona horaria configurada, se la mostramos.
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
        

        
async def reschedule_simple_reminders(application):
    """
    Recarga los recordatorios simples pendientes de la BD y los vuelve a programar.

    Esta función se llama una sola vez al iniciar el bot. Barre la base de datos
    en busca de todos los recordatorios que están activos y cuya fecha de vencimiento
    aún no ha pasado, y los vuelve a añadir a la `JobQueue` de Telegram.
    Esto asegura que los recordatorios sobrevivan a reinicios del bot.
    """
    logger.info("Re-programando recordatorios simples pendientes desde la base de datos...")
    async with DBSession(SessionLocal) as db:
        now_utc = datetime.now(pytz.utc)
        
        # Seleccionar todos los recordatorios que todavía están activos y son para el futuro.
        # Es una consulta compleja que une Recordatorio, Account y PlatformIdentity
        # para obtener el telegram_id necesario para la JobQueue.
        stmt = (
            select(Recordatorio, PlatformIdentity.platform_user_id)
            .join(Account, Recordatorio.account_id == Account.id)
            .join(PlatformIdentity, Account.id == PlatformIdentity.account_id)
            .where(
                Recordatorio.is_active == True,
                Recordatorio.due_datetime > now_utc,
                PlatformIdentity.platform == 'telegram' # Nos aseguramos de obtener el ID de Telegram
            )
        )
        
        results = await db.execute(stmt)
        pending_reminders = results.all()

        count = 0
        for reminder, telegram_id_str in pending_reminders:
            # El job_name es crucial para evitar duplicados y poder cancelar.
            if not reminder.job_name:
                logger.warning(f"El recordatorio {reminder.id} no tiene job_name, no se puede re-programar de forma segura.")
                continue

            try:
                telegram_id = int(telegram_id_str)
                application.job_queue.run_once(
                    _send_simple_reminder_callback,
                    when=reminder.due_datetime,
                    data={"reminder_id": reminder.id, "telegram_id": telegram_id, "text": reminder.text},
                    name=reminder.job_name
                )
                count += 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error al procesar el telegram_id '{telegram_id_str}' para el recordatorio {reminder.id}: {e}")
        
        if count > 0:
            logger.info(f"✅ {count} recordatorio(s) simple(s) han sido re-programados.")
        else:
            logger.info("ℹ️ No se encontraron recordatorios simples pendientes para re-programar.")
