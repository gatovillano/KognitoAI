import asyncio
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.getcwd())

from knowledge_graph.graph_database import GraphDB
from core.config import settings

async def check_neo4j_status():
    print("--- Diagnóstico de Conexión Neo4j ---")
    
    uri = settings.neo4j_uri or os.getenv("NEO4J_URI")
    user = settings.neo4j_user or os.getenv("NEO4J_USER")
    password = settings.neo4j_password or os.getenv("NEO4J_PASSWORD")
    
    print(f"URI: {uri}")
    print(f"User: {user}")
    print(f"Password: {'******' if password else 'None'}")
    
    if not uri:
        print("❌ Error: NEO4J_URI no está configurada.")
        return

    try:
        graph_db = GraphDB(uri=uri, user=user, password=password)
        graph_db.connect()
        print("✅ Conexión establecida (Driver creado).")
        
        print("🔄 Intentando verificar conectividad real...")
        graph_db._driver.verify_connectivity()
        print("✅ Conectividad verificada.")
        
        print("🔄 Intentando obtener el esquema...")
        await graph_db.refresh_schema()
        
        if graph_db.schema:
            print("✅ Esquema obtenido exitosamente:")
            print("-" * 20)
            print(graph_db.schema[:500] + "..." if len(graph_db.schema) > 500 else graph_db.schema)
            print("-" * 20)
        else:
            print("⚠️ El esquema se obtuvo pero está VACÍO. Esto puede indicar una base de datos vacía o un problema de permisos.")
            
        graph_db.close()
        
    except Exception as e:
        print(f"❌ Error crítico durante el diagnóstico: {e}")

if __name__ == "__main__":
    asyncio.run(check_neo4j_status())
