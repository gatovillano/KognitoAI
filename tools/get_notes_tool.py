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

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de notas.
# (Asumimos que esta función también será refactorizada para usar account_id).
from core.notes_manager import get_notes

logger = logging.getLogger(__name__)


class GetNotesInput(BaseModel):
    """
    Define los parámetros de entrada para la herramienta `get_notes_tool`.
    El `account_id` es el único campo estrictamente requerido.
    """

    category: Optional[str] = Field(
        None,
        description="Filtra las notas por una categoría específica. Ejemplo: 'Trabajo', 'Ideas'.",
        json_schema_extra={"type": "string"}
    )
    search_query: Optional[str] = Field(
        None,
        description="Busca un texto específico en el título o contenido de las notas. "
                   "Ejemplo: 'receta de pastel'.",
        json_schema_extra={"type": "string"}
    )


class GetNotesTool(BaseTool):
    """
    Una herramienta para que el agente busque y recupere notas de un usuario.
    """
    name: str = "get_notes_tool"
    description: str = ("Útil para cuando un usuario quiere ver, listar o buscar sus notas. "
                       "Permite filtrar las notas por una categoría o buscar por palabras clave. "
                       "Si el usuario solo dice 'muéstrame mis notas', no se necesita 'category' "
                       "ni 'search_query'.")

    args_schema: Type[BaseModel] = GetNotesInput
    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    async def _arun(
        self,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """
        Ejecuta la herramienta de forma asíncrona.

        Invoca la función `get_notes` del gestor de notas, pasándole el `account_id`
        y los filtros opcionales para devolver la lista de notas al agente.

        Args:
            category: La categoría por la que filtrar (opcional).
            search_query: El término de búsqueda para filtrar (opcional).
            run_manager: Gestor de ejecución para obtener configuración.
            **kwargs: Argumentos adicionales.

        Returns:
            Una cadena de texto con la lista de notas formateada o un mensaje
            indicando que no se encontraron notas.
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
        if not account_id:
            logger.error("Se intentó llamar a GetNotesTool sin un account_id.")
            return "Error: No se pudo identificar la cuenta del usuario para buscar las notas."

        logger.info("Buscando notas para la cuenta %s con filtros: Categoria='%s', Query='%s'",
                    account_id, category, search_query)

        try:
            # Llamamos a la función de lógica de negocio con el account_id
            return await get_notes(
                account_id=account_id,
                category=category,
                search_query=search_query
            )
        except Exception as e:
            logger.error("Error al ejecutar get_notes para la cuenta %s: %s",
                        account_id, e, exc_info=True)
            return "Ocurrió un error inesperado al intentar buscar tus notas."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en esta arquitectura."""
        raise NotImplementedError("get_notes_tool no soporta ejecución síncrona.")
