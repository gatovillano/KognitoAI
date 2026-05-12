import logging
from typing import Optional, Any, Dict, List, Literal
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from knowledge_graph.entity_quality_reviewer import EntityQualityReviewer
from knowledge_graph.trend_analyzer import TrendAnalyzer
from core.llm_manager import get_main_llm, get_fast_llm
from core.config import settings

logger = logging.getLogger(__name__)

class KnowledgeGraphService:
    def __init__(self, graph_db: Optional[GraphDB] = None, graph_integration: Optional[GraphIntegration] = None):
        # Configurar GraphDB con las configuraciones de settings si no se proporciona
        if graph_db is not None:
            self.graph_db = graph_db
        elif not settings.neo4j_uri:
            raise ValueError("Neo4j URI no está configurada en settings.neo4j_uri")
        else:
            self.graph_db = GraphDB(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password
            )
        
        # Configurar GraphIntegration si no se proporciona
        if graph_integration is not None:
            self.graph_integration = graph_integration
        else:
            self.graph_integration = GraphIntegration(self.graph_db)
        
        # Inicializar componentes especializados
        self.entity_reviewer = EntityQualityReviewer(graph_db=self.graph_db)
        self.trend_analyzer = TrendAnalyzer(graph_db=self.graph_db)

    async def fetch_memories_flow(self, workspace_id: Optional[str] = None, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para obtener recuerdos del grafo de conocimiento.
        
        Args:
            workspace_id: ID del workspace (opcional)
            account_id: ID de cuenta del usuario
            
        Returns:
            Dict con los recuerdos encontrados
        """
        try:
            logger.info(f"🔍 Obteniendo memorias para workspace: {workspace_id}, cuenta: {account_id}")
            
            # Conectar a la base de datos si es necesario
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Query para obtener memorias (documentos procesados, conversaciones, etc.)
            query = """
            MATCH (n)
            WHERE n.account_id = $account_id
            AND (
                n.type IN ['DOCUMENT', 'CONCEPTUAL_QUOTE', 'IDEA_PROFILE'] OR
                n.name CONTAINS 'memoria' OR
                n.name CONTAINS 'conversación' OR
                n.name CONTAINS 'chat'
            )
            """
            
            params = {'account_id': account_id}
            
            if workspace_id:
                if workspace_id == "global_context":
                    query += " AND (n.workspace_id IS NULL OR n.workspace_id = '')"
                else:
                    query += " AND n.workspace_id = $workspace_id"
                    params['workspace_id'] = workspace_id
            
            query += """
            RETURN n.name as name, n.type as type, n.description as description,
                   n.created_at as created_at, n.confidence as confidence
            ORDER BY n.created_at DESC
            LIMIT 50
            """
            
            result = await self.graph_db.execute_query(query, params)
            
            memories = [
                {
                    "id": f"{record.get('name', 'unknown')}_{record.get('type', 'unknown')}",
                    "name": record.get('name', 'Sin nombre'),
                    "type": record.get('type', 'unknown'),
                    "description": record.get('description', ''),
                    "created_at": record.get('created_at', ''),
                    "confidence": record.get('confidence', 0.0)
                }
                for record in result
            ]
            
            return {
                "success": True,
                "memories": memories,
                "total": len(memories),
                "workspace_id": workspace_id,
                "account_id": account_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo memorias: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def process_documents_flow(self, db_session: AsyncSession, documents: Optional[List[Dict[str, Any]]] = None, dataset_name: str = "default", account_id: Optional[str] = None, processing_mode: Literal["conceptual", "hybrid"] = "conceptual", topic: Optional[str] = None, workspace_id: Optional[str] = None, request: Optional[Any] = None, **kwargs):
        """
        Flujo para procesar documentos y extraer información para el grafo de conocimiento.
        
        Args:
            db_session: Sesión de base de datos asíncrona inyectada por FastAPI.
            documents: Lista de documentos a procesar
            dataset_name: Nombre del dataset
            account_id: ID de cuenta del usuario
            processing_mode: Modo de procesamiento ("conceptual" o "hybrid")
            topic: Tema para filtrar documentos
            workspace_id: ID del workspace
            request: Objeto request de la API (opcional)
            **kwargs: Argumentos adicionales
        
        Returns:
            Dict con el resultado del procesamiento
        """
        try:
            logger.info(f"DEBUG: db_session en process_documents_flow: {db_session}")
            # Si se proporciona un objeto request, extraer parámetros de él
            if request is not None:
                # Extraer parámetros del request
                documents = getattr(request, 'documents', None)
                dataset_name = getattr(request, 'dataset_name', dataset_name)
                topic = getattr(request, 'topic', topic)
                workspace_id = getattr(request, 'workspace_id', workspace_id)
                processing_mode = getattr(request, 'processing_mode', processing_mode)
                
                # Si hay un topic, usarlo como dataset_name para mantener consistencia con la colección
                if topic:
                    from urllib.parse import unquote
                    decoded_topic = unquote(topic)
                    dataset_name = decoded_topic
                    logger.info(f"🏷️ Forzando dataset_name a '{dataset_name}' basado en el topic de la colección")
                
                # Decodificar dataset_name si viene del topic y está URL encoded
                elif dataset_name and '%' in dataset_name:
                    from urllib.parse import unquote
                    dataset_name = unquote(dataset_name)
                
                logger.info(f"📋 Extrayendo parámetros del request: topic={topic}, workspace_id={workspace_id}, processing_mode={processing_mode}, dataset_name={dataset_name}")
            
            # Asegurar que documents sea una lista vacía si es None
            if documents is None:
                documents = []
            
            logger.info(f"🔄 process_documents_flow llamado con: topic={topic}, workspace_id={workspace_id}, documents_count={len(documents)}")
            
            # Conectar a la base de datos si no está conectada
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Usar GraphIntegration para procesar los documentos
            return await self.graph_integration.process_documents(
                db_session=db_session,
                documents=documents,
                dataset_name=dataset_name,
                account_id=account_id,
                processing_mode=processing_mode,
                topic=topic,
                workspace_id=workspace_id,
                task_id=kwargs.get("task_id")
            )
        except Exception as e:
            logger.error(f"Error en process_documents_flow: {e}", exc_info=True)
            return {"error": str(e), "status": "error"}

    async def search_graph_flow(self, query: str, workspace_id: Optional[str] = None, limit: int = 50, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca nodos en el grafo combinando tres estrategias en cascada:
        1. Full-text index (rápido, requiere que los nodos tengan dataset_name indexado)
        2. Búsqueda por CONTAINS sobre name/title/content (tolerante, sin filtro de dataset)
        3. Fuzzy por similitud de embedding si los anteriores no dan resultados
        """
        try:
            logger.info(f"🔍 Buscando en grafo: '{query}' para cuenta: {account_id}")

            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()

            params: Dict[str, Any] = {"account_id": account_id, "limit": limit}

            # Filtro de workspace opcional
            ws_clause = ""
            if workspace_id and workspace_id not in ("all", "global_context"):
                ws_clause = "AND n.workspace_id = $workspace_id"
                params["workspace_id"] = workspace_id

            # ── Estrategia 1: full-text index ───────────────────────────────
            # Escapar caracteres especiales de Lucene que rompen la query
            safe_query = query.replace("+", " ").replace("-", " ").replace("AND", " ").replace("OR", " ").replace("NOT", " ").strip()
            params["ft_query"] = safe_query

            ft_cypher = f"""
            CALL db.index.fulltext.queryNodes('node_fulltext_index', $ft_query)
            YIELD node AS n, score
            WHERE (n.account_id = $account_id OR n.account_id IS NULL)
            {ws_clause}
            RETURN n.id AS id,
                   coalesce(n.name, n.title, '') AS label,
                   coalesce(n.type, labels(n)[0], 'Entity') AS type,
                   coalesce(n.content, n.description, n.summary, '') AS description,
                   n.dataset_name AS dataset_name,
                   n.workspace_id AS workspace_id,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """

            results = await self.graph_db.execute_query(ft_cypher, params)
            hits = [dict(r) for r in (results or []) if r.get("id") or r.get("label")]

            # ── Estrategia 2: CONTAINS fallback ─────────────────────────────
            if not hits:
                logger.info(f"🔍 Full-text sin resultados, intentando CONTAINS para: '{query}'")
                query_lower = query.lower()
                params["q"] = query_lower

                contains_cypher = f"""
                MATCH (n)
                WHERE (n.account_id = $account_id OR n.account_id IS NULL)
                {ws_clause}
                AND (
                    toLower(coalesce(n.name, ''))        CONTAINS $q OR
                    toLower(coalesce(n.title, ''))       CONTAINS $q OR
                    toLower(coalesce(n.content, ''))     CONTAINS $q OR
                    toLower(coalesce(n.description, '')) CONTAINS $q OR
                    toLower(coalesce(n.summary, ''))     CONTAINS $q
                )
                RETURN n.id AS id,
                       coalesce(n.name, n.title, '') AS label,
                       coalesce(n.type, labels(n)[0], 'Entity') AS type,
                       coalesce(n.content, n.description, n.summary, '') AS description,
                       n.dataset_name AS dataset_name,
                       n.workspace_id AS workspace_id,
                       1.0 AS score
                ORDER BY label ASC
                LIMIT $limit
                """

                results2 = await self.graph_db.execute_query(contains_cypher, params)
                hits = [dict(r) for r in (results2 or []) if r.get("id") or r.get("label")]

            # ── Estrategia 3: términos individuales (query multi-palabra) ────
            if not hits and " " in query:
                logger.info(f"🔍 Sin resultados, intentando términos individuales")
                terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 3]
                if terms:
                    term_conditions = " OR ".join(
                        [f"toLower(coalesce(n.name, '')) CONTAINS $t{i} OR "
                         f"toLower(coalesce(n.title, '')) CONTAINS $t{i} OR "
                         f"toLower(coalesce(n.content, '')) CONTAINS $t{i}"
                         for i, _ in enumerate(terms)]
                    )
                    term_params = {f"t{i}": t for i, t in enumerate(terms)}
                    term_params.update({"account_id": account_id, "limit": limit})
                    if workspace_id and workspace_id not in ("all", "global_context"):
                        term_params["workspace_id"] = workspace_id

                    terms_cypher = f"""
                    MATCH (n)
                    WHERE (n.account_id = $account_id OR n.account_id IS NULL)
                    {ws_clause}
                    AND ({term_conditions})
                    RETURN n.id AS id,
                           coalesce(n.name, n.title, '') AS label,
                           coalesce(n.type, labels(n)[0], 'Entity') AS type,
                           coalesce(n.content, n.description, n.summary, '') AS description,
                           n.dataset_name AS dataset_name,
                           n.workspace_id AS workspace_id,
                           0.5 AS score
                    ORDER BY label ASC
                    LIMIT $limit
                    """
                    results3 = await self.graph_db.execute_query(terms_cypher, term_params)
                    hits = [dict(r) for r in (results3 or []) if r.get("id") or r.get("label")]

            # Deduplicar por id
            seen_ids: set = set()
            unique_hits = []
            for h in hits:
                key = h.get("id") or h.get("label")
                if key and key not in seen_ids:
                    seen_ids.add(key)
                    unique_hits.append(h)

            logger.info(f"✅ Búsqueda completada: {len(unique_hits)} resultados para '{query}'")
            return unique_hits[:limit]

        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}", exc_info=True)
            return []

    async def get_entity_connections_flow(self, entity_id: str, workspace_id: Optional[str] = None, depth: int = 1, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para obtener conexiones de una entidad específica.
        
        Args:
            entity_id: ID de la entidad
            workspace_id: ID del workspace (opcional)
            depth: Profundidad de búsqueda
            account_id: ID de cuenta del usuario
            
        Returns:
            Dict con las conexiones encontradas
        """
        try:
            logger.info(f"🔗 Obteniendo conexiones para entidad: {entity_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Query para obtener conexiones de la entidad
            query = f"""
            MATCH (n)-[r]-(m)
            WHERE n.id = $entity_id
            AND n.account_id = $account_id
            """
            
            params = {'entity_id': entity_id, 'account_id': account_id}
            
            if workspace_id and workspace_id != "global_context":
                query += " AND n.workspace_id = $workspace_id"
                params['workspace_id'] = workspace_id
            
            query += """
            RETURN n, type(r) as relationship_type, m, r
            LIMIT 50
            """
            
            result = await self.graph_db.execute_query(query, params)
            
            connections = [
                {
                    "from_entity": record["n"].get('name', 'unknown'),
                    "to_entity": record["m"].get('name', 'unknown'),
                    "relationship_type": record["relationship_type"],
                    "confidence": record["r"].get('confidence', 0.0)
                }
                for record in result
            ]
            
            return {
                "success": True,
                "entity_id": entity_id,
                "connections": connections,
                "total": len(connections),
                "depth": depth
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conexiones: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def test_neo4j_connection_flow(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Prueba la conexión con Neo4j y obtiene estadísticas básicas.
        
        Args:
            account_id: ID de cuenta del usuario
            
        Returns:
            Dict con el resultado de la prueba
        """
        try:
            logger.info("🔍 Probando conexión con Neo4j")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Query para contar nodos del usuario
            count_query = """
            MATCH (n)
            WHERE n.account_id = $account_id
            RETURN count(n) as total_nodes
            """
            
            result = await self.graph_db.execute_query(count_query, {'account_id': account_id})
            total_nodes = result[0]['total_nodes'] if result else 0
            
            return {
                "success": True,
                "connected": True,
                "total_nodes": total_nodes,
                "message": "Conexión con Neo4j exitosa"
            }
            
        except Exception as e:
            logger.error(f"❌ Error probando conexión: {e}", exc_info=True)
            return {
                "success": False,
                "connected": False,
                "error": str(e)
            }

    async def clear_graph_flow(self, workspace_id: Optional[str] = None, confirm_delete_all: bool = False, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Limpia la base de datos Neo4j.
        
        Args:
            workspace_id: ID del workspace (opcional)
            confirm_delete_all: Confirmar eliminación completa
            account_id: ID de cuenta del usuario
            
        Returns:
            Dict con el resultado de la limpieza
        """
        try:
            logger.info(f"🧹 Iniciando limpieza del grafo para workspace: {workspace_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Validar que se proporcione workspace_id o confirmación para eliminación global
            if not workspace_id and not confirm_delete_all:
                return {
                    "success": False,
                    "error": "Se requiere workspace_id o confirm_delete_all=True para eliminar todos los datos"
                }
            
            # Construir query de eliminación
            delete_query = "MATCH (n)"
            params = {'account_id': account_id}
            
            if workspace_id:
                if workspace_id == "global_context":
                    delete_query += " WHERE (n.workspace_id IS NULL OR n.workspace_id = '') AND n.account_id = $account_id"
                else:
                    delete_query += " WHERE n.workspace_id = $workspace_id AND n.account_id = $account_id"
                    params['workspace_id'] = workspace_id
            else:
                delete_query += " WHERE n.account_id = $account_id"
            
            delete_query += " DETACH DELETE n"
            
            # Ejecutar limpieza
            result = await self.graph_db.execute_query(delete_query, params)
            
            return {
                "success": True,
                "message": f"Limpieza completada para workspace: {workspace_id or 'global'}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error limpiando grafo: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def review_entities_flow(self, workspace_id: Optional[str] = None, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para revisar y mejorar la calidad de las entidades en el grafo.
        
        Args:
            workspace_id: ID del workspace (opcional)
            account_id: ID de cuenta del usuario
            
        Returns:
            Dict con los resultados de la revisión
        """
        try:
            logger.info(f"🔍 Revisando calidad de entidades para workspace: {workspace_id}")
            
            # Usar el entity_reviewer para realizar la revisión
            results = await self.entity_reviewer.review_all_entities(
                workspace_id=workspace_id or "",
                account_id=account_id
            )
            
            return {
                "success": True,
                "review_results": results,
                "workspace_id": workspace_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error revisando entidades: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def apply_corrections_flow(self, corrections: List[Dict[str, Any]], auto_apply: bool = False, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para aplicar correcciones y actualizaciones al grafo.
        
        Args:
            corrections: Lista de correcciones a aplicar
            auto_apply: Si aplicar automáticamente
            account_id: ID de cuenta del usuario
            
        Returns:
            Dict con el resultado de la aplicación
        """
        try:
            logger.info(f"🔧 Aplicando {len(corrections)} correcciones")
            
            # Usar el entity_reviewer para aplicar correcciones
            results = await self.entity_reviewer.apply_corrections(
                corrections=corrections,
                auto_apply=auto_apply
            )
            
            return {
                "success": True,
                "results": results,
                "corrections_applied": len(corrections)
            }
            
        except Exception as e:
            logger.error(f"❌ Error aplicando correcciones: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def detect_trends_flow(self) -> Dict[str, Any]:
        """
        Flujo para detectar tendencias y patrones en el grafo de conocimiento.
        """
        try:
            logger.info("📈 Detectando tendencias en el grafo")
            
            # Usar trend_analyzer para detectar tendencias
            trends = self.trend_analyzer.detect_trends(
                dataset_name="default",
                time_window="last_6_months"
            )
            
            return {
                "success": True,
                "trends": trends
            }
            
        except Exception as e:
            logger.error(f"❌ Error detectando tendencias: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_graph_stats_flow(self, workspace_id: Optional[str] = None, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para obtener estadísticas y métricas del grafo.
        
        Args:
            workspace_id: ID del workspace (opcional)
            account_id: ID de cuenta del usuario
            
        Returns:
            Dict con las estadísticas
        """
        try:
            logger.info(f"📊 Obteniendo estadísticas para workspace: {workspace_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Query para obtener estadísticas básicas
            stats_query = """
            MATCH (n)
            WHERE n.account_id = $account_id
            """
            
            params = {'account_id': account_id}
            
            if workspace_id and workspace_id != "global_context":
                stats_query += " AND n.workspace_id = $workspace_id"
                params['workspace_id'] = workspace_id
            
            stats_query += """
            RETURN n.type as type, count(n) as count
            ORDER BY count DESC
            """
            
            result = await self.graph_db.execute_query(stats_query, params)
            
            stats = {
                "entity_types": [
                    {"type": record["type"], "count": record["count"]}
                    for record in result
                ],
                "total_entities": sum(record["count"] for record in result),
                "workspace_id": workspace_id,
                "account_id": account_id
            }
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_visualization_data_flow(self, workspace_id: Optional[str] = None, account_id: Optional[str] = None, dataset_name: str = "default", focus_query: Optional[str] = None, max_nodes: int = 50) -> Dict[str, Any]:
        """
        Flujo para obtener datos para la visualización del grafo, filtrando por usuario y workspace.
        
        Args:
            workspace_id: ID del workspace (opcional)
            account_id: ID de cuenta del usuario
            dataset_name: Nombre del dataset
            focus_query: Consulta de foco para filtrar nodos relevantes
            max_nodes: Número máximo de nodos a devolver
        """
        try:
            logger.info(f"📈 Obteniendo datos para visualización: account={account_id}, workspace={workspace_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Delegar a GraphIntegration con los filtros correctos
            result = await self.graph_integration.get_visualization_data(
                dataset_name=dataset_name,
                focus_query=focus_query,
                max_nodes=max_nodes,
                account_id=account_id,
                workspace_id=workspace_id
            )
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de visualización: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_datasets_flow(self, account_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para obtener conjuntos de datos relacionados con el grafo, filtrando por usuario y workspace.
        
        Args:
            account_id: ID de cuenta del usuario
            workspace_id: ID del workspace (opcional)
        """
        try:
            logger.info(f"📚 Obteniendo datasets para account={account_id}, workspace={workspace_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Delegar a GraphDB con filtros de usuario
            result = await self.graph_db.get_available_datasets(
                account_id=account_id or "",
                workspace_id=workspace_id
            )
            
            datasets = [
                {
                    "name": record["name"],
                    "node_count": record["node_count"]
                }
                for record in result
            ]
            
            return {
                "success": True,
                "datasets": datasets,
                "total": len(datasets)
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datasets: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_graph_data_flow(self, account_id: Optional[str] = None, workspace_id: Optional[str] = None, max_nodes: int = 100) -> Dict[str, Any]:
        """
        Flujo para obtener los datos crudos del grafo, filtrando estrictamente por usuario y workspace.
        
        Args:
            account_id: ID de cuenta del usuario
            workspace_id: ID del workspace (opcional)
            max_nodes: Número máximo de nodos a devolver
        """
        try:
            logger.info(f"📊 Obteniendo datos del grafo para account={account_id}, workspace={workspace_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Construir query con filtros obligatorios de usuario
            params: Dict[str, Any] = {"account_id": account_id}
            where_clauses = ["(n.account_id = $account_id OR n.account_id IS NULL)"]
            
            if workspace_id and workspace_id != "global_context":
                where_clauses.append("n.workspace_id = $workspace_id")
                params["workspace_id"] = workspace_id
            elif workspace_id == "global_context":
                where_clauses.append("(n.workspace_id IS NULL OR n.workspace_id = '')")
            else:
                # Sin workspace_id: solo nodos del usuario sin workspace asignado
                where_clauses.append("(n.workspace_id IS NULL OR n.workspace_id = '')")
            
            where_str = " AND ".join(where_clauses)
            
            query = f"""
            MATCH (n)
            WHERE {where_str}
            OPTIONAL MATCH (n)-[r]-(m)
            WHERE (m.account_id = $account_id OR m.account_id IS NULL)
            RETURN n, r, m
            LIMIT {max_nodes}
            """
            
            result = await self.graph_db.execute_query(query, params)
            
            # Procesar resultados
            seen_nodes = set()
            nodes = []
            edges = []
            
            for record in result:
                n = record.get("n")
                if n is not None:
                    node_id = str(n.get('id', n.get('element_id', '')))
                    if node_id and node_id not in seen_nodes:
                        seen_nodes.add(node_id)
                        nodes.append({
                            "id": node_id,
                            "label": n.get('name', 'unknown'),
                            "type": n.get('type', 'unknown')
                        })
                
                r = record.get("r")
                m = record.get("m")
                if r is not None and m is not None:
                    edges.append({
                        "from": str(n.get('id', '') if n else ''),
                        "to": str(m.get('id', '')),
                        "type": r.get('type', 'related') if isinstance(r, dict) else getattr(r, 'type', 'related')
                    })
            
            return {
                "success": True,
                "nodes": nodes,
                "edges": edges
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos del grafo: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_graph_metadata_flow(self, account_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para obtener los metadatos del grafo, filtrando por usuario y workspace.
        
        Args:
            account_id: ID de cuenta del usuario
            workspace_id: ID del workspace (opcional)
        """
        try:
            logger.info(f"📋 Obteniendo metadatos del grafo para account={account_id}, workspace={workspace_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            params: Dict[str, Any] = {"account_id": account_id}
            workspace_filter = ""
            if workspace_id and workspace_id != "global_context":
                workspace_filter = " AND n.workspace_id = $workspace_id"
                params["workspace_id"] = workspace_id
            elif workspace_id == "global_context":
                workspace_filter = " AND (n.workspace_id IS NULL OR n.workspace_id = '')"
            
            # Query para obtener tipos de nodos filtrados por usuario
            node_types_query = f"""
            MATCH (n)
            WHERE n.account_id = $account_id{workspace_filter}
            RETURN DISTINCT n.type as type, count(n) as count
            ORDER BY count DESC
            """
            
            # Query para obtener tipos de relaciones filtrados por usuario
            rel_types_query = f"""
            MATCH (n)-[r]->(m)
            WHERE n.account_id = $account_id{workspace_filter}
            RETURN DISTINCT type(r) as type, count(r) as count
            ORDER BY count DESC
            """
            
            node_results = await self.graph_db.execute_query(node_types_query, params)
            rel_results = await self.graph_db.execute_query(rel_types_query, params)
            
            metadata = {
                "nodeTypes": [
                    {"type": record["type"], "count": record["count"]}
                    for record in node_results
                ],
                "edgeTypes": [
                    {"type": record["type"], "count": record["count"]}
                    for record in rel_results
                ]
            }
            
            return {
                "success": True,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo metadatos: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def delete_dataset_flow(self, dataset_name: str, account_id: str) -> Dict[str, Any]:
        """
        Flujo para eliminar un dataset completo del grafo.
        """
        try:
            logger.info(f"🗑️ Iniciando flujo de eliminación de dataset: {dataset_name}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Ejecutar eliminación en GraphDB
            await self.graph_db.delete_dataset(dataset_name, account_id)
            
            return {
                "success": True,
                "message": f"Dataset '{dataset_name}' eliminado correctamente del grafo.",
                "dataset_name": dataset_name
            }
            
        except Exception as e:
            logger.error(f"❌ Error en flujo de eliminación de dataset: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def update_dataset_name_flow(self, old_dataset_name: str, new_dataset_name: str, account_id: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo para actualizar el nombre de un dataset en el grafo.
        """
        try:
            logger.info(f"🔄 Iniciando flujo de actualización de dataset: {old_dataset_name} -> {new_dataset_name}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Ejecutar actualización en GraphDB
            result = await self.graph_db.update_dataset_name(old_dataset_name, new_dataset_name, account_id, file_name)
            
            return {
                "success": True,
                "message": f"Dataset actualizado correctamente en el grafo.",
                "details": result
            }
            
        except Exception as e:
            logger.error(f"❌ Error en flujo de actualización de dataset: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
