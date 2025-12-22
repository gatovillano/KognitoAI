# knowledge_graph/graph_database.py

import logging
import time
import random
from neo4j import GraphDatabase, exceptions
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Constantes para reintentos
MAX_RETRIES = 3
INITIAL_DELAY = 0.5 # segundos

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
        self.schema: Optional[str] = None # Caché para el schema
        logger.info("GraphDB inicializado con la configuración de Neo4j.")

    async def refresh_schema(self):
        """
        Refresca el schema de la base de datos (tipos de nodos, relaciones, propiedades)
        y lo guarda en la caché interna.
        """
        logger.info("🔄 Refrescando el schema del grafo de conocimiento...")
        try:
            # Obtener todos los labels de nodos
            node_labels_query = "CALL db.labels()"
            node_labels_result = await self.execute_query(node_labels_query)
            node_labels = [record["label"] for record in node_labels_result]

            # Obtener todos los tipos de relaciones
            rel_types_query = "CALL db.relationshipTypes()"
            rel_types_result = await self.execute_query(rel_types_query)
            rel_types = [record["relationshipType"] for record in rel_types_result]

            # Obtener propiedades para cada tipo de nodo
            schema_parts = []
            for label in node_labels:
                props_query = f"MATCH (n:`{label}`) WITH n LIMIT 1 RETURN keys(n) as props"
                props_result = await self.execute_query(props_query)
                props = props_result[0]['props'] if props_result else []
                schema_parts.append(f"Nodo '{label}' con propiedades: {props}")

            # Obtener estructura de las relaciones
            for rel_type in rel_types:
                rel_schema_query = f"""
                MATCH (n)-[r:`{rel_type}`]->(m)
                WITH n, m LIMIT 1
                RETURN labels(n) as from_labels, labels(m) as to_labels
                """
                rel_schema_result = await self.execute_query(rel_schema_query)
                if rel_schema_result:
                    from_labels = rel_schema_result[0]['from_labels']
                    to_labels = rel_schema_result[0]['to_labels']
                    schema_parts.append(f"Relación ':{rel_type}' conecta ({':'.join(from_labels)}) con ({':'.join(to_labels)})")

            self.schema = "\n".join(schema_parts)
            logger.info("✅ Schema del grafo refrescado y cacheado exitosamente.")
            logger.debug(f"Schema detectado:\n{self.schema}")

        except Exception as e:
            logger.error(f"❌ Error al refrescar el schema del grafo: {e}", exc_info=True)
            self.schema = None # Invalidar schema en caso de error

    def connect(self):
        """Establece la conexión con la base de datos."""
        # Si ya hay un driver y no está cerrado, lo reutilizamos.
        if self._driver is not None and not getattr(self._driver, 'closed', False):
            try:
                self._driver.verify_connectivity()
                logger.warning("⚠️ La conexión a GraphDB ya existe y está abierta y funcional. Reutilizando la conexión existente.")
                return
            except exceptions.ServiceUnavailable:
                logger.warning("🔄 La conexión existente a GraphDB está inactiva. Intentando reconectar...")
                self.close() # Forzar cierre del driver inactivo
            except Exception as e:
                logger.warning(f"🔄 Error al verificar la conexión existente a GraphDB: {e}. Intentando reconectar...")
                self.close() # Forzar cierre del driver en caso de otros errores

        # Intentar establecer una nueva conexión
        try:
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
            self._driver = None # Asegurar que el driver se resetee
            raise
        except exceptions.ServiceUnavailable as e:
            logger.error(f"❌ No se pudo conectar a Neo4j en {self.uri}: {e}. ¿Está el contenedor de Neo4j corriendo? Reintentando...")
            self._driver = None # Asegurar que el driver se resetee
            raise
        except Exception as e:
            logger.error(f"❌ Ocurrió un error inesperado al conectar con Neo4j: {e}", exc_info=True)
            self._driver = None # Asegurar que el driver se resetee
            raise

    def close(self):
        """Cierra la conexión con la base de datos."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("🔌 Conexión a la base de datos de grafos Neo4j cerrada.")

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta Cypher en la base de datos de forma asíncrona con reintentos.

        Args:
            query (str): La consulta Cypher a ejecutar.
            parameters (dict, optional): Parámetros para la consulta.

        Returns:
            List[Dict[str, Any]]: Una lista de registros resultantes.
        """
        last_exception = None
        for i in range(MAX_RETRIES):
            try:
                if self._driver is None or getattr(self._driver, 'closed', False):
                    logger.warning(f"🔄 Driver no disponible o cerrado en intento {i+1}/{MAX_RETRIES}, intentando reconectar...")
                    self.connect()

                # Ejecutar en un thread pool para no bloquear el event loop
                import asyncio
                import concurrent.futures

                def _execute_sync():
                    with self._driver.session() as session:
                        logger.debug(f"[_execute_sync] Query: {query}")
                        logger.debug(f"[_execute_sync] Params: {parameters}")
                        result = session.run(query, parameters)
                        return [dict(record) for record in result]

                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, _execute_sync)

            except (exceptions.ServiceUnavailable, exceptions.TransientError) as e:
                last_exception = e
                self._driver = None  # Forzar reconexión en el siguiente intento
                delay = INITIAL_DELAY * (2 ** i) + random.uniform(0, 0.1) # Retroceso exponencial con jitter
                logger.warning(f"⚠️ Error de conexión a Neo4j: {e}. Reintentando en {delay:.2f} segundos... (Intento {i+1}/{MAX_RETRIES})")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"❌ Error inesperado al ejecutar consulta Cypher: {e}", exc_info=True)
                raise # Re-lanzar otras excepciones inmediatamente

        logger.error(f"❌ Fallaron todos los intentos de conectar y ejecutar consulta Cypher después de {MAX_RETRIES} reintentos.")
        raise last_exception # Re-lanzar la última excepción de conexión/transitoria

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