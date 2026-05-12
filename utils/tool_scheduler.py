# utils/tool_scheduler.py

"""
Sistema de Programación de Herramientas Automáticas.

Este módulo permite programar herramientas para que se ejecuten automáticamente
en intervalos específicos usando el JobQueue de Telegram o APScheduler.
"""

import logging
import asyncio
from datetime import time, datetime, timedelta
from typing import Dict, Any, Optional, Callable
# from telegram_client.bot_manager import bot_manager # Ya no se usará JobQueue de Telegram
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Cambiar a AsyncIOScheduler
from core.database import SessionLocal
from core.config import settings
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class ToolScheduler:
    """
    Gestor de programación de herramientas automáticas.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler() # Usar AsyncIOScheduler
        self.scheduled_jobs = {} # Mantener esto para consistencia si es necesario

    def _sync_scheduled_jobs(self):
        """Sincroniza la caché en memoria con los jobs reales de APScheduler."""
        self.scheduled_jobs = {job.id: job for job in self.scheduler.get_jobs()}
        
    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler iniciado.")
        
    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("APScheduler detenido.")

    async def _execute_tool_callback(self, tool_name: str, tool_function: Callable, account_id: Optional[str] = None, **tool_kwargs):
        """Callback interno que ejecuta la herramienta programada."""
        logger.info(f"Ejecutando herramienta programada: {tool_name}")
        
        try:
            if asyncio.iscoroutinefunction(tool_function):
                result = await tool_function(account_id=account_id, **tool_kwargs)
            else:
                result = tool_function(account_id=account_id, **tool_kwargs)
                
            logger.info(f"Herramienta '{tool_name}' ejecutada exitosamente: {result}")
            
        except Exception as e:
            logger.error(f"Error al ejecutar herramienta programada '{tool_name}': {e}", exc_info=True)

    async def schedule_daily_tool(
        self,
        tool_name: str,
        tool_function: Callable,
        execution_time: time,
        account_id: Optional[str] = None,
        **tool_kwargs
    ):
        """
        Programa una herramienta para ejecutarse diariamente a una hora específica usando APScheduler.
        """
        job_id = f"daily_{tool_name}_{account_id or 'all'}"
        
        # Eliminar job existente si existe
        if self.scheduler.get_job(job_id):
            self.cancel_scheduled_tool(job_id)
        
        self.scheduler.add_job(
            self._execute_tool_callback,
            'cron',
            hour=execution_time.hour,
            minute=execution_time.minute,
            id=job_id,
            args=[tool_name, tool_function, account_id],
            kwargs=tool_kwargs
        )
        self.scheduled_jobs[job_id] = self.scheduler.get_job(job_id) # Mantener referencia
        logger.info(f"Herramienta '{tool_name}' programada diariamente a las {execution_time}")
        return True
    
    async def schedule_weekly_tool(
        self,
        tool_name: str,
        tool_function: Callable,
        day_of_week: int,  # 0=Lunes, 6=Domingo
        execution_time: time,
        account_id: Optional[str] = None,
        **tool_kwargs
    ):
        """
        Programa una herramienta para ejecutarse semanalmente usando APScheduler.
        """
        job_id = f"weekly_{tool_name}_{account_id or 'all'}"

        if self.scheduler.get_job(job_id):
            self.cancel_scheduled_tool(job_id)

        # APScheduler usa 0=Lunes, 6=Domingo, que coincide con nuestra convención
        self.scheduler.add_job(
            self._execute_tool_callback,
            'cron',
            day_of_week=day_of_week,
            hour=execution_time.hour,
            minute=execution_time.minute,
            id=job_id,
            args=[tool_name, tool_function, account_id],
            kwargs=tool_kwargs
        )
        self.scheduled_jobs[job_id] = self.scheduler.get_job(job_id) # Mantener referencia
        days_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        logger.info(f"Herramienta '{tool_name}' programada semanalmente los {days_names[day_of_week]} a las {execution_time}")
        return True
    
    async def schedule_interval_tool(
        self,
        tool_name: str,
        tool_function: Callable,
        interval_hours: int = 0,
        interval_minutes: int = 0,
        account_id: Optional[str] = None,
        **tool_kwargs
    ):
        """
        Programa una herramienta para ejecutarse cada X horas o minutos usando APScheduler.
        """
        if interval_hours == 0 and interval_minutes == 0:
            logger.error(f"No se especificó un intervalo válido para {tool_name}")
            return False

        job_id = f"interval_{tool_name}_{account_id or 'all'}"

        if self.scheduler.get_job(job_id):
            self.cancel_scheduled_tool(job_id)
        
        self.scheduler.add_job(
            self._execute_tool_callback,
            'interval',
            hours=interval_hours,
            minutes=interval_minutes,
            id=job_id,
            args=[tool_name, tool_function, account_id],
            kwargs=tool_kwargs
        )
        self.scheduled_jobs[job_id] = self.scheduler.get_job(job_id) # Mantener referencia
        logger.info(f"Herramienta '{tool_name}' programada cada {interval_hours} horas y {interval_minutes} minutos")
        return True
    
    def cancel_scheduled_tool(self, job_id: str):
        """Cancela una herramienta programada usando APScheduler."""
        removed = False

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            removed = True

        # Aunque no exista en APScheduler, limpiar caché evita "fantasmas" en listado.
        if job_id in self.scheduled_jobs:
            del self.scheduled_jobs[job_id]
            removed = True

        # Mantener caché siempre consistente tras intentos de cancelación.
        self._sync_scheduled_jobs()

        if removed:
            logger.info(f"Herramienta programada '{job_id}' cancelada")
            return True
        return False
    
    def list_scheduled_tools(self) -> Dict[str, Any]:
        """Lista todas las herramientas programadas gestionadas por APScheduler."""
        self._sync_scheduled_jobs()
        jobs_info = {}
        for job in self.scheduler.get_jobs():
            # Extraer información del job_id
            job_name = job.id
            parts = job_name.split('_')
            
            # Asegurarse de que el formato del job_id es el esperado
            if len(parts) >= 2:
                schedule_type = parts[0]
                tool_name = parts[1]
                account_id = parts[2] if len(parts) > 2 and parts[2] != 'all' else None
                
                # Intentar obtener la próxima ejecución de forma segura
                next_run_time = job.next_run_time.isoformat() if job.next_run_time else None

                jobs_info[job_name] = {
                    "tool_name": tool_name,
                    "schedule_type": schedule_type,
                    "account_id": account_id,
                    "schedule_info": str(job.trigger), # Información del trigger de APScheduler
                    "next_run": next_run_time,
                    "is_active": job.next_run_time is not None # Un job está activo si tiene una próxima ejecución
                }
            else:
                logger.warning(f"Formato de job_id inesperado: {job_name}")
        return jobs_info

# Instancia global del scheduler
tool_scheduler = ToolScheduler()

# Funciones de conveniencia para herramientas específicas
async def schedule_daily_analysis(account_id: Optional[str] = None, hour: int = 2, minute: int = 0):
    """Programa análisis diario de conocimiento."""
    # from utils.proactive_knowledge_linker import run_batch_analysis_job
    
    async def daily_analysis_task(account_id: Optional[str] = None, **kwargs):
        """Tarea de análisis diario."""
        logger.info("Análisis diario saltado (proactive_knowledge_linker no disponible).")
        # if account_id:
        #     await run_batch_analysis_job(account_id_filter=account_id)
        # else:
        #     await run_batch_analysis_job()
        return "Análisis diario saltado exitosamente"
    
    return await tool_scheduler.schedule_daily_tool(
        tool_name="daily_analysis",
        tool_function=daily_analysis_task,
        execution_time=time(hour=hour, minute=minute),
        account_id=account_id
    )


async def schedule_daily_insights(account_id: str, hour: int = 7, minute: int = 0):
    """Programa generación de insights diarios."""
    async def daily_insights_task(account_id: str, **kwargs):
        """Tarea diaria compatible que ejecuta el heartbeat autónomo."""
        from core.autonomous_heartbeat import run_autonomous_agent_heartbeat

        return await run_autonomous_agent_heartbeat(
            account_id=account_id,
            workspace_id=kwargs.get("workspace_id"),
            heartbeat_instructions=kwargs.get("heartbeat_instructions"),
            max_insights=kwargs.get("max_insights"),
            lookback_days=kwargs.get("lookback_days"),
        )
    
    if not account_id:
        logger.warning("Se requiere account_id para programar insights diarios")
        return False
        
    return await tool_scheduler.schedule_daily_tool(
        tool_name="daily_insights",
        tool_function=daily_insights_task,
        execution_time=time(hour=hour, minute=minute),
        account_id=account_id,
        heartbeat_instructions=settings.autonomous_heartbeat_instructions,
        max_insights=settings.autonomous_heartbeat_max_insights,
        lookback_days=settings.autonomous_heartbeat_lookback_days,
    )


async def schedule_autonomous_agent_heartbeat(
    account_id: str,
    interval_hours: Optional[int] = None,
    workspace_id: Optional[str] = None,
    heartbeat_instructions: Optional[str] = None,
    max_insights: Optional[int] = None,
    lookback_days: Optional[int] = None,
):
    """Programa el heartbeat autónomo del agente cada cierto número de horas."""
    if not account_id:
        logger.warning("Se requiere account_id para programar heartbeat autónomo")
        return False

    async def autonomous_heartbeat_task(account_id: str, **kwargs):
        from core.autonomous_heartbeat import run_autonomous_agent_heartbeat

        return await run_autonomous_agent_heartbeat(
            account_id=account_id,
            workspace_id=kwargs.get("workspace_id"),
            heartbeat_instructions=kwargs.get("heartbeat_instructions"),
            max_insights=kwargs.get("max_insights"),
            lookback_days=kwargs.get("lookback_days"),
        )

    return await tool_scheduler.schedule_interval_tool(
        tool_name="autonomous_heartbeat",
        tool_function=autonomous_heartbeat_task,
        interval_hours=interval_hours or settings.autonomous_heartbeat_interval_hours,
        account_id=account_id,
        workspace_id=workspace_id,
        heartbeat_instructions=heartbeat_instructions or settings.autonomous_heartbeat_instructions,
        max_insights=max_insights or settings.autonomous_heartbeat_max_insights,
        lookback_days=lookback_days or settings.autonomous_heartbeat_lookback_days,
    )

async def schedule_custom_user_heartbeat(account_id: str, interval_minutes: int, allowed_tools: Optional[list] = None, workspace_id: Optional[str] = None):
    """Programa el heartbeat personalizado del usuario configurado individualmente."""
    if not account_id:
        return False

    async def custom_heartbeat_task(account_id: str, **kwargs):
        from core.agent import run_custom_user_heartbeat
        # Pasamos allowed_tools a la función si está preparado para recibirlo
        return await run_custom_user_heartbeat(
            account_id=account_id, 
            workspace_id=kwargs.get("workspace_id")
        )

    return await tool_scheduler.schedule_interval_tool(
        tool_name="custom_user_heartbeat",
        tool_function=custom_heartbeat_task,
        interval_minutes=interval_minutes,
        account_id=account_id,
        workspace_id=workspace_id,
        allowed_tools=allowed_tools
    )
