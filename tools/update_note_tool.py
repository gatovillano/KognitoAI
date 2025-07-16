# tools/update_note_tool.py

"""
Herramienta de LangChain para actualizar una nota existente en la cuenta de un usuario.

Esta herramienta permite al agente de IA modificar el título, el contenido o la
categoría de una nota específica. Es una parte crucial de las operaciones CRUD
(Crear, Leer, Actualizar, Eliminar) para la gestión de notas.

La herramienta opera con el `account_id` universal del usuario, asegurando que
funcione desde cualquier interfaz. Exige que el LLM proporcione el `note_id`
de la nota a modificar, guiando al agente a ser más interactivo si el usuario
no proporciona esta información inicialmente.
"""

import logging
from typing import Type, Optional, Any

# --- Importaciones de LangChain y Pydantic ---
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# --- Importaciones de la Lógica de Negocio ---
from core.notes_manager import update_note

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)


class UpdateNoteInput(BaseModel):
    """
    Schema de entrada para la herramienta de actualización de notas.
    Define los argumentos que el LLM debe proporcionar.
    """
    note_id: int = Field(
        ...,
        description="El ID numérico de la nota que se va a modificar. Este campo es obligatorio."
    )
    new_content: Optional[str] = Field(
        None,
        description="El nuevo contenido para la nota. Si se proporciona, reemplazará completamente el contenido anterior.",
        json_schema_extra={"type": "string"}
    )
    new_title: Optional[str] = Field(
        None,
        description="El nuevo título para la nota.",
        json_schema_extra={"type": "string"}
    )
    new_category: Optional[str] = Field(
        None,
        description="La nueva categoría para la nota.",
        json_schema_extra={"type": "string"}
    )


class UpdateNoteTool(BaseTool):
    """
    Una herramienta de LangChain para que el agente pueda modificar notas existentes.
    """
    name: str = "update_note_tool"
    description: str = (
        "Útil para modificar una nota existente. Requiere el ID numérico de la nota (`note_id`). "
        "Si el usuario intenta modificar una nota sin proporcionar su ID, debes informarle que lo necesitas y sugerirle "
        "que use la herramienta `get_notes_tool` para listar sus notas y encontrar el ID correcto."
    )
    args_schema: Type[BaseModel] = UpdateNoteInput
    account_id: str

    async def _arun(
        self,
        note_id: int,
        new_content: Optional[str] = None,
        new_title: Optional[str] = None,
        new_category: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Ejecuta la lógica de actualización de la nota de forma asíncrona.

        Esta es la corrutina que LangChain llamará. Llama a la función de lógica
        de negocio (`update_note`) con los argumentos validados por Pydantic.

        Returns:
            Un mensaje de confirmación o error para que el agente lo interprete.
        """
        logger.info(f"Ejecutando UpdateNoteTool para la nota {note_id} de la cuenta {self.account_id[:8]}...")
        try:
            result_message = await update_note(
                account_id=self.account_id,
                note_id=note_id,
                new_content=new_content,
                new_title=new_title,
                new_category=new_category
            )
            return result_message
        except Exception as e:
            logger.error(f"Error en UpdateNoteTool para la cuenta {self.account_id[:8]}: {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar actualizar la nota: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en esta arquitectura."""
        raise NotImplementedError("La herramienta 'update_note_tool' solo soporta ejecución asíncrona.")