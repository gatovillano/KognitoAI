# core/agenda_manager.py

import logging
import uuid
from datetime import datetime
import pytz
import dateparser
from typing import Tuple, List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Importaciones del proyecto
from core.database import SessionLocal, Account, AgendaEvent, ContactProfile
from utils.db_session import DBSession

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


async def schedule_event(account_id: str, description: str, event_date: str, event_time: str, team_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Tuple[bool, str, AgendaEvent | None]:
    """
    Crea un nuevo evento y lo guarda en la base de datos para un usuario o equipo.

    Esta versión pura NO interactúa con la JobQueue. Solo se encarga de la
    lógica de la base de datos y devuelve el objeto del evento creado para que
    el llamador (el handler) decida cómo programar la notificación.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        description: La descripción del evento.
        event_date: La fecha del evento en formato YYYY-MM-DD.
        event_time: La hora del evento en formato HH:MM.
        team_id: El ID del equipo (UUID en formato string) al que se asocia el evento, si aplica.
        workspace_id: El ID del workspace (UUID en formato string) al que se asocia el evento, si aplica.

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
            
            try:
                # Combinar fecha y hora en un string y parsear como datetime naive
                local_datetime_str = f"{event_date} {event_time}"
                naive_datetime = datetime.strptime(local_datetime_str, "%Y-%m-%d %H:%M")
                logger.info(f"[schedule_event] naive_datetime: {naive_datetime}")
                
                # Obtener el offset actual de la zona horaria del usuario para la fecha/hora dada
                offset = user_tz.utcoffset(naive_datetime)
                logger.info(f"[schedule_event] user_tz: {user_tz}, offset: {offset}")
                
                # Convertir la hora local naive a UTC restando el offset
                event_datetime_utc = naive_datetime - offset
                # Asegurarse de que sea un datetime aware en UTC
                event_datetime_utc = pytz.utc.localize(event_datetime_utc)
                logger.info(f"[schedule_event] event_datetime_utc (antes de guardar): {event_datetime_utc}")

            except ValueError:
                return False, f"Formato de fecha u hora inválido: {event_date} {event_time}", None

            now_utc = datetime.now(pytz.utc)
            if event_datetime_utc < now_utc:
                return False, "No puedo programar eventos en el pasado. Por favor, elige una fecha y hora futura.", None

            new_event = AgendaEvent(
                account_id=account_id,
                team_id=uuid.UUID(team_id) if team_id else None,
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                description=description,
                event_datetime_utc=event_datetime_utc,
                is_active=True
            )
            db.add(new_event)
            await db.commit()
            await db.refresh(new_event)
            # Cargar la relación workspace de forma ansiosa para evitar DetachedInstanceError
            loaded_event = await db.execute(
                select(AgendaEvent).options(selectinload(AgendaEvent.workspace)).where(AgendaEvent.id == new_event.id)
            )
            new_event = loaded_event.scalars().first()
            
            if not new_event:
                return False, "Error al recuperar el evento recién creado.", None
            
            display_time = event_datetime_utc.astimezone(user_tz)
            display_time_str = display_time.strftime('%H:%M del %d-%m-%Y')
            
            message = f"¡Evento guardado! Te recordaré sobre '{description}' el {display_time_str} ({user_tz_str})."
            logger.info(f"Evento {new_event.id} creado para la cuenta {account_id}.")
            
            return True, message, new_event

        except Exception as e:
            logger.error(f"Error al guardar evento para la cuenta '{account_id}': {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al guardar tu evento.", None



async def get_agenda_for_period(account_id: str, period_type: str, target_date: str, team_id: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
    """
    Obtiene los eventos de un usuario o equipo para un período específico (día, semana, mes)
    y los formatea como texto.
    Esta función está diseñada para ser llamada por el agente de IA.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        period_type: El tipo de período a consultar ('day', 'week', 'month').
        target_date: Una cadena en lenguaje natural que representa la fecha o período a consultar.
        team_id: El ID del equipo (UUID en formato string) para filtrar eventos del equipo, si aplica.
        workspace_id: El ID del workspace (UUID en formato string) para filtrar eventos del workspace, si aplica.

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
        parsed_date_obj = dateparser.parse(target_date, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': now_in_user_tz})
        
        if not parsed_date_obj:
            return f"No entendí la fecha o período '{target_date}'. Por favor, intenta de nuevo."

        start_period_utc = None
        end_period_utc = None
        period_description = ""

        if period_type == "day":
            start_period = user_tz.localize(datetime(parsed_date_obj.year, parsed_date_obj.month, parsed_date_obj.day, 0, 0, 0))
            end_period = user_tz.localize(datetime(parsed_date_obj.year, parsed_date_obj.month, parsed_date_obj.day, 23, 59, 59))
            period_description = f"el {parsed_date_obj.strftime('%d de %B de %Y')}"
        elif period_type == "week":
            # Calcular el inicio de la semana (lunes)
            start_of_week = parsed_date_obj - timedelta(days=parsed_date_obj.weekday())
            start_period = user_tz.localize(datetime(start_of_week.year, start_of_week.month, start_of_week.day, 0, 0, 0))
            end_period = start_period + timedelta(days=6, hours=23, minutes=59, seconds=59)
            period_description = f"la semana del {start_of_week.strftime('%d de %B de %Y')}"
        elif period_type == "month":
            start_period = user_tz.localize(datetime(parsed_date_obj.year, parsed_date_obj.month, 1, 0, 0, 0))
            # Calcular el último día del mes
            next_month = parsed_date_obj.replace(day=28) + timedelta(days=4)  # Esto asegura que estamos en el próximo mes
            end_period = user_tz.localize(datetime(next_month.year, next_month.month, 1, 0, 0, 0)) - timedelta(seconds=1)
            period_description = f"el mes de {parsed_date_obj.strftime('%B de %Y')}"
        else:
            return "Tipo de período no válido. Por favor, usa 'day', 'week' o 'month'."

        start_period_utc = start_period.astimezone(pytz.utc)
        end_period_utc = end_period.astimezone(pytz.utc)

        stmt = (
            select(AgendaEvent)
            .where(
                AgendaEvent.account_id == account_id,
                AgendaEvent.is_active == True,
                AgendaEvent.event_datetime_utc >= start_period_utc,
                AgendaEvent.event_datetime_utc <= end_period_utc
            )
        )
        if workspace_id:
            stmt = stmt.where(AgendaEvent.workspace_id == uuid.UUID(workspace_id))
        elif team_id:
            stmt = stmt.where(AgendaEvent.team_id == uuid.UUID(team_id))
        else:
            stmt = stmt.where(AgendaEvent.team_id.is_(None), AgendaEvent.workspace_id.is_(None))
        stmt = stmt.order_by(AgendaEvent.event_datetime_utc)
        result = await db.execute(stmt)
        events = result.scalars().all()

        if not events:
            return f"No tienes eventos programados para {period_description}."

        event_list = [f"Tu agenda para {period_description}:"]
        for event in events:
            local_time = event.event_datetime_utc.astimezone(user_tz)
            event_list.append(f"- ID {event.id}: {event.description} a las {local_time.strftime('%H:%M del %d-%m-%Y')}")
        
        return "\n".join(event_list)

async def get_agenda_for_day(account_id: str, target_day: str, team_id: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
    """
    Función de compatibilidad para mantener la API existente.
    Delega la llamada a get_agenda_for_period con period_type='day'.
    """
    return await get_agenda_for_period(account_id, "day", target_day, team_id, workspace_id)


async def get_events_as_dicts(account_id: str, team_id: Optional[str] = None, workspace_id: Optional[str] = None, include_past: bool = False) -> List[Dict[str, Any]]:
    """
    Recupera eventos de un usuario o equipo y los devuelve como una lista de diccionarios.
    Si include_past es False (por defecto), solo recupera eventos futuros.
    Esta función está diseñada para ser utilizada por endpoints de API que sirven a interfaces web.
    """
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, account_id)
        if not account:
            return []

        now_utc = datetime.now(pytz.utc)
        stmt = (
            select(AgendaEvent)
            .options(selectinload(AgendaEvent.contact_profiles), selectinload(AgendaEvent.workspace)) # NEW: Load workspace
            .where(
                AgendaEvent.account_id == account_id,
                AgendaEvent.is_active == True
            )
        )

        if not include_past:
            stmt = stmt.where(AgendaEvent.event_datetime_utc > now_utc)

        if workspace_id:
            stmt = stmt.where(AgendaEvent.workspace_id == uuid.UUID(workspace_id))
        elif team_id:
            stmt = stmt.where(AgendaEvent.team_id == uuid.UUID(team_id))
        else:
            stmt = stmt.where(AgendaEvent.team_id.is_(None), AgendaEvent.workspace_id.is_(None))
        stmt = stmt.order_by(AgendaEvent.event_datetime_utc)
        result = await db.execute(stmt)
        events = result.scalars().all()
        
        # Usa el método to_dict que definimos en el modelo AgendaEvent
        # Modificamos para incluir los perfiles vinculados
        event_dicts = []
        for event in events:
            event_dict = event.to_dict(account.timezone)
            linked_profiles_data = []
            for cp in event.contact_profiles:
                linked_profiles_data.append({
                    "id": str(cp.id),
                    "name": cp.name,
                    "email": cp.email,
                    "phone": cp.phone,
                })
            event_dict["linked_profiles"] = linked_profiles_data
            event_dicts.append(event_dict)
        return event_dicts


async def cancel_event(account_id: str, event_id: int, team_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Cancela un evento marcándolo como inactivo en la base de datos.
    NO se encarga de cancelar el job en la JobQueue, eso debe hacerlo el llamador.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        event_id: El ID del evento a cancelar.
        team_id: El ID del equipo (UUID en formato string) para verificar la pertenencia, si aplica.
        workspace_id: El ID del workspace (UUID en formato string) para verificar la pertenencia, si aplica.

    Returns:
        Una tupla (bool, str) indicando éxito y un mensaje para el usuario.
    """
    async with DBSession(SessionLocal) as db:
        if workspace_id:
            # Si se proporciona un workspace_id, buscamos el evento por ID y workspace_id
            # y luego verificamos que el usuario tenga acceso a ese workspace.
            stmt = select(AgendaEvent).where(
                AgendaEvent.id == event_id,
                AgendaEvent.workspace_id == uuid.UUID(workspace_id)
            )
            result = await db.execute(stmt)
            event_to_cancel = result.scalars().first()

            if event_to_cancel:
                # Verificar que el usuario tiene acceso al workspace
                workspace = await db.get(Workspace, uuid.UUID(workspace_id))
                if not workspace or workspace.account_id != uuid.UUID(account_id):
                    return False, "No tienes permisos para cancelar eventos en este workspace."
            else:
                return False, "No se encontró un evento con ese ID en el workspace especificado."
        elif team_id:
            stmt = select(AgendaEvent).where(
                AgendaEvent.id == event_id,
                AgendaEvent.team_id == uuid.UUID(team_id)
            )
            result = await db.execute(stmt)
            event_to_cancel = result.scalars().first()

            if event_to_cancel:
                # Verificar que el usuario es miembro del equipo o el propietario del evento
                team_member = await db.execute(
                    select(TeamMember).where(
                        TeamMember.team_id == uuid.UUID(team_id),
                        TeamMember.account_id == uuid.UUID(account_id)
                    )
                )
                if not team_member.scalars().first() and event_to_cancel.account_id != uuid.UUID(account_id):
                    return False, "No tienes permisos para cancelar eventos en este equipo."
            else:
                return False, "No se encontró un evento con ese ID en el equipo especificado."
        else:
            # Para eventos personales (sin workspace_id ni team_id)
            stmt = select(AgendaEvent).where(
                AgendaEvent.id == event_id,
                AgendaEvent.account_id == uuid.UUID(account_id),
                AgendaEvent.team_id.is_(None),
                AgendaEvent.workspace_id.is_(None)
            )
            result = await db.execute(stmt)
            event_to_cancel = result.scalars().first()
            if not event_to_cancel:
                return False, "No se encontró un evento personal con ese ID en tu cuenta."

        if not event_to_cancel:
            return False, "No se encontró un evento con ese ID en tu cuenta."
        
        if not event_to_cancel.is_active:
            return False, "Este evento ya ha sido cancelado o ya ocurrió."
            
        event_to_cancel.is_active = False
        await db.commit()
        
        logger.info(f"Evento {event_id} cancelado en la base de datos para la cuenta {account_id}.")
        return True, f"El evento '{event_to_cancel.description}' ha sido cancelado."

async def link_profile_to_event(account_id: str, event_id: int, profile_id: str) -> bool:
    """
    Vincula un perfil a un evento existente.
    """
    logger.info(f"Intentando vincular perfil {profile_id} al evento {event_id} para la cuenta {account_id}")
    async with DBSession(SessionLocal) as db:
        # Verificar que el evento existe y pertenece al usuario
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.contact_profiles)).where(AgendaEvent.id == event_id, AgendaEvent.account_id == account_id)
        event = (await db.execute(event_stmt)).scalars().first()
        if not event:
            logger.warning(f"Evento {event_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return False

        # Verificar que el perfil existe y pertenece al usuario
        profile_stmt = select(ContactProfile).where(ContactProfile.id == profile_id, ContactProfile.account_id == uuid.UUID(account_id))
        profile = (await db.execute(profile_stmt)).scalars().first()
        if not profile:
            logger.warning(f"Perfil {profile_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return False

        # Verificar si el vínculo ya existe
        if profile in event.contact_profiles:
            logger.info(f"El vínculo entre el evento {event_id} y el perfil {profile_id} ya existe.")
            return True # Ya está vinculado, consideramos éxito

        # Crear el nuevo vínculo
        event.contact_profiles.append(profile)
        await db.commit()
        await db.refresh(event)
        logger.info(f"Perfil {profile_id} vinculado exitosamente al evento {event_id}.")
        return True

async def unlink_profile_from_event(account_id: str, event_id: int, profile_id: str) -> bool:
    """
    Desvincula un perfil de un evento existente.
    """
    logger.info(f"Intentando desvincular perfil {profile_id} del evento {event_id} para la cuenta {account_id}")
    async with DBSession(SessionLocal) as db:
        # Verificar que el evento existe y pertenece al usuario
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.contact_profiles)).where(AgendaEvent.id == event_id, AgendaEvent.account_id == account_id)
        event = (await db.execute(event_stmt)).scalars().first()
        if not event:
            logger.warning(f"Evento {event_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return False

        # Eliminar el vínculo
        profile_to_remove_stmt = select(ContactProfile).where(ContactProfile.id == profile_id, ContactProfile.account_id == uuid.UUID(account_id))
        profile_to_remove = (await db.execute(profile_to_remove_stmt)).scalars().first()

        if profile_to_remove and profile_to_remove in event.contact_profiles:
            event.contact_profiles.remove(profile_to_remove)
            await db.commit()
            logger.info(f"Perfil {profile_id} desvinculado exitosamente del evento {event_id}.")
            return True
        else:
            logger.warning(f"El vínculo entre el evento {event_id} y el perfil {profile_id} no fue encontrado para desvincular o el perfil no existe/no pertenece al usuario.")
            return False

async def get_event_by_id(account_id: str, event_id: int) -> Optional[Dict[str, Any]]:
    """
    Recupera un evento específico por su ID, incluyendo perfiles vinculados.
    """
    logger.info(f"Consultando evento {event_id} para la cuenta {account_id}.")
    async with DBSession(SessionLocal) as db:
        stmt = select(AgendaEvent).options(selectinload(AgendaEvent.contact_profiles)).where(
            AgendaEvent.id == event_id,
            AgendaEvent.account_id == uuid.UUID(account_id)
        )
        result = await db.execute(stmt)
        event = result.scalars().first()

        if not event:
            logger.warning(f"Evento {event_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return None
        
        # Usar el método to_dict del modelo AgendaEvent para obtener la representación base
        event_dict = event.to_dict(account.timezone)

        # Añadir los perfiles vinculados
        linked_profiles_data = []
        for cp in event.contact_profiles:
            linked_profiles_data.append({
                "id": str(cp.id),
                "name": cp.name,
                "email": cp.email,
                "phone": cp.phone,
            })
        event_dict["linked_profiles"] = linked_profiles_data
        
        return event_dict
