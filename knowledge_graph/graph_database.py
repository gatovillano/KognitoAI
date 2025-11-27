# knowledge_graph/graph_database.py

import logging
from neo4j import GraphDatabase, exceptions
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GraphDB:
    """
    Clase de envoltura para manejar la conexión y las operaciones con una base de datos de grafos Neo4j.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GraphDB, cls).__new__(cls)
        return cls._instance

    def __init__(self, uri: str, user: Optional[str] = None, password: Optional[str] = None):
        """
        Inicializa la conexión a la base de datos.
        """
        # Evitar re-inicialización si ya está configurado
        if hasattr(self, 'uri') and self.uri:
            return

        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None
        logger.info("GraphDB inicializado con la configuración de Neo4j.")

    def connect(self):
        """Establece la conexión con la base de datos."""
        if self._driver is not None:
            logger.warning("⚠️ La conexión a GraphDB ya existe. Reutilizando la conexión existente.")
            return
        try:
            # Conectar con o sin autenticación según la configuración
            if self.user and self.password:
                self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                logger.info(f"✅ Conectado a Neo4j en {self.uri} con autenticación")
            else:
                self._driver = GraphDatabase.driver(self.uri)
                logger.info(f"✅ Conectado a Neo4j en {self.uri} sin autenticación")
            self._driver.verify_connectivity()
            logger.info("✅ Conexión a la base de datos de grafos Neo4j establecida exitosamente.")
        except exceptions.AuthError as e:
            logger.error(f"❌ Error de autenticación con Neo4j: {e}. Revisa tus credenciales en .env (NEO4J_USER, NEO4J_PASSWORD).")
            raise
        except exceptions.ServiceUnavailable as e:
            logger.error(f"❌ No se pudo conectar a Neo4j en {self.uri}: {e}. ¿Está el contenedor de Neo4j corriendo?")
            raise
        except Exception as e:
            logger.error(f"❌ Ocurrió un error inesperado al conectar con Neo4j: {e}")
            raise

    def close(self):
        """Cierra la conexión con la base de datos."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("🔌 Conexión a la base de datos de grafos Neo4j cerrada.")

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta Cypher en la base de datos de forma asíncrona.

        Args:
            query (str): La consulta Cypher a ejecutar.
            parameters (dict, optional): Parámetros para la consulta.

        Returns:
            List[Dict[str, Any]]: Una lista de registros resultantes.
        """
        if self._driver is None:
            raise ConnectionError("No hay conexión a la base de datos. Llama a connect() primero.")

        # Ejecutar en un thread pool para no bloquear el event loop
        import asyncio
        import concurrent.futures

        def _execute_sync():
            with self._driver.session() as session:
                logger.info(f"[_execute_sync] Query: {query}")
                logger.info(f"[_execute_sync] Params: {parameters}")
                result = session.run(query, parameters)
                return [record.data() for record in result]

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, _execute_sync)

    async def add_node(self, node_type: str, properties: Dict[str, Any]):
        """
        Añade un nodo al grafo. Si un nodo con la misma propiedad 'cognee_id' ya existe,
        actualiza sus propiedades (operación MERGE).

        Args:
            node_type (str): El tipo (label) del nodo.
            properties (dict): Las propiedades del nodo. 'cognee_id' se usa como clave única.
        """
        unique_property = 'cognee_id'
        if unique_property not in properties:
            logger.warning(f"⚠️ El nodo de tipo '{node_type}' no tiene '{unique_property}'. Se creará sin garantía de unicidad.")
            query = f"CREATE (n:{node_type} $props)"
            await self.execute_query(query, parameters={"props": properties})
            return

        query = (
            f"MERGE (n:{node_type} {{ {unique_property}: $unique_val }}) "
            "ON CREATE SET n = $props "
            "ON MATCH SET n += $props"
        )
        params = {"unique_val": properties[unique_property], "props": properties}
        await self.execute_query(query, parameters=params)

    async def add_relationship_by_property(self, source_prop_key: str, source_prop_value: Any, target_prop_key: str, target_prop_value: Any, rel_type: str, properties: Dict[str, Any]):
        """
        Crea una relación entre dos nodos, identificándolos por una propiedad única.

        Args:
            source_prop_key (str): La clave de la propiedad del nodo de origen (ej. 'cognee_id').
            source_prop_value (Any): El valor de la propiedad del nodo de origen.
            target_prop_key (str): La clave de la propiedad del nodo de destino.
            target_prop_value (Any): El valor de la propiedad del nodo de destino.
            rel_type (str): El tipo de la relación.
            properties (dict): Las propiedades de la relación.
        """
        query = (
            f"MATCH (a {{{source_prop_key}: $source_val}}), (b {{{target_prop_key}: $target_val}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            "SET r += $props"
        )
        params = {"source_val": source_prop_value, "target_val": target_prop_value, "props": properties}
        await self.execute_query(query, parameters=params)