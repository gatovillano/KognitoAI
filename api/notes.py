# api/notes.py

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, desc, update, or_

from core.database import SessionLocal, Account, TeamMember, Nota
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.notes_manager import get_notes_as_dicts, add_note, update_note, delete_note

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncSession:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

class ListNotesRequest(BaseModel):
    search_term: Optional[str] = None

# --- ENDPOINT DE NOTAS ACTUALIZADO ---
# Cambiamos el nombre del endpoint para que sea más claro
@router.post("/list-notes")
async def list_notes_endpoint(
    request: ListNotesRequest,  # Usamos el modelo
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve las notas de un usuario como una lista de objetos JSON, incluyendo notas compartidas con equipos."""
    account_uuid = uuid.UUID(current_account_id)
    
    # Obtener notas personales
    personal_notes = await get_notes_as_dicts(
        account_id=current_account_id, 
        search_query=request.search_term
    )
    logger.info(f"Personal notes for account {current_account_id}: {len(personal_notes)} notes found")
    
    # Obtener equipos del usuario
    member_teams_result = await db.execute(
        select(TeamMember).where(TeamMember.account_id == account_uuid)
    )
    member_teams = member_teams_result.scalars().all()
    team_ids = [str(team.team_id) for team in member_teams]
    logger.info(f"Teams for account {current_account_id} (notes): {team_ids}")
    
    # Obtener notas de equipos
    team_notes = []
    for team_id in team_ids:
        team_notes_for_id = await get_notes_as_dicts(
            account_id=current_account_id,
            search_query=request.search_term,
            team_id=team_id
        )
        logger.info(f"Team notes for team {team_id} and account {current_account_id}: {len(team_notes_for_id)} notes found")
        team_notes.extend(team_notes_for_id)
    
    # Combinar notas personales y de equipos, eliminando duplicados por ID
    combined_notes = {note['id']: note for note in personal_notes + team_notes}.values()
    logger.info(f"Total combined notes for account {current_account_id}: {len(combined_notes)} notes")
    return list(combined_notes)

# --- MODELOS PYDANTIC PARA NOTAS ---
class NoteRequest(BaseModel):
    title: Optional[str] = None
    content: str
    category: Optional[str] = None

@router.post("/add-note")
async def add_note_endpoint(note: NoteRequest, current_account_id: str = Depends(get_current_account_id)):
    """Añade una nueva nota para el usuario. Protegido por JWT."""
    new_note = await add_note(current_account_id, note.title or "", note.content, note.category or "")
    # Devolvemos la nota creada para poder añadirla al estado del frontend sin re-fetchear
    return new_note 

class NoteUpdateRequest(NoteRequest):
    note_id: int

@router.post("/update-note")
async def update_note_endpoint(note: NoteUpdateRequest, current_account_id: str = Depends(get_current_account_id)):
    """Actualiza una nota existente del usuario. Protegido por JWT."""
    result_message = await update_note(current_account_id, note.note_id, note.title, note.content, note.category)
    return {"message": result_message}

class NoteDeleteRequest(BaseModel):
    note_id: int

@router.post("/delete-note")
async def delete_note_endpoint(note: NoteDeleteRequest, current_account_id: str = Depends(get_current_account_id)):
    """Elimina una nota del usuario. Protegido por JWT."""
    result_message = await delete_note(current_account_id, note.note_id)
    return {"message": result_message}

@router.post("/notes/{note_id}/unshare", summary="Eliminar compartición de una nota")
async def unshare_note(note_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Elimina la asociación de una nota con cualquier equipo, dejándola como no compartida.
    """
    logger.info(f"Eliminando compartición de nota {note_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    note_id_int = int(note_id)
    
    result = await db.execute(
        update(Nota)
        .where(Nota.account_id == account_uuid, Nota.id == note_id_int)
        .values(team_id=None)
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no pertenece al usuario.")
    
    await db.commit()
    return {"message": "Nota ya no está compartida con ningún equipo."}
