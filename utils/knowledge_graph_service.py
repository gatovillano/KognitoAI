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
            WHERE (n.account_id = $account_id OR n.account_id IS NULL)
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
        Flujo para buscar información dentro del grafo de conocimiento.
        
        Args:
            query: Término de búsqueda
            workspace_id: ID del workspace (opcional)
            limit: Límite de resultados
            account_id: ID de cuenta del usuario
            
        Returns:
            Lista de resultados de búsqueda
        """
        try:
            logger.info(f"🔍 Buscando en grafo: '{query}' para cuenta: {account_id}")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Usar GraphIntegration para realizar la búsqueda
            search_results = await self.graph_integration.search_knowledge_graph(
                query=query,
                dataset_name="default",
                return_type="summary"
            )
            
            # Formatear resultados para la API
            results = search_results.get("results", [])
            
            # Limitar resultados si es necesario
            if limit and len(results) > limit:
                results = results[:limit]
            
            logger.info(f"✅ Búsqueda completada: {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}", exc_info=True)
            return [{"error": str(e), "type": "search_error"}]

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
            AND (n.account_id = $account_id OR n.account_id IS NULL)
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
            WHERE (n.account_id = $account_id OR n.account_id IS NULL)
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
                    delete_query += " WHERE (n.workspace_id IS NULL OR n.workspace_id = '') AND (n.account_id = $account_id OR n.account_id IS NULL)"
                else:
                    delete_query += " WHERE n.workspace_id = $workspace_id AND (n.account_id = $account_id OR n.account_id IS NULL)"
                    params['workspace_id'] = workspace_id
            else:
                delete_query += " WHERE (n.account_id = $account_id OR n.account_id IS NULL)"
            
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
            WHERE (n.account_id = $account_id OR n.account_id IS NULL)
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

    async def get_visualization_data_flow(self) -> Dict[str, Any]:
        """
        Flujo para obtener datos para la visualización del grafo.
        """
        try:
            logger.info("📈 Obteniendo datos para visualización")
            
            # Por ahora, delegar a get_graph_data_flow
            return await self.get_graph_data_flow()
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de visualización: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_datasets_flow(self) -> Dict[str, Any]:
        """
        Flujo para obtener conjuntos de datos relacionados con el grafo.
        """
        try:
            logger.info("📚 Obteniendo datasets disponibles")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Query para obtener datasets únicos
            query = """
            MATCH (n)
            WHERE n.dataset_name IS NOT NULL
            RETURN DISTINCT n.dataset_name as dataset_name, count(n) as node_count
            ORDER BY dataset_name
            """
            
            result = asyncio.run(self.graph_db.execute_query(query))
            
            datasets = [
                {
                    "name": record["dataset_name"],
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

    async def get_graph_data_flow(self) -> Dict[str, Any]:
        """
        Flujo para obtener los datos crudos del grafo.
        """
        try:
            logger.info("📊 Obteniendo datos del grafo")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Query para obtener datos del grafo
            query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN n, r, m
            LIMIT 100
            """
            
            result = asyncio.run(self.graph_db.execute_query(query))
            
            # Procesar resultados (simplificado)
            nodes = []
            edges = []
            
            for record in result:
                n = record["n"]
                if n and n not in nodes:
                    nodes.append({
                        "id": str(n.get('id', '')),
                        "label": n.get('name', 'unknown'),
                        "type": n.get('type', 'unknown')
                    })
                
                r = record["r"]
                m = record["m"]
                if r and m:
                    edges.append({
                        "from": str(n.get('id', '')),
                        "to": str(m.get('id', '')),
                        "type": r.get('type', 'related')
                    })
            
            return {
                "success": True,
                "nodes": nodes,
                "edges": edges
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos del grafo: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_graph_metadata_flow(self) -> Dict[str, Any]:
        """
        Flujo para obtener los metadatos del grafo.
        """
        try:
            logger.info("📋 Obteniendo metadatos del grafo")
            
            # Asegurar que la conexión esté activa
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', True):
                self.graph_db.connect()
            
            # Query para obtener tipos de nodos
            node_types_query = """
            MATCH (n)
            RETURN DISTINCT n.type as type, count(n) as count
            ORDER BY count DESC
            """
            
            # Query para obtener tipos de relaciones
            rel_types_query = """
            MATCH ()-[r]->()
            RETURN DISTINCT type(r) as type, count(r) as count
            ORDER BY count DESC
            """
            
            node_results = await self.graph_db.execute_query(node_types_query)
            rel_results = await self.graph_db.execute_query(rel_types_query)
            
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
