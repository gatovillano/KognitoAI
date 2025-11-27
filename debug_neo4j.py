import sys
import os
import asyncio
from pprint import pprint

# Add project root to sys.path
sys.path.append(os.getcwd())

# Mock settings object to avoid importing core.config which needs dotenv
class Settings:
    def __init__(self):
        self.neo4j_uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
        self.neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        self.neo4j_password = os.environ.get("NEO4J_PASSWORD", "Kn0wl3dg3Gr4ph2024!")

settings = Settings()

# We need to import GraphDB, but it might import other things.
# Let's try to import it. If it fails due to imports in graph_database.py, we might need to mock those too or copy the class.
# graph_database.py imports logging, neo4j, typing. Should be fine.
try:
    from knowledge_graph.graph_database import GraphDB
except ImportError:
    # Fallback if we can't import it easily (e.g. path issues)
    # We'll just define a minimal version here
    from neo4j import GraphDatabase as Neo4jDriver
    
    class GraphDB:
        def __init__(self, uri, user, password):
            self.uri = uri
            self.user = user
            self.password = password
            self._driver = None
            
        def connect(self):
            self._driver = Neo4jDriver.driver(self.uri, auth=(self.user, self.password))
            
        def close(self):
            if self._driver:
                self._driver.close()
                
        async def execute_query(self, query, parameters=None):
            import concurrent.futures
            def _execute_sync():
                with self._driver.session() as session:
                    result = session.run(query, parameters)
                    return [record.data() for record in result]
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return await loop.run_in_executor(executor, _execute_sync)

async def main():
    print("Connecting to Neo4j...")
    print(f"URI: {settings.neo4j_uri}")
    
    db = GraphDB(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password
    )
    try:
        db.connect()
        print("Connected successfully.")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("\n--- Checking Nodes ---")
    # Get 5 random nodes
    try:
        nodes = await db.execute_query("MATCH (n) RETURN n LIMIT 5")
        print(f"Found {len(nodes)} nodes.")
        for i, record in enumerate(nodes):
            print(f"Node {i+1}:")
            pprint(record['n'])
    except Exception as e:
        print(f"Error querying nodes: {e}")

    print("\n--- Checking Node Keys ---")
    # Get keys of nodes
    try:
        keys = await db.execute_query("MATCH (n) RETURN distinct keys(n) as keys LIMIT 10")
        for record in keys:
            print(f"Keys: {record['keys']}")
    except Exception as e:
        print(f"Error querying keys: {e}")

    print("\n--- Checking for account_id ---")
    try:
        account_check = await db.execute_query("MATCH (n) WHERE n.account_id IS NOT NULL RETURN count(n) as count")
        print(f"Nodes with account_id: {account_check[0]['count']}")
        
        # Check if any node has account_id property but maybe it's empty or different type
        account_sample = await db.execute_query("MATCH (n) WHERE n.account_id IS NOT NULL RETURN n.account_id as aid LIMIT 5")
        if account_sample:
            print(f"Sample account_ids: {[r['aid'] for r in account_sample]}")
    except Exception as e:
        print(f"Error checking account_id: {e}")

    print("\n--- Checking for workspace_id ---")
    try:
        workspace_check = await db.execute_query("MATCH (n) WHERE n.workspace_id IS NOT NULL RETURN count(n) as count")
        print(f"Nodes with workspace_id: {workspace_check[0]['count']}")
        
        workspace_sample = await db.execute_query("MATCH (n) WHERE n.workspace_id IS NOT NULL RETURN n.workspace_id as wid LIMIT 5")
        if workspace_sample:
            print(f"Sample workspace_ids: {[r['wid'] for r in workspace_sample]}")
    except Exception as e:
        print(f"Error checking workspace_id: {e}")

    db.close()

if __name__ == "__main__":
    asyncio.run(main())
