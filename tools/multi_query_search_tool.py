# tools/multi_query_search_tool.py

"""
Herramienta de búsqueda con múltiples consultas reformuladas (MultiQueryRetriever).
Mejora la recuperación de información generando consultas alternativas y fusionando resultados.
"""

import logging
import asyncio
import json
from typing import Any, Type, Union, Optional, List, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from utils.multi_query_retriever import multi_query_search
from core.citation_models import Source, ToolOutputWithSources  # Importamos las clases necesarias

logger = logging.getLogger(__name__)


class MultiQuerySearchInput(BaseModel):
    """Esquema de entrada para la herramienta de búsqueda multi-consulta."""
    query: str = Field(
        ...,
        description="Consulta de búsqueda original",
        json_schema_extra={"type": "string"}
    )
    content_type: Optional[str] = Field(
        None,
        description="Tipo de contenido a buscar (user_memories, user_documents, etc.)",
        json_schema_extra={"type": "string"}
    )
    topic: Optional[List[str]] = Field(
        None,
        description="Tema(s) específico(s) para filtrar resultados",
        json_schema_extra={"type": "array", "items": {"type": "string"}}
    )
    category: Optional[str] = Field(
        None,
        description="Categoría específica para filtrar resultados",
        json_schema_extra={"type": "string"}
    )
    k: Optional[int] = Field(
        5,
        description="Número máximo de resultados a retornar",
        json_schema_extra={"type": "integer"}
    )
    num_queries: Optional[int] = Field(
        3,
        description="Número de consultas alternativas a generar",
        json_schema_extra={"type": "integer"}
    )
    fusion_method: Optional[str] = Field(
        "rrf",
        description="Método de fusión de resultados ('rrf' o 'simple')",
        json_schema_extra={"type": "string"}
    )
    include_shared: Optional[bool] = Field(
        True,
        description="Incluir contenido compartido del equipo",
        json_schema_extra={"type": "boolean"}
    )
    document_name: Optional[str] = Field(
        None,
        description="El nombre exacto de un documento específico (ej: 'Reporte Anual 2023.pdf') para buscar solo en él."
    )
    document_id: Optional[str] = Field(
        None,
        description="El ID único de un documento específico (UUID) para buscar solo en él."
    )


class MultiQuerySearchTool(BaseTool):
    """
    Herramienta de búsqueda avanzada con múltiples consultas reformuladas.
    Esta herramienta mejora la recuperación de información mediante:
    1. Generación automática de consultas alternativas usando LLM
    2. Búsqueda paralela con todas las consultas
    3. Fusión inteligente de resultados usando Reciprocal Rank Fusion (RRF)
    Ideal para consultas complejas donde una sola reformulación podría no capturar
    todos los aspectos relevantes de la información buscada.
    """
    name: str = "multi_query_search"
    description: str = (
        "🚀 BÚSQUEDA MULTI-CONSULTA AVANZADA - Usa esta herramienta cuando necesites: "
        "• Búsquedas más exhaustivas y precisas "
        "• Capturar diferentes aspectos de un tema complejo "
        "• Mejorar la recuperación de información relevante "
        "• Consultas donde una sola reformulación podría ser insuficiente "
        "• Especificar un documento por su nombre exacto (ej. 'Reporte Anual 2023.pdf') o por su ID único si lo conoces para focalizar la búsqueda. "
        "\n✨ CARACTERÍSTICAS: "
        "• Genera automáticamente consultas alternativas con LLM "
        "• Ejecuta búsquedas paralelas para mayor eficiencia "
        "• Fusiona resultados usando Reciprocal Rank Fusion (RRF) "
        "• Compatible con todos los filtros del sistema (workspace, topic, etc.) "
        "\n⚡ OPTIMIZADO: Aprovecha la infraestructura de búsqueda optimizada de Kognito."
    )
    args_schema: Type[BaseModel] = MultiQuerySearchInput
    account_id: Optional[str] = Field(None, description="ID de la cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace para filtrar resultados, inyectado automáticamente.")
    team_id: Optional[str] = Field(None, description="ID del equipo para filtrar resultados, inyectado automáticamente.")
    telegram_id: Optional[str] = Field(None, description="ID del chat de Telegram para filtrar resultados, inyectado automáticamente.")
    thread_id: Optional[str] = Field(None, description="ID del hilo de conversación para filtrar resultados, inyectado automáticamente.")

    async def _arun(
            self,
            query: str,
            content_type: Union[str, None] = None,
            topic: Union[List[str], None] = None,
            category: Union[str, None] = None,
            k: Union[int, None] = 5,
            num_queries: Union[int, None] = 3,
            fusion_method: Union[str, None] = "rrf",
            include_shared: Union[bool, None] = True,
            document_name: Optional[str] = None,
            document_id: Optional[str] = None,
    ) -> ToolOutputWithSources:
        """
        Ejecuta la búsqueda multi-consulta de forma asíncrona.
        """
        try:
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
                    return ToolOutputWithSources(
                        context_for_llm=json.dumps({
                            "status": "error",
                            "message": f"No se encontró el documento '{document_name}' en tu base de conocimiento.",
                            "results": []
                        }, ensure_ascii=False, indent=2),
                        sources=[]
                    )
            elif document_id:
                explicit_document_ids = [document_id]
                logger.info(f"🔍 Buscando directamente con document_id: {document_id}")

            # Determinar visibility_teams basado en include_shared
            visibility_teams = None if include_shared else []
            results = await multi_query_search(
                account_id=self.account_id,
                query=query,
                content_type=content_type,
                topics=topic, # Aquí topic ya es List[str] o None
                category=category,
                workspace_id=self.workspace_id,
                team_id=self.team_id,
                visibility_teams=visibility_teams,
                k=k or 5,
                num_queries=num_queries or 3,
                fusion_method=fusion_method or "rrf",
                explicit_document_ids=explicit_document_ids,
            )
            if not results:
                return ToolOutputWithSources(
                    context_for_llm=json.dumps({
                        "status": "no_results",
                        "message": "No se encontraron resultados relevantes",
                        "results": []
                    }, ensure_ascii=False, indent=2),
                    sources=[]
                )

            # Formatear resultados para mejor legibilidad
            formatted_results = []
            sources: List[Source] = []
            for i, result in enumerate(results):
                formatted_result = {
                    "rank": i + 1,
                    "content": result.get('document', ''),
                    "metadata": result.get('cmetadata', {}),
                    "topic": result.get('topic'),
                    "category": result.get('category'),
                    "similarity_score": result.get('similarity_score')
                }
                formatted_results.append(formatted_result)
                # Crear objeto Source para cada resultado
                source = Source(
                    id=i + 1,
                    title=result.get('topic') or "Sin título",  # Usar topic como título
                    url="N/A",  # No hay URL disponible
                    snippet=result.get('document', '')[:200],  # Primeros 200 caracteres del documento
                    metadata=result.get('cmetadata', {})
                )
                sources.append(source)

            # Crear el contexto para el LLM
            context_for_llm = json.dumps({
                "status": "success",
                "query": query,
                "method": "multi_query_retrieval",
                "fusion_method": fusion_method or "rrf",
                "num_queries_generated": num_queries or 3,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "document_name": document_name,
                "document_id": document_id,
            }, ensure_ascii=False, indent=2)

            return ToolOutputWithSources(context_for_llm=context_for_llm, sources=sources)

        except Exception as e:
            logger.error(f"❌ Error en MultiQuerySearchTool (async): {e}", exc_info=True)
            return ToolOutputWithSources(
                context_for_llm=json.dumps({
                    "status": "error",
                    "message": f"Error ejecutando búsqueda multi-consulta: {str(e)}",
                    "results": []
                }, ensure_ascii=False, indent=2),
                sources=[]
            )

    def _run(
            self,
            query: str,
            content_type: Union[str, None] = None,
            topic: Union[List[str], None] = None,
            category: Union[str, None] = None,
            k: Union[int, None] = 5,
            num_queries: Union[int, None] = 3,
            fusion_method: Union[str, None] = "rrf",
            include_shared: Union[bool, None] = True,
            document_name: Optional[str] = None,
            document_id: Optional[str] = None,
    ) -> str:
        """
        Ejecuta la búsqueda multi-consulta de forma síncrona.
        """
        try:
            explicit_document_ids = None

            if document_name:
                from core.memory_manager import list_user_documents
                docs = asyncio.run(list_user_documents(
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                ))
                found_doc = next((d for d in docs if d.get("file_name") == document_name), None)
                if found_doc and found_doc.get("document_id"):
                    explicit_document_ids = [found_doc["document_id"]]
                    logger.info(f"🔍 Documento '{document_name}' encontrado con ID: {explicit_document_ids[0]}")
                else:
                    logger.warning(f"Documento '{document_name}' no encontrado para la cuenta {self.account_id} en workspace {self.workspace_id}.")
                    return json.dumps({
                        "status": "error",
                        "message": f"No se encontró el documento '{document_name}' en tu base de conocimiento.",
                        "results": []
                    }, ensure_ascii=False, indent=2)
            elif document_id:
                explicit_document_ids = [document_id]
                logger.info(f"🔍 Buscando directamente con document_id: {document_id}")

            # Determinar visibility_teams basado en include_shared
            visibility_teams = None if include_shared else []
            results = asyncio.run(multi_query_search(
                account_id=self.account_id,
                query=query,
                content_type=content_type,
                topics=topic, # Aquí topic ya es List[str] o None
                category=category,
                workspace_id=self.workspace_id,
                team_id=self.team_id,
                visibility_teams=visibility_teams,
                k=k or 5,
                num_queries=num_queries or 3,
                fusion_method=fusion_method or "rrf",
                explicit_document_ids=explicit_document_ids,
            ))
            if not results:
                return json.dumps({
                    "status": "no_results",
                    "message": "No se encontraron resultados relevantes",
                    "results": []
                }, ensure_ascii=False, indent=2)

            # Formatear resultados para mejor legibilidad
            formatted_results = []
            for i, result in enumerate(results):
                formatted_result = {
                    "rank": i + 1,
                    "content": result.get('document', ''),
                    "metadata": result.get('cmetadata', {}),
                    "topic": result.get('topic'),
                    "category": result.get('category'),
                    "similarity_score": result.get('similarity_score')
                }
                formatted_results.append(formatted_result)
            return json.dumps({
                "status": "success",
                "query": query,
                "method": "multi_query_retrieval",
                "fusion_method": fusion_method or "rrf",
                "num_queries_generated": num_queries or 3,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "document_name": document_name,
                "document_id": document_id,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Error en MultiQuerySearchTool: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "message": f"Error ejecutando búsqueda multi-consulta: {str(e)}",
                "results": []
            }, ensure_ascii=False, indent=2)