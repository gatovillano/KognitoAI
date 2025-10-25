# api/notes.py

import logging
from typing import List, Optional
import uuid
from datetime import datetime # Importar datetime
import io # Para manejar el PDF en memoria
import markdown # Para convertir Markdown a HTML
from weasyprint import HTML, CSS # Para generar PDF desde HTML

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse # Para devolver el PDF
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload # Import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

# Ya no necesitamos reportlab
# from reportlab.lib.pagesizes import letter
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
# from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.lib.units import inch

from core.database import SessionLocal
from core.notes_manager import NotesManager
from utils.security import get_current_account_id, check_workspace_permission
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
    skip: int = 0
    limit: int = 10

class NoteResponse(BaseModel):
    id: int
    title: Optional[str] # Modificado para ser opcional
    content: str
    category: Optional[str]
    created_at: datetime
    updated_at: datetime
    workspace_id: Optional[str]
    workspace_name: Optional[str] # Added
    workspace_color: Optional[str] # Added
    linked_profiles: List[ContactProfileResponse] = []

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
    workspace_id: Optional[str] = None

class NoteDeleteRequest(BaseModel):
    note_id: int

class PaginatedNotesResponse(BaseModel):
    total: int
    notes: List[NoteResponse]

# Se mantiene ProfileLinkRequest por si se usa en otros endpoints o en el futuro.
# Si no se usa en ningún otro lugar, se podría eliminar.
class ProfileLinkRequest(BaseModel):
    profile_id: uuid.UUID

class GeneratePdfRequest(BaseModel):
    note_id: int
    format: str = "markdown" # Por ahora solo soportamos markdown

# --- Endpoints de la API ---

@router.post("/notes/generate-pdf", summary="Generar PDF de una nota")
async def generate_note_pdf_endpoint(
    request: GeneratePdfRequest,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Genera un PDF a partir del contenido de una nota.
    """
    note_data = await notes_manager.get_note_by_id(current_account_id, request.note_id)
    if not note_data:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")

    # Verificar permisos de workspace si la nota pertenece a uno
    if note_data.get("workspace_id"):
        if not await check_workspace_permission(current_account_id, note_data["workspace_id"], notes_manager.db, required_roles=['admin', 'owner', 'member', 'viewer']):
            raise HTTPException(status_code=403, detail="No tienes permiso para generar PDF de esta nota.")

    buffer = io.BytesIO()

    # Convertir Markdown a HTML
    html_content = markdown.markdown(note_data["content"])

    # Convertir created_at a datetime si es una cadena y asegurar que siempre esté definida
    created_at_dt = note_data['created_at']
    if isinstance(created_at_dt, str):
        try:
            created_at_dt = datetime.fromisoformat(created_at_dt.replace('Z', '+00:00')) # Manejar formato ISO con Z
        except ValueError:
            # Si falla la conversión, se puede loggear o manejar de otra forma
            # En este caso, si no se puede parsear, created_at_dt seguirá siendo un string
            pass

    # Crear un HTML completo con estilos básicos
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{note_data.get("title", "Nota sin título")}</title>
        <style>
            body {{ font-family: sans-serif; margin: 1in; }}
            h1 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }}
            p {{ line-height: 1.5; }}
            pre {{ background-color: #f4f4f4; padding: 1em; border-radius: 5px; overflow-x: auto; }}
            code {{ font-family: monospace; }}
            .note-meta {{ font-size: 0.9em; color: #666; margin-top: 1em; border-top: 1px solid #eee; padding-top: 0.5em; }}
        </style>
    </head>
    <body>
        <h1>{note_data.get("title", "Nota sin título")}</h1>
        {html_content}
        <div class="note-meta">
            <p>Categoría: {note_data.get('category', 'N/A')}</p>
            <p>Creada el: {created_at_dt.strftime('%Y-%m-%d %H:%M:%S') if isinstance(created_at_dt, datetime) else str(created_at_dt)}</p>
        </div>
    </body>
    </html>
    """

    # Generar PDF usando WeasyPrint
    HTML(string=full_html).write_pdf(buffer)
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=\"{note_data.get('title', 'nota')}.pdf\""
    })

@router.get("/notes/{note_id}", response_model=NoteResponse, summary="Obtener una nota por ID")
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
    
    # Si la nota tiene un workspace_id, verificar permisos
    if note.get("workspace_id"):
        if not await check_workspace_permission(current_account_id, note["workspace_id"], notes_manager.db, required_roles=['admin', 'owner', 'member', 'viewer']):
            raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta nota.")
            
    return NoteResponse(**note)

@router.get("/notes/{note_id}/debug", summary="DEBUG: Obtener contenido crudo de una nota por ID")
async def debug_get_note_content_by_id_endpoint(
    note_id: int,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    DEBUG: Obtiene el contenido crudo de una nota específica por su ID, sin serialización Pydantic.
    Útil para verificar el contenido directamente de la base de datos.
    """
    note_data = await notes_manager.get_note_by_id(current_account_id, note_id)
    if not note_data:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")
    return {"id": note_data["id"], "title": note_data["title"], "content": note_data["content"], "category": note_data["category"], "workspace_id": note_data["workspace_id"]}

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
    
    # Si la nota tiene un workspace_id, verificar permisos
    if note.get("workspace_id"):
        if not await check_workspace_permission(current_account_id, note["workspace_id"], notes_manager.db, required_roles=['admin', 'owner', 'member', 'viewer']):
            raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta nota.")
            
    return note["linked_profiles"]

@router.post("/notes/list-notes", response_model=PaginatedNotesResponse, summary="Listar notas del usuario con paginación")
async def list_notes_endpoint(
    request: ListNotesRequest,
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Devuelve todas las notas de un usuario, incluyendo personales y de equipos, o filtradas por workspace, con paginación.
    """
    total, notes = await notes_manager.get_notes_as_dicts(current_account_id, request.search_term, workspace_id=request.workspace_id, skip=request.skip, limit=request.limit)
    
    return PaginatedNotesResponse(total=total, notes=[NoteResponse(**note) for note in notes])

@router.post("/notes/{note_id}/link-profile", summary="Vincular perfil a una nota") # CAMBIO EN LA RUTA
async def link_profile_to_note_endpoint(
    note_id: int,
    profile_link_request: ProfileLinkRequest, # CAMBIO: Ahora profile_id es un path parameter
    current_account_id: str = Depends(get_current_account_id),
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    """
    Vincula un perfil de contacto a una nota.
    """
    # Obtener la nota para verificar el workspace_id
    note_data = await notes_manager.get_note_by_id(current_account_id, note_id)
    if not note_data:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")

    # Verificar permisos de workspace si la nota pertenece a uno
    if note_data.get("workspace_id"):
                    if not await check_workspace_permission(current_account_id, note_data["workspace_id"], notes_manager.db, required_roles=['admin', 'owner', 'member']):
                        raise HTTPException(status_code=403, detail="No tienes permiso para vincular perfiles a esta nota.")
    success = await notes_manager.link_profile_to_note(
        account_id=current_account_id,
        note_id=note_id,
        profile_id=profile_link_request.profile_id # CAMBIO: Se pasa directamente el profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Nota o perfil no encontrado, o no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} vinculado a la nota {note_id} correctamente."}

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
    # Obtener la nota para verificar el workspace_id
    note_data = await notes_manager.get_note_by_id(current_account_id, note_id)
    if not note_data:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")

    # Verificar permisos de workspace si la nota pertenece a uno
    if note_data.get("workspace_id"):
        if not await check_workspace_permission(current_account_id, note_data["workspace_id"], notes_manager.db, required_roles=['admin', 'owner', 'member']):
            raise HTTPException(status_code=403, detail="No tienes permiso para desvincular perfiles de esta nota.")

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
    # Obtener la nota para verificar el workspace_id
    note_data = await notes_manager.get_note_by_id(current_account_id, note.note_id)
    if not note_data:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")

    # Verificar permisos de workspace si la nota pertenece a uno
    if note_data.get("workspace_id"):
        if not await check_workspace_permission(current_account_id, note_data["workspace_id"], notes_manager.db, required_roles=['admin', 'owner', 'member']):
            raise HTTPException(status_code=403, detail="No tienes permiso para actualizar esta nota.")

    success = await notes_manager.update_note(
        account_id=current_account_id,
        note_id=note.note_id,
        new_title=note.title,
        new_content=note.content,
        new_category=note.category,
        new_workspace_id=note.workspace_id
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
    # Obtener la nota para verificar el workspace_id
    note_data = await notes_manager.get_note_by_id(current_account_id, note.note_id)
    if not note_data:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")

    # Verificar permisos de workspace si la nota pertenece a uno
    if note_data.get("workspace_id"):
        if not await check_workspace_permission(current_account_id, note_data["workspace_id"], notes_manager.db, required_roles=['admin', 'owner', 'member']):
            raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta nota.")

    success = await notes_manager.delete_note(current_account_id, note.note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no pertenece al usuario.")
    return {"message": f"Nota con ID {note.note_id} eliminada."}
