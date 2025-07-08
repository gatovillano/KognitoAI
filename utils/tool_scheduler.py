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
from telegram_client.bot_manager import bot_manager
from core.database import SessionLocal
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class ToolScheduler:
    """
    Gestor de programación de herramientas automáticas.
    """
    
    def __init__(self):
        self.scheduled_jobs = {}
        
    async def schedule_daily_tool(
        self, 
        tool_name: str, 
        tool_function: Callable,
        execution_time: time,
        account_id: Optional[str] = None,
        **tool_kwargs
    ):
        """
        Programa una herramienta para ejecutarse diariamente a una hora específica.
        
        Args:
            tool_name: Nombre identificador de la herramienta
            tool_function: Función async a ejecutar
            execution_time: Hora del día para ejecutar (time object)
            account_id: ID de cuenta específica (opcional)
            **tool_kwargs: Argumentos adicionales para la herramienta
        """
        if not bot_manager.job_queue:
            logger.error("JobQueue no está disponible. No se puede programar la herramienta.")
            return False
            
        job_name = f"daily_{tool_name}_{account_id or 'all'}"
        
        # Cancelar job existente si existe
        if job_name in self.scheduled_jobs:
            self.cancel_scheduled_tool(job_name)
        
        # Programar nuevo job
        job = bot_manager.job_queue.run_daily(
            callback=self._execute_tool_callback,
            time=execution_time,
            data={
                "tool_name": tool_name,
                "tool_function": tool_function,
                "account_id": account_id,
                "tool_kwargs": tool_kwargs
            },
            name=job_name
        )
        
        self.scheduled_jobs[job_name] = job
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
        Programa una herramienta para ejecutarse semanalmente.
        
        Args:
            tool_name: Nombre identificador de la herramienta
            tool_function: Función async a ejecutar
            day_of_week: Día de la semana (0=Lunes, 6=Domingo)
            execution_time: Hora del día para ejecutar
            account_id: ID de cuenta específica (opcional)
            **tool_kwargs: Argumentos adicionales para la herramienta
        """
        if not bot_manager.job_queue:
            logger.error("JobQueue no está disponible. No se puede programar la herramienta.")
            return False
            
        job_name = f"weekly_{tool_name}_{account_id or 'all'}"
        
        # Cancelar job existente si existe
        if job_name in self.scheduled_jobs:
            self.cancel_scheduled_tool(job_name)
        
        # Calcular próxima ejecución
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_name = days[day_of_week]
        
        job = bot_manager.job_queue.run_repeating(
            callback=self._execute_tool_callback,
            interval=timedelta(weeks=1),
            first=self._get_next_weekday(day_of_week, execution_time),
            data={
                "tool_name": tool_name,
                "tool_function": tool_function,
                "account_id": account_id,
                "tool_kwargs": tool_kwargs
            },
            name=job_name
        )
        
        self.scheduled_jobs[job_name] = job
        logger.info(f"Herramienta '{tool_name}' programada semanalmente los {day_name} a las {execution_time}")
        return True
    
    async def schedule_interval_tool(
        self,
        tool_name: str,
        tool_function: Callable,
        interval_hours: int,
        account_id: Optional[str] = None,
        **tool_kwargs
    ):
        """
        Programa una herramienta para ejecutarse cada X horas.
        
        Args:
            tool_name: Nombre identificador de la herramienta
            tool_function: Función async a ejecutar
            interval_hours: Intervalo en horas entre ejecuciones
            account_id: ID de cuenta específica (opcional)
            **tool_kwargs: Argumentos adicionales para la herramienta
        """
        if not bot_manager.job_queue:
            logger.error("JobQueue no está disponible. No se puede programar la herramienta.")
            return False
            
        job_name = f"interval_{tool_name}_{account_id or 'all'}"
        
        # Cancelar job existente si existe
        if job_name in self.scheduled_jobs:
            self.cancel_scheduled_tool(job_name)
        
        job = bot_manager.job_queue.run_repeating(
            callback=self._execute_tool_callback,
            interval=timedelta(hours=interval_hours),
            data={
                "tool_name": tool_name,
                "tool_function": tool_function,
                "account_id": account_id,
                "tool_kwargs": tool_kwargs
            },
            name=job_name
        )
        
        self.scheduled_jobs[job_name] = job
        logger.info(f"Herramienta '{tool_name}' programada cada {interval_hours} horas")
        return True
    
    def cancel_scheduled_tool(self, job_name: str):
        """Cancela una herramienta programada."""
        if job_name in self.scheduled_jobs:
            job = self.scheduled_jobs[job_name]
            job.schedule_removal()
            del self.scheduled_jobs[job_name]
            logger.info(f"Herramienta programada '{job_name}' cancelada")
            return True
        return False
    
    def list_scheduled_tools(self) -> Dict[str, Any]:
        """Lista todas las herramientas programadas."""
        return {
            name: {
                "next_run": job.next_t,
                "enabled": job.enabled,
                "data": job.data
            }
            for name, job in self.scheduled_jobs.items()
        }
    
    async def _execute_tool_callback(self, context):
        """Callback interno que ejecuta la herramienta programada."""
        data = context.job.data
        tool_name = data["tool_name"]
        tool_function = data["tool_function"]
        account_id = data.get("account_id")
        tool_kwargs = data.get("tool_kwargs", {})
        
        logger.info(f"Ejecutando herramienta programada: {tool_name}")
        
        try:
            # Ejecutar la herramienta
            if asyncio.iscoroutinefunction(tool_function):
                result = await tool_function(account_id=account_id, **tool_kwargs)
            else:
                result = tool_function(account_id=account_id, **tool_kwargs)
                
            logger.info(f"Herramienta '{tool_name}' ejecutada exitosamente: {result}")
            
        except Exception as e:
            logger.error(f"Error al ejecutar herramienta programada '{tool_name}': {e}", exc_info=True)
    
    def _get_next_weekday(self, weekday: int, time_obj: time) -> datetime:
        """Calcula la próxima fecha para un día de la semana específico."""
        today = datetime.now()
        days_ahead = weekday - today.weekday()
        
        if days_ahead <= 0:  # El día ya pasó esta semana
            days_ahead += 7
            
        next_date = today + timedelta(days=days_ahead)
        return datetime.combine(next_date.date(), time_obj)


# Instancia global del scheduler
tool_scheduler = ToolScheduler()


# Funciones de conveniencia para herramientas específicas
async def schedule_daily_analysis(account_id: Optional[str] = None, hour: int = 2, minute: int = 0):
    """Programa análisis diario de conocimiento."""
    from utils.proactive_knowledge_linker import run_batch_analysis_job
    
    async def daily_analysis_task(account_id: Optional[str] = None, **kwargs):
        """Tarea de análisis diario."""
        logger.info("Iniciando análisis diario programado...")
        if account_id:
            await run_batch_analysis_job(account_id_filter=account_id)
        else:
            await run_batch_analysis_job()
        logger.info("Análisis diario completado.")
        return "Análisis diario ejecutado exitosamente"
    
    return await tool_scheduler.schedule_daily_tool(
        tool_name="daily_analysis",
        tool_function=daily_analysis_task,
        execution_time=time(hour=hour, minute=minute),
        account_id=account_id
    )


async def schedule_daily_insights(account_id: Optional[str] = None, hour: int = 8, minute: int = 0):
    """Programa generación diaria de insights proactivos."""
    from tools.get_proactive_insights_tool import GetProactiveInsightsTool
    
    async def daily_insights_task(account_id: str, **kwargs):
        """Tarea de insights diarios."""
        logger.info("Generando insights diarios programados...")
        tool = GetProactiveInsightsTool(account_id=account_id)
        result = await tool._arun(account_id=account_id)
        logger.info("Insights diarios generados.")
        return result
    
    if not account_id:
        logger.warning("Se requiere account_id para programar insights diarios")
        return False
        
    return await tool_scheduler.schedule_daily_tool(
        tool_name="daily_insights",
        tool_function=daily_insights_task,
        execution_time=time(hour=hour, minute=minute),
        account_id=account_id
    )
