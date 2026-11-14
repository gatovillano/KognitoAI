# tools/schedule_tool_execution.py

"""
Herramienta para Programar Ejecución Automática de Herramientas.

Permite programar CUALQUIER herramienta disponible para ejecutarse
automáticamente en intervalos específicos (diario, semanal, por intervalo).
"""

import logging
from datetime import time
from typing import Any, Dict, Optional, Type, Union
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from utils.tool_scheduler import tool_scheduler
from utils.scheduled_tools_manager import scheduled_tools_manager

logger = logging.getLogger(__name__)


class ScheduleToolExecutionInput(BaseModel):
    tool_name: str = Field(
        description="Nombre exacto de la herramienta a programar (ej: 'web_search_tool', 'create_note_tool', 'send_email_tool')"
    )
    schedule_type: str = Field(
        description="Tipo de programación: 'daily' (cada día), 'weekly' (cada semana), 'interval' (cada X horas)"
    )
    hour: int = Field(
        description="Hora del día para ejecutar (0-23). Para 'interval' indica la hora de inicio.",
        ge=0,
        le=23,
        default=8,
    )
    minute: int = Field(
        description="Minuto de la hora para ejecutar (0-59)",
        default=0,
        ge=0,
        le=59,
    )
    day_of_week: Optional[int] = Field(
        description="Solo para 'weekly': día de la semana (0=Lunes, 6=Domingo)",
        default=None,
        ge=0,
        le=6,
    )
    interval_hours: Optional[int] = Field(
        description="Solo para 'interval': cada cuántas horas ejecutar",
        default=None,
        ge=1,
    )
    tool_args: Optional[Dict[str, Any]] = Field(
        description="Argumentos a pasar a la herramienta al ejecutarse. Ej: {\"query\": \"noticias de IA\", \"topic\": \"innovacion\"}",
        default=None,
    )
    account_id: str = Field(description="ID de la cuenta del usuario")


class ScheduleToolExecutionTool(BaseTool):
    name: str = "schedule_tool_execution"
    description: str = """
    Programa CUALQUIER herramienta disponible para ejecutarse automáticamente en intervalos específicos.

    Puedes programar herramientas como:
    - Búsquedas web periódicas
    - Creación automática de notas o reportes
    - Envío de mensajes o recordatorios
    - Análisis programados
    - Cualquier otra herramienta del sistema

    Tipos de programación:
    - 'daily': Todos los días a la hora especificada
    - 'weekly': Una vez por semana en el día especificado
    - 'interval': Cada X horas

    Usa 'tool_args' para pasar los argumentos que necesita la herramienta al ejecutarse.
    """
    args_schema: Type[BaseModel] = ScheduleToolExecutionInput
    return_direct: bool = False
    account_id: str = Field(..., description="ID de cuenta inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="ID de workspace inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="ID de Telegram inyectado automáticamente.")

    async def _arun(
        self,
        tool_name: str,
        schedule_type: str,
        hour: int = 8,
        minute: int = 0,
        day_of_week: Optional[int] = None,
        interval_hours: Optional[int] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        effective_account_id = account_id or self.account_id
        logger.info(f"Programando herramienta '{tool_name}' para cuenta '{effective_account_id}'")

        # Validar que la herramienta existe cargándola dinámicamente
        from core.tools import get_all_langchain_tools
        try:
            all_tools = await get_all_langchain_tools(
                account_id=effective_account_id,
                workspace_id=self.workspace_id,
            )
        except Exception as e:
            logger.error(f"Error cargando herramientas: {e}", exc_info=True)
            return f"❌ No se pudieron cargar las herramientas disponibles: {str(e)}"

        tool_map = {t.name: t for t in all_tools}
        if tool_name not in tool_map:
            available = ", ".join(sorted(tool_map.keys()))
            return (
                f"❌ La herramienta '{tool_name}' no existe o no está disponible para tu cuenta.\n"
                f"Herramientas disponibles: {available}"
            )

        # Construir la función ejecutora genérica que se llamará en cada trigger
        _tool_name = tool_name
        _tool_args = dict(tool_args or {})
        _workspace_id = self.workspace_id
        _telegram_id = self.telegram_id

        async def generic_tool_executor(account_id: str, **exec_kwargs: Any) -> str:
            """Ejecuta la herramienta configurada en cada disparo del scheduler."""
            from core.tools import get_all_langchain_tools as _get_tools
            try:
                tools = await _get_tools(
                    account_id=account_id,
                    workspace_id=_workspace_id,
                )
                tmap = {t.name: t for t in tools}
                tool = tmap.get(_tool_name)
                if not tool:
                    logger.warning(f"Scheduler: herramienta '{_tool_name}' no encontrada al ejecutar")
                    return f"Herramienta '{_tool_name}' no disponible en el momento de ejecución"
                merged_args = {**_tool_args, **exec_kwargs}
                result = await tool.arun(tool_input=merged_args if merged_args else "")
                logger.info(f"Scheduler ejecutó '{_tool_name}' correctamente")
                return str(result)
            except Exception as exc:
                logger.error(f"Scheduler: error ejecutando '{_tool_name}': {exc}", exc_info=True)
                return f"Error al ejecutar '{_tool_name}': {str(exc)}"

        try:
            success = False
            schedule_info = ""

            if schedule_type == "daily":
                success = await tool_scheduler.schedule_daily_tool(
                    tool_name=tool_name,
                    tool_function=generic_tool_executor,
                    execution_time=time(hour=hour, minute=minute),
                    account_id=effective_account_id,
                )
                schedule_info = f"diariamente a las {hour:02d}:{minute:02d}"

            elif schedule_type == "weekly":
                if day_of_week is None:
                    return "❌ Para programación semanal debes especificar 'day_of_week' (0=Lunes … 6=Domingo)"
                success = await tool_scheduler.schedule_weekly_tool(
                    tool_name=tool_name,
                    tool_function=generic_tool_executor,
                    day_of_week=day_of_week,
                    execution_time=time(hour=hour, minute=minute),
                    account_id=effective_account_id,
                )
                days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                schedule_info = f"semanalmente los {days[day_of_week]} a las {hour:02d}:{minute:02d}"

            elif schedule_type == "interval":
                if interval_hours is None:
                    return "❌ Para programación por intervalo debes especificar 'interval_hours'"
                success = await tool_scheduler.schedule_interval_tool(
                    tool_name=tool_name,
                    tool_function=generic_tool_executor,
                    interval_hours=interval_hours,
                    account_id=effective_account_id,
                )
                schedule_info = f"cada {interval_hours} hora(s)"

            else:
                return f"❌ Tipo '{schedule_type}' no válido. Usa: daily, weekly, interval"

            if success:
                args_summary = f" con args: {_tool_args}" if _tool_args else ""
                return f"✅ Herramienta '{tool_name}' programada para ejecutarse {schedule_info}{args_summary}"
            else:
                return f"❌ No se pudo programar '{tool_name}'. Verifica que el scheduler esté activo."

        except Exception as e:
            logger.error(f"Error al programar '{tool_name}': {e}", exc_info=True)
            return f"❌ Error inesperado al programar la herramienta: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("schedule_tool_execution no soporta ejecución síncrona.")


class ListScheduledToolsInput(BaseModel):
    account_id: str = Field(description="ID de la cuenta del usuario")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo (opcional)")


class ListScheduledToolsTool(BaseTool):
    name: str = "list_scheduled_tools"
    description: str = "Útil para ver qué herramientas están programadas para ejecutarse automáticamente"
    args_schema: Type[BaseModel] = ListScheduledToolsInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo, inyectado automáticamente si está disponible.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente si está disponible.")

    async def _arun(self, account_id: str, **kwargs: Any) -> str:
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
                return "📅 No hay herramientas programadas para tu cuenta."

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
