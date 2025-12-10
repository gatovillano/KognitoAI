from typing import Union, Type, Optional, List
from pydantic import BaseModel, Field
import asyncio
import json
from core.memory_manager import get_relevant_memories
from langchain_core.tools import BaseTool

class KnowledgeSearchInput(BaseModel):
    """Esquema de entrada para la herramienta de búsqueda de conocimiento."""
    query: Optional[str] = Field(None, description="La consulta de búsqueda")
    content_types: Optional[List[str]] = Field(None, description="Lista de tipos de contenido: user_memories, user_documents, etc.")
    filter_topics: Optional[List[str]] = Field(None, description="Lista de topics para filtrar")
    category: Optional[str] = Field(None, description="Categoría automática del LLM")
    k: Optional[int] = Field(10, description="Número máximo de resultados a devolver")
    hybrid_search: bool = Field(True, description="Usar búsqueda híbrida (semántica + texto completo)")
    reranking: bool = Field(True, description="Usar reranking para mejorar la relevancia")
    document_name: Optional[str] = Field(None, description="El nombre exacto de un documento específico (ej: 'Reporte Anual 2023.pdf') para buscar solo en él.")
    document_id: Optional[str] = Field(None, description="El ID único de un documento específico (UUID) para buscar solo en él.")

class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = (
        "🧠 BÚSQUEDA AVANZADA EN BASE DE CONOCIMIENTO - Úsala para responder preguntas buscando en notas, documentos y conversaciones del usuario. "
        "Es ideal para consultas complejas que requieren encontrar información específica y relevante. "
        "Permite filtrar por tipo de contenido, temas y categorías para resultados más precisos. "
        "Puedes especificar un documento por su nombre exacto (ej. 'Reporte Anual 2023.pdf') o por su ID único si lo conoces para focalizar la búsqueda."
    )
    args_schema: Type[BaseModel] = KnowledgeSearchInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace (NULL = General), inyectado automáticamente.")
    team_id: Optional[str] = Field(None, description="ID del team propietario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="ID de Telegram del usuario, inyectado automáticamente.")

    def _run(
        self,
        query: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        filter_topics: Optional[List[str]] = None,
        category: Optional[str] = None,
        k: int = 10,
        hybrid_search: bool = True,
        reranking: bool = True,
        document_name: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> str:
        return asyncio.run(self._arun(
            query=query,
            content_types=content_types,
            filter_topics=filter_topics,
            category=category,
            k=k,
            hybrid_search=hybrid_search,
            reranking=reranking,
            document_name=document_name,
            document_id=document_id,
        ))

    async def _arun(
        self,
        query: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        filter_topics: Optional[List[str]] = None,
        category: Optional[str] = None,
        k: int = 10,
        hybrid_search: bool = True,
        reranking: bool = True,
        document_name: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> str:
        """Versión asíncrona de la búsqueda de conocimiento."""
        try:
            if not query:
                return json.dumps({
                    "status": "error",
                    "error": "Por favor, proporciona una consulta de búsqueda (query).",
                    "query": ""
                }, ensure_ascii=False)

            explicit_document_ids = None

            if document_name:
                from core.memory_manager import list_user_documents
                docs = await list_user_documents(
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                )
                found_doc = next((d for d in docs if d.get("file_name") == document_name), None)
                if found_doc and found_doc.get("document_id"):
                    explicit_document_ids = [found_doc["document_id"]]
                    logger.info(f"🔍 Documento '{document_name}' encontrado con ID: {explicit_document_ids[0]}")
                else:
                    logger.warning(f"Documento '{document_name}' no encontrado para la cuenta {self.account_id} en workspace {self.workspace_id}.")
                    return f"No se encontró el documento '{document_name}' en tu base de conocimiento."
            elif document_id:
                explicit_document_ids = [document_id]
                logger.info(f"🔍 Buscando directamente con document_id: {document_id}")

            results = await get_relevant_memories(
                account_id=self.account_id,
                query=query,
                content_types=content_types,
                filter_topics=filter_topics,
                workspace_id=self.workspace_id,
                k=k,
                hybrid_search=hybrid_search,
                reranking=reranking,
                explicit_document_ids=explicit_document_ids,
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
                    "document_name": document_name,
                    "document_id": document_id,
                },
                "results": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": query
            }, ensure_ascii=False)