# api/teams.py

import logging
import uuid
from datetime import datetime
from typing import List, Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, update, text

from core.database import SessionLocal, Account, Team, TeamMember, Nota, AgendaEvent
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from utils.db_session import DBSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:  # type: ignore
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

class TeamShareCollectionRequest(BaseModel):
    """Define la estructura de datos para compartir una colección completa con un equipo."""
    collection_topic: str

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
    all_teams = list(admin_teams) + list(member_teams)
    teams = list({team.id: team for team in all_teams}.values())  # Remove duplicates by id
    # Ordenar por fecha de creación descendente
    teams.sort(key=lambda x: getattr(x, 'created_at'), reverse=True)
    return [TeamResponse(
        id=str(getattr(team, 'id')),
        name=str(getattr(team, 'name')),
        created_at=getattr(team, 'created_at')
    ) for team in teams]

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
    return TeamResponse(
        id=str(getattr(team, 'id')),
        name=str(getattr(team, 'name')),
        created_at=getattr(team, 'created_at')
    )

@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo equipo")
async def create_team(team: TeamCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Crea un nuevo equipo para el usuario autenticado.
    """
    logger.info(f"Creando nuevo equipo para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)

    new_team = Team(admin_id=account_uuid, name=str(team.name))
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)
    return TeamResponse(
        id=str(getattr(new_team, 'id')),
        name=str(getattr(new_team, 'name')),
        created_at=getattr(new_team, 'created_at')
    )

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
        setattr(team, 'name', team_update.name)
    await db.commit()
    await db.refresh(team)
    return TeamResponse(
        id=str(getattr(team, 'id')),
        name=str(getattr(team, 'name')),
        created_at=getattr(team, 'created_at')
    )

@router.post("/teams/{team_id}/share/documents", summary="Compartir documentos con un equipo")
async def share_documents_with_team(team_id: str, share_request: TeamShareRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte documentos con un equipo específico.
    """
    logger.info(f"Compartiendo documentos con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)

    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para compartir con este equipo.")
    
    updated_count = 0
    # Importar las tablas necesarias de memory_manager
    from sqlalchemy import text

    async with DBSession(SessionLocal) as db_session:
        for file_name in share_request.documentIds:
            # 1. Verificar que el documento existe para esta cuenta
            check_sql = text("""
                SELECT COUNT(*)
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND content_type = 'user_documents'
                  AND cmetadata->>'file_name' = :file_name
                  AND cmetadata->>'type' = 'document_chunk'
            """)

            check_result = await db_session.execute(check_sql, {
                "account_id": current_account_id,
                "file_name": file_name
            })
            document_count = check_result.scalar_one_or_none()

            if not document_count or document_count == 0:
                logger.warning(f"No se encontraron chunks para el documento '{file_name}' para la cuenta {current_account_id}. No se puede compartir.")
                continue

            # 2. Actualizar solo la columna team_id directamente (no en cmetadata)
            update_sql = text("""
                UPDATE langchain_pg_embedding
                SET team_id = :team_id
                WHERE account_id = :account_id
                  AND content_type = 'user_documents'
                  AND cmetadata->>'file_name' = :file_name
                  AND cmetadata->>'type' = 'document_chunk'
            """)

            result = await db_session.execute(update_sql, {
                "team_id": str(team_uuid),
                "account_id": current_account_id,
                "file_name": file_name
            })

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

    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para compartir con este equipo.")
    
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

    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para compartir con este equipo.")
    
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

@router.post("/teams/{team_id}/share/collections", summary="Compartir una colección completa con un equipo")
async def share_collection_with_team(team_id: str, share_request: TeamShareCollectionRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte una colección completa (todos sus documentos) con un equipo específico.
    """
    logger.info(f"Compartiendo colección '{share_request.collection_topic}' con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)

    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para compartir con este equipo.")

    try:
        # Actualizar todos los documentos de la colección para asociarlos con el equipo
        # Usar las columnas optimizadas directamente
        update_query = text("""
            UPDATE langchain_pg_embedding
            SET team_id = :team_id,
                cmetadata = jsonb_set(cmetadata, '{team_shared}', 'true')
            WHERE account_id = :account_id
            AND topic = :collection_topic
            AND cmetadata->>'type' = 'document_chunk'
        """)

        result = await db.execute(update_query, {
            "team_id": str(team_uuid),
            "account_id": current_account_id,
            "collection_topic": share_request.collection_topic
        })

        # También actualizar en UserDocumentTopic si existe
        from core.database import UserDocumentTopic
        from sqlalchemy import update

        await db.execute(
            update(UserDocumentTopic)
            .where(
                UserDocumentTopic.account_id == account_uuid,
                UserDocumentTopic.name == share_request.collection_topic
            )
            .values(team_id=team_uuid)
        )

        await db.commit()

        documents_updated = getattr(result, 'rowcount', 0)
        logger.info(f"✅ Se compartieron {documents_updated} documentos de la colección '{share_request.collection_topic}' con el equipo {team_id}")

        return {"message": f"Colección '{share_request.collection_topic}' compartida con equipo {team_id}. {documents_updated} documentos actualizados."}

    except Exception as e:
        logger.error(f"❌ Error compartiendo colección '{share_request.collection_topic}' con equipo {team_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al compartir la colección con el equipo.")

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
    
    # Consulta optimizada para obtener documentos de equipo usando las nuevas columnas directamente
    document_list_query = text("""
        SELECT DISTINCT ON (cmetadata->>'file_name')
               cmetadata->>'file_name' AS file_name,
               cmetadata->>'title' AS title
        FROM langchain_pg_embedding
        WHERE account_id = :account_id
          AND content_type = 'user_documents'
          AND cmetadata->>'type' = 'document_chunk'
          AND team_id = :team_id
        ORDER BY cmetadata->>'file_name', id
    """)

    documents_result = await db.execute(document_list_query, {
        "account_id": current_account_id,
        "team_id": str(team_uuid)
    })
    documents = [dict(row) for row in documents_result.mappings()]

    # Agregar timestamp a cada documento
    for doc in documents:
        doc['shared_at'] = datetime.now()
    
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

@router.get("/teams/{team_id}/collections", response_model=List[dict], summary="Listar colecciones compartidas con un equipo")
async def list_team_collections(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todas las colecciones compartidas con un equipo específico.
    Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando colecciones del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)

    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver las colecciones compartidas.")

    # Obtener colecciones compartidas con el equipo usando las columnas optimizadas
    collections_query = text("""
        SELECT DISTINCT topic,
               COUNT(*) as document_count,
               MIN(account_id) as account_id
        FROM langchain_pg_embedding
        WHERE team_id = :team_id
          AND cmetadata->>'type' = 'document_chunk'
          AND topic IS NOT NULL
        GROUP BY topic
        ORDER BY topic
    """)

    collections_result = await db.execute(collections_query, {"team_id": str(team_uuid)})
    shared_collections = [dict(row) for row in collections_result.mappings()]

    # Añadir información de quién compartió cada colección
    for collection in shared_collections:
        if collection.get('account_id'):
            try:
                account = await db.get(Account, uuid.UUID(collection['account_id']))
                collection['shared_by'] = getattr(account, 'name', None) if account and getattr(account, 'name', None) else (getattr(account, 'email', None) if account else "Usuario desconocido")
            except Exception:
                collection['shared_by'] = "Usuario desconocido"
        else:
            collection['shared_by'] = "Usuario desconocido"

        # Añadir metadatos adicionales
        collection['type'] = 'collection'
        collection['id'] = collection['topic']
        collection['name'] = collection['topic']
        collection['title'] = collection['topic']

    logger.info(f"Total de colecciones compartidas con el equipo {team_id}: {len(shared_collections)}")
    return shared_collections

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
    
    # Obtener documentos compartidos con el equipo usando las columnas optimizadas

    # Consulta optimizada usando team_id directamente con SQL directo para evitar problemas con DISTINCT ON
    document_list_query = text("""
        SELECT DISTINCT ON (cmetadata->>'file_name')
               cmetadata->>'file_name' AS file_name,
               cmetadata->>'title' AS title,
               topic AS topic,
               account_id AS account_id
        FROM langchain_pg_embedding
        WHERE team_id = :team_id
          AND cmetadata->>'type' = 'document_chunk'
        ORDER BY cmetadata->>'file_name', id
    """)

    documents_result = await db.execute(document_list_query, {"team_id": str(team_uuid)})
    shared_documents = [dict(row) for row in documents_result.mappings()]
    for doc in shared_documents:
        doc['type'] = 'document'
        doc['id'] = doc['file_name']  # Usamos file_name como ID para documentos
        doc['shared_at'] = datetime.now()  # Añadir timestamp
    
    # Obtener eventos compartidos con el equipo
    events_result = await db.execute(select(AgendaEvent).where(AgendaEvent.team_id == team_uuid))
    shared_events = events_result.scalars().all()

    
    # Obtener notas compartidas con el equipo
    notes_result = await db.execute(select(Nota).where(Nota.team_id == team_uuid))
    shared_notes = notes_result.scalars().all()
    notes_list = []
    for note in shared_notes:
        # Obtener información del usuario que compartió la nota
        account = await db.get(Account, note.account_id)
        shared_by = getattr(account, 'name', None) if account and getattr(account, 'name', None) else (getattr(account, 'email', None) if account else "Usuario desconocido")
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
        shared_by = getattr(account, 'name', None) if account and getattr(account, 'name', None) else (getattr(account, 'email', None) if account else "Usuario desconocido")
        events_list_updated.append({
            "id": event.id,
            "description": event.description,
            "event_datetime": event.event_datetime,
            "type": 'event',
            "shared_at": event.created_at,
            "shared_by": shared_by
        })
    
    # Añadir información de quién compartió cada documento
    for doc in shared_documents:
        if doc.get('account_id'):
            try:
                account = await db.get(Account, uuid.UUID(doc['account_id']))
                doc['shared_by'] = getattr(account, 'name', None) if account and getattr(account, 'name', None) else (getattr(account, 'email', None) if account else "Usuario desconocido")
            except Exception:
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
