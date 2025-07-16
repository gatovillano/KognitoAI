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
    """Input para la herramienta de grafo de conocimiento con Cognee, como una cadena JSON."""
    tool_input_json: str = Field(
        ...,
        description="La entrada completa de la herramienta como una cadena JSON que contiene 'action', 'documents', 'query' y 'dataset_name'."
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
    _cognee_integration: Optional[CogneeIntegration] = None
    _graph_db: Optional[GraphDB] = None

    def _get_cognee_integration(self) -> CogneeIntegration:
        """Obtiene o crea la instancia de CogneeIntegration."""
        if self._cognee_integration is None:
            logger.info(f"DEBUG Neo4j Config: URI={settings.neo4j_uri}, User={settings.neo4j_user}, Password set={bool(settings.neo4j_password)}")
            if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
                raise ValueError(
                    "Configuración de Neo4j incompleta. "
                    "Asegúrate de configurar NEO4J_URI, NEO4J_USER y NEO4J_PASSWORD"
                )
            
            self._graph_db = GraphDB(
                settings.neo4j_uri,
                settings.neo4j_user,
                settings.neo4j_password
            )
            self._graph_db.connect()
            
            self._cognee_integration = CogneeIntegration(self._graph_db)
            logger.info("✅ CogneeIntegration inicializada")
        
        return self._cognee_integration
    
    async def _arun(
        self,
        tool_input_json: str, # Nuevo parámetro
        run_manager: Optional[Any] = None, # Añadido para consistencia con _arun de conceptual_processing
        **kwargs # Para capturar cualquier otro kwarg que pueda venir
    ) -> str:
        # Parsear la cadena JSON de entrada
        try:
            parsed_input = json.loads(tool_input_json)
        except json.JSONDecodeError:
            try:
                # Intentar limpiar y parsear si no es un JSON válido directamente
                cleaned_json = tool_input_json.replace("'", "\"")
                parsed_input = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error al parsear tool_input_json: {tool_input_json}. Error: {e}", exc_info=True)
                return json.dumps({
                    "error": "Error de formato de entrada",
                    "status": "error",
                    "details": "El tool_input no es un JSON válido."
                })
        
        action = parsed_input.get("action")
        documents = parsed_input.get("documents")
        query = parsed_input.get("query")
        dataset_name = parsed_input.get("dataset_name", "default")

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
            logger.debug(f"CogneeKnowledgeGraphTool._arun - action received: '{action}', documents: {documents}, query: {query}, dataset_name: {dataset_name}")
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
                    dataset_name=dataset_name_with_account
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
                if not query:
                    return "❌ Error: Se requiere una consulta para buscar"
                
                logger.info(f"🔍 Buscando en el grafo: {query} en dataset: {dataset_name_with_account}")
                result = await cognee_integration.search_knowledge_graph(
                    query=query,
                    dataset_name=dataset_name_with_account
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
{self._format_search_results(results)}

🧠 **Estado:** {result.get('status', 'completado')}
⚡ **Método:** {result.get('method', 'cognee')}"""
            
            elif action == "get_insights":
                if not query:
                    return "❌ Error: Se requiere una consulta para obtener insights"
                
                # Para insights, usamos la búsqueda pero con un enfoque más analítico
                logger.info(f"💡 Obteniendo insights para: {query} en dataset: {dataset_name_with_account}")
                result = await cognee_integration.search_knowledge_graph(
                    query=f"insights and patterns about: {query}",
                    dataset_name=dataset_name_with_account
                )
                
                return f"""💡 **Insights del grafo de conocimiento**

🎯 **Tema analizado:** {query}
📊 **Dataset:** {dataset_name}

🔗 **Patrones y conexiones encontradas:**
{self._format_insights(result.get('results', []))}

📈 **Estado del análisis:** {result.get('status', 'completado')}"""
            
            else:
                return f"❌ Error: Acción '{action}' no reconocida. Usa: process_documents, search_graph, get_insights"
        
        except Exception as e:
            logger.error(f"❌ Error en CogneeKnowledgeGraphTool: {e}")
            return f"❌ Error al ejecutar la herramienta: {str(e)}"
    
    def _run(self, tool_input_json: str, **kwargs) -> str:
        """Ejecuta la herramienta de forma síncrona."""
        return asyncio.run(self._arun(tool_input_json, **kwargs))
    
    def _format_search_results(self, results: List[Any]) -> str:
        """Formatea los resultados de búsqueda."""
        if not results:
            return "No se encontraron resultados específicos."
        
        formatted = []
        for i, result in enumerate(results[:5], 1):  # Limitar a 5 resultados
            if isinstance(result, dict):
                content = result.get('content', str(result))
                formatted.append(f"{i}. {content}")
            else:
                formatted.append(f"{i}. {str(result)}")
        
        return "\n".join(formatted)
    
    def _format_insights(self, results: List[Any]) -> str:
        """Formatea los insights obtenidos."""
        if not results:
            return "No se encontraron patrones específicos en el grafo actual."
        
        # Para insights, intentamos extraer información más estructurada
        insights = []
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
