
import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from knowledge_graph.graph_database import GraphDB
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reproduce_issue():
    # Initialize GraphDB
    if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
        logger.error("❌ Configuración de Neo4j incompleta.")
        return

    graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    graph_db.connect()

    try:
        # Create a test node
        await graph_db.execute_query("CREATE (n:TestNode {name: 'Test', id: 'test_1'})")
        
        # Query the node
        query = "MATCH (n:TestNode {id: 'test_1'}) RETURN n"
        results = await graph_db.execute_query(query)
        
        logger.info(f"Results type: {type(results)}")
        if results:
            record = results[0]
            logger.info(f"Record type: {type(record)}")
            logger.info(f"Record content: {record}")
            
            node = record.get('n')
            logger.info(f"Node type: {type(node)}")
            logger.info(f"Node content: {node}")
            
            # Check for labels
            if hasattr(node, 'labels'):
                logger.info(f"Labels found: {node.labels}")
            elif isinstance(node, dict) and 'labels' in node:
                logger.info(f"Labels found in dict: {node['labels']}")
            else:
                logger.error("❌ Labels NOT found (Issue reproduced)")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Cleanup
        await graph_db.execute_query("MATCH (n:TestNode {id: 'test_1'}) DELETE n")
        graph_db.close()

if __name__ == "__main__":
    asyncio.run(reproduce_issue())
