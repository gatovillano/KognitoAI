from typing import Optional, List, Any
import json
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from core.memory_manager import get_relevant_memories
import logging

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field, validator

class KnowledgeSearchInput(BaseModel):
    query: str = Field(description="La consulta de búsqueda para encontrar información relevante.")
    content_types: Optional[List[str]] = Field(None, description="Lista de tipos de contenido para filtrar la búsqueda (ej. 'document', 'note').")
    filter_topics: Optional[List[str]] = Field(None, description="Lista de temas para filtrar la búsqueda.")
    category: Optional[str] = Field(None, description="Categoría para filtrar la búsqueda.")
    k: int = Field(10, description="Número de resultados a devolver.")
    hybrid_search: bool = Field(True, description="Si se debe utilizar la búsqueda híbrida (semántica y de palabras clave).")
    reranking: bool = Field(True, description="Si se deben reordenar los resultados para mejorar la relevancia.")
    document_name: Optional[str] = Field(None, description="Nombre exacto de un documento para focalizar la búsqueda.")
    document_id: Optional[str] = Field(None, description="ID único de un documento para focalizar la búsqueda.")

    @validator('filter_topics', 'content_types', pre=True, allow_reuse=True)
    def parse_stringified_list(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                loaded_v = json.loads(v)
                if isinstance(loaded_v, list):
                    return loaded_v
                return [str(loaded_v)]
            except json.JSONDecodeError:
                return [v]
        if isinstance(v, list):
            return v
        return [str(v)]

class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = """🧠 BÚSQUEDA AVANZADA EN BASE DE CONOCIMIENTO - Úsala para responder preguntas buscando en notas, documentos y conversaciones del usuario. Es ideal para consultas complejas que requieren encontrar información específica y relevante. Permite filtrar por tipo de contenido, temas y categorías para resultados más precisos. Puedes especificar un documento por su nombre exacto (ej. 'Reporte Anual 2023.pdf') o por su ID único si lo conoces para focalizar la búsqueda."""
    args_schema: type[BaseModel] = KnowledgeSearchInput
    account_id: Optional[str] = None
    workspace_id: Optional[str] = None

    async def _arun(
        self,
        query: str,
        content_types: Optional[List[str]] = None,
        filter_topics: Optional[List[str]] = None,
        category: Optional[str] = None,
        k: int = 10,
        hybrid_search: bool = True,
        reranking: bool = True,
        document_name: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> str:
        try:
            if not self.account_id:
                raise ValueError("El 'account_id' es requerido para la búsqueda en la base de conocimiento, pero no fue proporcionado.")

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
                    "hybrid_search": hybrid_search,
                    "reranking": reranking,
                    "document_name": document_name,
                    "document_id": document_id,
                },
                "results": formatted_results
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error en KnowledgeSearchTool: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": query
            }, ensure_ascii=False)

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("KnowledgeSearchTool no soporta ejecución síncrona.")