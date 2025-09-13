# core/tasks_manager.py

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import Task, Account, Workspace, Team, ContactProfile # Importar los modelos necesarios
from utils.db_session import DBSession # Para manejar la sesión de la base de datos

logger = logging.getLogger(__name__)

class TasksManager:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convierte un objeto Task a un diccionario con UUIDs como strings, incluyendo perfiles vinculados."""
        linked_profiles_data = []
        for cp in task.contact_profiles:
            linked_profiles_data.append({
                "id": str(cp.id),
                "name": cp.name,
                "email": cp.email,
                "phone": cp.phone,
            })

        return {
            "id": str(task.id),
            "description": task.description,
            "is_completed": task.is_completed,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "account_id": str(task.account_id),
            "workspace_id": str(task.workspace_id) if task.workspace_id else None,
            "team_id": str(task.team_id) if task.team_id else None,
            "linked_profiles": linked_profiles_data
        }

    async def add_task(
        self,
        account_id: str,
        description: str,
        due_date: Optional[datetime] = None,
        workspace_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Añade una nueva tarea a la base de datos.
        """
        new_task = Task(
            account_id=uuid.UUID(account_id),
            description=description,
            due_date=due_date,
            workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
            team_id=uuid.UUID(team_id) if team_id else None
        )
        self.db_session.add(new_task)
        await self.db_session.commit()
        await self.db_session.refresh(new_task)

        # Cargar la tarea con los perfiles de contacto para evitar MissingGreenlet
        loaded_task_stmt = select(Task).options(selectinload(Task.contact_profiles)).where(Task.id == new_task.id)
        loaded_task_result = await self.db_session.execute(loaded_task_stmt)
        loaded_task = loaded_task_result.scalars().first()

        if not loaded_task:
            logger.error(f"Error: Tarea {new_task.id} no encontrada después de la creación y refresh.")
            raise Exception("Tarea no encontrada después de la creación.")

        logger.info(f"Tarea '{description}' añadida para account {account_id}.")
        return self._task_to_dict(loaded_task)

    async def list_tasks(
        self,
        account_id: str,
        workspace_id: Optional[str] = None,
        team_id: Optional[str] = None,
        is_completed: Optional[bool] = None,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista las tareas de un usuario, opcionalmente filtradas por workspace, equipo,
        estado de completado y término de búsqueda.
        """
        stmt = select(Task).options(selectinload(Task.contact_profiles)).where(Task.account_id == uuid.UUID(account_id))

        if workspace_id:
            stmt = stmt.where(Task.workspace_id == uuid.UUID(workspace_id))
        if team_id:
            stmt = stmt.where(Task.team_id == uuid.UUID(team_id))
        if is_completed is not None:
            stmt = stmt.where(Task.is_completed == is_completed)
        if search_term:
            stmt = stmt.where(Task.description.ilike(f"%{search_term}%"))

        stmt = stmt.order_by(desc(Task.created_at))

        result = await self.db_session.execute(stmt)
        tasks = result.scalars().all()
        logger.info(f"Listadas {len(tasks)} tareas para account {account_id}.")
        return [self._task_to_dict(task) for task in tasks]

    async def update_task(
        self,
        account_id: str,
        task_id: str,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        is_completed: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza una tarea existente.
        """
        stmt = select(Task).options(selectinload(Task.contact_profiles)).where(
            Task.id == uuid.UUID(task_id),
            Task.account_id == uuid.UUID(account_id)
        )
        result = await self.db_session.execute(stmt)
        task = result.scalars().first()

        if not task:
            logger.warning(f"Tarea {task_id} no encontrada o no pertenece a account {account_id}.")
            return None

        if description is not None:
            task.description = description
        if due_date is not None:
            task.due_date = due_date
        if is_completed is not None:
            task.is_completed = is_completed
        
        await self.db_session.commit()
        await self.db_session.refresh(task)
        logger.info(f"Tarea {task_id} actualizada para account {account_id}.")
        return self._task_to_dict(task)

    async def delete_task(self, account_id: str, task_id: str) -> bool:
        """
        Elimina una tarea.
        """
        stmt = select(Task).where(
            Task.id == uuid.UUID(task_id),
            Task.account_id == uuid.UUID(account_id)
        )
        result = await self.db_session.execute(stmt)
        task = result.scalars().first()

        if not task:
            logger.warning(f"Tarea {task_id} no encontrada o no pertenece a account {account_id}.")
            return False

        await self.db_session.delete(task)
        await self.db_session.commit()
        logger.info(f"Tarea {task_id} eliminada para account {account_id}.")
        return True

    async def get_task_by_id(self, account_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una tarea por su ID.
        """
        stmt = select(Task).options(selectinload(Task.contact_profiles)).where(
            Task.id == uuid.UUID(task_id),
            Task.account_id == uuid.UUID(account_id)
        )
        result = await self.db_session.execute(stmt)
        task = result.scalars().first()
        if task: 
            return self._task_to_dict(task)
        return None

    async def link_profile_to_task(self, account_id: str, task_id: str, profile_id: str) -> bool:
        """
        Vincula un perfil a una tarea existente.
        """
        logger.info(f"Intentando vincular perfil {profile_id} a la tarea {task_id} para la cuenta {account_id}")
        
        # Verificar que la tarea existe y pertenece al usuario
        task_stmt = select(Task).options(selectinload(Task.contact_profiles)).where(Task.id == uuid.UUID(task_id), Task.account_id == uuid.UUID(account_id))
        task = (await self.db_session.execute(task_stmt)).scalars().first()
        if not task:
            logger.warning(f"Tarea {task_id} no encontrada o no pertenece a la cuenta {account_id}.")
            return False

        # Verificar que el perfil existe y pertenece al usuario
        profile_stmt = select(ContactProfile).where(ContactProfile.id == uuid.UUID(profile_id), ContactProfile.account_id == uuid.UUID(account_id))
        profile = (await self.db_session.execute(profile_stmt)).scalars().first()
        if not profile:
            logger.warning(f"Perfil {profile_id} no encontrado o no pertenece a la cuenta {account_id}.")
            return False

        # Verificar si el vínculo ya existe
        if profile in task.contact_profiles:
            logger.info(f"El vínculo entre la tarea {task_id} y el perfil {profile_id} ya existe.")
            return True # Ya está vinculado, consideramos éxito

        # Crear el nuevo vínculo
        task.contact_profiles.append(profile)
        await self.db_session.commit()
        await self.db_session.refresh(task)
        logger.info(f"Perfil {profile_id} vinculado exitosamente a la tarea {task_id}.")
        return True

    async def unlink_profile_from_task(self, account_id: str, task_id: str, profile_id: str) -> bool:
        """
        Desvincula un perfil de una tarea existente.
        """
        logger.info(f"Intentando desvincular perfil {profile_id} de la tarea {task_id} para la cuenta {account_id}")

        # Verificar que la tarea existe y pertenece al usuario
        task_stmt = select(Task).options(selectinload(Task.contact_profiles)).where(Task.id == uuid.UUID(task_id), Task.account_id == uuid.UUID(account_id))
        task = (await self.db_session.execute(task_stmt)).scalars().first()
        if not task:
            logger.warning(f"Tarea {task_id} no encontrada o no pertenece a la cuenta {account_id}.")
            return False

        # Eliminar el vínculo
        profile_to_remove_stmt = select(ContactProfile).where(ContactProfile.id == uuid.UUID(profile_id), ContactProfile.account_id == uuid.UUID(account_id))
        profile_to_remove = (await self.db_session.execute(profile_to_remove_stmt)).scalars().first()

        if profile_to_remove and profile_to_remove in task.contact_profiles:
            task.contact_profiles.remove(profile_to_remove)
            await self.db_session.commit()
            logger.info(f"Perfil {profile_id} desvinculado exitosamente de la tarea {task_id}.")
            return True
        else:
            logger.warning(f"El vínculo entre la tarea {task_id} y el perfil {profile_id} no fue encontrado para desvincular o el perfil no existe/no pertenece al usuario.")
            return False