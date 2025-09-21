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

from core.database import SessionLocal, Account, TeamMember, AgendaEvent, Workspace, get_db_session, ContactProfile # Import ContactProfile model
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload # Import selectinload
from core.agenda_manager import schedule_event, cancel_event, get_event_by_id # Import schedule_event, cancel_event, get_event_by_id

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

@router.post("/list-events")
async def list_events_endpoint(request: ListEventsRequest, current_account_id: str = Depends(get_current_account_id)):
    """Lista los eventos de la agenda del usuario, incluyendo eventos compartidos con equipos y workspaces."""
    account_uuid = uuid.UUID(current_account_id)
    
    # Importar get_events_as_dicts aquí para asegurar que esté disponible
    from core.agenda_manager import get_events_as_dicts

    # Obtener eventos personales
    personal_events = await get_events_as_dicts(current_account_id, include_past=request.include_past)
    logger.info(f"Personal events for account {current_account_id}: {len(personal_events)} events found")
    
    # Obtener equipos del usuario
    async with DBSession(SessionLocal) as db:
        member_teams_result = await db.execute(
            select(TeamMember).where(TeamMember.account_id == account_uuid)
        )
        member_teams = member_teams_result.scalars().all()
        team_ids = [str(team.team_id) for team in member_teams]
        logger.info(f"Teams for account {current_account_id} (events): {team_ids})")

        # Obtener workspaces del usuario
        workspaces_result = await db.execute(
            select(Workspace).where(Workspace.account_id == account_uuid)
        )
        workspaces = workspaces_result.scalars().all()
        workspace_ids = [str(ws.id) for ws in workspaces]
        logger.info(f"Workspaces for account {current_account_id} (events): {workspace_ids})")
    
    # Obtener eventos de equipos
    team_events = []
    for team_id in team_ids:
        team_events_for_id = await get_events_as_dicts(
            account_id=current_account_id,
            team_id=team_id,
            include_past=request.include_past
        )
        logger.info(f"Team events for team {team_id} and account {current_account_id}: {len(team_events_for_id)} events found")
        team_events.extend(team_events_for_id)
    
    # Obtener eventos de workspaces
    workspace_events = []
    for workspace_id in workspace_ids:
        workspace_events_for_id = await get_events_as_dicts(
            account_id=current_account_id,
            workspace_id=workspace_id,
            include_past=request.include_past
        )
        logger.info(f"Workspace events for workspace {workspace_id} and account {current_account_id}: {len(workspace_events_for_id)} events found")
        workspace_events.extend(workspace_events_for_id)
    
    # Combinar eventos personales, de equipos y de workspaces, eliminando duplicados por ID
    combined_events = {event['id']: event for event in personal_events + team_events + workspace_events}.values()
    logger.info(f"Total combined events for account {current_account_id}: {len(combined_events)} events")
    return list(combined_events)

# --- MODELOS PYDANTIC PARA AGENDA ---
class EventRequest(BaseModel):
    description: str
    event_date: str  # Fecha en formato YYYY-MM-DD
    event_time: str  # Hora en formato HH:MM
    workspace_id: Optional[str] = None

class EventUpdateRequest(BaseModel):
    description: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    team_id: Optional[str] = None
    workspace_id: Optional[str] = None

@router.post("/add-event")
async def add_event_endpoint(event: EventRequest, current_account_id: str = Depends(get_current_account_id)):
    """Añade un nuevo evento a la agenda del usuario. Protegido por JWT."""
    success, message, new_event = await schedule_event(
        account_id=current_account_id,
        description=event.description,
        event_date=event.event_date, # Pasar fecha por separado
        event_time=event.event_time, # Pasar hora por separado
        workspace_id=event.workspace_id
    )
    if not success or not new_event:
        raise HTTPException(status_code=400, detail=message or "Error desconocido al crear el evento.")
    # Devolvemos el evento creado para añadirlo al estado del frontend
    return new_event.to_dict()

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
        event_stmt = select(AgendaEvent).options(selectinload(AgendaEvent.workspace)).where(AgendaEvent.id == event_id)
        event = (await session.execute(event_stmt)).scalars().first()

        if not event or event.account_id != uuid.UUID(current_account_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado o no autorizado.")

        update_data = event_update.model_dump(exclude_unset=True)
        logger.info(f"[update_event_endpoint] update_data: {update_data}")
        
        if ('event_date' in update_data and update_data['event_date']) and ('event_time' in update_data and update_data['event_time']):
            account = await session.get(Account, uuid.UUID(current_account_id))
            if not account or not account.timezone:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo determinar la zona horaria del usuario.")
            
            user_tz = pytz.timezone(account.timezone)
            
            try:
                # Combinar fecha y hora en un string y parsear como datetime naive
                local_datetime_str = f"{update_data['event_date']} {update_data['event_time']}"
                naive_datetime = datetime.strptime(local_datetime_str, "%Y-%m-%d %H:%M")
                logger.info(f"[update_event_endpoint] naive_datetime: {naive_datetime}")
                
                # Obtener el offset actual de la zona horaria del usuario para la fecha/hora dada
                offset = user_tz.utcoffset(naive_datetime)
                logger.info(f"[update_event_endpoint] user_tz: {user_tz}, offset: {offset}")
                
                # Convertir la hora local naive a UTC restando el offset
                event_datetime_utc = naive_datetime - offset
                # Asegurarse de que sea un datetime aware en UTC
                event_datetime_utc = pytz.utc.localize(event_datetime_utc)
                logger.info(f"[update_event_endpoint] event_datetime_utc (antes de asignar): {event_datetime_utc}")

            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Formato de fecha u hora inválido: {update_data['event_date']} {update_data['event_time']}")
            
            event.event_datetime_utc = event_datetime_utc
            del update_data['event_date']
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

        # --- PRUEBA DE DIAGNÓSTICO: FORZAR ACTUALIZACIÓN DE DESCRIPCIÓN ---
        event.description = "TEST_UPDATE_DESCRIPTION"
        logger.info(f"[update_event_endpoint] Forzando descripción a: {event.description}")
        # ------------------------------------------------------------------

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

class ProfileLinkRequest(BaseModel):
    profile_id: uuid.UUID

@router.post("/cancel-event")
async def cancel_event_endpoint(event: EventCancelRequest, current_account_id: str = Depends(get_current_account_id)):
    """Cancela un evento de la agenda del usuario. Protegido por JWT."""
    success, message = await cancel_event(current_account_id, event.event_id, workspace_id=event.workspace_id)
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
    from core.agenda_manager import unlink_profile_from_event # Explicit import
    success = await unlink_profile_from_event(
        account_id=current_account_id,
        event_id=event_id,
        profile_id=profile_link_request.profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado, o evento/perfil no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} desvinculado del evento {event_id} correctamente."}