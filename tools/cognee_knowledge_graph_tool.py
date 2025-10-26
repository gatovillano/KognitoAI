"""
Herramienta para crear y consultar grafos de conocimiento usando Cognee.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Literal, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.cognee_integration import CogneeIntegration
from core.config import settings
import json # Importar json

logger = logging.getLogger(__name__)

class CogneeKnowledgeGraphToolInput(BaseModel):
    """Input para la herramienta de grafo de conocimiento con Cognee."""
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

class CogneeKnowledgeGraphTool(BaseTool):
    """Herramienta para crear y consultar grafos de conocimiento usando Cognee."""
    
    name: str = "cognee_knowledge_graph"
    description: str = """
    Crea y consulta grafos de conocimiento usando Cognee. Puede:
    - Procesar documentos para extraer entidades y relaciones
    - Buscar información en el grafo de conocimiento
    - Obtener insights y conexiones semánticas
    
    Acciones disponibles:
    - process_documents: Procesa documentos y crea el grafo
    - search_graph: Busca información específica en el grafo
    - get_insights: Obtiene insights y patrones del grafo
    
    El 'account_id' se inyecta automáticamente en la herramienta y NO debe ser proporcionado por el LLM en el `tool_input`.
    """
    
    args_schema: Type[BaseModel] = CogneeKnowledgeGraphToolInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = None
    telegram_id: Optional[int] = None
    thread_id: Optional[str] = None
    _cognee_integration: Optional[CogneeIntegration] = None
    _graph_db: Optional[GraphDB] = None

    # Constructor para inyectar las dependencias
    def __init__(self, cognee_integration: Optional[CogneeIntegration] = None, graph_db: Optional[GraphDB] = None, **data: Any):
        super().__init__(**data)
        self._cognee_integration = cognee_integration
        self._graph_db = graph_db
        if self._cognee_integration is None or self._graph_db is None:
            logger.warning("⚠️ CogneeIntegration o GraphDB no inyectados en CogneeKnowledgeGraphTool. Inicializando internamente.")
            # Fallback: inicializar si no se inyectaron
            if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
                logger.error("❌ Configuración de Neo4j incompleta. No se puede inicializar CogneeKnowledgeGraphTool.")
                raise ValueError(
                    "Configuración de Neo4j incompleta. Asegúrate de configurar NEO4J_URI, NEO4J_USER y NEO4J_PASSWORD"
                )
            self._graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            self._graph_db.connect()
            self._cognee_integration = CogneeIntegration(self._graph_db)
            logger.info("✅ CogneeIntegration y GraphDB inicializados internamente para CogneeKnowledgeGraphTool.")

    # El método _get_cognee_integration ya no es necesario si las dependencias se inyectan correctamente.
    # Podríamos mantenerlo para compatibilidad o eliminarlo si estamos seguros de la inyección.
    # Para este ejercicio, lo dejamos, pero aseguramos que use las instancias existentes.
    def _get_cognee_integration(self) -> CogneeIntegration: # type: ignore
        if self._cognee_integration is None:
            raise ValueError("CogneeIntegration no está inicializada.")
        return self._cognee_integration
    
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
        **kwargs # Para capturar cualquier otro kwarg que pueda venir
    ) -> str:
        # La lógica de parseo de tool_input_json se elimina

        if not action:
            return json.dumps({
                "error": "La acción es requerida",
                "status": "error",
                "details": "El parámetro 'action' no fue proporcionado en la entrada JSON."
            })
        
        # Validar que la acción sea una de las literales esperadas
        valid_actions = ["process_documents", "search_graph", "get_insights"]
        if action not in valid_actions:
            return json.dumps({
                "error": f"Acción '{action}' no reconocida",
                "status": "error",
                "details": f"La acción debe ser una de: {', '.join(valid_actions)}."
            })
        
        try:
            logger.debug(f"CogneeKnowledgeGraphTool._arun - action received: '{action}', documents: {documents}, query: {query}, dataset_name: {dataset_name}, relationship_types: {relationship_types}, source_concept: {source_concept}, target_concept: {target_concept}, max_hops: {max_hops}, pattern_description: {pattern_description}, return_type: {return_type}")
            # Asegurarse de que dataset_name no sea None
            actual_dataset_name = dataset_name if dataset_name is not None else "default"
            
            cognee_integration = self._get_cognee_integration()
            
            # Personalizar dataset por cuenta
            # Utilizar un nombre de dataset basado en el account_id para aislamiento.
            # Convertir el UUID a string para el nombre del dataset.
            dataset_name_with_account = f"{actual_dataset_name}_{self.account_id.replace('-', '_')}"
            
            if action == "process_documents":
                if not documents:
                    return json.dumps({
                        "error": "Se requieren documentos para procesar",
                        "status": "error",
                        "details": "El parámetro 'documents' es requerido para la acción 'process_documents'."
                    })
                
                logger.info(f"🧠 Procesando {len(documents)} documentos con Cognee para dataset: {dataset_name_with_account}")
                result = await cognee_integration.process_documents(
                    documents=documents,
                    dataset_name=dataset_name_with_account,
                    account_id=self.account_id
                )
                
                return f"""✅ Documentos procesados exitosamente con Cognee

📊 **Resumen del procesamiento:**
- Dataset: {dataset_name}
- Documentos procesados: {len(documents)}
- Estado: {result.get('status', 'completado')}
- Método: {result.get('method', 'cognee')}

🔗 **Entidades y relaciones extraídas:**
- Entidades: {len(result.get('entities', []))}
- Relaciones: {len(result.get('relationships', []))}

💡 Los documentos han sido analizados y el grafo de conocimiento ha sido actualizado.
Puedes usar 'search_graph' para buscar información específica."""
            
            elif action == "search_graph":
                if not query and not (source_concept and target_concept):
                    return "❌ Error: Se requiere una consulta (query) o un concepto de origen y destino para buscar caminos o relaciones específicas en el grafo."
                
                logger.info(f"🔍 Buscando en el grafo: {query} en dataset: {dataset_name_with_account}")
                result = await cognee_integration.search_knowledge_graph(
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
                    return f"""🔍 **Búsqueda en grafo de conocimiento**

❓ **Consulta:** {query}
📊 **Dataset:** {dataset_name}
📝 **Resultados:** No se encontraron resultados específicos

💡 **Sugerencias:**
- Intenta con términos más generales
- Verifica que los documentos hayan sido procesados
- Usa 'process_documents' si aún no has añadido contenido"""
                
                return f"""🔍 **Búsqueda en grafo de conocimiento**

❓ **Consulta:** {query}
📊 **Dataset:** {dataset_name}
✅ **Resultados encontrados:** {len(results)}

📝 **Información relevante:**
{self._format_search_results(results, return_type)}

🧠 **Estado:** {result.get('status', 'completado')}
⚡ **Método:** {result.get('method', 'cognee')}"""
            
            elif action == "get_insights":
                if not query and not pattern_description:
                    return "❌ Error: Se requiere una consulta (query) o una descripción de patrón para obtener insights."
                
                # Para insights, usamos la búsqueda pero con un enfoque más analítico
                logger.info(f"💡 Obteniendo insights para: {query} en dataset: {dataset_name_with_account}")
                result = await cognee_integration.search_knowledge_graph(
                    query=f"insights and patterns about: {query}" if query else None,
                    dataset_name=dataset_name_with_account,
                    relationship_types=relationship_types,
                    source_concept=source_concept,
                    target_concept=target_concept,
                    max_hops=max_hops,
                    pattern_description=pattern_description,
                    return_type=return_type
                )
                
                return f"""💡 **Insights del grafo de conocimiento**

🎯 **Tema analizado:** {query if query else pattern_description}
📊 **Dataset:** {dataset_name}

🔗 **Patrones y conexiones encontradas:**
{self._format_insights(result.get('results', []), return_type)}

📈 **Estado del análisis:** {result.get('status', 'completado')}"""
            
            else:
                return f"❌ Error: Acción '{action}' no reconocida. Usa: process_documents, search_graph, get_insights"
        
        except Exception as e:
            logger.error(f"❌ Error en CogneeKnowledgeGraphTool: {e}")
            return f"❌ Error al ejecutar la herramienta: {str(e)}"
    
    def _run(
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
        **kwargs
    ) -> str:
        """Ejecuta la herramienta de forma síncrona."""
        return asyncio.run(self._arun(
            action=action,
            documents=documents,
            query=query,
            dataset_name=dataset_name,
            relationship_types=relationship_types,
            source_concept=source_concept,
            target_concept=target_concept,
            max_hops=max_hops,
            pattern_description=pattern_description,
            return_type=return_type,
            **kwargs
        ))
    
    def _format_search_results(self, results: List[Any], return_type: str = "summary") -> str:
        """Formatea los resultados de búsqueda."""
        if not results:
            return "No se encontraron resultados específicos."
        
        formatted = []
        if return_type == "nodes":
            for i, result in enumerate(results[:5], 1):
                if isinstance(result, dict) and "properties" in result:
                    formatted.append(f"{i}. Nodo: {result.get('labels', [''])[0]} - {result['properties'].get('name', result['properties'].get('text', str(result)))}")
                else:
                    formatted.append(f"{i}. {str(result)}")
        elif return_type == "relationships":
            for i, result in enumerate(results[:5], 1):
                if isinstance(result, dict) and "type" in result:
                    start_node = result.get('start_node', {}).get('properties', {}).get('name', '')
                    end_node = result.get('end_node', {}).get('properties', {}).get('name', '')
                    formatted.append(f"{i}. Relación: {start_node} -[{result['type']}]-> {end_node}")
                else:
                    formatted.append(f"{i}. {str(result)}")
        elif return_type == "paths":
            for i, path in enumerate(results[:3], 1): # Limitar a 3 caminos para no ser demasiado verboso
                path_str = []
                for item in path:
                    if isinstance(item, dict):
                        if "properties" in item: # Es un nodo
                            path_str.append(item['properties'].get('name', item['properties'].get('text', '')))
                        elif "type" in item: # Es una relación
                            path_str.append(f"-[{item['type']}]->")
                    else:
                        path_str.append(str(item))
                formatted.append(f"{i}. {' '.join(path_str)}")
        else: # summary o cualquier otro caso
            for i, result in enumerate(results[:5], 1):  # Limitar a 5 resultados
                if isinstance(result, dict):
                    content = result.get('content', str(result))
                    formatted.append(f"{i}. {content}")
                else:
                    formatted.append(f"{i}. {str(result)}")
        
        return "\n".join(formatted)
    
    def _format_insights(self, results: List[Any], return_type: str = "summary") -> str:
        """Formatea los insights obtenidos."""
        if not results:
            return "No se encontraron patrones específicos en el grafo actual."
        
        # Para insights, intentamos extraer información más estructurada
        insights = []
        if return_type == "nodes":
            for result in results:
                if isinstance(result, dict) and "properties" in result:
                    insights.append(f"• Nodo: {result.get('labels', [''])[0]} - {result['properties'].get('name', result['properties'].get('text', str(result)))}")
                else:
                    insights.append(f"• {str(result)}")
        elif return_type == "relationships":
            for result in results:
                if isinstance(result, dict) and "type" in result:
                    start_node = result.get('start_node', {}).get('properties', {}).get('name', '')
                    end_node = result.get('end_node', {}).get('properties', {}).get('name', '')
                    insights.append(f"• Relación: {start_node} -[{result['type']}]-> {end_node}")
                else:
                    insights.append(f"• {str(result)}")
        elif return_type == "paths":
            for path in results[:3]:
                path_str = []
                for item in path:
                    if isinstance(item, dict):
                        if "properties" in item:
                            path_str.append(item['properties'].get('name', item['properties'].get('text', '')))
                        elif "type" in item:
                            path_str.append(f"-[{item['type']}]->")
                    else:
                        path_str.append(str(item))
                insights.append(f"• {' '.join(path_str)}")
        else: # summary o cualquier otro caso
            for result in results:
                if isinstance(result, dict):
                    insight = result.get('insight', result.get('content', str(result)))
                    insights.append(f"• {insight}")
                else:
                    insights.append(f"• {str(result)}")
        
        return "\n".join(insights[:10])  # Limitar a 10 insights
    
    def __del__(self):
        """Limpia las conexiones al destruir la herramienta."""
        if self._graph_db:
            try:
                self._graph_db.close()
            except:
                pass