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
import asyncio
from typing import Type, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

# Importa la función de lógica de notas.
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
    
    # ¡EL CAMBIO CLAVE! Ahora requerimos el identificador universal de la cuenta.
    # El LLM debe recibir este ID del contexto de la conversación y pasarlo aquí.
    
    # El título opcional para la nota.
    title: str = Field(default="", description="Un título opcional para la nota.")
    
    # La categoría opcional para organizar la nota.
    category: str = Field(default="General", description="Una categoría opcional para la nota, como 'Trabajo', 'Personal', 'Ideas'.")


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
    account_id: str

    async def _arun(
        self,
        content: str,
        title: str = "",
        category: str = "General",
        **kwargs: Any,
    ) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Este método llama a la función `add_note` del gestor de notas,
        pasándole los datos validados para crear la nota en la base de datos.

        Args:
            content: El texto de la nota.
            title: El título de la nota (vacío si no se proporciona).
            category: La categoría de la nota (por defecto "General").

        Returns:
            Una cadena de texto confirmando el resultado de la operación.
        """
        if not self.account_id or not content:
            return "Error: Se requiere el ID de la cuenta y el contenido para guardar una nota."
        
        try:
            result_dict = await add_note(
                account_id=self.account_id,
                content=content,
                title=title if title else None,
                category=category if category else None
            )
            logger.info(f"Nota añadida exitosamente para la cuenta {self.account_id}.")
            
            # Crear mensaje de confirmación a partir del diccionario retornado
            note_title = result_dict.get('title', 'Sin título')
            note_id = result_dict.get('id')
            result_message = f"✅ Nota guardada exitosamente con ID {note_id}: '{note_title}'"
            
            return result_message 
        except Exception as e:
            logger.error(f"Error en AddNoteTool para la cuenta {self.account_id}: {e}", exc_info=True)

            return f"Ocurrió un error al intentar guardar la nota: {e}"
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en esta herramienta."""
        raise NotImplementedError("add_note_tool no soporta ejecución síncrona.")
