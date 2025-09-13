# api/notes.py

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal
from core.notes_manager import NotesManager
from utils.security import get_current_account_id
from api.contact_profiles import ContactProfileResponse # Importar ContactProfileResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# --- Dependencias de FastAPI ---

async def get_db() -> AsyncSession:
    """Crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        yield session

def get_notes_manager(db: AsyncSession = Depends(get_db)) -> NotesManager:
    """Inyecta una instancia del gestor de notas."""
    return NotesManager(db)

# --- Modelos Pydantic para la API ---

class ListNotesRequest(BaseModel):
    search_term: Optional[str] = None
    workspace_id: Optional[str] = None

class NoteRequest(BaseModel):
    title: Optional[str] = None
    content: str
    category: Optional[str] = None
    workspace_id: Optional[str] = None

class NoteUpdateRequest(BaseModel):
    note_id: int
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None

class NoteDeleteRequest(BaseModel):
    note_id: int

# Se mantiene ProfileLinkRequest por si se usa en otros endpoints o en el futuro.
# Si no se usa en ningún otro lugar, se podría eliminar.
class ProfileLinkRequest(BaseModel):
    profile_id: uuid.UUID

# --- Endpoints de la API ---

@router.get("/notes/{note_id}", summary="Obtener una nota por ID")
async def get_note_by_id_endpoint(
    note_id: int,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Obtiene una nota específica por su ID, incluyendo los perfiles de contacto vinculados.
    """
    note = await notes_manager.get_note_by_id(current_account_id, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")
    return note

@router.get("/notes/{note_id}/linked-profiles", response_model=List[ContactProfileResponse], summary="Obtener perfiles vinculados a una nota")
async def get_linked_profiles_for_note_endpoint(
    note_id: int,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Obtiene la lista de perfiles de contacto vinculados a una nota específica.
    """
    note = await notes_manager.get_note_by_id(current_account_id, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")
    
    return note["linked_profiles"]

@router.post("/list-notes")
async def list_notes_endpoint(
    request: ListNotesRequest,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """Devuelve todas las notas de un usuario, incluyendo personales y de equipos, o filtradas por workspace."""
    if request.workspace_id:
        notes = await notes_manager.get_notes_as_dicts(current_account_id, request.search_term, workspace_id=request.workspace_id)
    else:
        notes = await notes_manager.list_all_notes(current_account_id, request.search_term)
    return notes

@router.post("/notes/{note_id}/link-profile/{profile_id}", summary="Vincular perfil a una nota") # CAMBIO EN LA RUTA
async def link_profile_to_note_endpoint(
    note_id: int,
    profile_id: uuid.UUID, # CAMBIO: Ahora profile_id es un path parameter
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Vincula un perfil de contacto a una nota.
    """
    success = await notes_manager.link_profile_to_note(
        account_id=current_account_id,
        note_id=note_id,
        profile_id=profile_id # CAMBIO: Se pasa directamente el profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Nota o perfil no encontrado, o no autorizado.")
    return {"message": f"Perfil {profile_id} vinculado a la nota {note_id} correctamente."}

@router.post("/notes/{note_id}/unlink-profile", summary="Desvincular perfil de una nota")
async def unlink_profile_from_note_endpoint(
    note_id: int,
    profile_link_request: ProfileLinkRequest,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Desvincula un perfil de contacto de una nota.
    """
    success = await notes_manager.unlink_profile_from_note(
        account_id=current_account_id,\
        note_id=note_id,\
        profile_id=profile_link_request.profile_id\
    )
    if not success:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado, o nota/perfil no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} desvinculado de la nota {note_id} correctamente."}

@router.post("/add-note")
async def add_note_endpoint(
    note: NoteRequest,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """Añade una nueva nota para el usuario."""
    new_note = await notes_manager.add_note(
        account_id=current_account_id,\
        title=note.title or "",\
        content=note.content,\
        category=note.category or "",\
        workspace_id=note.workspace_id\
    )
    return new_note

@router.post("/update-note")
async def update_note_endpoint(
    note: NoteUpdateRequest,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """Actualiza una nota existente del usuario."""
    success = await notes_manager.update_note(
        account_id=current_account_id,\
        note_id=note.note_id,\
        new_title=note.title,\
        new_content=note.content,\
        new_category=note.category\
    )
    if not success:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no pertenece al usuario.")
    return {"message": f"Nota con ID {note.note_id} actualizada correctamente."}

@router.post("/delete-note")
async def delete_note_endpoint(
    note: NoteDeleteRequest,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """Elimina una nota del usuario."""
    success = await notes_manager.delete_note(current_account_id, note.note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no pertenece al usuario.")
    return {"message": f"Nota con ID {note.note_id} eliminada."}

@router.post("/notes/{note_id}/unshare", summary="Eliminar compartición de una nota")
async def unshare_note_endpoint(
    note_id: int,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Elimina la asociación de una nota con cualquier equipo.
    """
    success = await notes_manager.unshare_note(note_id, current_account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no pertenece al usuario.")
    return {"message": "Nota ya no está compartida con ningún equipo."}
