# tools/get_agenda_tool.py

"""
Herramienta de LangChain para consultar la agenda de un usuario para un día específico.

Esta herramienta permite al agente de IA responder a preguntas del usuario sobre
sus eventos programados, como "¿Qué tengo para hoy?" o "¿Cómo está mi agenda mañana?".

Al igual que las otras herramientas de la arquitectura, opera con el `account_id`
universal del usuario, lo que le permite obtener la información correcta sin
depender de la plataforma desde la que se realiza la consulta.
"""

import logging
from typing import Type, Any

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de agenda.
from core.agenda_manager import get_agenda_for_day

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class GetAgendaInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de consulta de agenda.
    Valida que todos los argumentos necesarios sean proporcionados por el LLM.
    """
    target_day: str = Field(
        ...,
        description="El día para el cual se consulta la agenda. Puede ser 'hoy', 'mañana', o una fecha específica como '15 de junio' o 'próximo jueves'."
    )
    # Cambiamos telegram_id por account_id para que sea universal.


class GetAgendaTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `get_agenda_for_day`
    para obtener y listar los eventos de un usuario para un día determinado.
    """
    name: str = "get_agenda_tool"
    description: str = (
        "Útil para cuando un usuario pregunta qué tiene programado en su agenda. "
        "Responde a preguntas como '¿Qué tengo para hoy?', '¿Cómo está mi agenda mañana?', "
        "o '¿Tengo algo para el 25 de diciembre?'."
    )
    args_schema: Type[BaseModel] = GetAgendaInput
    return_direct: bool = False
    account_id: str
    workspace_id: Optional[str] = None

    async def _arun(self, target_day: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            target_day: El día específico a consultar.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Una cadena de texto con la lista de eventos o un mensaje indicando que no hay eventos.
        """
        logger.info(f"Ejecutando GetAgendaTool para la cuenta '{self.account_id}' en el día: '{target_day}'.")
        try:
            agenda_string = await get_agenda_for_day(account_id=self.account_id, target_day=target_day)
            logger.info(f"Herramienta de consulta de agenda completada para la cuenta '{self.account_id}'.")
            return agenda_string
        except Exception as e:
            logger.error(f"Error en GetAgendaTool para la cuenta '{self.account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar consultar tu agenda: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_agenda_tool no soporta ejecución síncrona.")