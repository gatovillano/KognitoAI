# core/tasks_manager.py

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import Task, Account, Workspace, ContactProfile # Importar los modelos necesarios
from utils.db_session import DBSession # Para manejar la sesión de la base de datos

logger = logging.getLogger(__name__)

from core.database import SessionLocal, Task, Account, Workspace, ContactProfile # Importar los modelos necesarios
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
            "start_date": task.start_date.isoformat() if task.start_date else None, # Nuevo campo
            "end_date": task.end_date.isoformat() if task.end_date else None, # Nuevo campo
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "account_id": str(task.account_id),
            "workspace_id": str(task.workspace_id) if task.workspace_id else None,
            "linked_profiles": linked_profiles_data
        }

    async def create_task( # Renombrado de add_task a create_task
        self,
        account_id: str,
        description: str,
        due_date: Optional[datetime] = None,
        start_date: Optional[datetime] = None, # Nuevo campo
        end_date: Optional[datetime] = None, # Nuevo campo
        is_completed: Optional[bool] = False, # Añadido para consistencia con CalDAV
        workspace_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> Task: # Devolver el objeto Task directamente para ScheduleEvent
        """
        Añade una nueva tarea a la base de datos.
        """
        new_task = Task(
            id=task_id, # Usar el ID proporcionado o dejar que la base de datos lo genere
            account_id=uuid.UUID(account_id),
            description=description,
            due_date=due_date,
            start_date=start_date, # Nuevo campo
            end_date=end_date, # Nuevo campo
            is_completed=is_completed,
            workspace_id=uuid.UUID(workspace_id) if workspace_id else None
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
        return loaded_task # Devolver el objeto Task

    async def list_tasks(
        self,
        account_id: str,
        workspace_id: Optional[str] = None,
        is_completed: Optional[bool] = None,
        status: Optional[str] = None,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista las tareas de un usuario, opcionalmente filtradas por workspace,
        estado de completado y término de búsqueda.
        """
        stmt = select(Task).options(selectinload(Task.contact_profiles)).where(Task.account_id == uuid.UUID(account_id))

        if workspace_id:
            stmt = stmt.where(Task.workspace_id == uuid.UUID(workspace_id))
        if is_completed is not None:
            stmt = stmt.where(Task.is_completed == is_completed)
        if status:
            stmt = stmt.where(Task.status == status)
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
        task_id: uuid.UUID, # Cambiado a uuid.UUID
        summary: Optional[str] = None, # Añadido summary para consistencia
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        start_date: Optional[datetime] = None, # Nuevo campo
        end_date: Optional[datetime] = None, # Nuevo campo
        is_completed: Optional[bool] = None,
        workspace_id: Optional[str] = None,
        status: Optional[str] = None,  # Añadido parámetro status
        linked_profiles: Optional[List[str]] = None,
    ) -> Optional[Task]: # Devolver el objeto Task
        """
        Actualiza una tarea existente.
        """
        stmt = select(Task).options(selectinload(Task.contact_profiles)).where(
            Task.id == task_id, # Usar task_id como uuid.UUID
            Task.account_id == uuid.UUID(account_id)
        )
        result = await self.db_session.execute(stmt)
        task = result.scalars().first()

        if not task:
            logger.warning(f"Tarea {task_id} no encontrada o no pertenece a account {account_id}.")
            return None

        if summary is not None:
            task.summary = summary
        if description is not None:
            task.description = description
        if due_date is not None:
            task.due_date = due_date
        if start_date is not None: # Nuevo campo
            task.start_date = start_date
        if end_date is not None: # Nuevo campo
            task.end_date = end_date
        if is_completed is not None:
            task.is_completed = is_completed
        if workspace_id is not None:
            task.workspace_id = uuid.UUID(workspace_id) if workspace_id else None
        if status is not None:
            task.status = status
        
        # Lógica para linked_profiles
        if linked_profiles is not None:
            current_profile_uuids = {cp.id for cp in task.contact_profiles}
            new_profile_uuids = {uuid.UUID(pid) for pid in linked_profiles}

            to_add_uuids = new_profile_uuids - current_profile_uuids
            to_remove_uuids = current_profile_uuids - new_profile_uuids

            if to_add_uuids:
                new_profiles = await self.db_session.execute(select(ContactProfile).where(ContactProfile.id.in_(list(to_add_uuids))))
                task.contact_profiles.extend(new_profiles.scalars().all())
            
            if to_remove_uuids:
                task.contact_profiles = [cp for cp in task.contact_profiles if cp.id not in to_remove_uuids]
        
        try:
            await self.db_session.commit()
            await self.db_session.refresh(task)
            return task
        except Exception as e:
            logger.error(f"Error al actualizar la tarea {task_id}: {e}", exc_info=True)
            await self.db_session.rollback()
            return None

    async def delete_task(self, account_id: str, task_id: uuid.UUID) -> bool: # Cambiado a uuid.UUID
        """
        Elimina una tarea.
        """
        stmt = select(Task).where(
            Task.id == task_id, # Usar task_id como uuid.UUID
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

    async def get_task_by_id(self, account_id: str, task_id: uuid.UUID) -> Optional[Task]: # Cambiado a uuid.UUID, devuelve objeto Task
        """
        Obtiene una tarea por su ID.
        """
        stmt = select(Task).options(selectinload(Task.contact_profiles)).where(
            Task.id == task_id, # Usar task_id como uuid.UUID
            Task.account_id == uuid.UUID(account_id)
        )
        result = await self.db_session.execute(stmt)
        task = result.scalars().first()
        return task
        
    async def get_tasks_as_dicts(self, account_id: str, include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        Recupera tareas de un usuario y las devuelve como una lista de diccionarios.
        Si include_completed es False (por defecto), solo recupera tareas no completadas.
        """
        async with DBSession(SessionLocal) as db:
            stmt = select(Task).options(selectinload(Task.contact_profiles)).where(
                Task.account_id == uuid.UUID(account_id)
            )
            if not include_completed:
                stmt = stmt.where(Task.is_completed == False)
            
            stmt = stmt.order_by(desc(Task.created_at))
            result = await db.execute(stmt)
            tasks = result.scalars().all()
            return [self._task_to_dict(task) for task in tasks]


    async def link_profile_to_task(self, account_id: str, task_id: uuid.UUID, profile_id: uuid.UUID) -> bool: # Cambiado a uuid.UUID
        """
        Vincula un perfil a una tarea existente.
        """
        logger.info(f"Intentando vincular perfil {profile_id} a la tarea {task_id} para la cuenta {account_id}")
        account_uuid = uuid.UUID(account_id)
        task_stmt = select(Task).options(selectinload(Task.contact_profiles)).where(Task.id == task_id, Task.account_id == account_uuid)
        task = (await self.db_session.execute(task_stmt)).scalars().first()
        if not task:
            logger.warning(f"Tarea {task_id} no encontrada o no pertenece a la cuenta {account_id}.")
            return False

        # Verificar que el perfil existe y pertenece al usuario
        profile_stmt = select(ContactProfile).where(ContactProfile.id == profile_id, ContactProfile.account_id == account_uuid)
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

    async def unlink_profile_from_task(self, account_id: str, task_id: uuid.UUID, profile_id: uuid.UUID) -> bool: # Cambiado a uuid.UUID
        """
        Desvincula un perfil de una tarea existente.
        """
        logger.info(f"Intentando desvincular perfil {profile_id} de la tarea {task_id} para la cuenta {account_id}")
        account_uuid = uuid.UUID(account_id)

        # Verificar que la tarea existe y pertenece al usuario
        task_stmt = select(Task).options(selectinload(Task.contact_profiles)).where(Task.id == task_id, Task.account_id == account_uuid)
        task = (await self.db_session.execute(task_stmt)).scalars().first()
        if not task:
            logger.warning(f"Tarea {task_id} no encontrada o no pertenece a la cuenta {account_id}.")
            return False

        # Eliminar el vínculo
        profile_to_remove_stmt = select(ContactProfile).where(ContactProfile.id == profile_id, ContactProfile.account_id == account_uuid)
        profile_to_remove = (await self.db_session.execute(profile_to_remove_stmt)).scalars().first()

        if profile_to_remove and profile_to_remove in task.contact_profiles:
            task.contact_profiles.remove(profile_to_remove)
            await self.db_session.commit()
            logger.info(f"Perfil {profile_id} desvinculado exitosamente de la tarea {task_id}.")
            return True
        else:
            logger.warning(f"El vínculo entre la tarea {task_id} y el perfil {profile_id} no fue encontrado para desvincular o el perfil no existe/no pertenece al usuario.")
            return False

# Funciones a nivel de módulo para ser usadas por la API
async def create_task(
    account_id: str,
    description: str,
    due_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None, # Nuevo campo
    end_date: Optional[datetime] = None, # Nuevo campo
    is_completed: Optional[bool] = False,
    workspace_id: Optional[str] = None,
    task_id: Optional[int] = None
) -> Tuple[bool, str, Task | None]:
    """Wrapper para TasksManager.create_task."""
    async with DBSession(SessionLocal) as db:
        manager = TasksManager(db)
        try:
            new_task = await manager.create_task(account_id, description, due_date, start_date, end_date, is_completed, workspace_id, task_id)
            return True, "Tarea creada exitosamente.", new_task
        except Exception as e:
            logger.error(f"Error al crear tarea: {e}", exc_info=True)
            return False, f"Error al crear tarea: {e}", None

async def get_task_by_id_db(account_id: str, task_id: str) -> Optional[Task]: # task_id como str para compatibilidad con CalDAV
    """Wrapper para TasksManager.get_task_by_id."""
    async with DBSession(SessionLocal) as db:
        manager = TasksManager(db)
        try:
            # Convertir task_id a UUID
            task_uuid = uuid.UUID(task_id)
            return await manager.get_task_by_id(account_id, task_uuid)
        except ValueError:
            logger.warning(f"ID de tarea inválido: {task_id}")
            return None

async def update_task_db(
    db_session: AsyncSession, # Recibe la sesión directamente para transacciones externas
    account_id: str,
    task_id: str, # task_id como str para compatibilidad con CalDAV
    summary: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None, # Nuevo campo
    end_date: Optional[datetime] = None, # Nuevo campo
    is_completed: Optional[bool] = None,
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,  # Añadido parámetro status
    linked_profiles: Optional[List[str]] = None,
) -> Optional[Task]:
    """Wrapper para TasksManager.update_task."""
    manager = TasksManager(db_session)
    try:
        # Convertir task_id a UUID
        task_uuid = uuid.UUID(task_id)
        return await manager.update_task(account_id, task_uuid, summary, description, due_date, start_date, end_date, is_completed, workspace_id, status, linked_profiles)
    except ValueError:
        logger.warning(f"ID de tarea inválido: {task_id}")
        return None

async def delete_task(account_id: str, task_id: str) -> Tuple[bool, str]: # task_id como str para compatibilidad con CalDAV
    """Wrapper para TasksManager.delete_task."""
    async with DBSession(SessionLocal) as db:
        manager = TasksManager(db)
        try:
            # Convertir task_id a UUID
            task_uuid = uuid.UUID(task_id)
            success = await manager.delete_task(account_id, task_uuid)
            if success:
                return True, "Tarea eliminada exitosamente."
            return False, "Tarea no encontrada o no se pudo eliminar."
        except ValueError:
            logger.warning(f"ID de tarea inválido: {task_id}")
            return False, "ID de tarea inválido."
        except Exception as e:
            logger.error(f"Error al eliminar tarea: {e}", exc_info=True)
            return False, f"Error al eliminar tarea: {e}"

async def get_tasks_as_dicts(account_id: str, include_completed: bool = False) -> List[Dict[str, Any]]:
    """Wrapper para TasksManager.get_tasks_as_dicts."""
    async with DBSession(SessionLocal) as db:
        manager = TasksManager(db)
        return await manager.get_tasks_as_dicts(account_id, include_completed)
