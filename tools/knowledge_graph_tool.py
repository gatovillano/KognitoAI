# tools/knowledge_graph_tool.py
"""
Herramienta para crear y consultar grafos de conocimiento usando GraphIntegration.
Reemplaza la herramienta anterior basada en Cognee.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Literal, Type
import json

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from core.config import settings

logger = logging.getLogger(__name__)

class KnowledgeGraphToolInput(BaseModel):
    """Input para la herramienta de grafo de conocimiento."""
    action: Literal["process_documents", "search_graph", "get_insights", "list_datasets"] = Field(
        ...,
        description="La acción a realizar: 'process_documents', 'search_graph', 'get_insights', o 'list_datasets'."
    )
    documents: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Lista de documentos a procesar. Requerido para 'process_documents'. Cada documento debe tener 'file_name' y opcionalmente 'content'."
    )
    query: Optional[str] = Field(
        None,
        description="Consulta de búsqueda o tema para insights. Requerido para 'search_graph' y 'get_insights'."
    )
    dataset_name: str = Field(
        "default",
        description="Nombre del dataset para el procesamiento o la consulta (opcional, por defecto 'default')."
    )
    processing_mode: Optional[Literal["conceptual", "hybrid"]] = Field(
        "conceptual",
        description="Modo de procesamiento para 'process_documents': 'conceptual' (LLM-driven, experimental) o 'hybrid' (spaCy+Embeddings, habitual)."
    )
    relationship_types: Optional[List[str]] = Field(
        None,
        description="Lista de tipos de relaciones a explorar (ej. 'MARCOS_TEORICOS_AFINES', 'FUNDAMENTACION_TEORICA'). Solo para 'search_graph' o 'get_insights'."
    )
    source_concept: Optional[str] = Field(
        None,
        description="Concepto de inicio para buscar caminos o relaciones específicas. Solo para 'search_graph' o 'get_insights'."
    )
    target_concept: Optional[str] = Field(
        None,
        description="Concepto de destino para buscar caminos o relaciones específicas. Solo para 'search_graph' o 'get_insights'."
    )
    max_hops: Optional[int] = Field(
        None,
        description="Número máximo de saltos (relaciones) para buscar caminos entre conceptos. Solo para 'search_graph' o 'get_insights'."
    )
    pattern_description: Optional[str] = Field(
        None,
        description="Descripción en lenguaje natural de un patrón de grafo a buscar (ej. 'conceptos que fundamentan teóricamente a X'). Solo para 'get_insights'."
    )
    return_type: Optional[Literal["nodes", "relationships", "paths", "summary"]] = Field(
        "summary",
        description="Formato de los resultados: 'nodes' (solo nodos), 'relaciones' (solo relaciones), 'paths' (caminos entre conceptos), 'summary' (resumen en lenguaje natural)."
    )

class KnowledgeGraphTool(BaseTool):
    name: str = "knowledge_graph"
    description: str = (
        "Una herramienta para interactuar con el grafo de conocimiento. "
        "Permite procesar documentos para extraer y almacenar conocimiento, "
        "buscar información específica en el grafo, y obtener insights o patrones. "
        "Soporta consultas avanzadas especificando relaciones, conceptos de origen/destino, "
        "descripciones de patrones y tipos de retorno. "
        "Siempre se debe especificar un `dataset_name` para aislar la información."
    )
    
    args_schema: Type[BaseModel] = KnowledgeGraphToolInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = None
    telegram_id: Optional[int] = None
    thread_id: Optional[str] = None
    _graph_integration: Optional[GraphIntegration] = None
    _graph_db: Optional[GraphDB] = None

    def __init__(self, graph_integration: Optional[GraphIntegration] = None, graph_db: Optional[GraphDB] = None, **data: Any):
        super().__init__(**data)
        self._graph_integration = graph_integration
        self._graph_db = graph_db
        
        if self._graph_integration is None or self._graph_db is None:
            logger.warning("⚠️ GraphIntegration o GraphDB no inyectados en KnowledgeGraphTool. Inicializando internamente.")
            if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
                logger.error("❌ Configuración de Neo4j incompleta.")
                raise ValueError("Configuración de Neo4j incompleta.")
            
            self._graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            self._graph_db.connect()
            self._graph_integration = GraphIntegration(self._graph_db)
            logger.info("✅ GraphIntegration y GraphDB inicializados internamente.")

    def _get_graph_integration(self) -> GraphIntegration:
        if self._graph_integration is None:
            raise ValueError("GraphIntegration no está inicializada.")
        return self._graph_integration
    
    async def _arun(
        self,
        action: Literal["process_documents", "search_graph", "get_insights", "list_datasets"],
        documents: Optional[List[Dict[str, Any]]] = None,
        query: Optional[str] = None,
        dataset_name: str = "default",
        processing_mode: Literal["conceptual", "hybrid"] = "conceptual",
        relationship_types: Optional[List[str]] = None,
        source_concept: Optional[str] = None,
        target_concept: Optional[str] = None,
        max_hops: Optional[int] = None,
        pattern_description: Optional[str] = None,
        return_type: Optional[Literal["nodes", "relationships", "paths", "summary"]] = "summary",
        run_manager: Optional[Any] = None,
        **kwargs
    ) -> str:
        if not action:
            return json.dumps({"error": "La acción es requerida", "status": "error"})

        valid_actions = ["process_documents", "search_graph", "get_insights", "list_datasets"]
        if action not in valid_actions:
            return json.dumps({"error": f"Acción '{action}' no reconocida", "status": "error"})

        try:
            actual_dataset_name = dataset_name if dataset_name is not None else "default"
            graph_integration = self._get_graph_integration()
            # dataset_name_with_account = f"{actual_dataset_name}_{self.account_id.replace('-', '_')}"
            # Usar directamente el dataset_name del input, ya que la API lo maneja con account_id
            # o el frontend lo generará con sufijo si es necesario.
            dataset_name_for_api = actual_dataset_name


            if action == "process_documents":
                if not documents and not self.workspace_id:
                    return json.dumps({"error": "Se requieren documentos o un workspace_id para procesar", "status": "error"})

                logger.info(f"🧠 Procesando {len(documents) if documents else 'documentos de DB'} para dataset: {dataset_name_for_api} en modo: {processing_mode}")
                result = await graph_integration.process_documents(
                    documents=documents if documents else [], # Pasar lista vacía si no se proporcionan, para que la integración los busque
                    dataset_name=dataset_name_for_api,
                    account_id=self.account_id,
                    processing_mode=processing_mode,
                    workspace_id=self.workspace_id # Pasar el workspace_id de la herramienta
                )

                if processing_mode == "hybrid":
                    return f"""✅ Documentos procesados exitosamente (Modo Híbrido)

📊 **Resumen:**
- Dataset: {dataset_name_for_api}
- Documentos: {len(documents) if documents else 'buscados en DB'}
- Estado: {result.get('success', False)}
- Método: {result.get('processing_type', 'hybrid')}

🔗 **Elementos extraídos:**
- Entidades: {result.get('entities_count', 0)}
- Relaciones: {result.get('relationships_count', 0)}"""
                else:
                    return f"""✅ Documentos procesados exitosamente (Modo Conceptual)

📊 **Resumen:**
- Dataset: {dataset_name_for_api}
- Documentos: {len(documents) if documents else 'buscados en DB'}
- Estado: {result.get('status', 'completado')}
- Método: {result.get('processing_type', 'unknown')}

🔗 **Elementos extraídos:**
- Citas conceptuales: {result.get('conceptual_quotes', 0)}
- Relaciones temáticas: {result.get('thematic_relationships', 0)}
- Perfiles de ideas: {result.get('idea_profiles', 0)}"""

            elif action == "search_graph":
                if not query and not (source_concept and target_concept):
                    return "❌ Error: Se requiere una consulta o conceptos origen/destino."

                logger.info(f"🔍 Buscando en grafo: {query} en dataset: {dataset_name_for_api}")
                result_kg = await graph_integration.search_knowledge_graph(
                    query=query if query is not None else "", # Asegurarse de que query sea str
                    dataset_name=dataset_name_for_api,
                    relationship_types=relationship_types,
                    source_concept=source_concept,
                    target_concept=target_concept,
                    max_hops=max_hops,
                    pattern_description=pattern_description,
                    return_type=return_type if return_type is not None else "summary" # Asegurarse de que return_type sea str
                )

                results = result_kg.get('results', [])
                if not results:
                    return json.dumps({"status": "success", "message": f"🔍 No se encontraron resultados para '{query}' en el dataset '{dataset_name_for_api}'."})

                formatted_results = self._format_search_results(results, return_type if return_type is not None else "summary")
                return json.dumps({
                    "status": "success",
                    "query": query,
                    "dataset": dataset_name_for_api,
                    "count": len(results),
                    "results": formatted_results
                })

            elif action == "get_insights":
                if not query and not pattern_description:
                    return json.dumps({"error": "Se requiere consulta o descripción de patrón.", "status": "error"})

                logger.info(f"💡 Obteniendo insights para: {query} en dataset: {dataset_name_for_api}")
                result = await graph_integration.search_knowledge_graph(
                    query=f"insights and patterns about: {query}" if query else "", # Asegurarse de que query sea str
                    dataset_name=dataset_name_for_api,
                    relationship_types=relationship_types,
                    source_concept=source_concept,
                    target_concept=target_concept,
                    max_hops=max_hops,
                    pattern_description=pattern_description,
                    return_type=return_type if return_type is not None else "summary" # Asegurarse de que return_type sea str
                )
                
                formatted_insights = self._format_insights(result.get('results', []), return_type if return_type is not None else "summary")
                return json.dumps({
                    "status": "success",
                    "topic": query if query else pattern_description,
                    "dataset": dataset_name_for_api,
                    "insights": formatted_insights
                })

            elif action == "list_datasets":
                logger.info(f"📋 Listando datasets disponibles para account_id: {self.account_id}")
                response = await graph_integration.graph_db.execute_query(
                    "MATCH (n) WHERE n.account_id = $account_id OR n.account_id IS NULL RETURN DISTINCT n.dataset_name AS dataset_name",
                    {"account_id": self.account_id}
                )
                datasets = [record["dataset_name"] for record in response if record["dataset_name"]]
                if not datasets:
                    return json.dumps({"status": "success", "message": "No hay datasets disponibles en el grafo de conocimiento.", "datasets": []})
                return json.dumps({"status": "success", "message": f"Datasets disponibles: {', '.join(datasets)}", "datasets": datasets})

            else:
                return json.dumps({"error": f"Acción '{action}' no reconocida.", "status": "error"})

        except Exception as e:
            logger.error(f"❌ Error en KnowledgeGraphTool: {e}")
            return json.dumps({"error": f"Error al ejecutar la herramienta: {str(e)}", "status": "error"})

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    def _format_search_results(self, results: Any, return_type: str = "summary") -> List[Dict[str, Any]]:
        logger.debug(f"[_format_search_results] Tipo de resultados: {type(results)}, Contenido: {results}")
        
        # Si los resultados son un diccionario (posiblemente estadísticas o resumen), lo envolvemos en una lista.
        if isinstance(results, dict):
            # Si es un dict de resumen de 'search_knowledge_graph', lo tratamos como un único resultado
            if all(k in results for k in ['node_count', 'relationship_count', 'total_records']):
                results = [{"type": "summary_stats", "data": results}]
            else:
                # Si es otro dict, lo convertimos a lista para el procesamiento general
                results = [results]
        elif not isinstance(results, list):
            logger.error(f"[_format_search_results] 'results' no es una lista ni un diccionario. Tipo: {type(results)}, Valor: {results}")
            return []
        
        if not results: return []
        formatted = []
        limit = 10 # Aumentar el límite para insights más detallados

        for result in results[:limit]:
            if isinstance(result, dict):
                if "properties" in result:
                    # Formato para nodos (CONCEPTUAL_QUOTE, IDEA_PROFILE)
                    name = result['properties'].get('name', result['properties'].get('concept', result['properties'].get('text', 'Unnamed')))
                    label = result.get('labels', ['Node'])[0]
                    formatted.append({"type": "node", "label": label, "name": name, "properties": result['properties']})
                elif "relationship_type" in result:
                    # Formato para relaciones
                    start_node_id = result.get('start_node_element_id', 'Unknown')
                    end_node_id = result.get('end_node_element_id', 'Unknown')
                    rel_type = result.get('relationship_type', 'RELATIONSHIP')
                    # Intentar obtener nombres de nodos si están disponibles en las propiedades de la relación
                    start_node_name = result['properties'].get('start_node_name', start_node_id)
                    end_node_name = result['properties'].get('end_node_name', end_node_id)
                    description = result['properties'].get('description', f"{start_node_name} -[{rel_type}]-> {end_node_name}")
                    formatted.append({"type": "relationship", "relation": rel_type, "description": description, "source": start_node_name, "target": end_node_name, "properties": result['properties']})
                elif "type" in result and result["type"] in ["node_stats", "rel_stats"]:
                    # Formato para estadísticas de nodos o relaciones
                    if result["type"] == "node_stats":
                        formatted.append({
                            "type": "insight_node_stats",
                            "description": "Estadísticas de categorías de nodos más comunes:",
                            "data": result["data"]
                        })
                    elif result["type"] == "rel_stats":
                        formatted.append({
                            "type": "insight_relationship_stats",
                            "description": "Estadísticas de tipos de relaciones más comunes:",
                            "data": result["data"]
                        })
                elif result.get("type") == "summary_stats" and "data" in result:
                    # Manejar el diccionario de estadísticas envuelto
                    formatted.append({
                        "type": "summary_statistics",
                        "description": "Resumen de estadísticas del grafo:",
                        "data": result["data"]
                    })
                else:
                    # Para otros resultados crudos que ya son diccionarios
                    formatted.append({"type": "raw_result", "content": result})
            else:
                # Para resultados que no son diccionarios (ej. cadenas de texto)
                formatted.append({"type": "raw_result", "content": str(result)})

        return formatted

    def _format_insights(self, results: List[Any], return_type: str = "summary") -> List[Dict[str, Any]]:
        return self._format_search_results(results, return_type)

    def __del__(self):
        if self._graph_db:
            try:
                self._graph_db.close()
            except:
                pass
