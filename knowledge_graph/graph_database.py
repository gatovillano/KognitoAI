# knowledge_graph/graph_database.py
from neo4j import GraphDatabase
from core.config import settings  #  Asegúrate de que este archivo exista y tenga las configuraciones correctas
import logging
from knowledge_graph.knowledge_models import Node  #  Importa el modelo Node

logger = logging.getLogger(__name__)

class GraphDB:
    def __init__(self, uri, user, password):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

    def connect(self):
        """Establece una conexión con la base de datos de grafos."""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.verify_connection()  # Verificar la conexión
            logger.info("Conexión a la base de datos de grafos establecida.")
        except Exception as e:
            logger.error(f"Error al conectar a la base de datos de grafos: {e}", exc_info=True)
            raise

    def close(self):
        """Cierra la conexión con la base de datos de grafos."""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Conexión a la base de datos de grafos cerrada.")

    def verify_connection(self):
        """Verifica que la conexión a la base de datos sea válida."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Conexión a la base de datos de grafos verificada.")
        except Exception as e:
            logger.error(f"Error al verificar la conexión a la base de datos: {e}", exc_info=True)
            raise


    def create_node(self, node: Node):
        """Crea un nuevo nodo en la base de datos de grafos."""
        try:
            query = f"CREATE (n:{node.label} $properties) RETURN n"
            with self.driver.session() as session:
                result = session.run(query, properties=node.properties)
                node = result.single()[0]  #  Acceder al nodo directamente
                logger.info(f"Nodo creado: {node}")
                return node
        except Exception as e:
            logger.error(f"Error al crear el nodo: {e}", exc_info=True)
            raise

    def get_node(self, label, property_name, property_value):
        """Obtiene un nodo de la base de datos de grafos basado en una propiedad."""
        try:
            query = f"MATCH (n:{label} {{{property_name}: $property_value}}) RETURN n"
            with self.driver.session() as session:
                result = session.run(query, property_value=property_value)
                node = result.single()
                if node:
                    logger.info(f"Nodo obtenido: {node[0]}")
                    return node[0]
                else:
                    logger.info("No se encontró el nodo.")
                    return None
        except Exception as e:
            logger.error(f"Error al obtener el nodo: {e}", exc_info=True)
            raise

    def update_node(self, label, property_name, property_value, new_properties):
        """Actualiza las propiedades de un nodo en la base de datos de grafos."""
        try:
            query = f"MATCH (n:{label} {{{property_name}: $property_value}}) SET n = $new_properties RETURN n"
            with self.driver.session() as session:
                result = session.run(query, property_value=property_value, new_properties=new_properties)
                node = result.single()
                if node:
                    logger.info(f"Nodo actualizado: {node[0]}")
                    return node[0]
                else:
                    logger.info("No se encontró el nodo para actualizar.")
                    return None
        except Exception as e:
            logger.error(f"Error al actualizar el nodo: {e}", exc_info=True)
            raise

    def delete_node(self, label, property_name, property_value):
        """Elimina un nodo de la base de datos de grafos."""
        try:
            query = f"MATCH (n:{label} {{{property_name}: $property_value}}) DELETE n"
            with self.driver.session() as session:
                session.run(query, property_value=property_value)
                logger.info(f"Nodo eliminado.")
        except Exception as e:
            logger.error(f"Error al eliminar el nodo: {e}", exc_info=True)
            raise

    def create_relationship(self, node1_label, node1_property_name, node1_property_value, relationship_type, node2_label, node2_property_name, node2_property_value, properties=None):
        """Crea una relación entre dos nodos en la base de datos de grafos."""
        try:
            if properties is None:
                properties = {}
            query = (
                f"MATCH (n1:{node1_label} {{{node1_property_name}: $node1_property_value}}), "
                f"(n2:{node2_label} {{{node2_property_name}: $node2_property_value}}) "
                f"CREATE (n1)-[r:{relationship_type} $properties]->(n2) "
                f"RETURN r"
            )
            with self.driver.session() as session:
                result = session.run(
                    query,
                    node1_property_value=node1_property_value,
                    node2_property_value=node2_property_value,
                    properties=properties,
                )
                relationship = result.single()
                if relationship:
                    logger.info(f"Relación creada: {relationship[0]}")
                    return relationship[0]
                else:
                    logger.info("No se pudieron encontrar los nodos para crear la relación.")
                    return None
        except Exception as e:
            logger.error(f"Error al crear la relación: {e}", exc_info=True)
            raise

    def execute_query(self, query, parameters=None):
        """Ejecuta una consulta Cypher personalizada en la base de datos de grafos."""
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                data = result.data()
                logger.info(f"Consulta ejecutada. Resultados: {data}")
                return data
        except Exception as e:
            logger.error(f"Error al ejecutar la consulta: {e}", exc_info=True)
            raise

# Ejemplo de uso (puedes mover esto a otro archivo para pruebas):
if __name__ == '__main__':
    #  Asegúrate de que estas variables de entorno estén configuradas
    neo4j_uri = settings.neo4j_uri
    neo4j_user = settings.neo4j_user
    neo4j_password = settings.neo4j_password

    graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)

    try:
        graph_db.connect()

        #  Ejemplo de creación de un nodo
        concepto1 = graph_db.create_node("Concepto", {"nombre": "Inteligencia Artificial", "descripcion": "Campo de la informática dedicado a la creación de sistemas inteligentes."})
        print(f"Concepto 1 creado: {concepto1}")

        concepto2 = graph_db.create_node("Concepto", {"nombre": "Aprendizaje Automático", "descripcion": "Subcampo de la IA que permite a las máquinas aprender de los datos."})
        print(f"Concepto 2 creado: {concepto2}")

        #  Ejemplo de creación de una relación
        relacion = graph_db.create_relationship("Concepto", "nombre", "Aprendizaje Automático", "ES_UN", "Concepto", "nombre", "Inteligencia Artificial")
        print(f"Relación creada: {relacion}")

        #  Ejemplo de consulta
        query = "MATCH (n:Concepto) RETURN n.nombre AS nombre, n.descripcion AS descripcion"
        resultados = graph_db.execute_query(query)
        print(f"Resultados de la consulta: {resultados}")

    except Exception as e:
        print(f"Ocurrió un error durante la ejecución: {e}")
    finally:
        graph_db.close()