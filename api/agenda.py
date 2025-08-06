# api/agenda.py

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, desc, update, or_

from core.database import SessionLocal, Account, TeamMember, AgendaEvent
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.agenda_manager import get_events_as_dicts, schedule_event, cancel_event

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

from utils.db_session import DBSession

@router.post("/list-events")  # Cambiado a POST
async def list_events_endpoint(current_account_id: str = Depends(get_current_account_id)):
    """Lista los eventos de la agenda del usuario, incluyendo eventos compartidos con equipos. Protegido por JWT."""
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
    
    # Obtener eventos de equipos
    team_events = []
    for team_id in team_ids:
        team_events_for_id = await get_events_as_dicts(
            account_id=current_account_id,
            team_id=team_id
        )
        logger.info(f"Team events for team {team_id} and account {current_account_id}: {len(team_events_for_id)} events found")
        team_events.extend(team_events_for_id)
    
    # Combinar eventos personales y de equipos, eliminando duplicados por ID
    combined_events = {event['id']: event for event in personal_events + team_events}.values()
    logger.info(f"Total combined events for account {current_account_id}: {len(combined_events)} events")
    return list(combined_events)

# --- MODELOS PYDANTIC PARA AGENDA ---
class EventRequest(BaseModel):
    description: str
    event_datetime: str  # "mañana a las 3pm"

@router.post("/add-event")
async def add_event_endpoint(event: EventRequest, current_account_id: str = Depends(get_current_account_id)):
    """Añade un nuevo evento a la agenda del usuario. Protegido por JWT."""
    success, message, new_event = await schedule_event(
        account_id=current_account_id,
        description=event.description,
        natural_language_datetime=event.event_datetime
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    # Devolvemos el evento creado para añadirlo al estado del frontend
    return new_event.to_dict() if new_event else {}

class EventCancelRequest(BaseModel):
    event_id: int

@router.post("/cancel-event")
async def cancel_event_endpoint(event: EventCancelRequest, current_account_id: str = Depends(get_current_account_id)):
    """Cancela un evento de la agenda del usuario. Protegido por JWT."""
    success, message = await cancel_event(current_account_id, event.event_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"message": message}
