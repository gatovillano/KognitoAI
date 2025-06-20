# tools/add_note_tool.py

"""
Herramienta de LangChain para añadir una nueva nota a la base de datos de una cuenta de usuario.

Esta herramienta se integra con el agente de IA para permitirle crear notas
basándose en las peticiones del usuario. Sigue el patrón de diseño "Responsabilidad del LLM",
donde el modelo de lenguaje es responsable de proporcionar todos los datos necesarios,
incluyendo el identificador universal de la cuenta del usuario (`account_id`).

Esto desacopla la herramienta de cualquier plataforma específica (Telegram, web, etc.)
y la hace reutilizable y robusta dentro de un backend centralizado.
"""

import logging
from typing import Type, Optional, Any
from pydantic.v1 import BaseModel, Field
from langchain.tools import BaseTool

# Importa la función de lógica de notas. (Esta función también deberá ser
# refactorizada para aceptar account_id en lugar de telegram_id).
from core.notes_manager import add_note

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)


class AddNoteInput(BaseModel):
    """
    Define los argumentos de entrada que la herramienta `add_note_tool` espera.
    Pydantic se encarga de validar que estos argumentos se proporcionen correctamente.
    """
    # El contenido principal de la nota. Es un campo requerido.
    content: str = Field(description="El contenido principal de la nota a guardar.")
    
    # El título opcional para la nota.
    title: Optional[str] = Field(None, description="Un título opcional para la nota.")
    
    # La categoría opcional para organizar la nota.
    category: Optional[str] = Field(None, description="Una categoría opcional para la nota, como 'Trabajo', 'Personal', 'Ideas'.")
    
    # ¡EL CAMBIO CLAVE! Ahora requerimos el identificador universal de la cuenta.
    # El LLM debe recibir este ID del contexto de la conversación y pasarlo aquí.
    account_id: str = Field(description="El identificador universal (UUID) de la cuenta del usuario.")


class AddNoteTool(BaseTool):
    """
    Una herramienta de LangChain que permite al agente de IA crear y guardar una nueva nota
    para un usuario específico, identificado por su `account_id`.
    """
    name: str = "add_note_tool"
    description: str = (
        "Útil para cuando un usuario quiere crear o guardar una nueva nota, apunte o idea. "
        "Debes proporcionar el contenido y, opcionalmente, un título y una categoría. "
        "El 'account_id' del usuario es un argumento obligatorio."
    )
    args_schema: Type[BaseModel] = AddNoteInput

    async def _arun(
        self,
        account_id: str,
        content: str,
        title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Este método llama a la función `add_note` del gestor de notas,
        pasándole los datos validados para crear la nota en la base de datos.

        Args:
            account_id: El UUID de la cuenta del usuario.
            content: El texto de la nota.
            title: El título opcional.
            category: La categoría opcional.

        Returns:
            Una cadena de texto confirmando el resultado de la operación.
        """
        if not account_id or not content:
            return "Error: Se requiere el ID de la cuenta y el contenido para guardar una nota."
        
        try:
            # NOTA: La función `add_note` también necesita ser actualizada para
            # buscar y guardar usando `account_id` en lugar de `telegram_id`.
            # Asumimos que ese cambio ya está hecho en `notes_manager.py`.
            result_message = await add_note(
                account_id=account_id,
                content=content,
                title=title,
                category=category
            )
            logger.info(f"Nota añadida exitosamente para la cuenta {account_id}.")
            return result_message
        except Exception as e:
            logger.error(f"Error en AddNoteTool para la cuenta {account_id}: {e}", exc_info=True)
            return f"Ocurrió un error al intentar guardar la nota: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en esta herramienta."""
        raise NotImplementedError("add_note_tool no soporta ejecución síncrona.")
