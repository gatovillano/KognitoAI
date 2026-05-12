# knowledge_graph/graph_reasoning_node.py

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

from core.llm_manager import get_fast_llm
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.prompts_graph import CYPHER_GENERATION_PROMPT
from knowledge_graph.output_parsers_graph import GraphOutputParser
from core.database import SessionLocal, AnalysisTask
from utils.db_session import DBSession
import uuid
from datetime import datetime

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
        Punto de entrada asíncrono para el nodo. Realiza 'Pensamiento Neuronal' (razonamiento latente)
        de forma obligatoria para encontrar conexiones profundas en el grafo.

        Args:
            state: El estado actual del grafo de LangGraph.
            target_datasets: Lista de datasets específicos a consultar.

        Returns:
            Un diccionario con el contexto enriquecido y las nuevas fuentes.
        """
        logger.info("--- (Grafo) Nodo: Pensamiento Neuronal sobre Grafo de Conocimiento ---")
        
        user_message = self._get_last_user_message(state.get("messages", []))
        if not user_message:
            logger.warning("No se encontró mensaje de usuario para el razonamiento del grafo. Saltando nodo.")
            return {}

        logger.info(f"🧠 Iniciando Pensamiento Neuronal para la pregunta: '{user_message}'")
        
        # Obtener LLM específico para el usuario si está disponible
        account_id = state.get("account_id")
        workspace_id = state.get("workspace_id")
        
        llm_to_use = self.llm
        if account_id:
            from core.llm_manager import get_llm_for_user
            user_llm = await get_llm_for_user(account_id, purpose="fast")
            if user_llm:
                llm_to_use = user_llm

        if target_datasets:
            logger.info(f"🎯 Datasets objetivo: {target_datasets}")
        else:
            logger.info("🎯 Buscando en todos los datasets disponibles.")

        # 1. Ejecutar Pensamiento Neuronal (Exploración Latente)
        neural_insights, analysis_id, neural_data = await self._perform_neural_thinking(
            user_message, target_datasets, account_id, workspace_id, llm=llm_to_use
        )
        
        if not neural_data and not neural_insights:
            logger.info("❌ El pensamiento neuronal no encontró conexiones relevantes.")
            return {}

        # 2. Interpretar y formatear resultados
        # Usamos la data cruda encontrada por el pensamiento neuronal para generar fuentes y contexto base
        formatted_context, sources = self._format_results(neural_data)
        
        # 3. Integrar insights neuronales (la síntesis del LLM) en el contexto
        if neural_insights:
            if formatted_context and formatted_context != "No se encontraron resultados en el grafo de conocimiento.":
                formatted_context = f"### 🕸️ Relaciones Encontradas en el Grafo\n{formatted_context}\n\n### 🧠 Análisis Neuronal (Relaciones Latentes)\n{neural_insights}"
            else:
                formatted_context = f"### 🧠 Análisis Neuronal (Relaciones Latentes)\n{neural_insights}"
            
            # Añadir una fuente "virtual" para el insight neuronal
            from core.citation_models import Source, SourceType
            
            source_url = f"analysis://{analysis_id}" if analysis_id else "graph://neural_insight"
            
            sources.append(Source(
                id=len(sources) + 1,
                title="Análisis de Relaciones Latentes (Grafo)",
                url=source_url,
                snippet=neural_insights,
                type=SourceType.GRAPH,
                metadata={"type": "neural_insight"}
            ).dict())
        
        # 4. Generar diagrama Mermaid a partir de la data neuronal
        mermaid_diagram = self._generate_mermaid_diagram(neural_data)

        logger.info(f"✅ Contexto enriquecido generado vía Pensamiento Neuronal. Fuentes totales: {len(sources)}")

        return {
            "graph_context": formatted_context,
            "graph_sources": sources,
            "mermaid_diagram": mermaid_diagram,
        }

    async def _perform_neural_thinking(self, user_query: str, target_datasets: Optional[List[str]] = None, account_id: Optional[str] = None, workspace_id: Optional[str] = None, llm: Optional[Any] = None) -> Tuple[str, Optional[str], List[Dict[str, Any]]]:
        """
        Realiza un 'Pensamiento Neuronal' explorando el grafo de forma agresiva 
        para encontrar relaciones que no son evidentes en una consulta simple.
        
        Retorna: (insight_text, analysis_id, raw_data)
        """
        llm_to_use = llm or self.llm
        if not llm_to_use:
            return "", None, []

        # Identificar conceptos clave
        concepts = []
        try:
            # Usar siempre el LLM para mejor calidad, con un prompt más robusto para capturar el intento
            concepts_prompt = f"Extrae los 3 conceptos o entidades más importantes de esta consulta para buscar en un grafo: '{user_query}'. Responde solo con los nombres separados por comas, sin explicaciones."
            concepts_resp = await llm_to_use.ainvoke(concepts_prompt)
            concepts = [c.strip() for c in str(concepts_resp.content).split(",") if c.strip() and len(c) > 2]
            logger.info(f"🧠 Conceptos clave identificados vía LLM: {concepts}")
        except Exception as e:
            logger.error(f"Error extrayendo conceptos vía LLM: {e}")
            concepts = [w for w in user_query.split() if len(w) > 4][:3] # Fallback simple
        
        all_neural_data = []
        
        dataset_filter_sp = ""
        if target_datasets:
            dataset_filter_sp = f"AND ALL(node IN nodes(p) WHERE node.dataset_name IN {target_datasets})"

        # Profundidad Dinámica: Si hay más de un concepto, intentar encontrar el camino más corto entre los dos primeros
        if len(concepts) >= 2:
            concept1 = concepts[0]
            concept2 = concepts[1]
            
            workspace_filter_nodes = ""
            params_sp = {"concept1": concept1, "concept2": concept2, "account_id": account_id}
            if workspace_id:
                workspace_filter_nodes = "AND n.workspace_id = $workspace_id AND m.workspace_id = $workspace_id AND ALL(node IN nodes(p) WHERE node.workspace_id = $workspace_id) AND ALL(rel IN relationships(p) WHERE rel.workspace_id = $workspace_id)"
                params_sp["workspace_id"] = workspace_id
            else:
                workspace_filter_nodes = "AND n.workspace_id IS NULL AND m.workspace_id IS NULL AND ALL(node IN nodes(p) WHERE node.workspace_id IS NULL) AND ALL(rel IN relationships(p) WHERE rel.workspace_id IS NULL)"

            shortest_path_query = f"""
            MATCH (n), (m)
            WHERE (n.name CONTAINS $concept1 OR n.description CONTAINS $concept1)
              AND (m.name CONTAINS $concept2 OR m.description CONTAINS $concept2)
              AND (n.account_id = $account_id OR n.account_id IS NULL)
              AND (m.account_id = $account_id OR m.account_id IS NULL)
            MATCH p = shortestPath((n)-[*1..4]-(m))
            WHERE ALL(node IN nodes(p) WHERE (node.account_id = $account_id OR node.account_id IS NULL))
              AND ALL(rel IN relationships(p) WHERE (rel.account_id = $account_id OR rel.account_id IS NULL))
              {workspace_filter_nodes}
              {dataset_filter_sp}
            RETURN p as path
            LIMIT 5
            """
            sp_results = await self.graph_db.execute_query(shortest_path_query, params_sp)
            if sp_results:
                logger.info(f"🕸️ Camino más corto encontrado entre '{concept1}' y '{concept2}': {len(sp_results)} caminos.")
                all_neural_data.extend(sp_results)

        for concept in concepts:
            # Query de expansión: busca el concepto y sus vecinos hasta 2 saltos
            dataset_filter = ""
            if target_datasets:
                dataset_filter = f"AND ALL(node IN nodes(p) WHERE node.dataset_name IN {target_datasets})"
            
            workspace_filter_path = ""
            params = {"concept": concept, "account_id": account_id}
            if workspace_id:
                workspace_filter_path = "AND ALL(node IN nodes(p) WHERE node.workspace_id = $workspace_id) AND ALL(rel IN relationships(p) WHERE rel.workspace_id = $workspace_id)"
                params["workspace_id"] = workspace_id
            else:
                workspace_filter_path = "AND ALL(node IN nodes(p) WHERE node.workspace_id IS NULL) AND ALL(rel IN relationships(p) WHERE rel.workspace_id IS NULL)"

            neural_query = f"""
            MATCH p = (n)-[r*1..2]-(m)
            WHERE (n.name CONTAINS $concept OR n.description CONTAINS $concept)
              AND ALL(node IN nodes(p) WHERE (node.account_id = $account_id OR node.account_id IS NULL))
              AND ALL(rel IN relationships(p) WHERE (rel.account_id = $account_id OR rel.account_id IS NULL))
              {workspace_filter_path}
              {dataset_filter}
            RETURN p as path
            LIMIT 10
            """
            results = await self.graph_db.execute_query(neural_query, params)
            if results:
                logger.info(f"🕸️ Exploración para '{concept}': {len(results)} caminos encontrados.")
                all_neural_data.extend(results)
            
        if not all_neural_data:
            logger.info("🧠 No se encontraron conexiones latentes relevantes.")
            return "", None, []
            
        # Ranking de relevancia por superposición de conceptos
        def score_path(record):
            path_str = str(record).lower()
            return sum(1 for c in concepts if c.lower() in path_str)
        
        all_neural_data.sort(key=score_path, reverse=True)
            
        # Pedir al LLM que "piense" sobre estos datos latentes
        # Para el prompt de síntesis, enriquecemos la semántica (tipo y descripción)
        simplified_data = []
        parser = GraphOutputParser()
        # Tomamos los top 15 después del ranking
        for record in all_neural_data[:15]:
            path_obj = record.get("path")
            path = parser._to_dict(path_obj) if path_obj else {}
            nodes = []
            rels = []
            
            if path and isinstance(path, dict):
                for n in path.get("nodes", []):
                    node_str = f"[{n.get('type', 'Entity')}] {n.get('name', 'Unknown')}"
                    desc = n.get('description', '')
                    if desc:
                        node_str += f" (Desc: {desc[:80]}...)"
                    nodes.append(node_str)
                rels = [r.get("type") for r in path.get("relationships", [])]
            else:
                logger.warning(f"El objeto path no se pudo convertir a diccionario.")
                nodes = []
                rels = []
            simplified_data.append({"camino": " -> ".join(filter(None, nodes)), "relaciones": rels})

        thinking_prompt = f"""
Analiza estos fragmentos de relaciones encontrados en el grafo de conocimiento para la consulta: "{user_query}"

**Datos del Grafo (Caminos encontrados)**:
{json.dumps(simplified_data, indent=2)}

**Tarea**:
Genera un breve análisis (3-4 frases) sobre conexiones interesantes o patrones que el usuario podría no haber notado. 
Enfócate en cómo estos conceptos se entrelazan y qué revelan sobre el contexto de la pregunta.
"""
        logger.info("🧠 Sintetizando insights a partir de las conexiones encontradas...")
        response = await llm_to_use.ainvoke(thinking_prompt)
        insight = str(response.content).strip()
        logger.info(f"🧠 Síntesis completada.")

        # Guardar el insight como un AnalysisTask si tenemos account_id
        analysis_id = None
        if account_id and insight:
            try:
                async with DBSession(SessionLocal) as db:
                    result_payload = {
                        "summary": insight,
                        "neural_data_sample": simplified_data,
                        "user_query": user_query,
                        "concepts": concepts,
                        "analysis_metadata": {
                            "analysis_type": "neural_insight",
                            "created_at": datetime.now().isoformat(),
                            "workspace_id": workspace_id
                        }
                    }
                    
                    new_task = AnalysisTask(
                        account_id=uuid.UUID(account_id),
                        file_name=f"Neural Insight: {concepts[0] if concepts else 'General'}",
                        status="completed",
                        analysis_type="neural_insight",
                        result_payload=result_payload
                    )
                    db.add(new_task)
                    await db.commit()
                    analysis_id = str(new_task.id)
                    logger.info(f"💾 Neural Insight guardado como AnalysisTask (ID: {new_task.id})")
            except Exception as e:
                logger.error(f"❌ Error al guardar Neural Insight en BD: {e}", exc_info=True)

        return insight, analysis_id, all_neural_data

    def _get_last_user_message(self, messages: List[BaseMessage]) -> Optional[str]:
        """Extrae el contenido del último HumanMessage."""
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                from core.agent import extract_text_content
                return extract_text_content(message.content)
        return None

    async def _generate_cypher_query(self, user_query: str, target_datasets: Optional[List[str]] = None, llm: Optional[Any] = None) -> Optional[str]:
        """Genera una consulta Cypher usando un LLM a partir de la pregunta del usuario."""
        llm_to_use = llm or self.llm
        if not llm_to_use:
            return None

        schema_to_use = self.graph_db.schema
        if not schema_to_use:
            logger.warning("⚠️ Schema del grafo no disponible. Intentando refrescar...")
            await self.graph_db.refresh_schema()
            schema_to_use = self.graph_db.schema
            
        if not schema_to_use:
            logger.warning("⚠️ Refresco de schema fallido. Usando SCHEMA DE FALLBACK genérico.")
            schema_to_use = """
            Nodes have properties: name, description, dataset_name, account_id, type.
            Relationships have properties: type, description, weight.
            Common labels: Entity, Concept, Document, Chunk.
            Common relationships: RELATED_TO, MENTIONS, HAS_PART.
            """
            
        prompt = ChatPromptTemplate.from_template(CYPHER_GENERATION_PROMPT)
        
        try:
            chain = prompt | llm_to_use
            
            # Preparar información de datasets para el prompt
            dataset_context = ""
            if target_datasets:
                dataset_context = f"\n**Datasets Objetivo**: {', '.join(target_datasets)}\nFiltra los nodos usando `WHERE n.dataset_name IN {target_datasets}`."
            else:
                dataset_context = "\nBusca en todos los datasets disponibles."

            response = await chain.ainvoke({
                "question": f"{user_query}{dataset_context}", 
                "schema": schema_to_use
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

        parser = GraphOutputParser()
        for record in results:
            path_obj = record.get("path")
            path = parser._to_dict(path_obj) if path_obj else None
            
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
                n = parser._to_dict(record.get('n'))
                r = parser._to_dict(record.get('r'))
                m = parser._to_dict(record.get('m'))
                
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
