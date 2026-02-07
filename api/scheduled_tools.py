# api/scheduled_tools.py

"""
API endpoints para administración de herramientas programadas.
Solo accesible para administradores.
"""

import logging
import uuid
from datetime import time, datetime
from typing import List, Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal, Account
from utils.security import get_current_account_id
from utils.tool_scheduler import tool_scheduler
from utils.scheduled_tools_manager import scheduled_tools_manager
from core.dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Dependencias ---

# get_db eliminado en favor de core.dependencies.get_db_session

# Dependencia para verificar si el usuario es administrador
async def get_current_admin_account(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)) -> Account:
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account or not bool(account.is_admin):  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador.")
    return account

# --- Modelos Pydantic ---

class ScheduledToolResponse(BaseModel):
    """Respuesta con información de una herramienta programada."""
    job_name: str
    tool_name: str
    schedule_type: str
    account_id: Optional[str] = None
    schedule_info: str
    next_run: Optional[str] = None
    is_active: bool

class CreateScheduledToolRequest(BaseModel):
    """Solicitud para crear una nueva herramienta programada."""
    tool_name: str = Field(description="Nombre de la herramienta (daily_analysis, daily_insights, weekly_cleanup)")
    schedule_type: str = Field(description="Tipo de programación (daily, weekly, interval)")
    hour: int = Field(ge=0, le=23, description="Hora de ejecución (0-23)")
    minute: int = Field(ge=0, le=59, default=0, description="Minuto de ejecución (0-59)")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Día de la semana para programación semanal (0=Lunes, 6=Domingo)")
    interval_hours: Optional[int] = Field(None, ge=1, description="Intervalo en horas para programación por intervalo")
    account_id: Optional[str] = Field(None, description="ID de cuenta específica (opcional para herramientas globales)")

class UpdateScheduledToolRequest(BaseModel):
    """Solicitud para actualizar una herramienta programada."""
    hour: int = Field(ge=0, le=23, description="Nueva hora de ejecución (0-23)")
    minute: int = Field(ge=0, le=59, default=0, description="Nuevo minuto de ejecución (0-59)")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Nuevo día de la semana (solo para programación semanal)")
    interval_hours: Optional[int] = Field(None, ge=1, description="Nuevo intervalo en horas (solo para programación por intervalo)")

class ScheduledToolsStatusResponse(BaseModel):
    """Respuesta con el estado general del sistema de herramientas programadas."""
    total_scheduled: int
    active_jobs: int
    system_initialized: bool
    available_tools: List[str]

# --- Endpoints ---

@router.get("/admin/scheduled-tools", response_model=List[ScheduledToolResponse], summary="Listar herramientas programadas")
async def list_scheduled_tools(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todas las herramientas programadas en el sistema.
    Solo accesible para administradores.
    """
    logger.info(f"Admin {admin_account.id} listando herramientas programadas")
    
    try:
        scheduled_tools = []
        
        # Obtener trabajos programados del scheduler
        for job_name, job in tool_scheduler.scheduled_jobs.items():
            try:
                # Extraer información del nombre del trabajo
                parts = job_name.split('_')
                if len(parts) >= 2:
                    schedule_type = parts[0]  # daily, weekly, interval
                    tool_name = parts[1]
                    account_id = parts[2] if len(parts) > 2 and parts[2] != 'all' else None
                    
                    # Obtener información de programación
                    schedule_info = _get_schedule_info(job, schedule_type)
                    next_run = _get_next_run_time(job)
                    
                    scheduled_tools.append(ScheduledToolResponse(
                        job_name=job_name,
                        tool_name=tool_name,
                        schedule_type=schedule_type,
                        account_id=account_id,
                        schedule_info=schedule_info,
                        next_run=next_run,
                        is_active=job.enabled if hasattr(job, 'enabled') else True
                    ))
            except Exception as e:
                logger.warning(f"Error procesando trabajo {job_name}: {e}")
                continue
        
        return scheduled_tools
        
    except Exception as e:
        logger.error(f"Error listando herramientas programadas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar herramientas programadas"
        )

@router.post("/admin/scheduled-tools", response_model=Dict[str, str], summary="Crear herramienta programada")
async def create_scheduled_tool(
    request: CreateScheduledToolRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Crea una nueva herramienta programada.
    Solo accesible para administradores.
    """
    logger.info(f"Admin {admin_account.id} creando herramienta programada: {request.tool_name}")
    
    try:
        # Validar herramienta disponible
        available_tools = {
            'daily_analysis': _get_daily_analysis_function,
            'daily_insights': _get_daily_insights_function,
            'weekly_cleanup': _get_weekly_cleanup_function,
            'key_rotation_check': _get_key_rotation_check_function
        }
        
        if request.tool_name not in available_tools:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Herramienta '{request.tool_name}' no disponible. Herramientas disponibles: {', '.join(available_tools.keys())}"
            )
        
        # Obtener función de la herramienta
        tool_function = available_tools[request.tool_name]()
        
        # Programar según el tipo
        success = False
        schedule_info = ""
        
        if request.schedule_type == "daily":
            success = await tool_scheduler.schedule_daily_tool(
                tool_name=request.tool_name,
                tool_function=tool_function,
                execution_time=time(hour=request.hour, minute=request.minute),
                account_id=request.account_id
            )
            schedule_info = f"diariamente a las {request.hour:02d}:{request.minute:02d}"
            
        elif request.schedule_type == "weekly":
            if request.day_of_week is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Se requiere especificar el día de la semana para programación semanal"
                )
            
            success = await tool_scheduler.schedule_weekly_tool(
                tool_name=request.tool_name,
                tool_function=tool_function,
                day_of_week=request.day_of_week,
                execution_time=time(hour=request.hour, minute=request.minute),
                account_id=request.account_id
            )
            
            days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            schedule_info = f"semanalmente los {days[request.day_of_week]} a las {request.hour:02d}:{request.minute:02d}"
            
        elif request.schedule_type == "interval":
            if request.interval_hours is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Se requiere especificar el intervalo en horas para programación por intervalo"
                )
            
            success = await tool_scheduler.schedule_interval_tool(
                tool_name=request.tool_name,
                tool_function=tool_function,
                interval_hours=request.interval_hours,
                account_id=request.account_id
            )
            schedule_info = f"cada {request.interval_hours} horas"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de programación '{request.schedule_type}' no válido. Tipos disponibles: daily, weekly, interval"
            )
        
        if success:
            return {
                "message": f"Herramienta '{request.tool_name}' programada exitosamente para ejecutarse {schedule_info}",
                "status": "success"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al programar la herramienta '{request.tool_name}'. Verifica que el sistema de programación esté disponible."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando herramienta programada: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear herramienta programada"
        )

@router.put("/admin/scheduled-tools/{job_name}", response_model=Dict[str, str], summary="Actualizar herramienta programada")
async def update_scheduled_tool(
    job_name: str,
    request: UpdateScheduledToolRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza una herramienta programada existente.
    Solo accesible para administradores.
    """
    logger.info(f"Admin {admin_account.id} actualizando herramienta programada: {job_name}")
    
    try:
        # Verificar que el trabajo existe
        if job_name not in tool_scheduler.scheduled_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Herramienta programada '{job_name}' no encontrada"
            )
        
        # Extraer información del nombre del trabajo
        parts = job_name.split('_')
        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de nombre de trabajo inválido"
            )
        
        tool_name = parts[1]
        account_id = parts[2] if len(parts) > 2 and parts[2] != 'all' else None
        
        # Reprogramar la herramienta
        success = await scheduled_tools_manager.reschedule_tool(
            tool_name=tool_name,
            new_time=time(hour=request.hour, minute=request.minute),
            account_id=account_id
        )
        
        if success:
            return {
                "message": f"Herramienta '{tool_name}' reprogramada exitosamente",
                "status": "success"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al reprogramar la herramienta '{tool_name}'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando herramienta programada: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar herramienta programada"
        )

@router.delete("/admin/scheduled-tools/{job_name}", response_model=Dict[str, str], summary="Eliminar herramienta programada")
async def delete_scheduled_tool(
    job_name: str,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina una herramienta programada.
    Solo accesible para administradores.
    """
    logger.info(f"Admin {admin_account.id} eliminando herramienta programada: {job_name}")
    
    try:
        # Verificar que el trabajo existe
        if job_name not in tool_scheduler.scheduled_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Herramienta programada '{job_name}' no encontrada"
            )
        
        # Cancelar el trabajo
        success = tool_scheduler.cancel_scheduled_tool(job_name)
        
        if success:
            return {
                "message": f"Herramienta programada '{job_name}' eliminada exitosamente",
                "status": "success"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar la herramienta programada '{job_name}'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando herramienta programada: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar herramienta programada"
        )

@router.get("/admin/scheduled-tools/status", response_model=ScheduledToolsStatusResponse, summary="Estado del sistema de herramientas programadas")
async def get_scheduled_tools_status(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene el estado general del sistema de herramientas programadas.
    Solo accesible para administradores.
    """
    logger.info(f"Admin {admin_account.id} consultando estado de herramientas programadas")
    
    try:
        total_scheduled = len(tool_scheduler.scheduled_jobs)
        active_jobs = sum(1 for job in tool_scheduler.scheduled_jobs.values() 
                         if getattr(job, 'enabled', True))
        
        available_tools = [
            'daily_analysis',
            'daily_insights',
            'weekly_cleanup',
            'key_rotation_check'
        ]
        
        return ScheduledToolsStatusResponse(
            total_scheduled=total_scheduled,
            active_jobs=active_jobs,
            system_initialized=scheduled_tools_manager.initialized,
            available_tools=available_tools
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de herramientas programadas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener estado del sistema"
        )

# --- Funciones auxiliares ---

def _get_schedule_info(job, schedule_type: str) -> str:
    """Obtiene información legible de la programación de un trabajo."""
    try:
        if schedule_type == "daily":
            return "Diario"
        elif schedule_type == "weekly":
            return "Semanal"
        elif schedule_type == "interval":
            return "Por intervalo"
        else:
            return "Desconocido"
    except:
        return "No disponible"

def _get_next_run_time(job) -> Optional[str]:
    """Obtiene la próxima hora de ejecución de un trabajo."""
    try:
        if hasattr(job, 'next_t') and job.next_t:
            return job.next_t.strftime("%Y-%m-%d %H:%M:%S")
        return None
    except:
        return None

def _get_daily_analysis_function():
    """Retorna la función para análisis diario."""
    async def daily_analysis_task(account_id: str, **kwargs):
        from utils.proactive_knowledge_linker import run_batch_analysis_job
        logger.info(f"Ejecutando análisis diario programado para cuenta {account_id}")
        await run_batch_analysis_job(account_id_filter=account_id)
        return "Análisis diario completado"
    return daily_analysis_task

def _get_daily_insights_function():
    """Retorna la función para insights diarios."""
    async def daily_insights_task(account_id: str, **kwargs):
        from tools.get_proactive_insights_tool import GetProactiveInsightsTool
        logger.info(f"Generando insights diarios programados para cuenta {account_id}")
        tool = GetProactiveInsightsTool(account_id=account_id)
        result = await tool._arun(account_id=account_id)
        return result
    return daily_insights_task

def _get_weekly_cleanup_function():
    """Retorna la función para limpieza semanal."""
    async def weekly_cleanup_task(account_id: str, **kwargs):
        logger.info(f"Ejecutando limpieza semanal programada para cuenta {account_id}")
        # Aquí puedes agregar lógica específica de limpieza
        return "Limpieza semanal completada"
    return weekly_cleanup_task

def _get_key_rotation_check_function():
    """Retorna la función para verificar rotación de claves."""
    async def key_rotation_check_task(account_id: str, **kwargs):
        from core.utils.key_rotation import KeyRotationManager
        from utils.db_session import DBSession
        from core.database import SessionLocal
        
        logger.info("Ejecutando verificación de rotación de claves")
        async with DBSession(SessionLocal) as session:
            manager = KeyRotationManager(session)
            expiring_keys = await manager.check_expiring_keys()
            if expiring_keys:
                await manager.notify_expiring_keys(expiring_keys)
                return f"Se encontraron {len(expiring_keys)} claves que requieren rotación."
            return "No se encontraron claves expiradas."
    return key_rotation_check_task
