# tools/get_notes_tool.py

"""
Herramienta de LangChain para obtener las notas de una cuenta de usuario.

Esta herramienta permite al agente de IA buscar y listar las notas guardadas
por un usuario. Puede filtrar por categoría o buscar por palabras clave en el
título y contenido.

Al igual que las otras herramientas de esta arquitectura, es completamente
agnóstica de la plataforma. Opera utilizando el `account_id` universal,
lo que garantiza que pueda ser llamada desde cualquier interfaz (Telegram, web, etc.)
que se conecte al backend central.
"""

import logging
from typing import Type, Optional, Any

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de notas.
# (Asumimos que esta función también será refactorizada para usar account_id).
from telegram_bot.notes_manager import get_notes

logger = logging.getLogger(__name__)


class GetNotesInput(BaseModel):
    """
    Define los parámetros de entrada para la herramienta `get_notes_tool`.
    El `account_id` es el único campo estrictamente requerido.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID) de la cuenta del usuario. Este campo ES OBLIGATORIO."
    )
    category: Optional[str] = Field(
        None,
        description="Filtra las notas por una categoría específica. Ejemplo: 'Trabajo', 'Ideas'."
    )
    search_query: Optional[str] = Field(
        None,
        description="Busca un texto específico en el título o contenido de las notas. Ejemplo: 'receta de pastel'."
    )


class GetNotesTool(BaseTool):
    """
    Una herramienta para que el agente busque y recupere notas de un usuario.
    """
    name = "get_notes_tool"
    description = (
        "Útil para cuando un usuario quiere ver, listar o buscar sus notas. "
        "Permite filtrar las notas por una categoría o buscar por palabras clave. "
        "Si el usuario solo dice 'muéstrame mis notas', no se necesita 'category' ni 'search_query'."
    )
    args_schema: Type[BaseModel] = GetNotesInput

    async def _arun(
        self,
        account_id: str,
        category: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> str:
        """
        Ejecuta la herramienta de forma asíncrona.

        Invoca la función `get_notes` del gestor de notas, pasándole el `account_id`
        y los filtros opcionales para devolver la lista de notas al agente.

        Args:
            account_id: El UUID de la cuenta del usuario.
            category: La categoría por la que filtrar (opcional).
            search_query: El término de búsqueda para filtrar (opcional).

        Returns:
            Una cadena de texto con la lista de notas formateada o un mensaje
            indicando que no se encontraron notas.
        """
        if not account_id:
            # Esta comprobación es una defensa adicional. Pydantic ya debería haberlo validado.
            logger.error("Se intentó llamar a GetNotesTool sin un account_id.")
            return "Error: No se pudo identificar la cuenta del usuario para buscar las notas."

        logger.info(f"Buscando notas para la cuenta {account_id} con filtros: Categoria='{category}', Query='{search_query}'")

        try:
            # Llamamos a la función de lógica de negocio con el account_id
            return await get_notes(
                account_id=account_id,
                category=category,
                search_query=search_query
            )
        except Exception as e:
            logger.error(f"Error al ejecutar get_notes para la cuenta {account_id}: {e}", exc_info=True)
            return "Ocurrió un error inesperado al intentar buscar tus notas."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en esta arquitectura."""
        raise NotImplementedError("get_notes_tool no soporta ejecución síncrona.")
