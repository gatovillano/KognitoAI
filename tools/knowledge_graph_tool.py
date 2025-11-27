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
    action: Literal["process_documents", "search_graph", "get_insights"] = Field(
        ...,
        description="La acción a realizar: 'process_documents', 'search_graph', o 'get_insights'."
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
        action: Literal["process_documents", "search_graph", "get_insights"],
        documents: Optional[List[Dict[str, Any]]] = None,
        query: Optional[str] = None,
        dataset_name: str = "default",
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
        
        valid_actions = ["process_documents", "search_graph", "get_insights"]
        if action not in valid_actions:
            return json.dumps({"error": f"Acción '{action}' no reconocida", "status": "error"})
        
        try:
            actual_dataset_name = dataset_name if dataset_name is not None else "default"
            graph_integration = self._get_graph_integration()
            dataset_name_with_account = f"{actual_dataset_name}_{self.account_id.replace('-', '_')}"
            
            if action == "process_documents":
                if not documents:
                    return json.dumps({"error": "Se requieren documentos para procesar", "status": "error"})
                
                logger.info(f"🧠 Procesando {len(documents)} documentos para dataset: {dataset_name_with_account}")
                result = await graph_integration.process_documents(
                    documents=documents,
                    dataset_name=dataset_name_with_account,
                    account_id=self.account_id
                )
                
                return f"""✅ Documentos procesados exitosamente
                
📊 **Resumen:**
- Dataset: {dataset_name}
- Documentos: {len(documents)}
- Estado: {result.get('status', 'completado')}
- Método: {result.get('processing_type', 'unknown')}

🔗 **Elementos extraídos:**
- Citas conceptuales: {result.get('conceptual_quotes', 0)}
- Relaciones temáticas: {result.get('thematic_relationships', 0)}
- Perfiles de ideas: {result.get('idea_profiles', 0)}"""
            
            elif action == "search_graph":
                if not query and not (source_concept and target_concept):
                    return "❌ Error: Se requiere una consulta o conceptos origen/destino."
                
                logger.info(f"🔍 Buscando en grafo: {query} en dataset: {dataset_name_with_account}")
                result = await graph_integration.search_knowledge_graph(
                    query=query,
                    dataset_name=dataset_name_with_account,
                    relationship_types=relationship_types,
                    source_concept=source_concept,
                    target_concept=target_concept,
                    max_hops=max_hops,
                    return_type=return_type
                )
                
                results = result.get('results', [])
                if not results:
                    return f"🔍 No se encontraron resultados para '{query}' en el dataset '{dataset_name}'."
                
                return f"""🔍 **Resultados de búsqueda**
                
❓ **Consulta:** {query}
📊 **Dataset:** {dataset_name}
✅ **Resultados:** {len(results)}

📝 **Detalle:**
{self._format_search_results(results, return_type)}"""
            
            elif action == "get_insights":
                if not query and not pattern_description:
                    return "❌ Error: Se requiere consulta o descripción de patrón."
                
                logger.info(f"💡 Obteniendo insights para: {query} en dataset: {dataset_name_with_account}")
                result = await graph_integration.search_knowledge_graph(
                    query=f"insights and patterns about: {query}" if query else None,
                    dataset_name=dataset_name_with_account,
                    relationship_types=relationship_types,
                    source_concept=source_concept,
                    target_concept=target_concept,
                    max_hops=max_hops,
                    pattern_description=pattern_description,
                    return_type=return_type
                )
                
                return f"""💡 **Insights del Grafo**
                
🎯 **Tema:** {query if query else pattern_description}
📊 **Dataset:** {dataset_name}

🔗 **Patrones:**
{self._format_insights(result.get('results', []), return_type)}"""
            
            else:
                return f"❌ Error: Acción '{action}' no reconocida."
        
        except Exception as e:
            logger.error(f"❌ Error en KnowledgeGraphTool: {e}")
            return f"❌ Error al ejecutar la herramienta: {str(e)}"
    
    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))
    
    def _format_search_results(self, results: List[Any], return_type: str = "summary") -> str:
        if not results: return "Sin resultados."
        formatted = []
        limit = 5
        
        for i, result in enumerate(results[:limit], 1):
            if isinstance(result, dict):
                if "properties" in result:
                    name = result['properties'].get('name', result['properties'].get('text', 'Unnamed'))
                    label = result.get('labels', ['Node'])[0]
                    formatted.append(f"{i}. [{label}] {name}")
                elif "type" in result:
                    start = result.get('start_node_element_id', '?')
                    end = result.get('end_node_element_id', '?')
                    formatted.append(f"{i}. ({start}) -[{result['type']}]-> ({end})")
                else:
                    formatted.append(f"{i}. {str(result)}")
            else:
                formatted.append(f"{i}. {str(result)}")
                
        return "\n".join(formatted)
    
    def _format_insights(self, results: List[Any], return_type: str = "summary") -> str:
        return self._format_search_results(results, return_type)

    def __del__(self):
        if self._graph_db:
            try:
                self._graph_db.close()
            except:
                pass
