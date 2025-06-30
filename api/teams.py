# api/teams.py

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, Form
from pydantic import BaseModel
from sqlalchemy import select, desc, update, or_, text, func

from core.database import SessionLocal, Account, Team, TeamMember, Nota, AgendaEvent
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from utils.db_session import DBSession

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

# --- Modelos Pydantic para Equipos ---
class TeamCreateRequest(BaseModel):
    """Define la estructura de datos para crear un nuevo equipo."""
    name: str

class TeamUpdateRequest(BaseModel):
    """Define la estructura de datos para actualizar un equipo existente."""
    name: Optional[str] = None

class TeamShareRequest(BaseModel):
    """Define la estructura de datos para compartir recursos con un equipo."""
    documentIds: List[str] = []
    eventIds: List[int] = []
    noteIds: List[int] = []

class TeamResponse(BaseModel):
    """Define la estructura de datos para la respuesta de un equipo."""
    id: str
    name: str
    created_at: datetime

@router.get("/teams", response_model=List[TeamResponse], summary="Listar equipos del usuario")
async def list_teams(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los equipos de un usuario autenticado, incluyendo aquellos donde es administrador o miembro.
    """
    logger.info(f"Listando equipos para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    # Obtener equipos donde el usuario es administrador
    admin_teams_result = await db.execute(select(Team).where(Team.admin_id == account_uuid).order_by(Team.created_at.desc()))
    admin_teams = admin_teams_result.scalars().all()
    # Obtener equipos donde el usuario es miembro
    member_teams_result = await db.execute(
        select(Team)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.account_id == account_uuid)
        .order_by(Team.created_at.desc())
    )
    member_teams = member_teams_result.scalars().all()
    # Combinar y eliminar duplicados
    teams = list(set(admin_teams + member_teams))
    # Ordenar por fecha de creación descendente
    teams.sort(key=lambda x: x.created_at, reverse=True)
    return [TeamResponse(id=str(team.id), name=team.name, created_at=team.created_at) for team in teams]

@router.get("/teams/{team_id}", response_model=TeamResponse, summary="Obtener detalles de un equipo")
async def get_team(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Obtiene los detalles de un equipo específico si pertenece al usuario autenticado.
    """
    logger.info(f"Obteniendo detalles del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    return TeamResponse(id=str(team.id), name=team.name, created_at=team.created_at)

@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo equipo")
async def create_team(team: TeamCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Crea un nuevo equipo para el usuario autenticado.
    """
    logger.info(f"Creando nuevo equipo para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    new_team = Team(admin_id=account_uuid, name=team.name)
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)
    return TeamResponse(id=str(new_team.id), name=new_team.name, created_at=new_team.created_at)

@router.put("/teams/{team_id}", response_model=TeamResponse, summary="Actualizar un equipo existente")
async def update_team(team_id: str, team_update: TeamUpdateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Actualiza un equipo existente si pertenece al usuario autenticado.
    """
    logger.info(f"Actualizando equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    if team_update.name:
        team.name = team_update.name
    await db.commit()
    await db.refresh(team)
    return TeamResponse(id=str(team.id), name=team.name, created_at=team.created_at)

@router.post("/teams/{team_id}/share/documents", summary="Compartir documentos con un equipo")
async def share_documents_with_team(team_id: str, share_request: TeamShareRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte documentos con un equipo específico.
    """
    logger.info(f"Compartiendo documentos con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    
    updated_count = 0
    # Importar las tablas necesarias de memory_manager
    from core.memory_manager import langchain_pg_embedding, langchain_pg_collection

    async with DBSession(SessionLocal) as db_session:
        # Obtener el UUID de la colección del usuario
        collection_uuid_query = select(langchain_pg_collection.c.uuid).where(
            langchain_pg_collection.c.name == f"user_memories_{current_account_id}"
        )
        collection_result = await db_session.execute(collection_uuid_query)
        collection_uuid = collection_result.scalar_one_or_none()

        if not collection_uuid:
            logger.warning(f"No se encontró la colección de memoria para la cuenta {current_account_id}. No se pueden compartir documentos.")
            raise HTTPException(status_code=404, detail="Colección de memoria del usuario no encontrada.")

        for file_name in share_request.documentIds:
            # 1. Obtener el cmetadata actual de los chunks del documento
            #    Necesitamos hacer esto para no sobrescribir otros metadatos existentes.
            select_stmt = select(langchain_pg_embedding.c.cmetadata).where(
                langchain_pg_embedding.c.collection_id == collection_uuid,
                langchain_pg_embedding.c.cmetadata['file_name'].astext == file_name,
                langchain_pg_embedding.c.cmetadata['type'].astext == 'document_chunk'
            ).limit(1)  # Solo necesitamos un chunk para obtener la estructura de metadatos

            cmetadata_result = await db_session.execute(select_stmt)
            current_cmetadata = cmetadata_result.scalar_one_or_none()

            if not current_cmetadata:
                logger.warning(f"No se encontraron chunks para el documento '{file_name}' en la colección personal de {current_account_id}. No se puede compartir.")
                continue

            # 2. Actualizar el cmetadata para incluir el team_id
            updated_cmetadata = current_cmetadata.copy()
            updated_cmetadata['team_id'] = str(team_uuid)  # Asegurarse de que sea string

            # 3. Ejecutar la actualización en todos los chunks de ese documento
            result = await db_session.execute(
                update(langchain_pg_embedding)
                .where(
                    langchain_pg_embedding.c.collection_id == collection_uuid,
                    langchain_pg_embedding.c.cmetadata['file_name'].astext == file_name,
                    langchain_pg_embedding.c.cmetadata['type'].astext == 'document_chunk'
                )
                .values(cmetadata=updated_cmetadata)
            )
            if result.rowcount > 0:
                updated_count += result.rowcount
                logger.info(f"Documento '{file_name}' compartido con equipo {team_id}, actualizadas {result.rowcount} entradas.")
            else:
                logger.warning(f"No se actualizaron entradas para el documento '{file_name}' con account_id {current_account_id}.")
        
        await db_session.commit()
        if updated_count == 0:
            logger.warning(f"No se compartieron documentos con el equipo {team_id} para la cuenta {current_account_id}.")
            return {"message": "No se encontraron documentos para compartir o ya estaban compartidos. Verifica los IDs de los documentos."}
        return {"message": f"{updated_count} documentos compartidos con equipo {team_id}"}

@router.post("/teams/{team_id}/share/events", summary="Compartir eventos con un equipo")
async def share_events_with_team(team_id: str, share_request: TeamShareRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte eventos con un equipo específico.
    """
    logger.info(f"Compartiendo eventos con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    
    updated_count = 0
    for event_id in share_request.eventIds:
        # Update AgendaEvent table to associate events with the team
        result = await db.execute(
            update(AgendaEvent)
            .where(AgendaEvent.account_id == account_uuid, AgendaEvent.id == event_id)
            .values(team_id=team_uuid)
        )
        if result.rowcount > 0:
            updated_count += result.rowcount
    
    await db.commit()
    return {"message": f"{updated_count} eventos compartidos con equipo {team_id}"}

@router.post("/teams/{team_id}/share/notes", summary="Compartir notas con un equipo")
async def share_notes_with_team(team_id: str, share_request: TeamShareRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte notas con un equipo específico.
    """
    logger.info(f"Compartiendo notas con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    
    updated_count = 0
    for note_id in share_request.noteIds:
        # Update Nota table to associate notes with the team
        result = await db.execute(
            update(Nota)
            .where(Nota.account_id == account_uuid, Nota.id == note_id)
            .values(team_id=team_uuid)
        )
        if result.rowcount > 0:
            updated_count += result.rowcount
    
    await db.commit()
    return {"message": f"{updated_count} notas compartidas con equipo {team_id}"}

# --- Endpoints para Gestión de Miembros de Equipo ---
class TeamMemberAddRequest(BaseModel):
    """Define la estructura de datos para añadir un miembro a un equipo."""
    account_id: str

class TeamMemberRemoveRequest(BaseModel):
    """Define la estructura de datos para eliminar un miembro de un equipo."""
    account_id: str

@router.post("/teams/{team_id}/members", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Añadir miembro a un equipo")
async def add_team_member(team_id: str, request: TeamMemberAddRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Añade un miembro a un equipo específico. Solo el administrador del equipo puede realizar esta acción.
    """
    logger.info(f"Añadiendo miembro al equipo {team_id} por la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para gestionar miembros.")
    
    member_uuid = uuid.UUID(request.account_id)
    # Verificar si el miembro ya está en el equipo
    existing_member = await db.scalar(select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == member_uuid))
    if existing_member:
        raise HTTPException(status_code=409, detail="El usuario ya es miembro de este equipo.")
    
    new_member = TeamMember(team_id=team_uuid, account_id=member_uuid)
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    return {"message": f"Miembro {request.account_id} añadido al equipo {team_id}"}

@router.delete("/teams/{team_id}/members", response_model=dict, summary="Eliminar miembro de un equipo")
async def remove_team_member(team_id: str, request: TeamMemberRemoveRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Elimina un miembro de un equipo específico. Solo el administrador del equipo puede realizar esta acción.
    """
    logger.info(f"Eliminando miembro del equipo {team_id} por la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para gestionar miembros.")
    
    member_uuid = uuid.UUID(request.account_id)
    member = await db.scalar(select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == member_uuid))
    if not member:
        raise HTTPException(status_code=404, detail="Miembro no encontrado en este equipo.")
    
    await db.delete(member)
    await db.commit()
    return {"message": f"Miembro {request.account_id} eliminado del equipo {team_id}"}

@router.get("/teams/{team_id}/members", response_model=List[dict], summary="Listar miembros de un equipo")
async def list_team_members(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los miembros de un equipo específico. Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando miembros del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver los miembros.")
    
    members_result = await db.execute(select(TeamMember).where(TeamMember.team_id == team_uuid))
    members = members_result.scalars().all()
    return [{"account_id": str(member.account_id), "joined_at": member.joined_at} for member in members]

@router.get("/teams/{team_id}/documents", response_model=List[dict], summary="Listar documentos compartidos con un equipo")
async def list_team_documents(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los documentos compartidos con un equipo específico. Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando documentos del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver los documentos.")
    
    # Importar las tablas necesarias de memory_manager
    from core.memory_manager import langchain_pg_embedding, langchain_pg_collection
    
    # Obtener el UUID de la colección del usuario
    collection_uuid_query = select(langchain_pg_collection.c.uuid).where(
        langchain_pg_collection.c.name == f"user_memories_{current_account_id}"
    )
    collection_result = await db.execute(collection_uuid_query)
    collection_uuid = collection_result.scalar_one_or_none()

    if not collection_uuid:
        logger.info(f"No se encontró la colección de memoria para la cuenta {current_account_id}. No hay documentos de equipo para listar.")
        return []

    # Consulta para obtener documentos de equipo desde langchain_pg_embedding
    # Filtrar por collection_id y por team_id en cmetadata
    document_list_query = select(
        langchain_pg_embedding.c.cmetadata['file_name'].astext.label('file_name'),
        langchain_pg_embedding.c.cmetadata['title'].astext.label('title'),
        func.now().label('shared_at')  # Usar created_at del embedding como shared_at
    ).where(
        langchain_pg_embedding.c.collection_id == collection_uuid,
        langchain_pg_embedding.c.cmetadata['type'].astext == 'document_chunk',
        langchain_pg_embedding.c.cmetadata['team_id'].astext == str(team_uuid)  # Filtrar por el team_id
    ).distinct(langchain_pg_embedding.c.cmetadata['file_name']).order_by(
        langchain_pg_embedding.c.cmetadata['file_name']
    )
    
    documents_result = await db.execute(document_list_query)
    documents = [dict(row) for row in documents_result.mappings()]
    
    logger.info(f"Listados {len(documents)} documentos compartidos con el equipo {team_id} para la cuenta: {current_account_id}")
    return documents

@router.get("/teams/{team_id}/notes", response_model=List[dict], summary="Listar notas compartidas con un equipo")
async def list_team_notes(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todas las notas compartidas con un equipo específico. Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando notas del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver las notas.")
    
    notes_result = await db.execute(select(Nota).where(Nota.team_id == team_uuid))
    notes = notes_result.scalars().all()
    return [{"id": note.id, "title": note.title, "updated_at": note.updated_at} for note in notes]

@router.get("/teams/{team_id}/shared-items", response_model=List[dict], summary="Listar todos los elementos compartidos con un equipo")
async def list_team_shared_items(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los elementos (documentos, eventos y notas) compartidos con un equipo específico.
    Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando elementos compartidos del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver los elementos compartidos.")
    
    # Obtener documentos compartidos con el equipo
    from core.memory_manager import langchain_pg_embedding, langchain_pg_collection
    collection_uuid_query = select(langchain_pg_collection.c.uuid).where(
        langchain_pg_collection.c.name == f"user_memories_{current_account_id}"
    )
    collection_result = await db.execute(collection_uuid_query)
    collection_uuid = collection_result.scalar_one_or_none()

    shared_documents = []
    if collection_uuid:
        document_list_query = select(
            langchain_pg_embedding.c.cmetadata['file_name'].astext.label('file_name'),
            langchain_pg_embedding.c.cmetadata['title'].astext.label('title'),
            func.now().label('shared_at')
        ).where(
            langchain_pg_embedding.c.collection_id == collection_uuid,
            langchain_pg_embedding.c.cmetadata['type'].astext == 'document_chunk',
            langchain_pg_embedding.c.cmetadata['team_id'].astext == str(team_uuid)
        ).distinct(text("file_name")).order_by(
            text("file_name"),
            langchain_pg_embedding.c.cmetadata['title'].astext
        )
        
        documents_result = await db.execute(document_list_query)
        shared_documents = [dict(row) for row in documents_result.mappings()]
        for doc in shared_documents:
            doc['type'] = 'document'
            doc['id'] = doc['file_name']  # Usamos file_name como ID para documentos
    
    # Obtener eventos compartidos con el equipo
    events_result = await db.execute(select(AgendaEvent).where(AgendaEvent.team_id == team_uuid))
    shared_events = events_result.scalars().all()
    events_list = [{"id": event.id, "description": event.description, "event_datetime": event.event_datetime, "type": 'event', "shared_at": event.created_at} for event in shared_events]
    
    # Obtener notas compartidas con el equipo
    notes_result = await db.execute(select(Nota).where(Nota.team_id == team_uuid))
    shared_notes = notes_result.scalars().all()
    notes_list = []
    for note in shared_notes:
        # Obtener información del usuario que compartió la nota
        account = await db.get(Account, note.account_id)
        shared_by = account.name if account and account.name else (account.email if account else "Usuario desconocido")
        notes_list.append({
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "type": 'note',
            "shared_at": note.updated_at or note.created_at,
            "shared_by": shared_by
        })
    
    # Obtener eventos compartidos con el equipo
    events_result = await db.execute(select(AgendaEvent).where(AgendaEvent.team_id == team_uuid))
    shared_events = events_result.scalars().all()
    events_list_updated = []
    for event in shared_events:
        # Obtener información del usuario que compartió el evento
        account = await db.get(Account, event.account_id)
        shared_by = account.name if account and account.name else (account.email if account else "Usuario desconocido")
        events_list_updated.append({
            "id": event.id,
            "description": event.description,
            "event_datetime": event.event_datetime,
            "type": 'event',
            "shared_at": event.created_at,
            "shared_by": shared_by
        })
    
    # Obtener documentos compartidos con el equipo (ya procesado anteriormente)
    for doc in shared_documents:
        # Obtener el account_id del propietario del documento desde la base de datos
        if collection_uuid:
            chunk_query = select(
                langchain_pg_embedding.c.cmetadata['account_id'].astext.label('account_id')
            ).where(
                langchain_pg_embedding.c.collection_id == collection_uuid,
                langchain_pg_embedding.c.cmetadata['file_name'].astext == doc['file_name'],
                langchain_pg_embedding.c.cmetadata['type'].astext == 'document_chunk'
            ).limit(1)
            
            chunk_result = await db.execute(chunk_query)
            account_id = chunk_result.scalar_one_or_none()
            
            if account_id:
                account = await db.get(Account, uuid.UUID(account_id))
                doc['shared_by'] = account.name if account and account.name else (account.email if account else "Usuario desconocido")
            else:
                doc['shared_by'] = "Usuario desconocido"
        else:
            doc['shared_by'] = "Usuario desconocido"
    
    # Combinar todos los elementos compartidos
    combined_items = shared_documents + events_list_updated + notes_list
    logger.info(f"Total de elementos compartidos con el equipo {team_id}: {len(combined_items)}")
    return combined_items

class SharedItemUpdateRequest(BaseModel):
    """Define la estructura de datos para actualizar un elemento compartido."""
    itemId: str
    type: str
    title: Optional[str] = None
    content: Optional[str] = None

@router.post("/teams/{team_id}/shared-items/update", response_model=dict, summary="Actualizar un elemento compartido")
async def update_shared_item(team_id: str, request: SharedItemUpdateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Actualiza un elemento compartido (nota o documento) con un equipo específico.
    Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Actualizando elemento compartido {request.itemId} de tipo {request.type} en el equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para actualizar elementos compartidos.")
    
    if request.type == 'note':
        item_id_int = int(request.itemId)
        # Verificar que la nota está compartida con el equipo
        note = await db.scalar(select(Nota).where(Nota.id == item_id_int, Nota.team_id == team_uuid))
        if not note:
            raise HTTPException(status_code=404, detail="Nota no encontrada o no está compartida con este equipo.")
        
        # Actualizar la nota
        update_data = {}
        if request.title is not None:
            update_data['title'] = request.title
        if request.content is not None:
            update_data['content'] = request.content
        
        if update_data:
            result = await db.execute(
                update(Nota)
                .where(Nota.id == item_id_int)
                .values(**update_data)
            )
            if result.rowcount > 0:
                await db.commit()
                return {"message": f"Nota {request.itemId} actualizada con éxito en el equipo {team_id}"}
            else:
                raise HTTPException(status_code=500, detail="Error al actualizar la nota.")
        else:
            return {"message": "No se proporcionaron datos para actualizar la nota."}
    else:
        raise HTTPException(status_code=400, detail="Tipo de elemento no soportado para actualización.")
