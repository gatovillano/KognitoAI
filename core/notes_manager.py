# core/notes_manager.py

import logging
from typing import Any, Optional, List, Dict
import uuid

from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import Nota, TeamMember, ContactProfile, Workspace, NoteContactProfileAssociation, WorkspacePermission
from utils.embeddings import get_embedding_model
from utils.security import check_workspace_permission # Importar check_workspace_permission

logger = logging.getLogger(__name__)

class NotesManager:
    """Gestiona la lógica de negocio relacionada con las notas."""
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_note(self, account_id: str, title: Optional[str], content: str, category: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Añade una nueva nota a la base de datos para una cuenta o workspace.
        """
        logger.info(f"Añadiendo nueva nota para la cuenta {account_id} con título '{title}'")
        effective_category = category if category and category.strip() else "General"

        embeddings_model = get_embedding_model()
        note_embedding = None
        if embeddings_model:
            try:
                note_embedding = await embeddings_model.aembed_query(content)
            except Exception as e:
                logger.error(f"Error generando embedding para la nota: {e}", exc_info=True)

        new_note = Nota(
            account_id=uuid.UUID(account_id),
            title=title,
            content=content,
            category=effective_category,
            embedding=note_embedding,
            workspace_id=uuid.UUID(workspace_id) if workspace_id else None
        )
        self.db.add(new_note)
        await self.db.commit()
        await self.db.refresh(new_note)
        logger.info(f"Nota '{title}' añadida exitosamente con ID {new_note.id}.")

        return {
            "id": new_note.id,
            "title": new_note.title,
            "content": new_note.content,
            "category": new_note.category,
            "created_at": new_note.created_at.isoformat(),
            "workspace_id": str(new_note.workspace_id) if new_note.workspace_id else None,
        }

    async def get_notes_as_dicts(self, account_id: str, search_query: Optional[str] = None, workspace_id: Optional[str] = None, category: Optional[str] = None, skip: int = 0, limit: int = 10) -> tuple[int, List[Dict[str, Any]]]:
        """
        Recupera notas como una lista de diccionarios, incluyendo perfiles vinculados, con paginación.
        Devuelve una tupla (total_notas, lista_de_notas_paginadas).
        """
        logger.info(f"get_notes_as_dicts called for account_id: {account_id}, workspace_id: {workspace_id}, skip: {skip}, limit: {limit}")
        
        base_stmt = select(Nota).where(Nota.account_id == uuid.UUID(account_id))
        
        if workspace_id:
            # Si se especifica un workspace, verificar permisos
            try:
                await check_workspace_permission(account_id, workspace_id, self.db, required_roles=['admin', 'owner', 'member', 'viewer'])
            except Exception as e:
                logger.warning(f"Permission denied for account {account_id} on workspace {workspace_id}: {e}")
                # Si no tiene permiso, no devolver ninguna nota de ese workspace
                return 0, []
            base_stmt = base_stmt.where(Nota.workspace_id == uuid.UUID(workspace_id))
        else:
            # Si no se especifica un workspace, obtener notas personales y de todos los workspaces a los que tiene acceso
            accessible_workspaces_stmt = select(WorkspacePermission.workspace_id).where(WorkspacePermission.account_id == uuid.UUID(account_id))
            result = await self.db.execute(accessible_workspaces_stmt)
            accessible_workspace_ids = [row[0] for row in result.fetchall()]
            
            base_stmt = base_stmt.where(
                or_(
                    Nota.workspace_id.is_(None),
                    Nota.workspace_id.in_(accessible_workspace_ids)
                )
            )
            
        if search_query:
            base_stmt = base_stmt.where(Nota.title.ilike(f"%{search_query}%") | Nota.content.ilike(f"%{search_query}%"))

        if category:
            base_stmt = base_stmt.where(Nota.category.ilike(f"%{category}%"))
        
        # Contar el total de notas sin paginación
        total_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self.db.execute(total_stmt)
        total_notes = total_result.scalar_one()

        # Obtener notas paginadas
        paginated_stmt = base_stmt.options(selectinload(Nota.contact_profiles), selectinload(Nota.workspace)).order_by(Nota.created_at.desc()).offset(skip).limit(limit)
        
        logger.info(f"SQL statement for paginated notes: {paginated_stmt}")
        result = await self.db.execute(paginated_stmt)
        notes = result.scalars().all()
        logger.info(f"Found {len(notes)} paginated notes for account {account_id} with specified filters.")

        formatted_notes = [
            {
                "id": note.id, "title": note.title, "content": note.content,
                "category": note.category, "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
                "workspace_id": str(note.workspace_id) if note.workspace_id else None,
                "workspace_name": note.workspace.name if note.workspace else None,
                "workspace_color": note.workspace.color if note.workspace else None,
                "linked_profiles": [{
                    "id": str(cp.id),
                    "account_id": str(cp.account_id),
                    "name": cp.name,
                    "email": cp.email,
                    "phone": cp.phone,
                    "created_at": cp.created_at.isoformat(),
                    "updated_at": cp.updated_at.isoformat(),
                } for cp in note.contact_profiles]
            } for note in notes
        ]
        return total_notes, formatted_notes

    async def list_all_notes(self, account_id: str, search_query: Optional[str] = None, category: Optional[str] = None, skip: int = 0, limit: int = 10) -> tuple[int, List[Dict[str, Any]]]:
        """
        Devuelve todas las notas de un usuario, incluyendo personales y de workspaces, con paginación.
        """
        logger.info(f"Listando todas las notas para la cuenta {account_id}, skip: {skip}, limit: {limit}")
        
        # Ahora get_notes_as_dicts puede manejar la lógica de obtener todas las notas si no se especifica workspace_id
        total, notes = await self.get_notes_as_dicts(
            account_id=account_id,
            search_query=search_query,
            category=category,
            skip=skip,
            limit=limit
        )
        return total, notes

    async def update_note(self, account_id: str, note_id: int, new_title: Optional[str] = None, new_content: Optional[str] = None, new_category: Optional[str] = None, new_workspace_id: Optional[str] = None) -> bool:
        """
        Actualiza una nota existente. Devuelve True si fue exitoso, False en caso contrario.
        """
        stmt = select(Nota).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        note_to_update = (await self.db.execute(stmt)).scalars().first()

        if not note_to_update:
            logger.warning(f"Nota {note_id} no encontrada para la cuenta {account_id}.")
            return False
        
        # Verificar permisos de workspace si la nota pertenece a uno
        if note_to_update.workspace_id:
            if not await check_workspace_permission(account_id, str(note_to_update.workspace_id), self.db, required_roles=['admin', 'owner', 'member']):
                logger.warning(f"Acceso denegado para actualizar la nota {note_id} en workspace {note_to_update.workspace_id} para la cuenta {account_id}.")
                return False

        update_data = {}
        content_changed = False
        if new_title is not None:
            update_data['title'] = new_title
        if new_content is not None and note_to_update.content != new_content:
            update_data['content'] = new_content
            content_changed = True
        if new_category is not None:
            update_data['category'] = new_category
        if new_workspace_id is not None:
            update_data['workspace_id'] = uuid.UUID(new_workspace_id) if new_workspace_id else None

        if content_changed:
            embeddings_model = get_embedding_model()
            if embeddings_model:
                try:
                    embedding = await embeddings_model.aembed_query(new_content)
                    if embedding:
                        update_data['embedding'] = embedding
                except Exception as e:
                    logger.error(f"Error al actualizar embedding para la nota {note_id}: {e}", exc_info=True)
        
        if update_data:
            await self.db.execute(
                update(Nota)
                .where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
                .values(**update_data)
            )
            await self.db.commit()
        logger.info(f"Nota {note_id} actualizada para la cuenta {account_id}.")
        return True

    async def delete_note(self, account_id: str, note_id: int) -> bool:
        """
        Elimina una nota. Devuelve True si fue exitoso, False en caso contrario.
        """
        stmt = select(Nota).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        note_to_delete = (await self.db.execute(stmt)).scalars().first()
        
        if not note_to_delete:
            logger.warning(f"Nota {note_id} no encontrada para eliminar para la cuenta {account_id}.")
            return False
        
        # Verificar permisos de workspace si la nota pertenece a uno
        if note_to_delete.workspace_id:
            if not await check_workspace_permission(account_id, str(note_to_delete.workspace_id), self.db, required_roles=['admin', 'owner', 'member']):
                logger.warning(f"Acceso denegado para eliminar la nota {note_id} en workspace {note_to_delete.workspace_id} para la cuenta {account_id}.")
                return False
            
        await self.db.delete(note_to_delete)
        await self.db.commit()
        logger.info(f"Nota {note_id} eliminada para la cuenta {account_id}.")
        return True

    async def link_profile_to_note(self, account_id: str, note_id: int, profile_id: uuid.UUID) -> bool: # CAMBIO: profile_id ahora es uuid.UUID
        """
        Vincula un perfil a una nota existente.
        """
        logger.info(f"Intentando vincular perfil {profile_id} a la nota {note_id} para la cuenta {account_id}")
        
        # Verificar que la nota existe y pertenece al usuario
        note_stmt = select(Nota).options(selectinload(Nota.contact_profiles)).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        note = (await self.db.execute(note_stmt)).scalars().first()
        if not note:
            logger.warning(f"Nota {note_id} no encontrada o no pertenece a la cuenta {account_id}.")
            return False
        
        # Verificar permisos de workspace si la nota pertenece a uno
        if note.workspace_id:
            if not await check_workspace_permission(account_id, str(note.workspace_id), self.db, required_roles=['admin', 'owner', 'member']):
                logger.warning(f"Acceso denegado para vincular perfil a la nota {note_id} en workspace {note.workspace_id} para la cuenta {account_id}.")
                return False

        # Verificar que el perfil existe y pertenece al usuario
        profile_stmt = select(ContactProfile).where(ContactProfile.id == profile_id, ContactProfile.account_id == uuid.UUID(account_id)) # CAMBIO: Se usa profile_id directamente
        profile = (await self.db.execute(profile_stmt)).scalars().first()
        if not profile:
            logger.warning(f"Perfil {profile_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return False

        # Verificar si el vínculo ya existe
        if profile in note.contact_profiles:
            logger.info(f"El vínculo entre la nota {note_id} y el perfil {profile_id} ya existe.")
            return True # Ya está vinculado, consideramos éxito

        # Crear el nuevo vínculo
        note.contact_profiles.append(profile)
        await self.db.commit()
        await self.db.refresh(note)
        logger.info(f"Perfil {profile_id} vinculado exitosamente a la nota {note_id}.")
        return True

    async def unlink_profile_from_note(self, account_id: str, note_id: int, profile_id: uuid.UUID) -> bool: # CAMBIO: profile_id ahora es uuid.UUID
        """
        Desvincula un perfil de una nota existente.
        """
        logger.info(f"Intentando desvincular perfil {profile_id} de la nota {note_id} para la cuenta {account_id}")

        # Verificar que la nota existe y pertenece al usuario
        note_stmt = select(Nota).options(selectinload(Nota.contact_profiles)).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        note = (await self.db.execute(note_stmt)).scalars().first()
        if not note:
            logger.warning(f"Nota {note_id} no encontrada o no pertenece a la cuenta {account_id}.")
            return False
        
        # Verificar permisos de workspace si la nota pertenece a uno
        if note.workspace_id:
            if not await check_workspace_permission(account_id, str(note.workspace_id), self.db, required_roles=['admin', 'owner', 'member']):
                logger.warning(f"Acceso denegado para desvincular perfil de la nota {note_id} en workspace {note.workspace_id} para la cuenta {account_id}.")
                return False

        # Eliminar el vínculo
        # Necesitamos obtener el objeto ContactProfile para poder removerlo de la lista
        profile_to_remove_stmt = select(ContactProfile).where(ContactProfile.id == profile_id, ContactProfile.account_id == uuid.UUID(account_id)) # CAMBIO: Se usa profile_id directamente
        profile_to_remove = (await self.db.execute(profile_to_remove_stmt)).scalars().first()

        if profile_to_remove and profile_to_remove in note.contact_profiles:
            note.contact_profiles.remove(profile_to_remove)
            await self.db.commit()
            logger.info(f"Perfil {profile_id} desvinculado exitosamente de la nota {note_id}.")
            return True
        else:
            logger.warning(f"El vínculo entre la nota {note_id} y el perfil {profile_id} no fue encontrado para desvincular o el perfil no existe/no pertenece al usuario.")
            return False

    async def get_note_by_id(self, account_id: str, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera una nota específica por su ID, incluyendo perfiles vinculados.
        """
        logger.info(f"Consultando nota {note_id} para la cuenta {account_id}.")
        
        stmt = select(Nota).options(selectinload(Nota.contact_profiles), selectinload(Nota.workspace)).where(
            Nota.id == note_id,
            Nota.account_id == uuid.UUID(account_id)
        )
        result = await self.db.execute(stmt)
        note = result.scalars().first()

        if not note:
            logger.warning(f"Nota {note_id} no encontrada o no pertenece a la cuenta {account_id}.")
            return None
        
        # Verificar permisos de workspace si la nota pertenece a uno
        if note.workspace_id:
            if not await check_workspace_permission(account_id, str(note.workspace_id), self.db, required_roles=['admin', 'owner', 'member', 'viewer']):
                logger.warning(f"Acceso denegado a la nota {note_id} en workspace {note.workspace_id} para la cuenta {account_id}.")
                return None
        
        linked_profiles_data = []
        for cp in note.contact_profiles:
            linked_profiles_data.append({
                "id": str(cp.id),
                "account_id": str(cp.account_id), # Añadido
                "name": cp.name,
                "email": cp.email,
                "phone": cp.phone,
                "created_at": cp.created_at.isoformat(), # Añadido
                "updated_at": cp.updated_at.isoformat(), # Añadido
            })

        return {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "category": note.category,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "workspace_id": str(note.workspace_id) if note.workspace_id else None,
            "linked_profiles": linked_profiles_data
        }
