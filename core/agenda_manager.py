# core/agenda_manager.py

import logging
import uuid
from datetime import datetime, timedelta # Importar timedelta
import pytz
import dateparser
from typing import Tuple, List, Dict, Any, Optional
import logging # Importar logging si no está ya

from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

# Importaciones del proyecto
from core.database import SessionLocal, Account, AgendaEvent, ContactProfile, Workspace, WorkspacePermission, Task
from utils.db_session import DBSession
from fastapi import HTTPException
from utils.security import check_workspace_permission # Importar check_workspace_permission

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


async def schedule_event(
    account_id: str,
    summary: str,
    event_date: str,
    event_time: str,
    workspace_id: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendee_ids: Optional[List[str]] = None,
    external_attendees: Optional[List[str]] = None,
    event_id: Optional[int] = None,
    end_date: Optional[str] = None, # Nuevo campo
    end_time: Optional[str] = None # Nuevo campo
) -> Tuple[bool, str, AgendaEvent | None]:
    """
    Crea un nuevo evento y lo guarda en la base de datos para un usuario o workspace.

    Esta versión pura NO interactúa con la JobQueue. Solo se encarga de la
    lógica de la base de datos y devuelve el objeto del evento creado para que
    el llamador (el handler) decida cómo programar la notificación.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        summary: El resumen conciso del evento.
        event_date: La fecha del evento en formato YYYY-MM-DD.
        event_time: La hora del evento en formato HH:MM.
        workspace_id: El ID del workspace (UUID en formato string) al que se asocia el evento, si aplica.
        description: La descripción detallada del evento (opcional).
        location: La ubicación del evento (opcional).
        attendee_ids: Lista de IDs de cuentas de usuarios registrados que asistirán al evento (opcional).
        external_attendees: Lista de nombres de asistentes no registrados (opcional).

    Returns:
        Una tupla (bool, str, AgendaEvent | None) indicando éxito, un mensaje
        para el usuario, y el objeto del evento creado.
    """
    async with DBSession(SessionLocal) as db:
        try:
            account = await db.get(Account, account_id)
            if not account or not account.timezone:
                return False, "No pude programar el evento porque no conozco tu zona horaria. Por favor, configúrala primero.", None
            
            # Verificar permisos de workspace si se proporciona uno
            if workspace_id:
                try:
                    await check_workspace_permission(account_id, workspace_id, db, required_roles=['admin', 'owner', 'member'])
                except HTTPException as e:
                    return False, e.detail, None

            user_tz_str = account.timezone
            user_tz = pytz.timezone(user_tz_str)
            
            try:
                # Combinar fecha y hora en un string y parsear como datetime naive
                local_datetime_str = f"{event_date} {event_time}"
                naive_datetime = datetime.strptime(local_datetime_str, "%Y-%m-%d %H:%M")
                logger.info(f"[schedule_event] naive_datetime: {naive_datetime}")
                
                # Localizar el datetime naive con la zona horaria del usuario y luego convertir a UTC
                # Este método maneja correctamente los cambios de horario de verano (DST)
                localized_dt = user_tz.localize(naive_datetime)
                event_datetime_utc = localized_dt.astimezone(pytz.utc)
                logger.info(f"[schedule_event] event_datetime_utc (antes de guardar): {event_datetime_utc}")

            except ValueError:
                return False, f"Formato de fecha u hora inválido: {event_date} {event_time}", None

            end_datetime_utc: Optional[datetime] = None
            if end_date and end_time:
                try:
                    local_end_datetime_str = f"{end_date} {end_time}"
                    naive_end_datetime = datetime.strptime(local_end_datetime_str, "%Y-%m-%d %H:%M")
                    localized_end_dt = user_tz.localize(naive_end_datetime)
                    end_datetime_utc = localized_end_dt.astimezone(pytz.utc)
                    logger.info(f"[schedule_event] end_datetime_utc (antes de guardar): {end_datetime_utc}")
                except ValueError:
                    return False, f"Formato de fecha u hora de finalización inválido: {end_date} {end_time}", None
            elif end_date: # Si solo se proporciona la fecha, la hora se asume como medianoche
                try:
                    local_end_datetime_str = f"{end_date} 00:00"
                    naive_end_datetime = datetime.strptime(local_end_datetime_str, "%Y-%m-%d %H:%M")
                    localized_end_dt = user_tz.localize(naive_end_datetime)
                    end_datetime_utc = localized_end_dt.astimezone(pytz.utc)
                    logger.info(f"[schedule_event] end_datetime_utc (antes de guardar): {end_datetime_utc}")
                except ValueError:
                    return False, f"Formato de fecha de finalización inválido: {end_date}", None

            now_utc = datetime.now(pytz.utc)
            if event_datetime_utc < now_utc:
                return False, "No puedo programar eventos en el pasado. Por favor, elige una fecha y hora futura.", None
            
            if end_datetime_utc and end_datetime_utc < event_datetime_utc:
                return False, "La fecha de finalización no puede ser anterior a la fecha de inicio.", None

            new_event = AgendaEvent(
                id=event_id, # Usar el ID proporcionado o dejar que la base de datos lo genere
                account_id=account_id,
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                summary=summary,
                description=description,
                location=location,
                event_datetime_utc=event_datetime_utc,
                end_date=end_datetime_utc, # Asignar la fecha de finalización
                is_active=True,
                external_attendees=external_attendees if external_attendees else []
            )
            db.add(new_event)
            
            if attendee_ids:
                attendees = await db.execute(
                    select(Account).where(Account.id.in_([uuid.UUID(aid) for aid in attendee_ids]))
                )
                new_event.attendees.extend(attendees.scalars().all())

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
            
            message = f"¡Evento guardado! Te recordaré sobre '{summary}' el {display_time_str} ({user_tz_str})."
            logger.info(f"Evento {new_event.id} creado para la cuenta {account_id}.")
            
            return True, message, new_event

        except Exception as e:
            logger.error(f"Error al guardar evento para la cuenta '{account_id}': {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al guardar tu evento.", None


async def add_attendees_to_event(account_id: str, event_id: int, attendee_ids: Optional[List[str]] = None, external_attendees: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Añade asistentes (registrados y/o externos) a un evento existente.
    """
    async with DBSession(SessionLocal) as db:
        try:
            event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.attendees)).where(
                AgendaEvent.id == event_id,
                AgendaEvent.account_id == uuid.UUID(account_id)
            )
            event = (await db.execute(event_stmt)).scalars().first()

            if not event:
                return False, "Evento no encontrado o no pertenece a tu cuenta."

            if event.workspace_id:
                try:
                    await check_workspace_permission(account_id, str(event.workspace_id), db, required_roles=['admin', 'owner', 'member'])
                except HTTPException as e:
                    return False, e.detail

            if attendee_ids:
                existing_attendee_ids = {str(a.id) for a in event.attendees}
                new_attendee_uuids = [uuid.UUID(aid) for aid in attendee_ids if aid not in existing_attendee_ids]
                
                if new_attendee_uuids:
                    new_attendees = await db.execute(
                        select(Account).where(Account.id.in_(new_attendee_uuids))
                    )
                    event.attendees.extend(new_attendees.scalars().all())

            if external_attendees:
                current_external_attendees = set(event.external_attendees if event.external_attendees else [])
                new_external_attendees = [att for att in external_attendees if att not in current_external_attendees]
                if new_external_attendees: # Corregido: usar new_external_attendees en lugar de new_attendees
                    if event.external_attendees is None:
                        event.external_attendees = []
                    event.external_attendees.extend(new_external_attendees)

            await db.commit()
            await db.refresh(event)
            return True, "Asistentes añadidos exitosamente."

        except Exception as e:
            logger.error(f"Error al añadir asistentes al evento {event_id} para la cuenta {account_id}: {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al añadir asistentes."


async def remove_attendees_from_event(account_id: str, event_id: int, attendee_ids: Optional[List[str]] = None, external_attendees: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Remueve asistentes (registrados y/o externos) de un evento existente.
    """
    async with DBSession(SessionLocal) as db:
        try:
            event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.attendees)).where(
                AgendaEvent.id == event_id,
                AgendaEvent.account_id == uuid.UUID(account_id)
            )
            event = (await db.execute(event_stmt)).scalars().first()

            if not event:
                return False, "Evento no encontrado o no pertenece a tu cuenta."

            if event.workspace_id:
                try:
                    await check_workspace_permission(account_id, str(event.workspace_id), db, required_roles=['admin', 'owner', 'member'])
                except HTTPException as e:
                    return False, e.detail

            if attendee_ids:
                attendees_to_remove_uuids = [uuid.UUID(aid) for aid in attendee_ids]
                event.attendees = [att for att in event.attendees if att.id not in attendees_to_remove_uuids]

            if external_attendees and event.external_attendees:
                event.external_attendees = [att for att in event.external_attendees if att not in external_attendees]

            await db.commit()
            await db.refresh(event)
            return True, "Asistentes removidos exitosamente."

        except Exception as e:
            logger.error(f"Error al remover asistentes del evento {event_id} para la cuenta {account_id}: {e}", exc_info=True)
            await db.rollback()
            return False, "Ocurrió un error inesperado al remover asistentes."


async def get_agenda_for_period(account_id: str, period_type: str, target_date: str, workspace_id: Optional[str] = None) -> str:
    """
    Obtiene los eventos de un usuario o workspace para un período específico (día, semana, mes)
    y los formatea como texto.
    Esta función está diseñada para ser llamada por el agente de IA.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        period_type: El tipo de período a consultar ('day', 'week', 'month').
        target_date: Una cadena en lenguaje natural que representa la fecha o período a consultar.
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
        
        # Verificar permisos de workspace si se proporciona uno
        if workspace_id:
            try:
                await check_workspace_permission(account_id, workspace_id, db, required_roles=['admin', 'owner', 'member'])
            except HTTPException as e:
                return e.detail

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
        else:
            # Si no se especifica un workspace, obtener eventos personales y de todos los workspaces a los que tiene acceso
            accessible_workspaces_stmt = select(WorkspacePermission.workspace_id).where(WorkspacePermission.account_id == str(account_id))
            result = await db.execute(accessible_workspaces_stmt)
            accessible_workspace_ids = [row[0] for row in result.fetchall()]
            
            stmt = stmt.where(
                or_(
                    AgendaEvent.workspace_id.is_(None),
                    AgendaEvent.workspace_id.in_(accessible_workspace_ids)
                )
            )
        stmt = stmt.order_by(AgendaEvent.event_datetime_utc)
        result = await db.execute(stmt)
        events = result.scalars().all()

        if not events:
            return f"No tienes eventos programados para {period_description}."

        event_list = [f"Tu agenda para {period_description}:"]
        for event in events:
            local_time = event.event_datetime_utc.astimezone(user_tz)
            event_list.append(f"- ID {event.id}: {event.summary} a las {local_time.strftime('%H:%M del %d-%m-%Y')}")
        
        return "\n".join(event_list)

async def get_agenda_for_day(account_id: str, target_day: str, workspace_id: Optional[str] = None) -> str:
    """
    Función de compatibilidad para mantener la API existente.
    Delega la llamada a get_agenda_for_period con period_type='day'.
    """
    return await get_agenda_for_period(account_id, "day", target_day, workspace_id)

async def get_event_by_id_db(account_id: str, event_id: int) -> Optional[AgendaEvent]:
    """
    Recupera un evento específico por su ID directamente de la base de datos como objeto AgendaEvent.
    No realiza verificaciones de permiso de workspace aquí, se asume que el llamador lo hará.
    """
    async with DBSession(SessionLocal) as db:
        stmt = select(AgendaEvent).options(
            selectinload(AgendaEvent.contact_profiles),
            selectinload(AgendaEvent.workspace),
            selectinload(AgendaEvent.attendees)
        ).where(
            AgendaEvent.id == event_id,
            AgendaEvent.account_id == uuid.UUID(account_id)
        )
        result = await db.execute(stmt)
        event = result.scalars().first()
        return event

async def update_event_db(
    db_session: AsyncSession,
    account_id: str,
    event_id: int,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    event_datetime_utc: Optional[datetime] = None,
    end_date: Optional[datetime] = None, # Nuevo campo
    attendee_ids: Optional[List[str]] = None,
    external_attendees: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
) -> Optional[AgendaEvent]:
    """
    Actualiza un evento existente en la base de datos.
    """
    async with db_session as db: # Asegurarse de que db_session se maneje correctamente
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.attendees)).where(
            AgendaEvent.id == event_id,
            AgendaEvent.account_id == uuid.UUID(account_id)
        )
        event = (await db.execute(event_stmt)).scalars().first()

        if not event:
            return None

        # Actualizar campos básicos
        if summary is not None:
            event.summary = summary
        if description is not None:
            event.description = description
        if location is not None:
            event.location = location
        if event_datetime_utc is not None:
            event.event_datetime_utc = event_datetime_utc
        if end_date is not None: # Nuevo campo
            event.end_date = end_date
        if workspace_id is not None:
            event.workspace_id = uuid.UUID(workspace_id) if workspace_id else None
        
        # Lógica para attendee_ids
        if attendee_ids is not None:
            current_attendee_uuids = {att.id for att in event.attendees}
            new_attendee_uuids = {uuid.UUID(aid) for aid in attendee_ids}

            to_add_uuids = new_attendee_uuids - current_attendee_uuids
            to_remove_uuids = current_attendee_uuids - new_attendee_uuids

            if to_add_uuids:
                new_attendees = await db.execute(select(Account).where(Account.id.in_(list(to_add_uuids))))
                event.attendees.extend(new_attendees.scalars().all())
            
            if to_remove_uuids:
                event.attendees = [att for att in event.attendees if att.id not in to_remove_uuids]

        # Lógica para external_attendees
        if external_attendees is not None:
            event.external_attendees = external_attendees
        
        try:
            await db.commit()
            await db.refresh(event)
            return event
        except Exception as e:
            logger.error(f"Error al actualizar el evento {event_id}: {e}", exc_info=True)
            await db.rollback()
            return None


async def get_events_as_dicts(account_id: str, workspace_id: Optional[str] = None, include_past: bool = False) -> List[Dict[str, Any]]:
    """
    Recupera eventos de un usuario o workspace y los devuelve como una lista de diccionarios.
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
            .options(
                selectinload(AgendaEvent.contact_profiles),
                selectinload(AgendaEvent.workspace),
                selectinload(AgendaEvent.attendees) # Cargar ansiosamente los asistentes
            )
            .where(
                AgendaEvent.account_id == account_id,
                AgendaEvent.is_active == True
            )
        )

        if workspace_id:
            # Si se especifica un workspace, verificar permisos
            try:
                await check_workspace_permission(account_id, workspace_id, db, required_roles=['admin', 'owner', 'member', 'viewer'])
            except HTTPException as e:
                logger.warning(f"Permission denied for account {account_id} on workspace {workspace_id}: {e.detail}")
                # Si no tiene permiso, no devolver ningún evento de ese workspace
                return []
            stmt = stmt.where(AgendaEvent.workspace_id == uuid.UUID(workspace_id))
        else:
            # Si no se especifica un workspace, obtener eventos personales y de todos los workspaces a los que tiene acceso
            accessible_workspaces_stmt = select(WorkspacePermission.workspace_id).where(WorkspacePermission.account_id == str(account_id))
            result = await db.execute(accessible_workspaces_stmt)
            accessible_workspace_ids = [row[0] for row in result.fetchall()]
            
            stmt = stmt.where(
                or_(
                    AgendaEvent.workspace_id.is_(None),
                    AgendaEvent.workspace_id.in_(accessible_workspace_ids)
                )
            )
        stmt = stmt.order_by(AgendaEvent.event_datetime_utc)
        result = await db.execute(stmt)
        events = result.scalars().all()
        
        # Usa el método to_dict que definimos en el modelo AgendaEvent
        # Modificamos para incluir los perfiles vinculados
        event_dicts = []
        for event in events:
            logger.debug(f"Processing event ID: {event.id}, Summary: {event.summary}") # Log para depuración
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


async def get_task_by_id_db(account_id: str, task_id: int) -> Optional[Task]:
    """
    Recupera una tarea específica por su ID directamente de la base de datos como objeto Task.
    """
    async with DBSession(SessionLocal) as db:
        stmt = select(Task).where(
            Task.id == task_id,
            Task.account_id == uuid.UUID(account_id)
        )
        result = await db.execute(stmt)
        task = result.scalars().first()
        return task

async def update_task_db(
    db_session: AsyncSession,
    account_id: str,
    task_id: int,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None, # Nuevo campo
    end_date: Optional[datetime] = None, # Nuevo campo
    is_completed: Optional[bool] = None,
    workspace_id: Optional[str] = None,
    linked_profiles: Optional[List[str]] = None, # Añadir linked_profiles
) -> Optional[Task]:
    """
    Actualiza una tarea existente en la base de datos.
    """
    async with db_session as db:
        task_stmt = select(Task).options(selectinload(Task.linked_profiles)).where( # Cargar ansiosamente los perfiles vinculados
            Task.id == task_id,
            Task.account_id == uuid.UUID(account_id)
        )
        task = (await db.execute(task_stmt)).scalars().first()

        if not task:
            return None

        # Actualizar campos básicos si no son None
        if summary is not None:
            task.summary = summary
        if description is not None:
            task.description = description
        if due_date is not None:
            task.due_date = due_date
        if start_date is not None: # Nuevo campo
            task.start_date = start_date
        if end_date is not None: # Nuevo campo
            task.end_date = end_date
        if is_completed is not None:
            task.is_completed = is_completed
        if workspace_id is not None:
            task.workspace_id = uuid.UUID(workspace_id) if workspace_id else None
        
        # Lógica para linked_profiles
        if linked_profiles is not None:
            current_profile_uuids = {cp.id for cp in task.linked_profiles}
            new_profile_uuids = {uuid.UUID(pid) for pid in linked_profiles}

            to_add_uuids = new_profile_uuids - current_profile_uuids
            to_remove_uuids = current_profile_uuids - new_profile_uuids

            if to_add_uuids:
                new_profiles = await db.execute(select(ContactProfile).where(ContactProfile.id.in_(list(to_add_uuids))))
                task.linked_profiles.extend(new_profiles.scalars().all())
            
            if to_remove_uuids:
                task.linked_profiles = [cp for cp in task.linked_profiles if cp.id not in to_remove_uuids]
        
        try:
            await db.commit()
            await db.refresh(task)
            return task
        except Exception as e:
            logger.error(f"Error al actualizar la tarea {task_id}: {e}", exc_info=True)
            await db.rollback()
            return None


async def cancel_event(account_id: str, event_id: int, workspace_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Cancela un evento marcándolo como inactivo en la base de datos.
    NO se encarga de cancelar el job en la JobQueue, eso debe hacerlo el llamador.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        event_id: El ID del evento a cancelar.
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
                AgendaEvent.workspace_id == uuid.UUID(workspace_id),
                AgendaEvent.account_id == uuid.UUID(account_id) # Asegurar que el evento pertenece al usuario
            )
            result = await db.execute(stmt)
            event_to_cancel = result.scalars().first()

            if event_to_cancel:
                # Verificar que el usuario tiene acceso al workspace
                try:
                    await check_workspace_permission(account_id, workspace_id, db, required_roles=['admin', 'owner', 'member'])
                except HTTPException as e:
                    return False, e.detail
            else:
                return False, "No se encontró un evento con ese ID en el workspace especificado."
        else:
            # Para eventos personales (sin workspace_id)
            stmt = select(AgendaEvent).where(
                AgendaEvent.id == event_id,
                AgendaEvent.account_id == uuid.UUID(account_id),
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
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.contact_profiles)).where(AgendaEvent.id == event_id, AgendaEvent.account_id == uuid.UUID(account_id))
        event = (await db.execute(event_stmt)).scalars().first()
        if not event:
            logger.warning(f"Evento {event_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return False
        
        # Verificar permisos de workspace si el evento pertenece a uno
        if event.workspace_id:
            try:
                await check_workspace_permission(account_id, str(event.workspace_id), db, required_roles=['admin', 'owner', 'member'])
            except HTTPException as e:
                logger.warning(f"Acceso denegado para vincular perfil al evento {event_id} en workspace {event.workspace_id} para la cuenta {account_id}: {e.detail}")
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

async def unlink_profile_from_event(account_id: str, event_id: int, profile_id: uuid.UUID) -> bool:
    """
    Desvincula un perfil de un evento existente.
    """
    logger.info(f"Intentando desvincular perfil {profile_id} del evento {event_id} para la cuenta {account_id}")
    async with DBSession(SessionLocal) as db:
        # Verificar que el evento existe y pertenece al usuario
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.contact_profiles)).where(AgendaEvent.id == event_id, AgendaEvent.account_id == uuid.UUID(account_id))
        event = (await db.execute(event_stmt)).scalars().first()
        if not event:
            logger.warning(f"Evento {event_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return False
        
        # Verificar permisos de workspace si el evento pertenece a uno
        if event.workspace_id:
            try:
                await check_workspace_permission(account_id, str(event.workspace_id), db, required_roles=['admin', 'owner', 'member'])
            except HTTPException as e:
                logger.warning(f"Acceso denegado para desvincular perfil del evento {event_id} en workspace {event.workspace_id} para la cuenta {account_id}: {e.detail}")
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
        stmt = select(AgendaEvent).options(
            selectinload(AgendaEvent.contact_profiles),
            selectinload(AgendaEvent.workspace),
            selectinload(AgendaEvent.attendees) # Cargar ansiosamente los asistentes
        ).where(
            AgendaEvent.id == event_id,
            AgendaEvent.account_id == uuid.UUID(account_id)
        )
        result = await db.execute(stmt)
        event = result.scalars().first()

        if not event:
            logger.warning(f"Evento {event_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return None
        
        # Verificar permisos de workspace si el evento pertenece a uno
        if event.workspace_id:
            try:
                await check_workspace_permission(account_id, str(event.workspace_id), db, required_roles=['admin', 'owner', 'member'])
            except HTTPException as e:
                logger.warning(f"Acceso denegado al evento {event_id} en workspace {event.workspace_id} para la cuenta {account_id}: {e.detail}")
                return None
        
        account = await db.get(Account, uuid.UUID(account_id))
        if not account:
            logger.warning(f"Cuenta {account_id} no encontrada para el evento {event_id}.")
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
