# tools/schedule_event_tool.py

"""
Herramienta de LangChain para programar un nuevo evento en la agenda de un usuario.
Esta versión es "pura": interactúa con el core pero no con la lógica de entrega.
"""

import logging
from typing import Type, Any

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from core.agenda_manager import schedule_event
# ¡NUEVO! Importamos el bot_manager para acceder al user_data
from telegram_client.bot_manager import bot_manager

logger = logging.getLogger(__name__)

# ¡NUEVO! Clave para pasar el ID del evento al handler
EVENT_ID_FOR_SCHEDULING_KEY = "event_id_to_schedule"


class ScheduleEventInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta. Ya no necesita telegram_id.
    """
    description: str = Field(...)
    natural_language_datetime: str = Field(...)
    account_id: str = Field(...)


class ScheduleEventTool(BaseTool):
    """
    Herramienta que se conecta a la función `schedule_event` del core.
    """
    name: str = "schedule_event_tool"
    description: str = "Útil para programar una actividad, evento o recordatorio en la agenda."
    args_schema: Type[BaseModel] = ScheduleEventInput
    return_direct: bool = False

    async def _arun(self, description: str, natural_language_datetime: str, account_id: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica: llama al core para crear el evento y luego guarda el
        ID del evento para que el handler programe la notificación.
        """
        logger.info(f"Ejecutando ScheduleEventTool para la cuenta '{account_id}'...")
        try:
            # Llama a la función del core, que ahora devuelve el objeto del evento
            success, message, new_event = await schedule_event(
                account_id=account_id,
                description=description,
                natural_language_datetime=natural_language_datetime
            )

            # ¡NUEVO! Si el evento se creó, guardamos su ID en user_data.
            # Necesitamos el telegram_id del config de la invocación del agente.
            if success and new_event:
                run_manager = kwargs.get("run_manager")
                if run_manager:
                    telegram_id = run_manager.config.get("configurable", {}).get("telegram_id")
                    if telegram_id:
                        user_data = bot_manager.get_user_data(telegram_id)
                        user_data[EVENT_ID_FOR_SCHEDULING_KEY] = new_event.id
                        await bot_manager.flush_persistence()
                        logger.info(f"ID de evento {new_event.id} guardado en user_data para que el handler lo programe.")

            return message
        except Exception as e:
            logger.error(f"Error en ScheduleEventTool: {e}", exc_info=True)
            return "Ocurrió un error inesperado al programar el evento."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("schedule_event_tool no soporta ejecución síncrona.")
