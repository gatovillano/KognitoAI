# api/tasks.py

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal, Task, ProactiveInsight # Importar modelos
from core.tasks_manager import TasksManager # Importar el TasksManager
from utils.security import get_current_account_id # Para obtener el account_id del usuario autenticado
from core.dependencies import get_db_session # Importar dependencia centralizada

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Dependencias de FastAPI ---

# get_db eliminado en favor de core.dependencies.get_db_session

def get_tasks_manager(db: AsyncSession = Depends(get_db_session)) -> TasksManager:
    """Inyecta una instancia del gestor de tareas."""
    return TasksManager(db)

# --- Modelos Pydantic para la API ---

class TaskResponse(BaseModel):
    """Define la estructura de datos para la respuesta de una tarea."""
    id: uuid.UUID
    description: str
    is_completed: bool
    start_date: Optional[datetime] = None # Nuevo campo
    end_date: Optional[datetime] = None # due_date ahora es end_date
    status: str  # Añadido el nuevo campo
    created_at: datetime
    updated_at: datetime
    account_id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }

class TaskCreateRequest(BaseModel):
    """Define la estructura de datos para crear una nueva tarea."""
    description: str = Field(..., min_length=1, max_length=2000)
    start_date: Optional[datetime] = None # Nuevo campo
    end_date: Optional[datetime] = None # due_date ahora es end_date
    workspace_id: Optional[str] = None

class TaskUpdateRequest(BaseModel):
    """Define la estructura de datos para actualizar una tarea existente."""
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    start_date: Optional[datetime] = None # Nuevo campo
    end_date: Optional[datetime] = None # due_date ahora es end_date
    is_completed: Optional[bool] = None
    status: Optional[str] = None  # Añadido campo status

class TaskCancelRequest(BaseModel):
    """Define la estructura de datos para cancelar una tarea del tablero de resolución."""
    justification: Optional[str] = None

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
        new_task = await tasks_manager.create_task(
            account_id=current_account_id,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
            workspace_id=request.workspace_id
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
    is_completed: Optional[bool] = None,
    status: Optional[str] = None,  # Nuevo parámetro de filtro
    search_term: Optional[str] = None
):
    """
    Lista las tareas del usuario autenticado, con opciones de filtrado.
    """
    try:
        tasks = await tasks_manager.list_tasks(
            account_id=current_account_id,
            workspace_id=workspace_id,
            is_completed=is_completed,
            status=status,  # Pasar el nuevo parámetro
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

    return task

@router.get("/tasks/{task_id}/linked-profiles", summary="Obtener perfiles vinculados a una tarea")
async def get_linked_profiles_to_task_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Obtiene la lista de perfiles de contacto vinculados a una tarea específica.
    """
    task = await tasks_manager.get_task_by_id(current_account_id, task_id) # Use manager to get task
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no autorizada.")
    
    # Serializar los perfiles de contacto vinculados a un formato JSON amigable
    return [
        {
            "id": str(profile.id),
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
        }
        for profile in task.contact_profiles
    ]

@router.put("/tasks/{task_id}", response_model=TaskResponse, summary="Actualizar una tarea existente")
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_account_id: str = Depends(get_current_account_id),
    tasks_manager: TasksManager = Depends(get_tasks_manager)
):
    """
    Actualiza una tarea existente para el usuario autenticado.
    """
    try:
        updated_task = await tasks_manager.update_task(
            account_id=current_account_id,
            task_id=task_id,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
            is_completed=request.is_completed,
            status=request.status  # Añadido parámetro status
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


@router.get("/resolution-board", summary="Obtener datos para el Tablero de Resolución")
async def get_resolution_board(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene todas las tareas y los insights/alertas del Tablero de Resolución.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)
        
        # 1. Obtener todas las tareas del Tablero de Resolución
        tasks_stmt = (
            select(Task)
            .where(
                Task.account_id == account_uuid,
                Task.description.like("[Tablero de Resolución]%")
            )
            .order_by(desc(Task.created_at))
        )
        tasks_result = await db.execute(tasks_stmt)
        board_tasks = tasks_result.scalars().all()
        
        # 2. Obtener insights proactivos tipo 'alert' o relacionados
        insights_stmt = (
            select(ProactiveInsight)
            .where(
                ProactiveInsight.account_id == account_uuid,
                or_(
                    ProactiveInsight.type == "alert",
                    ProactiveInsight.insight_message.like("%Tablero de Resolución%")
                )
            )
            .order_by(desc(ProactiveInsight.created_at))
        )
        insights_result = await db.execute(insights_stmt)
        board_insights = insights_result.scalars().all()
        
        return {
            "tasks": [
                {
                    "id": str(task.id),
                    "description": task.description,
                    "is_completed": task.is_completed,
                    "start_date": task.start_date.isoformat() if task.start_date else None,
                    "end_date": task.end_date.isoformat() if task.end_date else None,
                    "status": task.status,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "workspace_id": str(task.workspace_id) if task.workspace_id else None
                }
                for task in board_tasks
            ],
            "insights": [
                {
                    "id": insight.id,
                    "type": insight.type,
                    "title": insight.title,
                    "insight_message": insight.insight_message,
                    "confidence_score": insight.confidence_score,
                    "action_suggestion": insight.action_suggestion,
                    "created_at": insight.created_at.isoformat(),
                    "related_items": insight.related_items
                }
                for insight in board_insights
            ]
        }
    except Exception as e:
        logger.error(f"Error al obtener el Tablero de Resolución: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al cargar el Tablero de Resolución.")


@router.post("/tasks/{task_id}/postpone", summary="Postergación explícita de una tarea escalada")
async def postpone_task(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Extiende la fecha límite de la tarea 48 horas y restablece su estado a 'Pendiente'.
    """
    try:
        task_uuid = uuid.UUID(task_id)
        account_uuid = uuid.UUID(current_account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de tarea inválido.")
        
    task = await db.get(Task, task_uuid)
    if not task or task.account_id != account_uuid:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no autorizada.")
        
    # Extender plazo 48 horas y poner de vuelta en Pendiente
    task.end_date = datetime.now(task.end_date.tzinfo or None) + timedelta(hours=48)
    task.status = "Pendiente"
    task.updated_at = datetime.now()
    
    await db.commit()
    return {
        "message": "Tarea postergada por 48 horas.",
        "new_due_date": task.end_date.isoformat(),
        "status": task.status
    }


@router.post("/tasks/{task_id}/cancel", summary="Cancelación explícita de una tarea escalada")
async def cancel_task(
    task_id: str,
    request: Optional[TaskCancelRequest] = None,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cancela explícitamente la tarea del Tablero de Resolución, marcándola como completada y cancelada.
    """
    try:
        task_uuid = uuid.UUID(task_id)
        account_uuid = uuid.UUID(current_account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de tarea inválido.")
        
    task = await db.get(Task, task_uuid)
    if not task or task.account_id != account_uuid:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no autorizada.")
        
    # Cancelar la tarea y marcar como completada
    task.status = "Cancelada"
    task.is_completed = True
    if request and request.justification:
        task.description = f"{task.description} [Justificación: {request.justification}]"
    task.updated_at = datetime.now()
    
    await db.commit()
    return {
        "message": "Tarea cancelada explícitamente.",
        "status": task.status
    }
