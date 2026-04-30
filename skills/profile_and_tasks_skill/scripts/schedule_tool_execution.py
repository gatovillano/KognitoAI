# tools/schedule_tool_execution.py

"""
Herramienta para Programar Ejecución Automática de Herramientas.

Esta herramienta permite a los usuarios programar la ejecución automática
de otras herramientas en intervalos específicos.
"""

import logging
from datetime import time, datetime
from typing import Any, Type, Union, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from utils.tool_scheduler import tool_scheduler
from utils.scheduled_tools_manager import scheduled_tools_manager

logger = logging.getLogger(__name__)

class ScheduleToolExecutionInput(BaseModel):
    """
    Esquema de entrada para programar herramientas automáticas.
    """
    tool_name: str = Field(
        description="Nombre de la herramienta a programar (ej: 'weekly_cleanup')"
    )
    schedule_type: str = Field(
        description="Tipo de programación: 'daily', 'weekly', 'interval'"
    )
    hour: int = Field(
        description="Hora del día para ejecutar (0-23)",
        ge=0,
        le=23
    )
    minute: int = Field(
        description="Minuto de la hora para ejecutar (0-59)",
        default=0,
        ge=0,
        le=59
    )
    day_of_week: Optional[int] = Field(
        description="Día de la semana para programación semanal (0=Lunes, 6=Domingo)",
        default=None,
        ge=0,
        le=6,
        json_schema_extra={"type": "integer"}
    )
    interval_hours: Optional[int] = Field(
        description="Intervalo en horas para programación por intervalo",
        default=None,
        ge=1,
        json_schema_extra={"type": "integer"}
    )
    account_id: str = Field(description="ID de la cuenta del usuario")

class ScheduleToolExecutionTool(BaseTool):
    """
    Herramienta para programar la ejecución automática de otras herramientas.
    """
    name: str = "schedule_tool_execution"
    description: str = """
    Útil para programar la ejecución automática de herramientas en intervalos específicos.
    Permite programar herramientas diariamente, semanalmente o cada X horas.

    - 'weekly_cleanup': Limpieza semanal de datos

    Tipos de programación:
    - 'daily': Ejecutar todos los días a una hora específica
    - 'weekly': Ejecutar una vez por semana en un día específico
    - 'interval': Ejecutar cada X horas
    """
    args_schema: Type[BaseModel] = ScheduleToolExecutionInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")

    async def _arun(
        self,
        tool_name: str,
        schedule_type: str,
        hour: int,
        minute: int = 0,
        day_of_week: Union[int, None] = None,
        interval_hours: Union[int, None] = None,
        account_id: Union[str, None] = None,
        **kwargs: Any
    ) -> str:
        """
        Ejecuta la programación de la herramienta.
        
        Args:
            tool_name: Nombre de la herramienta a programar
            schedule_type: Tipo de programación ('daily', 'weekly', 'interval')
            hour: Hora del día (0-23)
            minute: Minuto de la hora (0-59)
            day_of_week: Día de la semana para programación semanal (0-6)
            interval_hours: Intervalo en horas para programación por intervalo
            account_id: ID de la cuenta
            **kwargs: Argumentos adicionales
            
        Returns:
            Mensaje de confirmación o error
        """
        logger.info(f"Programando herramienta '{tool_name}' para la cuenta '{account_id}'")
        
        try:
            # Validar herramienta disponible
            available_tools = {
                'weekly_cleanup': self._get_weekly_cleanup_function
            }
            
            if tool_name not in available_tools:
                return f"❌ Herramienta '{tool_name}' no disponible. Herramientas disponibles: {', '.join(available_tools.keys())}"
            
            # Obtener función de la herramienta
            tool_function = available_tools[tool_name]()
            
            # Programar según el tipo
            success = False
            schedule_info = ""
            
            if schedule_type == "daily":
                success = await tool_scheduler.schedule_daily_tool(
                    tool_name=tool_name,
                    tool_function=tool_function,
                    execution_time=time(hour=hour, minute=minute),
                    account_id=account_id,
                    workspace_id=self.workspace_id,
                    telegram_id=self.telegram_id
                )
                schedule_info = f"diariamente a las {hour:02d}:{minute:02d}"
                
            elif schedule_type == "weekly":
                if day_of_week is None:
                    return "❌ Se requiere especificar el día de la semana para programación semanal"
                
                success = await tool_scheduler.schedule_weekly_tool(
                    tool_name=tool_name,
                    tool_function=tool_function,
                    day_of_week=day_of_week,
                    execution_time=time(hour=hour, minute=minute),
                    account_id=account_id,
                    workspace_id=self.workspace_id,
                    telegram_id=self.telegram_id
                )
                
                days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                schedule_info = f"semanalmente los {days[day_of_week]} a las {hour:02d}:{minute:02d}"
                
            elif schedule_type == "interval":
                if interval_hours is None:
                    return "❌ Se requiere especificar el intervalo en horas para programación por intervalo"
                
                success = await tool_scheduler.schedule_interval_tool(
                    tool_name=tool_name,
                    tool_function=tool_function,
                    interval_hours=interval_hours,
                    account_id=account_id,
                    workspace_id=self.workspace_id,
                    telegram_id=self.telegram_id
                )
                schedule_info = f"cada {interval_hours} horas"
                
            else:
                return f"❌ Tipo de programación '{schedule_type}' no válido. Tipos disponibles: daily, weekly, interval"
            
            if success:
                return f"✅ Herramienta '{tool_name}' programada exitosamente para ejecutarse {schedule_info}"
            else:
                return f"❌ Error al programar la herramienta '{tool_name}'. Verifica que el sistema de programación esté disponible."
                
        except Exception as e:
            logger.error(f"Error al programar herramienta '{tool_name}': {e}", exc_info=True)
            return f"❌ Error inesperado al programar la herramienta: {str(e)}"
    

    
    def _get_weekly_cleanup_function(self):
        """Retorna la función para limpieza semanal."""
        async def weekly_cleanup_task(account_id: str, **kwargs):
            logger.info(f"Ejecutando limpieza semanal programada para cuenta {account_id}")
            # Aquí puedes agregar lógica específica de limpieza
            return "Limpieza semanal completada"
        return weekly_cleanup_task

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("schedule_tool_execution no soporta ejecución síncrona.")


class ListScheduledToolsInput(BaseModel):
    """
    Esquema de entrada para listar herramientas programadas.
    """
    account_id: str = Field(description="ID de la cuenta del usuario")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo (opcional)")

class ListScheduledToolsTool(BaseTool):
    """
    Herramienta para listar las herramientas programadas actualmente.
    """
    name: str = "list_scheduled_tools"
    description: str = "Útil para ver qué herramientas están programadas para ejecutarse automáticamente"
    args_schema: Type[BaseModel] = ListScheduledToolsInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo, inyectado automáticamente si está disponible.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente si está disponible.")

    async def _arun(self, account_id: str, **kwargs: Any) -> str:
        """
        Lista las herramientas programadas para la cuenta.
        
        Args:
            account_id: ID de la cuenta
            **kwargs: Argumentos adicionales
            
        Returns:
            Lista de herramientas programadas
        """
        try:
            status = scheduled_tools_manager.get_scheduled_tools_status()
            scheduled_jobs = status.get("scheduled_jobs", {})
            
            if not scheduled_jobs:
                return "📅 No hay herramientas programadas actualmente."
            
            # Filtrar jobs para esta cuenta y workspace
            account_jobs = {}
            for name, info in scheduled_jobs.items():
                job_account_id = info.get("data", {}).get("account_id")
                job_workspace_id = info.get("data", {}).get("workspace_id")
                job_telegram_id = info.get("data", {}).get("telegram_id")

                if job_account_id == account_id:
                    if self.workspace_id:
                        if job_workspace_id == self.workspace_id:
                            if self.telegram_id:
                                if job_telegram_id == self.telegram_id:
                                    account_jobs[name] = info
                            elif job_telegram_id is None:
                                account_jobs[name] = info
                    elif job_workspace_id is None:
                        if self.telegram_id:
                            if job_telegram_id == self.telegram_id:
                                account_jobs[name] = info
                        elif job_telegram_id is None:
                            account_jobs[name] = info
            
            if not account_jobs:
                return f"📅 No hay herramientas programadas para tu cuenta."
            
            result = "📅 **Herramientas Programadas:**\n\n"
            
            for job_name, job_info in account_jobs.items():
                next_run = job_info.get("next_run")
                enabled = job_info.get("enabled", False)
                data = job_info.get("data", {})
                tool_name = data.get("tool_name", "Desconocida")
                
                status_icon = "✅" if enabled else "❌"
                next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "No programada"
                
                result += f"{status_icon} **{tool_name}**\n"
                result += f"   📍 Próxima ejecución: {next_run_str}\n"
                result += f"   🔧 Estado: {'Activa' if enabled else 'Inactiva'}\n\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error al listar herramientas programadas: {e}", exc_info=True)
            return f"❌ Error al obtener la lista de herramientas programadas: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("list_scheduled_tools no soporta ejecución síncrona.")
