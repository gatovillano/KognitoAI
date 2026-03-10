# tools/cancel_event_tool.py

"""
Herramienta de LangChain para cancelar un evento programado en la agenda de un usuario.

Esta herramienta completa las operaciones CRUD para la gestión de la agenda,
permitiendo al agente de IA eliminar un evento y su recordatorio asociado
a petición del usuario.

Como todas las herramientas de la nueva arquitectura, es independiente de la
plataforma, utilizando el `account_id` universal del usuario. Requiere el `event_id`
específico del evento a cancelar, lo que promueve una interacción segura y clara,
ya que el agente deberá solicitar este ID si el usuario no lo proporciona.
"""

import logging
from typing import Type, Any, Optional

from pydantic import BaseModel, Field, PrivateAttr
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de agenda.
from core.agenda_manager import cancel_event

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class CancelEventInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de cancelación de eventos.
    Valida que todos los argumentos necesarios sean proporcionados por el LLM.
    """
    event_id: int = Field(
        ...,
        description="El ID numérico único del evento que se desea cancelar. El usuario debe proporcionar este ID."
    )
    # Cambiamos telegram_id por account_id para que sea universal.


class CancelEventTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `cancel_event`
    para eliminar un evento y su recordatorio de la base de datos y de la cola de trabajos.
    """
    name: str = "cancel_event_tool"
    description: str = (
        "Útil para cuando un usuario quiere cancelar, borrar o eliminar un evento de su agenda. "
        "Esta herramienta requiere el ID del evento. Si el usuario no proporciona el ID, debes "
        "sugerirle que primero consulte su agenda con la herramienta `get_agenda_tool` para encontrar el ID."
    )
    args_schema: Type[BaseModel] = CancelEventInput
    return_direct: bool = False
    account_id: str = Field(..., description="ID de la cuenta del usuario.")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo del usuario.")
    telegram_id: Optional[str] = Field(None, description="ID de Telegram del usuario.")
    thread_id: Optional[str] = Field(None, description="ID del hilo de conversación.")

    async def _arun(self, event_id: int, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            event_id: El ID del evento a cancelar.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando CancelEventTool para la cuenta '{self.account_id}' y el evento ID '{event_id}'.")
        try:
            success, message = await cancel_event(account_id=self.account_id, event_id=event_id, workspace_id=self.workspace_id)
            logger.info(f"Herramienta de cancelación de evento completada para la cuenta '{self.account_id}'. Mensaje: {message}")
            return message
        except Exception as e:
            logger.error(f"Error en CancelEventTool para la cuenta '{self.account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar cancelar el evento: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("cancel_event_tool no soporta ejecución síncrona.")
