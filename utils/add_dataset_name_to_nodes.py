import asyncio
import logging
import sys
import os

# Añadir el directorio raíz del proyecto al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.graph_database import GraphDB
from core.config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def migrate_data():
    """
    Añade la propiedad 'dataset_name' a todos los nodos CONCEPTUAL_QUOTE.
    """
    db = None
    try:
        # Validar que la configuración de Neo4j esté presente
        if not all([settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password]):
            logger.error("La configuración de Neo4j (URI, user, password) no está completa en tu archivo .env.")
            return

        # Conectar a la base de datos
        db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        db.connect() # connect() es síncrona en la implementación actual

        # La consulta Cypher para la migración
        # Usamos MERGE para ser idempotentes: solo establece la propiedad si no existe.
        query = "MATCH (n:CONCEPTUAL_QUOTE) SET n.dataset_name = 'default'"

        logger.info("Iniciando migración: Añadiendo 'dataset_name' a los nodos CONCEPTUAL_QUOTE...")
        
        # Ejecutar la consulta
        await db.execute_query(query)

        # Contar nodos para verificar
        verification_query = "MATCH (n:CONCEPTUAL_QUOTE) WHERE n.dataset_name = 'default' RETURN count(n) AS count"
        result = await db.execute_query(verification_query)
        
        if result and result[0]['count'] > 0:
            logger.info(f"Verificación exitosa: {result[0]['count']} nodos actualizados.")
            logger.info("¡Migración completada exitosamente!")
            logger.info("Todos los nodos CONCEPTUAL_QUOTE ahora tienen la propiedad 'dataset_name' con el valor 'default'.")
        else:
            logger.warning("No se encontraron nodos para actualizar o la verificación falló.")

    except Exception as e:
        logger.error(f"Ocurrió un error durante la migración: {e}", exc_info=True)
    finally:
        if db:
            db.close() # close() es síncrona

if __name__ == "__main__":
    # Añadimos un input de confirmación para seguridad
    print("Este script añadirá la propiedad 'dataset_name: \"default\"' a todos los nodos :CONCEPTUAL_QUOTE en la base de datos.")
    confirm = input("¿Estás seguro de que quieres continuar? (s/n): ")
    if confirm.lower() == 's':
        asyncio.run(migrate_data())
    else:
        print("Migración cancelada.")
