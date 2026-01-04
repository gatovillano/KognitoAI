# knowledge_graph/graph_reasoning_node.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

from core.llm_manager import get_fast_llm
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.prompts_graph import CYPHER_GENERATION_PROMPT
from knowledge_graph.output_parsers_graph import GraphOutputParser

logger = logging.getLogger(__name__)

class GraphReasoningNode:
    """
    Nodo de LangGraph especializado en interactuar con el grafo de conocimiento.

    Funciones:
    1.  Genera consultas Cypher a partir de la pregunta del usuario.
    2.  Ejecuta las consultas en la base de datos Neo4j.
    3.  Interpreta los resultados y los formatea en un contexto legible para el LLM.
    4.  Genera una visualización Mermaid del subgrafo resultante.
    """

    def __init__(self, graph_db: GraphDB):
        """
        Inicializa el nodo con una conexión a la base de datos del grafo.

        Args:
            graph_db: Instancia de GraphDB para la conexión con Neo4j.
        """
        self.graph_db = graph_db
        self.llm = get_fast_llm()
        if not self.llm:
            raise ValueError("No se pudo obtener un LLM rápido para el GraphReasoningNode.")
        logger.info("✅ GraphReasoningNode inicializado con LLM rápido.")

    async def ainvoke(self, state: Dict[str, Any], target_datasets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Punto de entrada asíncrono para el nodo. Orquesta el proceso completo.

        Args:
            state: El estado actual del grafo de LangGraph.
            target_datasets: Lista de datasets específicos a consultar.

        Returns:
            Un diccionario con el contexto enriquecido y las nuevas fuentes.
        """
        logger.info("--- (Grafo) Nodo: Razonamiento sobre Grafo de Conocimiento ---")
        
        user_message = self._get_last_user_message(state.get("messages", []))
        if not user_message:
            logger.warning("No se encontró mensaje de usuario para el razonamiento del grafo. Saltando nodo.")
            return {}

        # 1. Generar consulta Cypher
        cypher_query = await self._generate_cypher_query(user_message, target_datasets)
        if not cypher_query:
            return {}
        
        # 2. Ejecutar consulta
        query_results = await self.graph_db.execute_query(cypher_query)
        if not query_results:
            logger.info("La consulta al grafo no devolvió resultados.")
            return {}

        # 3. Interpretar y formatear resultados
        formatted_context, sources = self._format_results(query_results)
        
        # 4. Generar diagrama Mermaid (opcional)
        mermaid_diagram = self._generate_mermaid_diagram(query_results)

        logger.info(f"Contexto generado desde el grafo: {formatted_context[:200]}...")

        # El estado se actualizará en el agente principal, aquí solo devolvemos los datos
        return {
            "graph_context": formatted_context,
            "graph_sources": sources,
            "mermaid_diagram": mermaid_diagram,
        }

    def _get_last_user_message(self, messages: List[BaseMessage]) -> Optional[str]:
        """Extrae el contenido del último HumanMessage."""
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                return str(message.content)
        return None

    async def _generate_cypher_query(self, user_query: str, target_datasets: Optional[List[str]] = None) -> Optional[str]:
        """Genera una consulta Cypher usando un LLM a partir de la pregunta del usuario."""
        if not self.graph_db.schema:
            logger.error("No se puede generar la consulta Cypher: el schema del grafo no está disponible.")
            await self.graph_db.refresh_schema() # Intenta refrescar el schema
            if not self.graph_db.schema:
                logger.error("Refresco de schema fallido. Abortando generación de Cypher.")
                return None
            
        prompt = ChatPromptTemplate.from_template(CYPHER_GENERATION_PROMPT)
        chain = prompt | self.llm
        
        try:
            if not self.llm:
                raise ValueError("LLM no está disponible")
            chain = prompt | self.llm
            
            # Preparar información de datasets para el prompt
            dataset_context = ""
            if target_datasets:
                dataset_context = f"\n**Datasets Objetivo**: {', '.join(target_datasets)}\nFiltra los nodos usando `WHERE n.dataset_name IN {target_datasets}`."
            else:
                dataset_context = "\nBusca en todos los datasets disponibles."

            response = await chain.ainvoke({
                "question": f"{user_query}{dataset_context}", 
                "schema": self.graph_db.schema
            })
            cypher_query = str(response.content).strip().replace("```cypher", "").replace("```", "").strip()
            logger.info(f"Consulta Cypher generada: {cypher_query}")
            return cypher_query
        except Exception as e:
            logger.error(f"Error generando la consulta Cypher: {e}", exc_info=True)
            return None

    def _format_results(self, results: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """Formatea los resultados de Cypher para el LLM y extrae las fuentes."""
        parser = GraphOutputParser()
        context, sources = parser.parse(results)
        # Convertir objetos Source a diccionarios para el estado
        return context, [s.dict() for s in sources]

    def _generate_mermaid_diagram(self, results: List[Dict[str, Any]]) -> str:
        """Genera un diagrama Mermaid a partir de los resultados de la consulta."""
        nodes = set()
        edges = []
        
        processed_node_ids = set()
        processed_edge_ids = set()

        for record in results:
            path = record.get("path")
            if path and isinstance(path, dict):
                path_nodes = path.get('nodes', [])
                path_relationships = path.get('relationships', [])
                
                for node in path_nodes:
                    node_id = node.get('id')
                    if node_id and node_id not in processed_node_ids:
                        nodes.add((str(node_id), f"{node.get('type', '')}: {node.get('name', '')}"))
                        processed_node_ids.add(node_id)

                for rel in path_relationships:
                    rel_id = rel.get('id')
                    if rel_id and rel_id not in processed_edge_ids:
                        edges.append((str(rel.get('start_node')), str(rel.get('end_node')), rel.get('type', '')))
                        processed_edge_ids.add(rel_id)
            else:
                # Manejar formato n, r, m
                n = record.get('n')
                r = record.get('r')
                m = record.get('m')
                if n and isinstance(n, dict):
                    n_id = n.get('id')
                    if n_id and n_id not in processed_node_ids:
                        nodes.add((str(n_id), f"{n.get('type', '')}: {n.get('name', '')}"))
                        processed_node_ids.add(n_id)
                if m and isinstance(m, dict):
                    m_id = m.get('id')
                    if m_id and m_id not in processed_node_ids:
                        nodes.add((str(m_id), f"{m.get('type', '')}: {m.get('name', '')}"))
                        processed_node_ids.add(m_id)
                if r and isinstance(r, dict) and n and m:
                    r_id = r.get('id')
                    if r_id and r_id not in processed_edge_ids:
                        edges.append((str(n.get('id')), str(m.get('id')), r.get('type', '')))
                        processed_edge_ids.add(r_id)

        if not nodes and not edges:
            return ""

        mermaid_str = "graph TD;\n"
        for node_id, node_label in nodes:
            # Escapar caracteres especiales para Mermaid
            safe_label = node_label.replace('"', '#quot;')
            mermaid_str += f'    {node_id}["{safe_label}"];\n'
        
        for start, end, label in edges:
            if start and end:
                mermaid_str += f"    {start} -- {label} --> {end};\n"

        return mermaid_str