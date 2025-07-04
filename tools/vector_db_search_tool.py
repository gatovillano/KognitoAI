from typing import Dict, List, Type, Union, Optional
from pydantic import BaseModel, Field
import asyncio
import json
from core.memory_manager import search_vector_db, search_vector_db_optimized
from langchain.tools import BaseTool

class VectorDBSearchInput(BaseModel):
    account_id: str = Field(..., description="El identificador de la cuenta del usuario")
    query: str = Field(..., description="La consulta de búsqueda")
    collection_name: Optional[str] = Field(None, description="Nombre de la colección (user_memories o user_documents)", json_schema_extra={"type": "string"})
    topic: Optional[str] = Field(None, description="Tema específico para filtrar", json_schema_extra={"type": "string"})
    workspace_id: Optional[str] = Field(None, description="ID del workspace para filtrar", json_schema_extra={"type": "string"})
    k: Optional[int] = Field(10, description="Número de resultados a devolver", json_schema_extra={"type": "integer"})

class VectorDBSearchTool(BaseTool):
    name: str = "vector_db_search"
    description: str = (
        "🔧 BÚSQUEDA VECTORIAL AVANZADA - Usa esta herramienta cuando necesites: "
        "• Control granular sobre parámetros específicos de búsqueda "
        "• Búsquedas en colecciones específicas (user_memories o user_documents) "
        "• Filtrado por topic/workspace conocidos de antemano "
        "• Búsquedas técnicas que requieren parámetros exactos "
        "\n⚠️ NOTA: Si la consulta es en lenguaje natural y no tienes parámetros claros, "
        "usa 'natural_query_interpreter' en su lugar para interpretación automática. "
        "\n⚡ OPTIMIZADO: 10-50x más rápido con búsquedas directas sin JOINs."
    )
    
    args_schema: Type[BaseModel] = VectorDBSearchInput
    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    def _run(
        self,
        account_id: str,
        query: str,
        collection_name: Union[str, None] = None,
        topic: Union[str, None] = None,
        workspace_id: Union[str, None] = None,
        k: Union[int, None] = 10,
    ) -> List[Dict]:
        """
        Realiza la búsqueda en la base de datos vectorial.
        """
        return asyncio.run(search_vector_db(
            account_id=account_id,
            query=query,
            collection_name=collection_name,
            topic=topic,
            workspace_id=workspace_id,
            k=k,
        ))

    async def _arun(
        self,
        account_id: str,
        query: str,
        collection_name: Union[str, None] = None,
        topic: Union[str, None] = None,
        workspace_id: Union[str, None] = None,
        k: Union[int, None] = 10,
    ) -> List[Dict]:
        """
        Realiza la búsqueda en la base de datos vectorial de forma asíncrona.
        """
        return await search_vector_db(
            account_id=account_id,
            query=query,
            collection_name=collection_name,
            topic=topic,
            workspace_id=workspace_id,
            k=k,
        )