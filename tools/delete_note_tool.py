# tools/delete_note_tool.py

"""
Herramienta de LangChain para eliminar una nota existente de la cuenta de un usuario.

Esta herramienta completa las operaciones CRUD para la gestión de notas,
permitiendo al agente de IA borrar permanentemente una nota específica a petición
del usuario.

La herramienta sigue el diseño de la arquitectura centralizada:
1.  Opera con el `account_id` universal, haciéndola independiente de la plataforma.
2.  Requiere que el LLM proporcione el `note_id` de la nota a eliminar, lo que
    fomenta una interacción clara y segura con el usuario (por ejemplo, pidiendo
    confirmación o listando notas si el ID no se conoce).
"""

import logging
from typing import Type, Any

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de notas.
from core.notes_manager import delete_note

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class DeleteNoteInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de eliminación de notas.
    Valida que todos los argumentos necesarios sean proporcionados por el LLM.
    """
    note_id: int = Field(
        ...,
        description="El ID numérico único de la nota que se va a eliminar. El usuario debe proporcionar este ID."
    )
    # Cambiamos telegram_id por account_id para que sea universal.


class DeleteNoteTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `delete_note`
    para eliminar una nota de la base de datos.
    """
    name: str = "delete_note_tool"
    description: str = (
        "Útil para borrar o eliminar permanentemente una nota existente. "
        "Esta herramienta requiere el ID de la nota a eliminar. Si el usuario no proporciona el ID, "
        "se le debe sugerir que primero liste sus notas con `get_notes_tool` para encontrar el ID correcto."
    )
    args_schema: Type[BaseModel] = DeleteNoteInput
    return_direct: bool = False
    account_id: str

    async def _arun(self, note_id: int, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            note_id: El ID de la nota a eliminar.
            **kwargs: Argumentos adicionales (no utilizados aquí).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando DeleteNoteTool para la cuenta '{self.account_id}' y la nota ID '{note_id}'.")
        try:
            result_message = await delete_note(account_id=self.account_id, note_id=note_id)
            logger.info(f"Herramienta de eliminación de nota completada para la cuenta '{self.account_id}'. Mensaje: {result_message}")
            return result_message
        except Exception as e:
            logger.error(f"Error en DeleteNoteTool para la cuenta '{self.account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar eliminar la nota: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("delete_note_tool no soporta ejecución síncrona.")
