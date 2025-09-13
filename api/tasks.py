# api/tasks.py

import logging
import uuid
from datetime import datetime
from typing import List, Optional, AsyncGenerator
import uuid

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal, Task # Importar SessionLocal y el modelo Task
from core.tasks_manager import TasksManager # Importar el TasksManager
from utils.security import get_current_account_id # Para obtener el account_id del usuario autenticado

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Dependencias de FastAPI ---

async def get_db() -> AsyncSession:
    """Crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        yield session

def get_tasks_manager(db: AsyncSession = Depends(get_db)) -> TasksManager:
    """Inyecta una instancia del gestor de tareas."""
    return TasksManager(db)

# --- Modelos Pydantic para la API ---

class TaskResponse(BaseModel):
    """Define la estructura de datos para la respuesta de una tarea."""
    id: str # Revertido a str
    description: str
    is_completed: bool
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    account_id: str # Revertido a str
    workspace_id: Optional[str] = None # Revertido a Optional[str]
    team_id: Optional[str] = None # Revertido a Optional[str]

    class Config:
        from_attributes = True # Habilita compatibilidad con ORM de SQLAlchemy

class TaskCreateRequest(BaseModel):
    """Define la estructura de datos para crear una nueva tarea."""
    description: str = Field(..., min_length=1, max_length=500)
    due_date: Optional[datetime] = None
    workspace_id: Optional[str] = None
    team_id: Optional[str] = None

class TaskUpdateRequest(BaseModel):
    """Define la estructura de datos para actualizar una tarea existente."""
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = None
    is_completed: Optional[bool] = None

class ProfileLinkRequest(BaseModel):
    profile_id: uuid.UUID

# --- Endpoints de la API ---

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Crear una nueva tarea")
async def create_task(
    request: TaskCreateRequest,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Crea una nueva tarea para el usuario autenticado.
    """
    try:
        new_task = await tasks_manager.add_task(
            account_id=current_account_id,
            description=request.description,
            due_date=request.due_date,
            workspace_id=request.workspace_id,
            team_id=request.team_id
        )
        return new_task
    except Exception as e:
        logger.error(f"Error al crear tarea para account {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear la tarea.")

@router.post("/tasks/{task_id}/link-profile", summary="Vincular perfil a una tarea")
async def link_profile_to_task_endpoint(
    task_id: str,
    profile_link_request: ProfileLinkRequest,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Vincula un perfil de contacto a una tarea.
    """
    success = await tasks_manager.link_profile_to_task(
        account_id=current_account_id,
        task_id=task_id,
        profile_id=profile_link_request.profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Tarea o perfil no encontrado, o no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} vinculado a la tarea {task_id} correctamente."}

@router.post("/tasks/{task_id}/unlink-profile", summary="Desvincular perfil de una tarea")
async def unlink_profile_from_task_endpoint(
    task_id: str,
    profile_link_request: ProfileLinkRequest,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Desvincula un perfil de contacto de una tarea.
    """
    success = await tasks_manager.unlink_profile_from_task(
        account_id=current_account_id,
        task_id=task_id,
        profile_id=profile_link_request.profile_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado, o tarea/perfil no autorizado.")
    return {"message": f"Perfil {profile_link_request.profile_id} desvinculado de la tarea {task_id} correctamente."}

@router.get("/tasks", response_model=List[TaskResponse], summary="Listar tareas del usuario")
async def list_tasks(
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager),
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None,
    is_completed: Optional[bool] = None,
    search_term: Optional[str] = None
):
    """
    Lista las tareas del usuario autenticado, con opciones de filtrado.
    """
    try:
        tasks = await tasks_manager.list_tasks(
            account_id=current_account_id,
            workspace_id=workspace_id,
            team_id=team_id,
            is_completed=is_completed,
            search_term=search_term
        )
        return tasks
    except Exception as e:
        logger.error(f"Error al listar tareas para account {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al listar las tareas.")

@router.get("/tasks/{task_id}", response_model=TaskResponse, summary="Obtener una tarea por ID")
async def get_task(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Obtiene una tarea específica por su ID.
    """
    try:
        task = await tasks_manager.get_task_by_id(current_account_id, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada o no pertenece al usuario.")
        return task
    except Exception as e:
        logger.error(f"Error al obtener tarea {task_id} para account {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener la tarea.")

@router.put("/tasks/{task_id}", response_model=TaskResponse, summary="Actualizar una tarea existente")
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Actualiza una tarea existente del usuario autenticado.
    """
    try:
        updated_task = await tasks_manager.update_task(
            account_id=current_account_id,
            task_id=task_id,
            description=request.description,
            due_date=request.due_date,
            is_completed=request.is_completed
        )
        if not updated_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada o no pertenece al usuario.")
        return updated_task
    except Exception as e:
        logger.error(f"Error al actualizar tarea {task_id} para account {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar la tarea.")

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una tarea")
async def delete_task(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Elimina una tarea del usuario autenticado.
    """
    try:
        success = await tasks_manager.delete_task(current_account_id, task_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada o no pertenece al usuario.")
        return
    except Exception as e:
        logger.error(f"Error al eliminar tarea {task_id} para account {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar la tarea.")