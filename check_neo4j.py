import asyncio
from knowledge_graph.graph_database import GraphDB
from core.config import settings

async def check():
    db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    db.connect()
    res = await db.execute_query('MATCH (n:DOCUMENT) RETURN n.type as type, count(n) as count')
    print(f"Nodes with label DOCUMENT: {res}")
    
    res2 = await db.execute_query('MATCH (n) WHERE n.type = "DOCUMENT" RETURN count(n) as count')
    print(f"Nodes with property type='DOCUMENT': {res2}")
    
    res3 = await db.execute_query('MATCH (n) RETURN DISTINCT n.type as type, count(n) as count')
    print(f"All node types: {res3}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(check())
