# api/agenda.py

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, desc, update, or_

from core.database import SessionLocal, Account, TeamMember, AgendaEvent, Workspace, get_db_session
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.agenda_manager import get_events_as_dicts, schedule_event, cancel_event, link_profile_to_event, unlink_profile_from_event, get_event_by_id

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

@router.post("/list-events")  # Cambiado a POST
async def list_events_endpoint(current_account_id: str = Depends(get_current_account_id)):
    """Lista los eventos de la agenda del usuario, incluyendo eventos compartidos con equipos y workspaces."""
    account_uuid = uuid.UUID(current_account_id)
    
    # Obtener eventos personales
    personal_events = await get_events_as_dicts(current_account_id)
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
            team_id=team_id
        )
        logger.info(f"Team events for team {team_id} and account {current_account_id}: {len(team_events_for_id)} events found")
        team_events.extend(team_events_for_id)
    
    # Obtener eventos de workspaces
    workspace_events = []
    for workspace_id in workspace_ids:
        workspace_events_for_id = await get_events_as_dicts(
            account_id=current_account_id,
            workspace_id=workspace_id
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
    event_datetime: str  # "mañana a las 3pm"
    workspace_id: Optional[str] = None

class EventUpdateRequest(BaseModel):
    description: Optional[str] = None
    event_datetime: Optional[str] = None
    team_id: Optional[str] = None
    workspace_id: Optional[str] = None

@router.post("/add-event")
async def add_event_endpoint(event: EventRequest, current_account_id: str = Depends(get_current_account_id)):
    """Añade un nuevo evento a la agenda del usuario. Protegido por JWT."""
    success, message, new_event = await schedule_event(
        account_id=current_account_id,
        description=event.description,
        natural_language_datetime=event.event_datetime,
        workspace_id=event.workspace_id
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    # Devolvemos el evento creado para añadirlo al estado del frontend
    return new_event.to_dict() if new_event else {}

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
        event = await session.get(AgendaEvent, event_id)

        if not event or event.account_id != uuid.UUID(current_account_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado o no autorizado.")

        update_data = event_update.model_dump(exclude_unset=True)
        
        if 'event_datetime' in update_data and update_data['event_datetime']:
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
            
            update_data['event_datetime_utc'] = event_datetime_utc
            del update_data['event_datetime']


        for key, value in update_data.items():
            setattr(event, key, value)

        await session.commit()
        await session.refresh(event)
        
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
    success = await unlink_profile_from_event(
        account_id=current_account_id,
        event_id=event_id,
        profile_id=profile_link_request.profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado, o evento/perfil no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} desvinculado del evento {event_id} correctamente."}
