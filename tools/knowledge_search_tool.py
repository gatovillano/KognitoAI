from typing import Union, Type, Optional, List
from pydantic import BaseModel, Field
import asyncio
import json
from core.memory_manager import get_relevant_memories
from langchain_core.tools import BaseTool

class KnowledgeSearchInput(BaseModel):
    """Esquema de entrada para la herramienta de búsqueda de conocimiento."""
    query: str = Field(..., description="La consulta de búsqueda")
    content_types: Optional[List[str]] = Field(None, description="Lista de tipos de contenido: user_memories, user_documents, etc.")
    filter_topics: Optional[List[str]] = Field(None, description="Lista de topics para filtrar")
    category: Optional[str] = Field(None, description="Categoría automática del LLM")
    k: Optional[int] = Field(10, description="Número máximo de resultados a devolver")
    hybrid_search: bool = Field(True, description="Usar búsqueda híbrida (semántica + texto completo)")
    reranking: bool = Field(True, description="Usar reranking para mejorar la relevancia")

class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = (
        "🧠 BÚSQUEDA AVANZADA EN BASE DE CONOCIMIENTO - Úsala para responder preguntas buscando en notas, documentos y conversaciones del usuario. "
        "Es ideal para consultas complejas que requieren encontrar información específica y relevante. "
        "Permite filtrar por tipo de contenido, temas y categorías para resultados más precisos."
    )
    args_schema: Type[BaseModel] = KnowledgeSearchInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace (NULL = General), inyectado automáticamente.")
    team_id: Optional[str] = Field(None, description="ID del team propietario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="ID de Telegram del usuario, inyectado automáticamente.")

    def _run(
        self,
        query: str,
        content_types: Optional[List[str]] = None,
        filter_topics: Optional[List[str]] = None,
        category: Optional[str] = None,
        k: int = 10,
        hybrid_search: bool = True,
        reranking: bool = True,
    ) -> str:
        return asyncio.run(self._arun(
            query=query,
            content_types=content_types,
            filter_topics=filter_topics,
            category=category,
            k=k,
            hybrid_search=hybrid_search,
            reranking=reranking,
        ))

    async def _arun(
        self,
        query: str,
        content_types: Optional[List[str]] = None,
        filter_topics: Optional[List[str]] = None,
        category: Optional[str] = None,
        k: int = 10,
        hybrid_search: bool = True,
        reranking: bool = True,
    ) -> str:
        """Versión asíncrona de la búsqueda de conocimiento."""
        try:
            results = await get_relevant_memories(
                account_id=self.account_id,
                query=query,
                content_type=category,
                filter_topics=filter_topics,
                workspace_id=self.workspace_id,
                team_id=self.team_id,
                k=k,
                hybrid_search=hybrid_search,
                reranking=reranking,
            )
            
            formatted_results = []
            if results and results.sources:
                for i, source in enumerate(results.sources):
                    formatted_result = {
                        "rank": i + 1,
                        "content": source.snippet,
                        "similarity_score": source.metadata.get("similarity_score"),
                        "topic": source.metadata.get("topic"),
                        "category": source.metadata.get("category"),
                        "workspace_id": source.metadata.get("workspace_id"),
                        "team_id": source.metadata.get("team_id"),
                        "metadata": source.metadata,
                    }
                    formatted_results.append(formatted_result)
            
            return json.dumps({
                "status": "success",
                "query": query,
                "total_results": len(formatted_results),
                "filters_applied": {
                    "content_types": content_types,
                    "filter_topics": filter_topics,
                    "category": category,
                    "workspace_id": self.workspace_id,
                    "team_id": self.team_id,
                    "hybrid_search": hybrid_search,
                    "reranking": reranking,
                },
                "results": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": query
            }, ensure_ascii=False)