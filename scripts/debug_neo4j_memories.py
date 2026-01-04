
import asyncio
import sys
import os
import logging
from datetime import datetime

# Add project root to Python path
sys.path.append(os.getcwd())

from knowledge_graph.graph_database import GraphDB
from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_neo4j():
    logger.info("🚀 Iniciando diagnóstico de Neo4j...")
    
    db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        # 1. Contar nodos por dataset_name
        logger.info("\n📊 Conteo de nodos por dataset_name:")
        query_datasets = """
        MATCH (n)
        RETURN n.dataset_name as dataset, count(n) as count
        ORDER BY count DESC
        """
        results = await db.execute_query(query_datasets)
        for record in results:
            logger.info(f"   - {record['dataset']}: {record['count']} nodos")

        # 2. Verificar nodos específicos de 'Agent Memories'
        logger.info("\n🔍 Muestra de nodos en 'Agent Memories':")
        query_memories = """
        MATCH (n)
        WHERE n.dataset_name = 'Agent Memories'
        RETURN n.id as id, labels(n) as labels, n.name as name, n.account_id as account_id, n.workspace_id as workspace_id
        LIMIT 5
        """
        memory_results = await db.execute_query(query_memories)
        if not memory_results:
             logger.info("   ⚠️ No se encontraron nodos con dataset_name = 'Agent Memories'")
        
        for record in memory_results:
            logger.info(f"   - ID: {record['id']}")
            logger.info(f"     Labels: {record['labels']}")
            logger.info(f"     Name: {record['name']}")
            logger.info(f"     Account ID: {record['account_id']}")
            logger.info(f"     Workspace ID: {record['workspace_id']}")
            logger.info("     ---")

        # 3. Inspeccionar nodos creados HOY
        logger.info("\n🕵️ Inspección de nodos creados HOY:")
        today = datetime.now().strftime("%Y-%m-%d")
        query_inspect = f"""
        MATCH (n)
        WHERE n.created_at STARTS WITH '{today}'
        RETURN labels(n) as labels, properties(n) as props
        LIMIT 10
        """
        inspect_results = await db.execute_query(query_inspect)
        if not inspect_results:
             logger.info("   ⚠️ No se encontraron nodos creados hoy.")
        
        for record in inspect_results:
             logger.info(f"   - Labels: {record['labels']}")
             logger.info(f"     Props: {record['props']}")
             logger.info("     ---")

    except Exception as e:
        logger.error(f"❌ Error conectando a Neo4j: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_neo4j())
