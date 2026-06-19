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
from sqlalchemy import select

from core.database import SessionLocal, Account
from core.config import settings
from utils.security import get_current_account_id
from core.database import SystemSettings
from utils.tool_scheduler import tool_scheduler, schedule_autonomous_agent_heartbeat
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


class AutonomousHeartbeatConfigResponse(BaseModel):
    enabled: bool
    interval_hours: int
    lookback_days: int
    max_insights: int
    instructions: str
    scheduled_jobs: int


class UpdateAutonomousHeartbeatConfigRequest(BaseModel):
    enabled: bool = Field(description="Activar o desactivar heartbeat autónomo")
    interval_hours: int = Field(ge=1, le=168, description="Intervalo de ejecución en horas")
    lookback_days: int = Field(ge=1, le=90, description="Ventana histórica analizada por el heartbeat")
    max_insights: int = Field(ge=1, le=20, description="Máximo de insights por ejecución")
    instructions: str = Field(min_length=10, max_length=4000, description="Instrucciones ejecutivas para generación de insights")


class TriggerHeartbeatRequest(BaseModel):
    account_id: str = Field(description="ID de la cuenta para la que ejecutar el heartbeat")
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        description="Lista de nombres de herramientas permitidas para ejecutar durante el heartbeat. Si es None, no se ejecutan herramientas."
    )

class CustomHeartbeatConfig(BaseModel):
    """Configuración del heartbeat personalizado para el usuario."""
    instructions: Optional[str] = Field(None, description="Instrucciones personalizadas para el agente.")
    interval_minutes: Optional[int] = Field(60, ge=5, le=1440, description="Frecuencia en minutos.")
    allowed_tools: List[str] = Field(default_factory=list, description="Herramientas permitidas.")

class CustomHeartbeatResponse(BaseModel):
    id: uuid.UUID
    name: str
    instructions: str
    schedule_type: str # "interval", "daily", "weekly"
    interval_minutes: Optional[int] = None
    hour: Optional[int] = None
    minute: Optional[int] = None
    day_of_week: Optional[int] = None
    allowed_tools: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    next_run: Optional[str] = None

    class Config:
        from_attributes = True

class CreateCustomHeartbeatRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    instructions: str = Field(..., min_length=1)
    schedule_type: str = Field(default="interval") # "interval", "daily", "weekly"
    interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    hour: Optional[int] = Field(None, ge=0, le=23)
    minute: Optional[int] = Field(None, ge=0, le=59)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    allowed_tools: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)

class UpdateCustomHeartbeatRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    instructions: Optional[str] = Field(None, min_length=1)
    schedule_type: Optional[str] = Field(None)
    interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    hour: Optional[int] = Field(None, ge=0, le=23)
    minute: Optional[int] = Field(None, ge=0, le=59)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    allowed_tools: Optional[List[str]] = None
    is_active: Optional[bool] = None


# --- Helpers de configuración persistente del heartbeat admin ---

_HEARTBEAT_KEYS = {
    "enabled": "autonomous_heartbeat_enabled",
    "interval_hours": "autonomous_heartbeat_interval_hours",
    "lookback_days": "autonomous_heartbeat_lookback_days",
    "max_insights": "autonomous_heartbeat_max_insights",
    "instructions": "autonomous_heartbeat_instructions",
}


async def _get_heartbeat_setting(db: AsyncSession, field: str, default):
    """Lee un valor de system_settings, regresando el default si no existe."""
    key = _HEARTBEAT_KEYS[field]
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    row = result.scalar_one_or_none()
    if row is None or row.value is None:
        return default
    if isinstance(default, bool):
        return row.value.lower() in ('true', '1', 't')
    if isinstance(default, int):
        return int(row.value)
    if isinstance(default, float):
        return float(row.value)
    return row.value


async def _save_heartbeat_setting(db: AsyncSession, field: str, value) -> None:
    """Guarda o actualiza un valor en system_settings."""
    key = _HEARTBEAT_KEYS[field]
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        db.add(SystemSettings(key=key, value=str(value)))
    else:
        row.value = str(value)


# --- Endpoints ---

@router.get("/scheduled-tools/custom-heartbeat", response_model=CustomHeartbeatConfig, summary="Obtener mi configuración de heartbeat")
async def get_my_custom_heartbeat_config(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Obtiene la configuración del heartbeat personalizado del usuario actual."""
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    return CustomHeartbeatConfig(
        instructions=account.custom_heartbeat_instructions,
        interval_minutes=account.custom_heartbeat_interval_minutes,
        allowed_tools=account.custom_heartbeat_allowed_tools or []
    )

@router.put("/scheduled-tools/custom-heartbeat", response_model=Dict[str, str], summary="Actualizar mi configuración de heartbeat")
async def update_my_custom_heartbeat_config(
    config: CustomHeartbeatConfig,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Actualiza la configuración del heartbeat personalizado del usuario actual."""
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    # Actualizar campos
    account.custom_heartbeat_instructions = config.instructions
    account.custom_heartbeat_interval_minutes = config.interval_minutes
    account.custom_heartbeat_allowed_tools = config.allowed_tools
    
    await db.commit()
    
    # Reprogramar el job en el scheduler si hay instrucciones
    from utils.tool_scheduler import schedule_custom_user_heartbeat
    if config.instructions:
        await schedule_custom_user_heartbeat(
            account_id=current_account_id,
            interval_minutes=config.interval_minutes or 60,
            allowed_tools=config.allowed_tools
        )
    else:
        # Si se borran las instrucciones, cancelar el job
        job_id = f"interval_custom_heartbeat_{current_account_id}"
        tool_scheduler.cancel_scheduled_tool(job_id)
        
    return {"status": "success", "message": "Configuración de heartbeat actualizada"}

@router.post("/scheduled-tools/custom-heartbeat/trigger", response_model=Dict[str, str], summary="Lanzar mi heartbeat manualmente")
async def trigger_my_custom_heartbeat(
    current_account_id: str = Depends(get_current_account_id),
):
    """Lanza el heartbeat personalizado del usuario actual inmediatamente."""
    logger.info(f"Usuario {current_account_id} lanzando heartbeat manual")
    try:
        from core.agent import run_custom_user_heartbeat
        result = await run_custom_user_heartbeat(account_id=current_account_id)
        if "No hay heartbeat personalizado configurado" in result:
             raise HTTPException(status_code=400, detail=result)
             
        return {"status": "success", "message": "Heartbeat iniciado", "detail": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en trigger manual: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled-tools/custom-heartbeats", response_model=List[CustomHeartbeatResponse], summary="Obtener todos mis heartbeats personalizados")
async def list_my_custom_heartbeats(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Obtiene la lista de todos los heartbeats personalizados del usuario actual."""
    from core.database import CustomHeartbeat
    account_uuid = uuid.UUID(current_account_id)
    stmt = select(CustomHeartbeat).where(CustomHeartbeat.account_id == account_uuid).order_by(CustomHeartbeat.created_at.desc())
    result = await db.execute(stmt)
    hbs = result.scalars().all()
    
    response = []
    for hb in hbs:
        job_id = f"custom_{hb.id}"
        job = tool_scheduler.scheduler.get_job(job_id)
        next_run = _get_next_run_time(job) if job else None
        
        response.append(CustomHeartbeatResponse(
            id=hb.id,
            name=hb.name,
            instructions=hb.instructions,
            schedule_type=hb.schedule_type,
            interval_minutes=hb.interval_minutes,
            hour=hb.hour,
            minute=hb.minute,
            day_of_week=hb.day_of_week,
            allowed_tools=hb.allowed_tools or [],
            is_active=hb.is_active,
            created_at=hb.created_at,
            updated_at=hb.updated_at,
            next_run=next_run
        ))
    return response


@router.post("/scheduled-tools/custom-heartbeats", response_model=CustomHeartbeatResponse, summary="Crear un nuevo heartbeat personalizado")
async def create_custom_heartbeat(
    request: CreateCustomHeartbeatRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Crea un nuevo heartbeat personalizado para el usuario actual y lo programa."""
    from core.database import CustomHeartbeat
    account_uuid = uuid.UUID(current_account_id)
    
    new_hb = CustomHeartbeat(
        account_id=account_uuid,
        name=request.name,
        instructions=request.instructions,
        schedule_type=request.schedule_type,
        interval_minutes=request.interval_minutes,
        hour=request.hour,
        minute=request.minute,
        day_of_week=request.day_of_week,
        allowed_tools=request.allowed_tools,
        is_active=request.is_active
    )
    db.add(new_hb)
    await db.commit()
    await db.refresh(new_hb)
    
    # Programar el job si está activo
    if new_hb.is_active:
        from utils.tool_scheduler import schedule_custom_heartbeat
        await schedule_custom_heartbeat(
            heartbeat_id=str(new_hb.id),
            account_id=current_account_id,
            schedule_type=new_hb.schedule_type,
            instructions=new_hb.instructions,
            allowed_tools=new_hb.allowed_tools,
            interval_minutes=new_hb.interval_minutes,
            hour=new_hb.hour,
            minute=new_hb.minute,
            day_of_week=new_hb.day_of_week
        )
        
    job_id = f"custom_{new_hb.id}"
    job = tool_scheduler.scheduler.get_job(job_id)
    next_run = _get_next_run_time(job) if job else None
    
    return CustomHeartbeatResponse(
        id=new_hb.id,
        name=new_hb.name,
        instructions=new_hb.instructions,
        schedule_type=new_hb.schedule_type,
        interval_minutes=new_hb.interval_minutes,
        hour=new_hb.hour,
        minute=new_hb.minute,
        day_of_week=new_hb.day_of_week,
        allowed_tools=new_hb.allowed_tools or [],
        is_active=new_hb.is_active,
        created_at=new_hb.created_at,
        updated_at=new_hb.updated_at,
        next_run=next_run
    )


@router.put("/scheduled-tools/custom-heartbeats/{heartbeat_id}", response_model=CustomHeartbeatResponse, summary="Actualizar un heartbeat personalizado")
async def update_custom_heartbeat(
    heartbeat_id: str,
    request: UpdateCustomHeartbeatRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Actualiza un heartbeat personalizado existente."""
    from core.database import CustomHeartbeat
    hb_uuid = uuid.UUID(heartbeat_id)
    account_uuid = uuid.UUID(current_account_id)
    
    hb = await db.get(CustomHeartbeat, hb_uuid)
    if not hb or hb.account_id != account_uuid:
        raise HTTPException(status_code=404, detail="Heartbeat no encontrado")
        
    if request.name is not None:
        hb.name = request.name
    if request.instructions is not None:
        hb.instructions = request.instructions
    if request.schedule_type is not None:
        hb.schedule_type = request.schedule_type
    if request.interval_minutes is not None:
        hb.interval_minutes = request.interval_minutes
    if request.hour is not None:
        hb.hour = request.hour
    if request.minute is not None:
        hb.minute = request.minute
    if request.day_of_week is not None:
        hb.day_of_week = request.day_of_week
    if request.allowed_tools is not None:
        hb.allowed_tools = request.allowed_tools
    if request.is_active is not None:
        hb.is_active = request.is_active
        
    await db.commit()
    await db.refresh(hb)
    
    # Actualizar la programación
    from utils.tool_scheduler import cancel_custom_heartbeat, schedule_custom_heartbeat
    if hb.is_active:
        await schedule_custom_heartbeat(
            heartbeat_id=str(hb.id),
            account_id=current_account_id,
            schedule_type=hb.schedule_type,
            instructions=hb.instructions,
            allowed_tools=hb.allowed_tools,
            interval_minutes=hb.interval_minutes,
            hour=hb.hour,
            minute=hb.minute,
            day_of_week=hb.day_of_week
        )
    else:
        cancel_custom_heartbeat(str(hb.id))
        
    job_id = f"custom_{hb.id}"
    job = tool_scheduler.scheduler.get_job(job_id)
    next_run = _get_next_run_time(job) if job else None
    
    return CustomHeartbeatResponse(
        id=hb.id,
        name=hb.name,
        instructions=hb.instructions,
        schedule_type=hb.schedule_type,
        interval_minutes=hb.interval_minutes,
        hour=hb.hour,
        minute=hb.minute,
        day_of_week=hb.day_of_week,
        allowed_tools=hb.allowed_tools or [],
        is_active=hb.is_active,
        created_at=hb.created_at,
        updated_at=hb.updated_at,
        next_run=next_run
    )


@router.delete("/scheduled-tools/custom-heartbeats/{heartbeat_id}", response_model=Dict[str, str], summary="Eliminar un heartbeat personalizado")
async def delete_custom_heartbeat(
    heartbeat_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Elimina un heartbeat personalizado."""
    from core.database import CustomHeartbeat
    hb_uuid = uuid.UUID(heartbeat_id)
    account_uuid = uuid.UUID(current_account_id)
    
    hb = await db.get(CustomHeartbeat, hb_uuid)
    if not hb or hb.account_id != account_uuid:
        raise HTTPException(status_code=404, detail="Heartbeat no encontrado")
        
    from utils.tool_scheduler import cancel_custom_heartbeat
    cancel_custom_heartbeat(str(hb.id))
    
    await db.delete(hb)
    await db.commit()
    
    return {"status": "success", "message": "Heartbeat personalizado eliminado con éxito"}


@router.post("/scheduled-tools/custom-heartbeats/{heartbeat_id}/trigger", response_model=Dict[str, str], summary="Lanzar un heartbeat personalizado manualmente")
async def trigger_custom_heartbeat(
    heartbeat_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Lanza un heartbeat personalizado específico del usuario inmediatamente."""
    from core.database import CustomHeartbeat
    hb_uuid = uuid.UUID(heartbeat_id)
    account_uuid = uuid.UUID(current_account_id)
    
    hb = await db.get(CustomHeartbeat, hb_uuid)
    if not hb or hb.account_id != account_uuid:
        raise HTTPException(status_code=404, detail="Heartbeat no encontrado")
        
    logger.info(f"Usuario {current_account_id} lanzando heartbeat manual '{hb.name}' ({hb.id})")
    try:
        from core.agent import run_custom_user_heartbeat
        result = await run_custom_user_heartbeat(
            account_id=current_account_id,
            heartbeat_id=str(hb.id)
        )
        return {"status": "success", "message": "Heartbeat iniciado", "detail": result}
    except Exception as e:
        logger.error(f"Error en trigger manual de heartbeat {hb.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/scheduled-tools/autonomous-heartbeat/trigger", response_model=Dict[str, str], summary="Lanzar mi heartbeat autónomo manualmente")
async def trigger_my_autonomous_heartbeat(
    current_account_id: str = Depends(get_current_account_id),
):
    """Lanza el heartbeat autónomo del usuario actual inmediatamente."""
    logger.info(f"Usuario {current_account_id} lanzando heartbeat autónomo manual")
    try:
        from core.autonomous_heartbeat import run_autonomous_agent_heartbeat
        result = await run_autonomous_agent_heartbeat(account_id=current_account_id)
        return {"status": "success", "message": "Heartbeat autónomo iniciado", "detail": result}
    except Exception as e:
        logger.error(f"Error en trigger manual de heartbeat autónomo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled-tools/available-tools", response_model=Dict[str, Any], summary="Listar herramientas disponibles para mi")
async def list_my_available_tools(
    current_account_id: str = Depends(get_current_account_id),
):
    """
    Lista todas las herramientas LangChain disponibles para el usuario actual.
    """
    try:
        from core.tools import get_all_langchain_tools
        tools = await get_all_langchain_tools(account_id=current_account_id)
        return {
            "tools": [
                {"name": t.name, "description": (t.description or "").strip()[:300]}
                for t in tools
            ]
        }
    except Exception as e:
        logger.error(f"Error listando herramientas para mi cuenta: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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

        # Sincronizar caché en memoria con jobs reales del scheduler.
        tool_scheduler._sync_scheduled_jobs()

        # Obtener trabajos programados del scheduler y precargar custom heartbeats
        from core.database import CustomHeartbeat
        result = await db.execute(select(CustomHeartbeat))
        custom_hbs = {str(hb.id): hb for hb in result.scalars().all()}

        for job in tool_scheduler.scheduler.get_jobs():
            try:
                job_name = job.id
                # Verificar si es un heartbeat personalizado
                if job_name.startswith("custom_"):
                    heartbeat_id = job_name.replace("custom_", "")
                    hb = custom_hbs.get(heartbeat_id)
                    if hb:
                        schedule_type = hb.schedule_type
                        tool_name = hb.name
                        account_id = str(hb.account_id)
                    else:
                        schedule_type = "custom"
                        tool_name = f"Custom Heartbeat ({heartbeat_id[:8]})"
                        account_id = None
                else:
                    # Extraer información del nombre del trabajo estándar
                    # Formato: {schedule_type}_{tool_name}_{account_id_or_all}
                    parts = job_name.split('_')
                    if len(parts) >= 2:
                        schedule_type = parts[0]  # daily, weekly, interval
                        account_id = parts[-1] if parts[-1] != 'all' else None
                        tool_name = "_".join(parts[1:-1])
                    else:
                        continue

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
                logger.warning(f"Error procesando trabajo: {e}")
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


@router.get(
    "/admin/scheduled-tools/heartbeat-config",
    response_model=AutonomousHeartbeatConfigResponse,
    summary="Obtener configuración del heartbeat autónomo",
)
async def get_autonomous_heartbeat_config(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Admin {admin_account.id} consultando configuración de heartbeat autónomo")
    try:
        heartbeat_jobs = [
            job_id for job_id in tool_scheduler.scheduled_jobs.keys()
            if job_id.startswith("interval_autonomous_heartbeat_")
        ]
        # Leer desde la base de datos (persistente), con fallback a settings del entorno
        enabled = await _get_heartbeat_setting(db, "enabled", settings.autonomous_heartbeat_enabled)
        interval_hours = await _get_heartbeat_setting(db, "interval_hours", settings.autonomous_heartbeat_interval_hours)
        lookback_days = await _get_heartbeat_setting(db, "lookback_days", settings.autonomous_heartbeat_lookback_days)
        max_insights = await _get_heartbeat_setting(db, "max_insights", settings.autonomous_heartbeat_max_insights)
        instructions = await _get_heartbeat_setting(db, "instructions", settings.autonomous_heartbeat_instructions)
        return AutonomousHeartbeatConfigResponse(
            enabled=bool(enabled),
            interval_hours=int(interval_hours),
            lookback_days=int(lookback_days),
            max_insights=int(max_insights),
            instructions=str(instructions),
            scheduled_jobs=len(heartbeat_jobs),
        )
    except Exception as e:
        logger.error(f"Error leyendo configuración del heartbeat autónomo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al leer configuración del heartbeat"
        )


@router.put(
    "/admin/scheduled-tools/heartbeat-config",
    response_model=Dict[str, str],
    summary="Actualizar configuración del heartbeat autónomo",
)
async def update_autonomous_heartbeat_config(
    request: UpdateAutonomousHeartbeatConfigRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Admin {admin_account.id} actualizando configuración de heartbeat autónomo")

    try:
        # 1. Persistir en la base de datos (sobrevive reinicios del servidor)
        await _save_heartbeat_setting(db, "enabled", request.enabled)
        await _save_heartbeat_setting(db, "interval_hours", request.interval_hours)
        await _save_heartbeat_setting(db, "lookback_days", request.lookback_days)
        await _save_heartbeat_setting(db, "max_insights", request.max_insights)
        await _save_heartbeat_setting(db, "instructions", str(request.instructions).strip())
        await db.commit()

        # 2. Actualizar configuración en runtime (para la sesión actual)
        settings.autonomous_heartbeat_enabled = bool(request.enabled)
        settings.autonomous_heartbeat_interval_hours = int(request.interval_hours)
        settings.autonomous_heartbeat_lookback_days = int(request.lookback_days)
        settings.autonomous_heartbeat_max_insights = int(request.max_insights)
        settings.autonomous_heartbeat_instructions = str(request.instructions).strip()

        # 3. Mantener la configuración del manager sincronizada
        scheduled_tools_manager.default_schedules["autonomous_heartbeat"] = {
            "interval_hours": settings.autonomous_heartbeat_interval_hours
        }

        # 4. Limpiar jobs existentes del heartbeat
        current_job_ids = list(tool_scheduler.scheduled_jobs.keys())
        for job_id in current_job_ids:
            if job_id.startswith("interval_autonomous_heartbeat_"):
                tool_scheduler.cancel_scheduled_tool(job_id)

        # 5. Reprogramar si quedó habilitado
        if settings.autonomous_heartbeat_enabled and settings.get_proactive_insights_enabled:
            result = await db.execute(select(Account).where(Account.is_active == True))
            active_accounts = result.scalars().all()

            for account in active_accounts:
                await schedule_autonomous_agent_heartbeat(
                    account_id=str(account.id),
                    interval_hours=settings.autonomous_heartbeat_interval_hours,
                    heartbeat_instructions=settings.autonomous_heartbeat_instructions,
                    max_insights=settings.autonomous_heartbeat_max_insights,
                    lookback_days=settings.autonomous_heartbeat_lookback_days,
                )

        return {
            "status": "success",
            "message": "Configuración del heartbeat autónomo actualizada y jobs reprogramados"
        }
    except Exception as e:
        logger.error(f"Error actualizando configuración del heartbeat autónomo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar configuración del heartbeat"
        )


@router.post(
    "/admin/scheduled-tools/trigger-heartbeat",
    response_model=Dict[str, str],
    summary="Ejecutar heartbeat autónomo manualmente",
)
async def trigger_autonomous_heartbeat(
    request: TriggerHeartbeatRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Ejecuta el heartbeat autónomo manualmente para una cuenta específica.
    Solo accesible para administradores.
    """
    logger.info(f"Admin {admin_account.id} disparando heartbeat autónomo para cuenta {request.account_id}")

    try:
        from core.autonomous_heartbeat import run_autonomous_agent_heartbeat

        # Verificar que la cuenta existe
        account = await db.get(Account, uuid.UUID(request.account_id))
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuenta '{request.account_id}' no encontrada"
            )

        # Ejecutar el heartbeat
        result = await run_autonomous_agent_heartbeat(
            account_id=request.account_id,
            heartbeat_instructions=settings.autonomous_heartbeat_instructions,
            max_insights=settings.autonomous_heartbeat_max_insights,
            lookback_days=settings.autonomous_heartbeat_lookback_days,
            notify=True,
            allowed_tools=request.allowed_tools or None,
        )

        return {
            "status": "success",
            "message": f"Heartbeat autónomo ejecutado para la cuenta. Resultado: {result}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disparando heartbeat autónomo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al ejecutar heartbeat autónomo: {str(e)}"
        )


@router.get("/admin/scheduled-tools/available-tools", response_model=Dict[str, Any], summary="Listar herramientas disponibles para una cuenta")
async def list_available_tools_for_heartbeat(
    account_id: str,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todas las herramientas LangChain disponibles para una cuenta específica.
    Se usa para configurar cuáles herramientas puede usar el heartbeat autónomo.
    Solo accesible para administradores.
    """
    try:
        account = await db.get(Account, uuid.UUID(account_id))
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cuenta '{account_id}' no encontrada")

        from core.tools import get_all_langchain_tools
        tools = await get_all_langchain_tools(account_id=account_id)
        return {
            "tools": [
                {"name": t.name, "description": (t.description or "").strip()[:300]}
                for t in tools
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando herramientas para cuenta {account_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener herramientas: {str(e)}"
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
        tool_scheduler._sync_scheduled_jobs()
        total_scheduled = len(tool_scheduler.scheduled_jobs)
        active_jobs = sum(1 for job in tool_scheduler.scheduled_jobs.values()
                         if getattr(job, 'enabled', True))

        available_tools = [
            'weekly_cleanup',
            'key_rotation_check',
            'autonomous_heartbeat',
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
        tool_scheduler._sync_scheduled_jobs()
        # Verificar que el trabajo existe
        if not tool_scheduler.scheduler.get_job(job_name) and job_name not in tool_scheduler.scheduled_jobs:
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

        account_id = parts[-1] if parts[-1] != 'all' else None
        tool_name = "_".join(parts[1:-1])

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
        tool_scheduler._sync_scheduled_jobs()
        # Verificar que el trabajo existe
        if not tool_scheduler.scheduler.get_job(job_name) and job_name not in tool_scheduler.scheduled_jobs:
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


# --- Funciones auxiliares ---

def _get_schedule_info(job, schedule_type: str) -> str:
    """Obtiene información legible de la programación de un trabajo."""
    try:
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        trigger = job.trigger
        if isinstance(trigger, CronTrigger):
            hour_field = next((f for f in trigger.fields if f.name == 'hour'), None)
            minute_field = next((f for f in trigger.fields if f.name == 'minute'), None)
            day_of_week_field = next((f for f in trigger.fields if f.name == 'day_of_week'), None)
            
            h = int(str(hour_field)) if hour_field and str(hour_field).isdigit() else 0
            m = int(str(minute_field)) if minute_field and str(minute_field).isdigit() else 0
            
            if schedule_type == "weekly":
                days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                day_str = str(day_of_week_field) if day_of_week_field else "0"
                day_idx = 0
                if day_str.isdigit():
                    day_idx = int(day_str)
                else:
                    day_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
                    day_idx = day_map.get(day_str.lower()[:3], 0)
                
                day_name = days[day_idx % 7]
                return f"semanalmente los ({day_name}) a las {h:02d}:{m:02d}"
            else:
                return f"diariamente a las {h:02d}:{m:02d}"
                
        elif isinstance(trigger, IntervalTrigger):
            interval = trigger.interval
            total_seconds = int(interval.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            if hours > 0:
                return f"cada {hours} horas"
            else:
                return f"cada {minutes} minutos"
    except Exception as e:
        logger.warning(f"Error parseando schedule info para job {job.id}: {e}")
        
    # Fallback
    if schedule_type == "daily":
        return "diariamente a las 00:00"
    elif schedule_type == "weekly":
        return "semanalmente los (Lunes) a las 00:00"
    elif schedule_type == "interval":
        return "cada 1 horas"
    return "Desconocido"

def _get_next_run_time(job) -> Optional[str]:
    """Obtiene la próxima hora de ejecución de un trabajo."""
    try:
        if hasattr(job, 'next_t') and job.next_t:
            return job.next_t.strftime("%Y-%m-%d %H:%M:%S")
        return None
    except:
        return None

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