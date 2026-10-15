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
        "Consulta el Grafo de Conocimiento relacional de KAI para descubrir entidades (personas, proyectos, "
        "conceptos, tecnologías, notas) y sus conexiones semánticas. Úsala cuando te pregunten "
        "por relaciones ('cómo se relaciona X con Y'), dependencias ('de qué depende Z'), impacto ('qué afecta cambiar W'), "
        "estructura de proyectos o mapas conceptuales. Devuelve entidades, propiedades y vínculos relacionales para enriquecer tu respuesta."
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
            logger.info(f"🧠 KnowledgeGraphTool: Ejecutando consulta relacional profunda con GraphReasoningNode: '{natural_language_query}'")

            from knowledge_graph.graph_reasoning_node import GraphReasoningNode
            from langchain_core.messages import HumanMessage

            graph_db = self._knowledge_graph_service.graph_db
            if graph_db._driver is None or getattr(graph_db._driver, "closed", True):
                graph_db.connect()

            # Obtener datasets disponibles para esta cuenta/workspace
            target_datasets = None
            try:
                datasets_info = await graph_db.get_available_datasets(
                    self.account_id, workspace_id=self.workspace_id
                )
                if datasets_info:
                    target_datasets = [d["name"] for d in datasets_info if isinstance(d, dict) and d.get("name")]
                    logger.info(f"🎯 Datasets disponibles en el grafo: {target_datasets}")
            except Exception as d_err:
                logger.warning(f"No se pudieron obtener datasets para el grafo: {d_err}")

            # Inicializar el nodo de razonamiento del grafo
            reasoning_node = GraphReasoningNode(graph_db=graph_db)

            synthetic_state = {
                "messages": [HumanMessage(content=natural_language_query)],
                "account_id": self.account_id,
                "workspace_id": self.workspace_id,
                "target_datasets": target_datasets,
            }

            graph_output = await reasoning_node.ainvoke(
                synthetic_state, target_datasets=target_datasets
            )

            graph_context = graph_output.get("graph_context") if graph_output else None
            mermaid_diagram = graph_output.get("mermaid_diagram") if graph_output else None
            sources = graph_output.get("graph_sources", []) if graph_output else []

            if not graph_context and not sources:
                # Fallback: intentar búsqueda por palabras clave en propiedades de nodos
                logger.info("Intentando fallback directo en Neo4j por palabras clave...")
                fallback_results = await self._keyword_fallback_search(natural_language_query, target_datasets)
                if fallback_results:
                    return json.dumps({
                        "status": "success",
                        "summary": fallback_results,
                        "context_for_llm": f"### Información recuperada del Grafo de Conocimiento:\n{fallback_results}",
                        "sources": [],
                    }, ensure_ascii=False, indent=2)

                return json.dumps({
                    "status": "success",
                    "message": f"No se encontraron entidades ni conexiones específicas en el grafo de conocimiento para '{natural_language_query}'.",
                    "sources": []
                })

            formatted_context = f"### Información de Entidades y Relaciones del Grafo:\n\n{graph_context}"
            if mermaid_diagram:
                formatted_context += f"\n\n### Diagrama Mermaid de Relaciones:\n```mermaid\n{mermaid_diagram}\n```"

            output = {
                "status": "success",
                "summary": graph_context,
                "mermaid_diagram": mermaid_diagram,
                "sources": sources,
                "context_for_llm": formatted_context,
                "method": "graph_reasoning_node",
            }

            return json.dumps(output, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ Error en KnowledgeGraphTool (GraphReasoningNode): {e}", exc_info=True)
            return json.dumps({"error": f"Error al ejecutar la consulta en el grafo: {str(e)}", "status": "error"})

    async def _keyword_fallback_search(self, query: str, target_datasets: Optional[List[str]] = None) -> Optional[str]:
        """Búsqueda simple de fallback por palabras individuales en nodos de Neo4j."""
        try:
            import re
            words = [w.lower() for w in re.findall(r'\b\w+\b', query) if len(w) > 3]
            if not words:
                return None

            conditions = " OR ".join([f"toLower(n.name) CONTAINS $w{i} OR toLower(n.description) CONTAINS $w{i}" for i, _ in enumerate(words[:4])])
            params = {f"w{i}": w for i, w in enumerate(words[:4])}
            params["account_id"] = self.account_id

            ds_filter = f"AND n.dataset_name IN {target_datasets}" if target_datasets else ""

            cypher = f"""
            MATCH (n)
            WHERE ({conditions})
              AND (n.account_id = $account_id OR n.account_id IS NULL)
              {ws_filter}
              {ds_filter}
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN n.name as entity, labels(n) as labels, n.description as description, type(r) as relation, m.name as related_entity
            LIMIT 15
            """

            records = await self._knowledge_graph_service.graph_db.execute_query(cypher, params)
            if not records:
                return None

            lines = []
            for rec in records:
                ent = rec.get("entity") or "Entidad"
                rel = rec.get("relation")
                rel_ent = rec.get("related_entity")
                desc = rec.get("description") or ""
                if rel and rel_ent:
                    lines.append(f"- **{ent}** --[{rel}]--> **{rel_ent}**" + (f": {desc}" if desc else ""))
                else:
                    lines.append(f"- **{ent}**" + (f": {desc}" if desc else ""))

            return "\n".join(lines[:12])
        except Exception as fb_err:
            logger.warning(f"Error en keyword fallback de grafo: {fb_err}")
            return None

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
