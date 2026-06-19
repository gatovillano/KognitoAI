# tools/schedule_event_tool.py

"""
Herramienta de LangChain para programar un nuevo evento en la agenda de un usuario.
Esta versión es "pura": interactúa con el core pero no con la lógica de entrega.
"""

import logging
from typing import Type, Any, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
import dateparser

from core.agenda_manager import schedule_event
from utils.telegram_api import store_telegram_user_data

logger = logging.getLogger(__name__)

# ¡NUEVO! Clave para pasar el ID del evento al handler
EVENT_ID_FOR_SCHEDULING_KEY = "event_id_to_schedule"


class ScheduleEventInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta.
    """
    summary: str = Field(..., description="El título o resumen del evento.")
    natural_language_datetime: str = Field(..., description="La fecha y hora del evento en lenguaje natural (e.g., 'mañana a las 10am').")
    description: Optional[str] = Field(None, description="La descripción detallada del evento.")


class ScheduleEventTool(BaseTool):
    """
    Herramienta que se conecta a la función `schedule_event` del core.
    """
    name: str = "schedule_event_tool"
    description: str = "Útil para programar una actividad, evento o recordatorio en la agenda."
    args_schema: Type[BaseModel] = ScheduleEventInput
    return_direct: bool = False
    account_id: str = Field(..., description="ID de la cuenta a la que pertenece el evento.")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo donde se programa el evento.")
    telegram_id: Optional[str] = Field(None, description="ID de Telegram del usuario que programa el evento.")
    thread_id: Optional[str] = Field(None, description="ID del hilo de conversación en el que se programa el evento.")

    async def _arun(self, summary: str, natural_language_datetime: str, description: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica: llama al core para crear el evento y luego guarda el
        ID del evento para que el handler programe la notificación.
        """
        logger.info(f"Ejecutando ScheduleEventTool para la cuenta '{self.account_id}'...")
        try:
            parsed_datetime = dateparser.parse(natural_language_datetime)
            if not parsed_datetime:
                return "No pude entender la fecha y hora. Por favor, intenta de nuevo con un formato más claro."

            event_date = parsed_datetime.strftime("%Y-%m-%d")
            event_time = parsed_datetime.strftime("%H:%M")

            success, message, new_event = await schedule_event(
                account_id=self.account_id,
                summary=summary,
                description=description,
                event_date=event_date,
                event_time=event_time,
                workspace_id=self.workspace_id
            )

            if success and new_event:
                # Priorizar self.telegram_id si está disponible, de lo contrario, usar run_manager
                telegram_id_to_use = self.telegram_id
                if not telegram_id_to_use:
                    run_manager = kwargs.get("run_manager")
                    if run_manager:
                        telegram_id_to_use = run_manager.config.get("configurable", {}).get("telegram_id")
                
                if telegram_id_to_use:
                    await store_telegram_user_data(
                        telegram_id=int(telegram_id_to_use),
                        key=EVENT_ID_FOR_SCHEDULING_KEY,
                        data=new_event.id
                    )
                    logger.info(f"ID de evento {new_event.id} guardado en user_data para que el handler lo programe.")
                else:
                    logger.warning("No se pudo obtener telegram_id para guardar el ID del evento en user_data.")

            return message
        except Exception as e:
            logger.error(f"Error en ScheduleEventTool para la cuenta '{self.account_id}': {e}", exc_info=True)
            return "Ocurrió un error inesperado al programar el evento."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("schedule_event_tool no soporta ejecución síncrona.")
