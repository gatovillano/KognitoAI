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
<<<<<<< HEAD
    # Eliminado: account_id. Ahora solo se obtiene de la configuración del agente.
=======
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
    # El 'type' ahora es una clasificación general de la memoria.
    type: str = Field(
        "user_memory", # Valor por defecto más específico para memorias del usuario
        description=(
            "El tipo general de la memoria. Ejemplos: 'user_memory' (para hechos, intereses, preferencias del usuario), "
            "'chat_summary' (para resúmenes de conversaciones), 'document_chunk' (para fragmentos de documentos)."
        )
    )
    # Añadimos 'category' para una clasificación más específica, que irá en los metadatos.
    category: Optional[str] = Field(
        None,
        description=(
            "Una categoría más específica para la memoria. "
            "Úsala para clasificar el 'content' dentro de su 'type' general. "
            "Ejemplos si 'type' es 'user_memory': 'interes', 'hecho', 'preferencia', 'habilidad', 'meta', 'idea'. "
            "Ejemplos si 'type' es 'chat_summary': 'resolucion_problema', 'planificacion_proyecto', 'discusion_general'. "
            "Si no es aplicable o no se puede inferir, déjalo como None."
        )
    )
    # Añadimos 'workspace_id' para asociar la memoria con un workspace específico.
    workspace_id: Optional[str] = Field(
        None,
        description="El identificador del workspace (UUID en formato string) para asociar la memoria con un workspace específico, si aplica."
    )


class MemoryAddTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `add_memory_to_vector_db`
    para guardar una memoria en la base de datos vectorial del usuario.
    """
    name: str = "memory_add_tool"
    description: str = (
        "CRUCIAL: Herramienta esencial para guardar información valiosa en la memoria vectorial a largo plazo del usuario. "
        "Úsala ACTIVAMENTE y con FRECUENCIA siempre que el usuario declare un hecho, preferencia, hábito, interés, "
        "habilidad, meta, o cualquier detalle personal o idea que pueda ser útil recordar más adelante para personalizar "
        "respuestas futuras y mejorar la asistencia. "
        "Define el 'type' para una clasificación general (ej. 'user_memory', 'chat_summary'). "
        "Define la 'category' para una clasificación más específica dentro del 'type' (ej. 'interes', 'hecho', 'idea'). "
        "NO la uses para notas de tareas o recordatorios que tienen su propia gestión."
    )
    args_schema: Type[BaseModel] = MemoryAddInput
    return_direct: bool = False
    account_id: str

<<<<<<< HEAD
    async def _arun(self, content: str, type: Optional[str] = "user_memory", category: Optional[str] = None, workspace_id: Optional[str] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> str:
=======
    async def _arun(self, content: str, account_id: str, type: Optional[str] = "user_memory", category: Optional[str] = None, workspace_id: Optional[str] = None, **kwargs: Any) -> str:
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            content: El contenido de la memoria a guardar.
            type: El tipo general de memoria a guardar (ej. 'user_memory').
            category: La categoría específica de la memoria (ej. 'interes').
            workspace_id: El ID del workspace para asociar la memoria (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
<<<<<<< HEAD
        if not self.account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        if not content or not content.strip():
            logger.warning(f"Se llamó a MemoryAddTool para la cuenta '{self.account_id}' con contenido vacío.")
            return "No se puede guardar contenido vacío en la memoria."

        log_content = content[:100] + '...' if len(content) > 100 else content
        logger.info(f"Ejecutando MemoryAddTool para la cuenta '{self.account_id}' (Tipo: {type}, Categoría: {category}, Workspace: {workspace_id}): '{log_content}'")
=======
        if not content or not content.strip():
            logger.warning(f"Se llamó a MemoryAddTool para la cuenta '{account_id}' con contenido vacío.")
            return "No se puede guardar contenido vacío en la memoria."

        log_content = content[:100] + '...' if len(content) > 100 else content
        logger.info(f"Ejecutando MemoryAddTool para la cuenta '{account_id}' (Tipo: {type}, Categoría: {category}, Workspace: {workspace_id}): '{log_content}'")
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)

        try:
            final_type = type if type else "user_memory"
            await add_memory_to_vector_db(
<<<<<<< HEAD
                account_id=self.account_id,
=======
                account_id=account_id,
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
                content=content,
                type=final_type,
                workspace_id=workspace_id,
                topic=category if category else "general"
            )
<<<<<<< HEAD
            logger.info(f"Memoria añadida exitosamente para la cuenta '{self.account_id}'.")

            new_entry = {
                'account_id': self.account_id,
=======
            logger.info(f"Memoria añadida exitosamente para la cuenta '{account_id}'.")

            new_entry = {
                'account_id': account_id,
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
                'content': content,
                'type': final_type,
                'category': category if category else "general"
            }
            asyncio.create_task(proactive_knowledge_linker_trigger(new_entry))
            
            return "La información ha sido añadida a tu memoria a largo plazo."
        except Exception as e:
<<<<<<< HEAD
            logger.error(f"Error en MemoryAddTool para la cuenta '{self.account_id}': {e}", exc_info=True)
=======
            logger.error(f"Error en MemoryAddTool para la cuenta '{account_id}': {e}", exc_info=True)
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
            return f"Ocurrió un error al intentar guardar la información en tu memoria: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("MemoryAddTool no soporta ejecución síncrona.")
