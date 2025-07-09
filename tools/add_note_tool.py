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
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

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
        "ACTUALIZADO: Ahora soporta aislamiento por workspace y actualiza columnas optimizadas automáticamente. "
        "Debes proporcionar el contenido y, opcionalmente, un título y una categoría."
    )
    args_schema: Type[BaseModel] = AddNoteInput
    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    async def _arun(
        self,
        content: str,
        title: str = "",
        category: str = "General",
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Este método llama a la función `add_note` del gestor de notas,
        pasándole los datos validados para crear la nota en la base de datos.

        Args:
            content: El texto de la nota.
            title: El título de la nota (vacío si no se proporciona).
            category: La categoría de la nota (por defecto "General").
            run_manager: Gestor de ejecución para obtener configuración.
            **kwargs: Argumentos adicionales.

        Returns:
            Una cadena de texto confirmando el resultado de la operación.
        """
        # Obtener account_id del contexto de configuración o instancia
        account_id = None
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
        if not account_id:
            account_id = getattr(self, 'account_id', "")

        # Validar que tenemos account_id
        if not account_id or not content:
            return "Error: Se requiere el ID de la cuenta y el contenido para guardar una nota."
        
        try:
            result_dict = await add_note(
                account_id=account_id,
                content=content,
                title=title if title else None,
                category=category if category else None
            )
            logger.info(f"Nota añadida exitosamente para la cuenta {account_id}.")
            
            # Crear mensaje de confirmación a partir del diccionario retornado
            note_title = result_dict.get('title', 'Sin título')
            note_id = result_dict.get('id')
            result_message = f"✅ Nota guardada exitosamente con ID {note_id}: '{note_title}'"
            
            return result_message 
        except Exception as e:
            logger.error(f"Error en AddNoteTool para la cuenta {account_id}: {e}", exc_info=True)

            return f"Ocurrió un error al intentar guardar la nota: {e}"
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en esta herramienta."""
        raise NotImplementedError("add_note_tool no soporta ejecución síncrona.")
