# tools/memory_add_tool.py

"""
Herramienta de LangChain para añadir una memoria específica a la base de datos
vectorial de una cuenta de usuario.

Esta herramienta permite al agente de IA guardar fragmentos de información
factual o contextual (memorias) que pueden ser recuperados más tarde a través
de búsqueda semántica. Es crucial para que el asistente "recuerde" detalles
de conversaciones anteriores más allá del perfil general del usuario.

Opera de forma agnóstica a la plataforma, utilizando el `account_id` universal
para asegurar que la memoria se asocie con la cuenta correcta, sin importar si
la información se originó en Telegram, una interfaz web, etc.
"""

import logging
import asyncio # AGREGAR ESTA LÍNEA
from typing import Any, Optional, Type

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de memoria.
from core.memory_manager import add_memory_to_vector_db
from tools.proactive_knowledge_linker_tool import proactive_knowledge_linker_trigger

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class MemoryAddInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de adición de memoria.
    Valida que todos los argumentos necesarios sean proporcionados por el LLM.
    """
    content: str = Field(
        ...,
        description="El texto o información específica que debe ser guardado en la memoria a largo plazo."
    )
    # Cambiamos telegram_id por account_id para que sea universal.
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    type: str = Field(
        "general_memory",
        description="Un tipo o categoría opcional para la memoria (ej: 'hecho', 'idea', 'cita', 'preferencia')."
    )


class MemoryAddTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `add_memory_to_vector_db`
    para guardar una memoria en la base de datos vectorial del usuario.
    """
    name: str = "memory_add_tool"
    description: str = (
        "Útil para guardar hechos, ideas, notas o detalles específicos de la conversación "
        "en la memoria vectorial a largo plazo del usuario. Usa esta herramienta siempre que el "
        "usuario declare un hecho o detalle que podría ser útil recordar más adelante, o cuando "
        "identifiques información valiosa para almacenar en conversaciones generales. No la uses para notas de tareas o recordatorios."
    )
    args_schema: Type[BaseModel] = MemoryAddInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, content: str, account_id: str, type: Optional[str] = "general_memory", **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            content: El contenido de la memoria a guardar.
            account_id: El ID universal de la cuenta del usuario.
            type: El tipo de memoria a guardar.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        if not content or not content.strip():
            logger.warning(f"Se llamó a MemoryAddTool para la cuenta '{account_id}' con contenido vacío.")
            return "No se puede guardar contenido vacío en la memoria."

        log_content = content[:100] + '...' if len(content) > 100 else content
        logger.info(f"Ejecutando MemoryAddTool para la cuenta '{account_id}' (Tipo: {type}): '{log_content}'")

        try:
            await add_memory_to_vector_db(
                account_id=account_id,
                content=content,
                type=type or "general_memory"  # Asegura que el tipo no sea None
            )
            logger.info(f"Memoria añadida exitosamente para la cuenta '{account_id}'.")
            # Llamada al trigger proactivo tras añadir la memoria
            new_entry = {
                'account_id': account_id,
                'content': content,
                'type': type or "general_memory"
            }
            # CORRECCIÓN: Programar como tarea en segundo plano
            asyncio.create_task(proactive_knowledge_linker_trigger(new_entry))
            return "La información ha sido añadida a tu memoria a largo plazo."
        except Exception as e:
            logger.error(f"Error en MemoryAddTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error al intentar guardar la información en tu memoria: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("MemoryAddTool no soporta ejecución síncrona.")
