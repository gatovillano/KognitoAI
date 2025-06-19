# tools/schedule_event_tool.py

"""
Herramienta de LangChain para programar un nuevo evento en la agenda de un usuario.

Esta herramienta permite al agente de IA crear eventos, citas o recordatorios
con fechas y horas específicas. Es fundamental para la gestión del tiempo y la
planificación del usuario.

La herramienta está diseñada para ser agnóstica de la plataforma, utilizando el
`account_id` universal del usuario. Esto permite que un usuario programe un
evento desde Telegram y, en el futuro, pueda consultarlo o modificarlo desde
una interfaz web, manteniendo una experiencia unificada.
"""

import logging
from typing import Type, Any

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de agenda.
from telegram_bot.agenda_manager import schedule_event

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class ScheduleEventInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de programación de eventos.
    Valida que todos los argumentos necesarios sean proporcionados por el LLM.
    """
    description: str = Field(
        ...,
        description="La descripción detallada del evento o actividad a programar."
    )
    natural_language_datetime: str = Field(
        ...,
        description="Una descripción en lenguaje natural de cuándo ocurrirá el evento. Por ejemplo: 'mañana a las 3pm', 'en 2 horas', 'el próximo viernes a las 10 de la mañana'."
    )
    # Cambiamos telegram_id por account_id para que sea universal.
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )


class ScheduleEventTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `schedule_event`
    para crear un nuevo evento en la base de datos y programar su recordatorio.
    """
    name: str = "schedule_event_tool"
    description: str = (
        "Útil para cuando un usuario quiere programar una actividad, un evento o un recordatorio "
        "en su agenda. Usa esto si dice 'recuérdame', 'agenda', 'anota para tal fecha', etc. "
        "Esta herramienta es ideal para eventos con fechas y horas específicas."
    )
    args_schema: Type[BaseModel] = ScheduleEventInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, description: str, natural_language_datetime: str, account_id: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            description: La descripción del evento.
            natural_language_datetime: El texto con la fecha/hora del evento.
            account_id: El ID universal de la cuenta del usuario.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando ScheduleEventTool para la cuenta '{account_id}' con descripción: '{description}'")
        try:
            # Llama a la función de lógica de negocio, que ahora debe ser actualizada
            # para aceptar 'account_id' en lugar de 'telegram_id'.
            success, message = await schedule_event(
                account_id=account_id,
                description=description,
                natural_language_datetime=natural_language_datetime
            )
            logger.info(f"Herramienta de programación de evento completada para la cuenta '{account_id}'. Mensaje: {message}")
            return message
        except Exception as e:
            logger.error(f"Error en ScheduleEventTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar programar el evento: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("schedule_event_tool no soporta ejecución síncrona.")