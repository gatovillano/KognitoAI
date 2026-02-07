# tools/knowledge_graph_tool.py
"""
Herramienta para crear y consultar grafos de conocimiento usando KnowledgeGraphService.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Literal, Type
import json

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from utils.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)

class KnowledgeGraphToolInput(BaseModel):
    """Input para la herramienta de grafo de conocimiento."""
    natural_language_query: str = Field(
        ...,
        description="Una pregunta en lenguaje natural sobre el grafo de conocimiento. Ej: '¿Cómo se relaciona el Agente con el Grafo de Conocimiento?' o 'Muéstrame las conexiones de la entidad X'."
    )

class KnowledgeGraphTool(BaseTool):
    name: str = "knowledge_graph"
    description: str = (
        "Realiza una consulta en lenguaje natural al grafo de conocimiento para descubrir entidades, "
        "relaciones y patrones complejos. Ideal para preguntas que implican 'cómo se relaciona', "
        "'qué conexiones tiene', o 'muéstrame un mapa de'."
    )
    
    args_schema: Type[BaseModel] = KnowledgeGraphToolInput
    account_id: Optional[str] = Field(None, description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = None
    telegram_id: Optional[int] = None
    thread_id: Optional[str] = None
    _knowledge_graph_service: KnowledgeGraphService

    def __init__(self, knowledge_graph_service: Optional[KnowledgeGraphService] = None, **data: Any):
        super().__init__(**data)
        if knowledge_graph_service:
            object.__setattr__(self, '_knowledge_graph_service', knowledge_graph_service)
        else:
            # Crear instancia del servicio si no se proporciona
            logger.info("🔧 Creando nueva instancia de KnowledgeGraphService para KnowledgeGraphTool")
            try:
                object.__setattr__(self, '_knowledge_graph_service', KnowledgeGraphService())
            except Exception as e:
                logger.error(f"❌ Error inicializando KnowledgeGraphService: {e}")
                raise ValueError(f"No se pudo inicializar KnowledgeGraphService: {e}")
        
        logger.info("✅ KnowledgeGraphTool inicializada con KnowledgeGraphService.")

    async def _arun(
        self,
        natural_language_query: str,
        run_manager: Optional[Any] = None,
        **kwargs
    ) -> str:
        
        try:
            logger.info(f"🧠 Ejecutando consulta en grafo con lenguaje natural: '{natural_language_query}'")

            # Usar GraphIntegration para buscar en el grafo de conocimiento
            graph_integration = self._knowledge_graph_service.graph_integration
            
            # Realizar búsqueda en el grafo usando la integración
            search_result = await graph_integration.search_knowledge_graph(
                query=natural_language_query,
                dataset_name="default",
                return_type="summary",
                account_id=self.account_id,
                workspace_id=self.workspace_id
            )

            if not search_result.get("results"):
                return json.dumps({
                    "status": "success",
                    "message": "La consulta no produjo resultados en el grafo de conocimiento."
                })

            # Formatear la salida para el LLM
            output = {
                "status": "success",
                "summary": self._format_search_results(search_result),
                "sources": search_result.get("results", []),
                "method": search_result.get("method", "graph_search"),
                "searched_at": search_result.get("searched_at")
            }
            
            return json.dumps(output, indent=2)

        except Exception as e:
            logger.error(f"❌ Error en KnowledgeGraphTool (modo servicio): {e}", exc_info=True)
            return json.dumps({"error": f"Error al ejecutar la consulta en el grafo: {str(e)}", "status": "error"})

    def _format_search_results(self, search_result: Dict[str, Any]) -> str:
        """Formatea los resultados de búsqueda para mejor legibilidad, incluyendo propiedades."""
        results = search_result.get("results", [])
        if not results:
            return "No se encontraron resultados en el grafo de conocimiento."
        
        # Si los resultados son un resumen de texto
        if len(results) == 1 and isinstance(results[0], dict) and results[0].get("type") == "summary_text_insight":
            content = results[0].get("content", "Resultados encontrados en el grafo.")
            # Si hay datos adicionales en el resumen (como conteos), incluirlos
            node_count = results[0].get("node_count")
            rel_count = results[0].get("relationship_count")
            if node_count is not None or rel_count is not None:
                content += f"\n(Estadísticas: {node_count or 0} nodos, {rel_count or 0} relaciones)"
            return content
        
        # Para otros tipos de resultados, crear un resumen detallado
        formatted_parts = []
        for result in results[:10]:  # Aumentar límite a 10 resultados para dar más contexto
            if isinstance(result, dict):
                # Extraer información básica
                name = result.get("name") or result.get("concept") or result.get("title") or "Sin nombre"
                res_type = result.get("type") or (result.get("labels", ["Desconocido"])[0] if result.get("labels") else "Entidad")
                description = result.get("description") or result.get("content") or ""
                
                # Construir string de propiedades adicionales
                excluded_keys = {"name", "concept", "title", "type", "labels", "description", "content", "element_id", "id", "dataset_name", "account_id", "workspace_id"}
                props = {k: v for k, v in result.items() if k not in excluded_keys and v is not None}
                props_str = ", ".join([f"{k}: {v}" for k, v in props.items()])
                
                part = f"- [{res_type}] {name}"
                if description:
                    part += f": {description}"
                if props_str:
                    part += f" (Propiedades: {props_str})"
                
                formatted_parts.append(part)
        
        if formatted_parts:
            header = f"Resultados encontrados ({len(results)} en total, mostrando {len(formatted_parts)}):\n"
            return header + "\n".join(formatted_parts)
        else:
            return "Se encontraron resultados en el grafo de conocimiento, pero no se pudieron formatear detalladamente."

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    def __del__(self):
        # El KnowledgeGraphService maneja sus propias conexiones
        # No necesitamos cerrar manualmente la conexión aquí
        logger.debug("🗑️ KnowledgeGraphTool siendo eliminada.")
