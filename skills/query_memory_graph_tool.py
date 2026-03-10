# tools/query_memory_graph_tool.py

"""
Herramienta para que el agente consulte explícitamente su propio grafo de memorias.
"""

import logging
from typing import Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from core.config import settings

# Configuración del logger
logger = logging.getLogger(__name__)

class QueryMemoryGraphInput(BaseModel):
    """Esquema de entrada para la herramienta QueryMemoryGraphTool."""
    query: str = Field(
        ...,
        description="La consulta o pregunta para buscar en el grafo de conocimiento de memorias personales."
    )

class QueryMemoryGraphTool(BaseTool):
    """
    Herramienta que permite al agente consultar su grafo de conocimiento personal
    para encontrar conexiones entre memorias, conceptos recurrentes y patrones de pensamiento.
    """
    name: str = "query_memory_graph"
    description: str = (
        "Útil para consultar tu grafo de conocimiento personal (tus memorias). "
        "Úsalo cuando necesites recordar información específica que has guardado, "
        "entender tus patrones de pensamiento o encontrar conexiones entre tus memorias pasadas. "
        "No uses esta herramienta para buscar en documentos generales."
    )
    args_schema: Type[BaseModel] = QueryMemoryGraphInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    
    _graph_integration: Optional[GraphIntegration] = None

    def __init__(self, **data):
        super().__init__(**data)
        # Inicializar la integración con el grafo
        try:
            graph_db = GraphDB(uri=str(settings.neo4j_uri), user=str(settings.neo4j_user), password=str(settings.neo4j_password))
            graph_db.connect()
            self._graph_integration = GraphIntegration(graph_db)
            logger.info("✅ QueryMemoryGraphTool inicializada con éxito.")
        except Exception as e:
            logger.error(f"❌ Error al inicializar QueryMemoryGraphTool: {e}", exc_info=True)

    async def _arun(self, query: str, **kwargs) -> str:
        """Ejecuta la búsqueda en el grafo de memorias."""
        if not self._graph_integration:
            return "Error: La integración con el grafo de conocimiento no está disponible."

        # Asegurarse de que account_id sea un string válido
        account_id_value = str(self.account_id) if self.account_id else None
        if not account_id_value or account_id_value == "None":
            logger.error("❌ account_id no está definido correctamente")
            return "Error: No se pudo determinar el ID de cuenta para la búsqueda."

        logger.info(f"🧠 Consultando el grafo de memorias para la cuenta {account_id_value} con la consulta: '{query}'")
        
        dataset_name = f"agent_memories_{account_id_value.replace('-', '_')}"

        try:
            # Usar el método de búsqueda de la integración de grafos
            search_result = await self._graph_integration.search_knowledge_graph(
                query=query,
                dataset_name=dataset_name,
                return_type="summary", # Pedir un resumen en lenguaje natural
                account_id=account_id_value  # Pasar explícitamente el account_id
            )
            
            if not search_result or not search_result.get('results'):
                return f"No encontré información relevante en mis memorias para la consulta: '{query}'."

            # Formatear la salida para que sea clara para el LLM
            formatted_result = f"Resultados de la consulta a mi grafo de memorias sobre '{query}':\n"
            formatted_result += search_result.get('results', "No se pudo generar un resumen.")
            
            return formatted_result

        except Exception as e:
            logger.error(f"❌ Error al consultar el grafo de memorias: {e}", exc_info=True)
            return f"Ocurrió un error técnico al intentar consultar mis memorias: {e}"
