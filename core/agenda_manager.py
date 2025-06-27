# core/agenda_manager.py

"""
Gestor de Lógica de Negocio para la Agenda (Versión Pura).

Este módulo encapsula toda la lógica para interactuar con la tabla `agenda_events`
en la base de datos. Se encarga de crear, consultar y eliminar eventos.

En esta arquitectura final y desacoplada, este módulo es "puro": no tiene
conocimiento de ninguna plataforma de interfaz como Telegram. Su única
responsabilidad es la lógica de negocio y la persistencia de datos.

La programación de notificaciones (que es específica de la plataforma) se
delega a la capa del cliente (ej. `telegram_client`).
"""

import logging
import uuid
from datetime import datetime
import pytz
import dateparser
from typing import Tuple, List, Dict, Any, Optional

from sqlalchemy import select

# Importaciones del proyecto
from core.database import SessionLocal, Account, AgendaEvent
from utils.db_session import DBSession

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


async def schedule_event(account_id: str, description: str, natural_language_datetime: str, team_id: Optional[str] = None) -> Tuple[bool, str, AgendaEvent | None]:
    """
    Crea un nuevo evento y lo guarda en la base de datos para un usuario o equipo.

    Esta versión pura NO interactúa con la JobQueue. Solo se encarga de la
    lógica de la base de datos y devuelve el objeto del evento creado para que
    el llamador (el handler) decida cómo programar la notificación.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        description: La descripción del evento.
        natural_language_datetime: La descripción en lenguaje natural del tiempo.
        team_id: El ID del equipo (UUID en formato string) al que se asocia el evento, si aplica.

    Returns:
        Una tupla (bool, str, AgendaEvent | None) indicando éxito, un mensaje
        para el usuario, y el objeto del evento creado.
    """
    async with DBSession(SessionLocal) as db:
        try:
            account = await db.get(Account, account_id)
            if not account or not account.timezone:
                return False, "No pude programar el evento porque no conozco tu zona horaria. Por favor, configúrala primero.", None

            user_tz_str = account.timezone
            user_tz = pytz.timezone(user_tz_str)
            
            # ¡CORREGIDO! Usamos un diccionario date_settings pasado como settings=... y ignoramos el error de tipo
            date_settings = {
                'TO_TIMEZONE': 'UTC', 
                'RETURN_AS_TIMEZONE_AWARE': True, 
                'RELATIVE_BASE': datetime.now(user_tz)
            }
            event_datetime_utc = dateparser.parse(
                natural_language_datetime, 
                settings=date_settings  # type: ignore
            )

            if not event_datetime_utc:
                logger.warning(f"Dateparser no pudo entender '{natural_language_datetime}'.")
                return False, f"No pude entender el tiempo '{natural_language_datetime}'. Intenta con 'mañana a las 3pm', 'en 2 horas', etc.", None

            now_utc = datetime.now(pytz.utc)
            if event_datetime_utc < now_utc:
                return False, "No puedo programar eventos en el pasado. Por favor, elige una fecha y hora futura.", None

            new_event = AgendaEvent(
                account_id=account_id,
                team_id=uuid.UUID(team_id) if team_id else None,
                description=description,
                event_datetime_utc=event_datetime_utc,
                is_active=True
            )
            db.add(new_event)
            await db.commit()
            await db.refresh(new_event)
            
            display_time = event_datetime_utc.astimezone(user_tz)
            display_time_str = display_time.strftime('%H:%M del %d-%m-%Y')
            
            message = f"¡Evento guardado! Te recordaré sobre '{description}' el {display_time_str} ({user_tz_str})."
            logger.info(f"Evento {new_event.id} creado para la cuenta {account_id}.")
            
            return True, message, new_event

        except Exception as e:
            logger.error(f"Error al guardar evento para la cuenta '{account_id}': {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al guardar tu evento.", None

async def get_agenda_for_day(account_id: str, target_day: str, team_id: Optional[str] = None) -> str:
    """
    Obtiene los eventos de un usuario o equipo para un día específico y los formatea como texto.
    Esta función está diseñada para ser llamada por el agente de IA.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        target_day: Una cadena en lenguaje natural que representa el día a consultar.
        team_id: El ID del equipo (UUID en formato string) para filtrar eventos del equipo, si aplica.

    Returns:
        Una cadena de texto formateada con la lista de eventos.
    """
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, account_id)
        if not account or not account.timezone:
            return "No puedo consultar tu agenda porque no conozco tu zona horaria."

        user_tz = pytz.timezone(account.timezone)
        now_in_user_tz = datetime.now(user_tz)
        
        # Usamos 'PREFER_DATES_FROM': 'future' para que 'hoy a las 10pm' no se interprete como en el pasado si ya son las 11pm.
        target_date_obj = dateparser.parse(target_day, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': now_in_user_tz})
        
        if not target_date_obj:
            return f"No entendí la fecha '{target_day}'. Por favor, intenta de nuevo."

        start_of_day = user_tz.localize(datetime(target_date_obj.year, target_date_obj.month, target_date_obj.day, 0, 0, 0))
        end_of_day = user_tz.localize(datetime(target_date_obj.year, target_date_obj.month, target_date_obj.day, 23, 59, 59))

        start_of_day_utc = start_of_day.astimezone(pytz.utc)
        end_of_day_utc = end_of_day.astimezone(pytz.utc)

        stmt = (
            select(AgendaEvent)
            .where(
                AgendaEvent.account_id == account_id,
                AgendaEvent.is_active == True,
                AgendaEvent.event_datetime_utc >= start_of_day_utc,
                AgendaEvent.event_datetime_utc <= end_of_day_utc
            )
        )
        if team_id:
            stmt = stmt.where(AgendaEvent.team_id == uuid.UUID(team_id))
        else:
            stmt = stmt.where(AgendaEvent.team_id.is_(None))
        stmt = stmt.order_by(AgendaEvent.event_datetime_utc)
        result = await db.execute(stmt)
        events = result.scalars().all()

        if not events:
            return f"No tienes eventos programados para el {target_date_obj.strftime('%d de %B de %Y')}."

        event_list = [f"Tu agenda para el {target_date_obj.strftime('%d de %B de %Y')}:"]
        for event in events:
            local_time = event.event_datetime_utc.astimezone(user_tz)
            event_list.append(f"- ID {event.id}: {event.description} a las {local_time.strftime('%H:%M')}")
        
        return "\n".join(event_list)


async def get_events_as_dicts(account_id: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Recupera todos los eventos futuros de un usuario o equipo y los devuelve como una lista de diccionarios.
    Esta función está diseñada para ser utilizada por endpoints de API que sirven a interfaces web.
    """
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, account_id)
        if not account:
            return []

        now_utc = datetime.now(pytz.utc)
        stmt = (
            select(AgendaEvent)
            .where(
                AgendaEvent.account_id == account_id,
                AgendaEvent.event_datetime_utc > now_utc,
                AgendaEvent.is_active == True
            )
        )
        if team_id:
            stmt = stmt.where(AgendaEvent.team_id == uuid.UUID(team_id))
        else:
            stmt = stmt.where(AgendaEvent.team_id.is_(None))
        stmt = stmt.order_by(AgendaEvent.event_datetime_utc)
        result = await db.execute(stmt)
        events = result.scalars().all()
        # Usa el método to_dict que definimos en el modelo AgendaEvent
        return [event.to_dict(account.timezone) for event in events]


async def cancel_event(account_id: str, event_id: int, team_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Cancela un evento marcándolo como inactivo en la base de datos.
    NO se encarga de cancelar el job en la JobQueue, eso debe hacerlo el llamador.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        event_id: El ID del evento a cancelar.
        team_id: El ID del equipo (UUID en formato string) para verificar la pertenencia, si aplica.

    Returns:
        Una tupla (bool, str) indicando éxito y un mensaje para el usuario.
    """
    async with DBSession(SessionLocal) as db:
        stmt = select(AgendaEvent).where(AgendaEvent.id == event_id, AgendaEvent.account_id == account_id)
        if team_id:
            stmt = stmt.where(AgendaEvent.team_id == uuid.UUID(team_id))
        else:
            stmt = stmt.where(AgendaEvent.team_id.is_(None))
        result = await db.execute(stmt)
        event_to_cancel = result.scalars().first()

        if not event_to_cancel:
            return False, "No se encontró un evento con ese ID en tu cuenta."
        
        if not event_to_cancel.is_active:
            return False, "Este evento ya ha sido cancelado o ya ocurrió."
            
        event_to_cancel.is_active = False
        await db.commit()
        
        logger.info(f"Evento {event_id} cancelado en la base de datos para la cuenta {account_id}.")
        return True, f"El evento '{event_to_cancel.description}' ha sido cancelado."
