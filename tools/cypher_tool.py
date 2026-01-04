import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from knowledge_graph.graph_database import GraphDB
from core.config import settings

logger = logging.getLogger(__name__)

class CypherToolInput(BaseModel):
    query: str = Field(..., description="La consulta Cypher a ejecutar en la base de datos Neo4j.")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parámetros opcionales para la consulta Cypher.")
    dataset_name: Optional[str] = Field(None, description="Nombre del dataset para filtrar resultados (opcional si la consulta ya lo incluye).")

class CypherTool(BaseTool):
    name: str = "cypher_tool"
    description: str = "Ejecutor Directo de Consultas Cypher. Permite realizar consultas avanzadas y personalizadas al grafo de conocimiento de Neo4j. Úsalo cuando necesites un control total sobre la búsqueda relacional."
    args_schema: Type[BaseModel] = CypherToolInput

    account_id: Optional[str] = None
    _graph_db: Optional[GraphDB] = None

    def _get_graph_db(self) -> GraphDB:
        if self._graph_db is None:
            self._graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            self._graph_db.connect()
        return self._graph_db

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("CypherTool no soporta ejecución síncrona.")

    async def _arun(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        dataset_name: Optional[str] = None,
        **kwargs
    ) -> str:
        graph_db = self._get_graph_db()
        
        # Inyectar account_id en los parámetros si no está
        params = parameters or {}
        if self.account_id:
            params['account_id'] = self.account_id
            
        logger.info(f"Ejecutando Cypher: {query} con params: {params}")

        try:
            results = await graph_db.execute_query(query, params)
            
            response_payload = {
                "status": "success",
                "query_executed": query,
                "results_count": len(results) if isinstance(results, list) else 0,
                "results": results,
                "executed_at": datetime.now().isoformat()
            }
            
            return json.dumps(response_payload, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error en CypherTool: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "message": str(e),
                "query_attempted": query
            }, ensure_ascii=False)
