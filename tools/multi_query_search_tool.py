# tools/multi_query_search_tool.py

"""
Herramienta de búsqueda con múltiples consultas reformuladas (MultiQueryRetriever).
Mejora la recuperación de información generando consultas alternativas y fusionando resultados.
"""

import logging
import asyncio
import json
from typing import Any, Type, Union, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from utils.multi_query_retriever import multi_query_search

logger = logging.getLogger(__name__)

class MultiQuerySearchInput(BaseModel):
    """Esquema de entrada para la herramienta de búsqueda multi-consulta."""
    
    account_id: str = Field(
        ..., 
        description="ID de la cuenta del usuario",
        json_schema_extra={"type": "string"}
    )
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
    topic: Optional[str] = Field(
        None, 
        description="Tema específico para filtrar resultados",
        json_schema_extra={"type": "string"}
    )
    category: Optional[str] = Field(
        None, 
        description="Categoría específica para filtrar resultados",
        json_schema_extra={"type": "string"}
    )
    workspace_id: Optional[str] = Field(
        None, 
        description="ID del workspace para filtrar resultados",
        json_schema_extra={"type": "string"}
    )
    team_id: Optional[str] = Field(
        None, 
        description="ID del equipo para filtrar resultados",
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
        "\n✨ CARACTERÍSTICAS: "
        "• Genera automáticamente consultas alternativas con LLM "
        "• Ejecuta búsquedas paralelas para mayor eficiencia "
        "• Fusiona resultados usando Reciprocal Rank Fusion (RRF) "
        "• Compatible con todos los filtros del sistema (workspace, topic, etc.) "
        "\n⚡ OPTIMIZADO: Aprovecha la infraestructura de búsqueda optimizada de Kognito."
    )
    
    args_schema: Type[BaseModel] = MultiQuerySearchInput

    async def _arun(
        self,
        account_id: str,
        query: str,
        content_type: Union[str, None] = None,
        topic: Union[str, None] = None,
        category: Union[str, None] = None,
        workspace_id: Union[str, None] = None,
        team_id: Union[str, None] = None,
        k: Union[int, None] = 5,
        num_queries: Union[int, None] = 3,
        fusion_method: Union[str, None] = "rrf",
        include_shared: Union[bool, None] = True,
    ) -> str:
        """
        Ejecuta la búsqueda multi-consulta de forma asíncrona.
        """
        try:
            # Determinar visibility_teams basado en include_shared
            visibility_teams = None if include_shared else []
            
            results = await multi_query_search(
                account_id=account_id,
                query=query,
                content_type=content_type,
                topic=topic,
                category=category,
                workspace_id=workspace_id,
                team_id=team_id,
                visibility_teams=visibility_teams,
                k=k or 5,
                num_queries=num_queries or 3,
                fusion_method=fusion_method or "rrf"
            )
            
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
                "results": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Error en MultiQuerySearchTool (async): {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "message": f"Error ejecutando búsqueda multi-consulta: {str(e)}",
                "results": []
            }, ensure_ascii=False, indent=2)

    def _run(
        self,
        account_id: str,
        query: str,
        content_type: Union[str, None] = None,
        topic: Union[str, None] = None,
        category: Union[str, None] = None,
        workspace_id: Union[str, None] = None,
        team_id: Union[str, None] = None,
        k: Union[int, None] = 5,
        num_queries: Union[int, None] = 3,
        fusion_method: Union[str, None] = "rrf",
        include_shared: Union[bool, None] = True,
    ) -> str:
        """
        Ejecuta la búsqueda multi-consulta de forma síncrona.
        """
        try:
            # Determinar visibility_teams basado en include_shared
            visibility_teams = None if include_shared else []
            
            results = asyncio.run(multi_query_search(
                account_id=account_id,
                query=query,
                content_type=content_type,
                topic=topic,
                category=category,
                workspace_id=workspace_id,
                team_id=team_id,
                visibility_teams=visibility_teams,
                k=k or 5,
                num_queries=num_queries or 3,
                fusion_method=fusion_method or "rrf"
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
                "results": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Error en MultiQuerySearchTool: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "message": f"Error ejecutando búsqueda multi-consulta: {str(e)}",
                "results": []
            }, ensure_ascii=False, indent=2)
