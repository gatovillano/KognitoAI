from typing import Dict, List, Type, Union, Optional, Any
from pydantic import BaseModel, Field
import asyncio
import json
from core.memory_manager import search_vector_db, search_vector_db_optimized
from langchain_core.tools import BaseTool

class VectorDBSearchInput(BaseModel):
    """Esquema de entrada para la herramienta de búsqueda vectorial."""
    query: str = Field(..., description="Consulta de búsqueda", json_schema_extra={"type": "string"})
    collection_name: Optional[str] = Field(None, description="Nombre de la colección", json_schema_extra={"type": "string"})
    topic: Optional[str] = Field(None, description="Tema específico", json_schema_extra={"type": "string"})
    workspace_id: Optional[str] = Field(None, description="ID del workspace", json_schema_extra={"type": "string"})
    k: int = Field(10, description="Número de resultados", json_schema_extra={"type": "integer"})

class VectorDBSearchTool(BaseTool):
    """Herramienta para búsqueda en base de datos vectorial."""
    name: str = "vector_db_search"
    description: str = "Busca información en la base de datos vectorial del usuario"
    args_schema: Type[BaseModel] = VectorDBSearchInput

    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    def _run(
        self,
        query: str,
        collection_name: Optional[str] = None,
        topic: Optional[str] = None,
        workspace_id: Optional[str] = None,
        k: int = 10,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """
        Realiza la búsqueda en la base de datos vectorial de forma síncrona.
        """
        return asyncio.run(self._arun(query, collection_name, topic, workspace_id, k, run_manager, **kwargs))

    async def _arun(
        self,
        query: str,
        collection_name: Optional[str] = None,
        topic: Optional[str] = None,
        workspace_id: Optional[str] = None,
        k: int = 10,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """
        Realiza la búsqueda en la base de datos vectorial de forma asíncrona.
        """
        try:
            results = await search_vector_db(
                account_id=self.account_id,
                query=query,
                collection_name=collection_name,
                topic=topic,
                workspace_id=workspace_id,
                k=k,
            )

            if not results:
                return f"No se encontraron resultados para la consulta: {query}"

            # Formatear resultados como string
            formatted_results = []
            for i, result in enumerate(results, 1):
                content = result.get('content', 'Sin contenido')
                metadata = result.get('metadata', {})
                topic_info = metadata.get('topic', 'Sin tema')
                formatted_results.append(f"{i}. {content[:200]}... (Tema: {topic_info})")

            return "\n".join(formatted_results)
        except Exception as e:
            return f"Error en la búsqueda vectorial: {str(e)}"