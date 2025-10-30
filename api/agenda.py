# api/agenda.py

import logging
import uuid
from typing import List, Optional
import pytz # Added import
from datetime import datetime # Changed import
import dateparser # Added import

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, desc, update, or_

from core.database import SessionLocal, Account, TeamMember, AgendaEvent, Workspace, get_db_session, ContactProfile, WorkspacePermission # Import ContactProfile model, WorkspacePermission
from utils.security import get_current_account_id, check_workspace_permission
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload # Import selectinload
from core.agenda_manager import schedule_event, cancel_event, get_event_by_id, add_attendees_to_event, remove_attendees_from_event # Import schedule_event, cancel_event, get_event_by_id, add_attendees_to_event, remove_attendees_from_event

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

from utils.db_session import DBSession

@router.get("/agenda/events/{event_id}", summary="Obtener un evento por ID")
async def get_event_by_id_endpoint(
    event_id: int,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Obtiene un evento específico por su ID, incluyendo los perfiles de contacto vinculados.
    """
    event = await get_event_by_id(current_account_id, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado o no autorizado.")
    
    # Si el evento tiene un workspace_id, verificar permisos
    if event.get("workspace_id"):
        # Necesitamos una sesión de DB para check_workspace_permission
        async with DBSession(SessionLocal) as db:
            if not await check_workspace_permission(current_account_id, event["workspace_id"], db, required_roles=['owner', 'editor', 'viewer']):
                raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este evento.")
                
    return event

@router.get("/agenda/events/{event_id}/linked-profiles", summary="Obtener perfiles vinculados a un evento")
async def get_linked_profiles_to_event_endpoint(
    event_id: int,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene la lista de perfiles de contacto vinculados a un evento específico.
    """
    async with db as session:
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.contact_profiles)).where(
            AgendaEvent.id == event_id,
            AgendaEvent.account_id == uuid.UUID(current_account_id)
        )
        event = (await session.execute(event_stmt)).scalars().first()

        if not event:
            raise HTTPException(status_code=404, detail="Evento no encontrado o no autorizado.")
        
        # Si el evento tiene un workspace_id, verificar permisos
        if event.workspace_id:
            if not await check_workspace_permission(current_account_id, str(event.workspace_id), db, required_roles=['owner', 'editor', 'viewer']):
                raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este evento.")
        
        # Convertir los perfiles vinculados a un formato serializable
        linked_profiles_data = []
        for profile in event.contact_profiles:
            linked_profiles_data.append({
                "id": str(profile.id),
                "name": profile.name,
                "email": profile.email,
                "phone": profile.phone,
                # Add other fields if necessary
            })
        return linked_profiles_data

class ListEventsRequest(BaseModel):
    include_past: bool = False
    workspace_id: Optional[str] = None # Nuevo campo

@router.post("/list-events")
async def list_events_endpoint(request: ListEventsRequest, current_account_id: str = Depends(get_current_account_id)):
    """Lista los eventos de la agenda del usuario, incluyendo eventos compartidos con equipos y workspaces, filtrados por workspace_id si se proporciona."""
    account_uuid = uuid.UUID(current_account_id)
    
    from core.agenda_manager import get_events_as_dicts

    if request.workspace_id:
        # Si se proporciona workspace_id, verificar permisos
        async with DBSession(SessionLocal) as db:
            if not await check_workspace_permission(current_account_id, request.workspace_id, db, required_roles=['owner', 'editor', 'viewer']):
                raise HTTPException(status_code=403, detail="No tienes permiso para acceder a eventos en este workspace.")
        
        # Luego, obtener eventos para ese workspace
        workspace_events = await get_events_as_dicts(
            account_id=current_account_id,
            workspace_id=request.workspace_id,
            include_past=request.include_past
        )
        logger.info(f"Workspace events for workspace {request.workspace_id} and account {current_account_id}: {len(workspace_events)} events found")
        return list(workspace_events)
    else:
        # Lógica existente para listar todos los eventos si no hay workspace_id
        personal_events = await get_events_as_dicts(current_account_id, include_past=request.include_past)
        logger.info(f"Personal events for account {current_account_id}: {len(personal_events)} events found")
        
        async with DBSession(SessionLocal) as db:
            # Obtener todos los workspaces a los que el usuario tiene acceso
            workspaces_result = await db.execute(
                select(WorkspacePermission.workspace_id).where(WorkspacePermission.account_id == account_uuid)
            )
            workspace_ids = [str(ws_id) for ws_id in workspaces_result.scalars().all()]
            logger.info(f"Workspaces for account {current_account_id} (events): {workspace_ids})")
        
        workspace_events = []
        for workspace_id in workspace_ids:
            workspace_events_for_id = await get_events_as_dicts(
                account_id=current_account_id,
                workspace_id=workspace_id,
                include_past=request.include_past
            )
            logger.info(f"Workspace events for workspace {workspace_id} and account {current_account_id}: {len(workspace_events_for_id)} events found")
            workspace_events.extend(workspace_events_for_id)
        
        combined_events = {event['id']: event for event in personal_events + workspace_events}.values()
        logger.info(f"Total combined events for account {current_account_id}: {len(combined_events)} events")
        return list(combined_events)

# --- MODELOS PYDANTIC PARA AGENDA ---
class EventRequest(BaseModel):
    summary: str
    description: str
    event_date: str  # Fecha en formato YYYY-MM-DD
    event_time: str  # Hora en formato HH:MM
    location: Optional[str] = None # Nuevo campo para la ubicación
    attendee_ids: Optional[List[uuid.UUID]] = None # Nuevo campo para IDs de asistentes registrados
    external_attendees: Optional[List[str]] = None # Nuevo campo para nombres de asistentes externos
    workspace_id: Optional[str] = None

class EventUpdateRequest(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    location: Optional[str] = None # Nuevo campo para la ubicación
    attendee_ids: Optional[List[uuid.UUID]] = None # Nuevo campo para IDs de asistentes registrados
    external_attendees: Optional[List[str]] = None # Nuevo campo para nombres de asistentes externos
    workspace_id: Optional[str] = None

@router.post("/add-event")
async def add_event_endpoint(
    event: EventRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session) # Inyectar la sesión de DB
):
    """Añade un nuevo evento a la agenda del usuario. Protegido por JWT."""
    success, message, new_event_instance = await schedule_event( # Renombrar new_event a new_event_instance para evitar conflicto
        account_id=current_account_id,
        summary=event.summary,
        description=event.description,
        event_date=event.event_date,
        event_time=event.event_time,
        location=event.location,
        attendee_ids=event.attendee_ids,
        external_attendees=event.external_attendees,
        workspace_id=event.workspace_id
    )
    if not success or not new_event_instance:
        raise HTTPException(status_code=400, detail=message or "Error desconocido al crear el evento.")

    # Recargar el evento con la relación 'attendees' cargada ansiosamente
    # para evitar DetachedInstanceError al llamar a to_dict()
    async with db as session:
        stmt = select(AgendaEvent).options(selectinload(AgendaEvent.attendees), selectinload(AgendaEvent.workspace)).where(AgendaEvent.id == new_event_instance.id)
        reloaded_event = (await session.execute(stmt)).scalars().first()

        if not reloaded_event:
            raise HTTPException(status_code=500, detail="Error al recargar el evento creado.")

        # Devolvemos el evento creado para añadirlo al estado del frontend
        # Asegurarse de pasar la zona horaria si to_dict la requiere
        account = await session.get(Account, uuid.UUID(current_account_id))
        return reloaded_event.to_dict(account.timezone) # Asumiendo que to_dict puede tomar timezone

async def _update_event_attendees(
    event: AgendaEvent,
    current_account_id: str,
    attendee_ids: Optional[List[uuid.UUID]],
    external_attendees: Optional[List[str]]
):
    # Lógica para attendee_ids
    if attendee_ids is not None:
        current_attendee_ids = {str(att.id) for att in event.attendees}
        
        to_add_attendee_ids = [str(aid) for aid in attendee_ids if str(aid) not in current_attendee_ids]
        to_remove_attendee_ids = [att_id for att_id in current_attendee_ids if att_id not in {str(aid) for aid in attendee_ids}]

        if to_add_attendee_ids:
            await add_attendees_to_event(current_account_id, event.id, attendee_ids=to_add_attendee_ids)
        if to_remove_attendee_ids:
            await remove_attendees_from_event(current_account_id, event.id, attendee_ids=to_remove_attendee_ids)

    # Lógica para external_attendees
    if external_attendees is not None:
        current_external_attendees = set(event.external_attendees if event.external_attendees else [])
        
        to_add_external_attendees = [att for att in external_attendees if att not in current_external_attendees]
        to_remove_external_attendees = [att for att in current_external_attendees if att not in external_attendees]

        if to_add_external_attendees:
            await add_attendees_to_event(current_account_id, event.id, external_attendees=to_add_external_attendees)
        if to_remove_external_attendees:
            await remove_attendees_from_event(current_account_id, event.id, external_attendees=to_remove_external_attendees)

@router.put("/agenda/events/{event_id}", summary="Actualizar un evento")
async def update_event_endpoint(
    event_id: int,
    event_update: EventUpdateRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza un evento existente.
    """
    async with db as session:
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.workspace), selectinload(AgendaEvent.attendees)).where(AgendaEvent.id == event_id)
        event = (await session.execute(event_stmt)).scalars().first()

        if not event or event.account_id != uuid.UUID(current_account_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado o no autorizado.")
        
        # Si el evento tiene un workspace_id, verificar permisos
        if event.workspace_id:
            if not await check_workspace_permission(current_account_id, str(event.workspace_id), session, required_roles=['owner', 'editor']):
                raise HTTPException(status_code=403, detail="No tienes permiso para actualizar este evento.")

        update_data = event_update.model_dump(exclude_unset=True)
        logger.info(f"[update_event_endpoint] update_data: {update_data}")
        
        # Manejar la actualización de asistentes por separado
        attendee_ids_to_update = update_data.pop("attendee_ids", None)
        external_attendees_to_update = update_data.pop("external_attendees", None)

        if attendee_ids_to_update is not None or external_attendees_to_update is not None:
            await _update_event_attendees(event, current_account_id, attendee_ids_to_update, external_attendees_to_update)

        if ('event_date' in update_data and update_data['event_date']) or ('event_time' in update_data and update_data['event_time']):
            account = await session.get(Account, uuid.UUID(current_account_id))
            if not account or not account.timezone:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo determinar la zona horaria del usuario.")
            
            user_tz = pytz.timezone(account.timezone)
            
            # Obtener la fecha/hora local actual del evento para usarla como base
            current_local_datetime = event.event_datetime_utc.astimezone(user_tz)
            
            # Usar los nuevos valores si se proporcionan, de lo contrario, mantener los actuales
            new_date_str = update_data.get('event_date', current_local_datetime.strftime('%Y-%m-%d'))
            new_time_str = update_data.get('event_time', current_local_datetime.strftime('%H:%M'))

            try:
                # Combinar fecha y hora en un string y parsear como datetime naive
                local_datetime_str = f"{new_date_str} {new_time_str}"
                naive_datetime = datetime.strptime(local_datetime_str, "%Y-%m-%d %H:%M")
                logger.info(f"[update_event_endpoint] Combined naive_datetime for update: {naive_datetime}")
                
                # Localizar el datetime naive con la zona horaria del usuario y luego convertir a UTC
                # Este método maneja correctamente los cambios de horario de verano (DST)
                localized_dt = user_tz.localize(naive_datetime)
                event_datetime_utc = localized_dt.astimezone(pytz.utc)
                logger.info(f"[update_event_endpoint] New event_datetime_utc: {event_datetime_utc}")

            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Formato de fecha u hora inválido: {new_date_str} {new_time_str}")
            
            event.event_datetime_utc = event_datetime_utc
            # Eliminar las claves para que no se procesen de nuevo en el bucle de abajo
            if 'event_date' in update_data:
                del update_data['event_date']
            if 'event_time' in update_data:
                del update_data['event_time']
        elif 'event_datetime' in update_data: # Mantener compatibilidad si se envía event_datetime (ej. desde el agente)
            account = await session.get(Account, uuid.UUID(current_account_id))
            user_tz = pytz.timezone(account.timezone)
            date_settings = {
                'TO_TIMEZONE': 'UTC', 
                'RETURN_AS_TIMEZONE_AWARE': True, 
                'RELATIVE_BASE': datetime.now(user_tz)
            }
            event_datetime_utc = dateparser.parse(
                update_data['event_datetime'], 
                settings=date_settings
            )
            if not event_datetime_utc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No se pudo interpretar la fecha y hora: {update_data['event_datetime']}")
            
            event.event_datetime_utc = event_datetime_utc
            del update_data['event_datetime']


        logger.info(f"[update_event_endpoint] Evento antes de la actualización: {event.description}, {event.event_datetime_utc}")



        for key, value in update_data.items():
            setattr(event, key, value)
        
        logger.info(f"[update_event_endpoint] Evento después de setattr: {event.description}, {event.event_datetime_utc}")

        try:
            await session.commit()
            await session.refresh(event)
            logger.info(f"[update_event_endpoint] Commit exitoso. Evento después del refresh: {event.description}, {event.event_datetime_utc}")
        except Exception as e:
            await session.rollback()
            logger.error(f"[update_event_endpoint] Error durante el commit: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al guardar los cambios en el evento.")
        
        account = await session.get(Account, uuid.UUID(current_account_id))
        return event.to_dict(account.timezone)

class EventCancelRequest(BaseModel):
    event_id: int
    workspace_id: Optional[str] = None

from api.schemas import ProfileLinkRequest

@router.post("/cancel-event")
async def cancel_event_endpoint(event: EventCancelRequest, current_account_id: str = Depends(get_current_account_id)):
    """Cancela un evento de la agenda del usuario. Protegido por JWT."""
    # Obtener el evento para verificar el workspace_id
    event_data = await get_event_by_id(current_account_id, event.event_id)
    if not event_data:
        raise HTTPException(status_code=404, detail="Evento no encontrado o no autorizado.")

    # Verificar permisos de workspace si el evento pertenece a uno
    if event_data.get("workspace_id"):
        async with DBSession(SessionLocal) as db:
                            if not await check_workspace_permission(current_account_id, event_data["workspace_id"], db, required_roles=['owner', 'editor']):
                                raise HTTPException(status_code=403, detail="No tienes permiso para cancelar este evento.")
    success, message = await cancel_event(current_account_id, event.event_id, workspace_id=event_data.get("workspace_id"))
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"message": message}

@router.post("/agenda/events/{event_id}/link-profile", summary="Vincular perfil a un evento")
async def link_profile_to_event_endpoint(
    event_id: int,
    profile_link_request: ProfileLinkRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Vincula un perfil de contacto a un evento.
    """
    # Obtener el evento para verificar el workspace_id
    event_data = await get_event_by_id(current_account_id, event_id)
    if not event_data:
        raise HTTPException(status_code=404, detail="Evento o perfil no encontrado, o no autorizado.")

    # Verificar permisos de workspace si el evento pertenece a uno
    if event_data.get("workspace_id"):
        async with DBSession(SessionLocal) as db:
            if not await check_workspace_permission(current_account_id, event_data["workspace_id"], db, required_roles=['owner', 'editor']):
                raise HTTPException(status_code=403, detail="No tienes permiso para vincular perfiles a este evento.")
    from core.agenda_manager import link_profile_to_event # Explicit import
    success = await link_profile_to_event(
        account_id=current_account_id,
        event_id=event_id,
        profile_id=profile_link_request.profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Evento o perfil no encontrado, o no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} vinculado al evento {event_id} correctamente."}

@router.post("/agenda/events/{event_id}/unlink-profile", summary="Desvincular perfil de un evento")
async def unlink_profile_from_event_endpoint(
    event_id: int,
    profile_link_request: ProfileLinkRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Desvincula un perfil de contacto de un evento.
    """
    # Obtener el evento para verificar el workspace_id
    event_data = await get_event_by_id(current_account_id, event_id)
    if not event_data:
        raise HTTPException(status_code=404, detail="Evento o perfil no encontrado, o no autorizado.")

    # Verificar permisos de workspace si el evento pertenece a uno
    if event_data.get("workspace_id"):
        async with DBSession(SessionLocal) as db:
            if not await check_workspace_permission(current_account_id, event_data["workspace_id"], db, required_roles=['owner', 'editor']):
                raise HTTPException(status_code=403, detail="No tienes permiso para desvincular perfiles de este evento.")

    from core.agenda_manager import unlink_profile_from_event # Explicit import
    success = await unlink_profile_from_event(
        account_id=current_account_id,
        event_id=event_id,
        profile_id=profile_link_request.profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado, o evento/perfil no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} desvinculado del evento {event_id} correctamente."}