
import asyncio
import logging
import os
import sys
from typing import List, Dict, Any

# Configurar path para importar módulos del proyecto
sys.path.append(os.getcwd())

from core.config import settings
from knowledge_graph.hybrid_graph_processor import HybridGraphProcessor
from knowledge_graph.graph_database import GraphDB
from utils.embeddings import initialize_embeddings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_system():
    logger.info("🚀 Iniciando verificación del sistema de grafos...")

    # 1. Verificar Embeddings con Ollama
    logger.info("\n🧪 1. Verificando Embeddings con Ollama...")
    try:
        await initialize_embeddings()
        processor = HybridGraphProcessor()
        # await processor.initialize() # Comentado para evitar descarga de spaCy
        
        # Asignar modelo manualmente para probar _get_embeddings
        from utils.embeddings import get_embedding_model
        processor.sentence_transformer = get_embedding_model()
        
        test_text = ["Hola mundo", "Inteligencia Artificial"]
        embeddings = await processor._get_embeddings(test_text)
        
        if embeddings.shape == (2, 4096) or embeddings.shape[0] == 2: # Dimensiones dependen del modelo
            logger.info(f"✅ Embeddings generados correctamente. Shape: {embeddings.shape}")
        else:
            logger.error(f"❌ Embeddings generados con dimensiones inesperadas: {embeddings.shape}")
            
    except Exception as e:
        logger.error(f"❌ Error verificando embeddings: {e}")
        sys.exit(1)

    # 2. Simular Procesamiento de Documentos (Bypassing spaCy extraction due to download issues)
    logger.info("\n🧪 2. Simulando Procesamiento de Documentos (Manual)...")
    
    test_account_id = "test-account-uuid-123"
    test_workspace_id = "test-workspace-uuid-456"
    dataset_name = "test_verification_dataset"
    
    try:
        # Inicializar solo lo necesario (embeddings ya probados arriba)
        # No llamamos a processor.initialize() completo para evitar descarga de spaCy
        from utils.embeddings import get_embedding_model
        processor.sentence_transformer = await initialize_embeddings()
        if not processor.sentence_transformer:
            processor.sentence_transformer = get_embedding_model()

        # Crear entidades y relaciones simuladas manualmente
        entities = [
            {"name": "Elon Musk", "type": "PERSON", "description": "CEO de Tesla", "source": "test_doc_1.txt"},
            {"name": "Tesla", "type": "ORG", "description": "Fabricante de autos", "source": "test_doc_1.txt"}
        ]
        
        relationships = [
            {"source": "Elon Musk", "target": "Tesla", "type": "CEO_OF", "description": "Elon Musk es CEO de Tesla", "source_doc": "test_doc_1.txt"}
        ]
        
        # Agregar IDs usando el helper (simulando lo que hace el processor)
        processor.account_id = test_account_id
        processor.workspace_id = test_workspace_id
        
        entities = [processor._add_tenant_ids(e) for e in entities]
        relationships = [processor._add_tenant_ids(r) for r in relationships]
        
        # Generar embeddings para las entidades (probando la integración)
        entity_texts = [f"{e['name']} {e['description']}" for e in entities]
        embeddings = await processor._get_embeddings(entity_texts)
        logger.info(f"✅ Embeddings generados para entidades simuladas. Shape: {embeddings.shape}")
        
        # Guardar en Neo4j usando el adapter directamente
        from knowledge_graph.neo4j_adapter import Neo4jAdapter
        adapter = Neo4jAdapter(db)
        
        # Estructurar datos como espera el adapter
        graph_data = {
            "entities": entities,
            "relationships": relationships
        }
        
        await adapter.save_graph_data(graph_data)
        logger.info(f"✅ Datos simulados guardados en Neo4j.")

    except Exception as e:
        logger.error(f"❌ Error en procesamiento simulado: {e}", exc_info=True)
        sys.exit(1)

    # 3. Verificar en Neo4j
    logger.info("\n🧪 3. Verificando datos en Neo4j...")
    
    db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    db.connect()
    
    try:
        # Verificar nodos con los IDs correctos
        query = """
        MATCH (n) 
        WHERE n.account_id = $account_id AND n.workspace_id = $workspace_id
        RETURN count(n) as count, collect(n.name) as names
        """
        result = await db.execute_query(query, {
            "account_id": test_account_id,
            "workspace_id": test_workspace_id
        })
        
        count = result[0]['count']
        names = result[0]['names']
        
        if count > 0:
            logger.info(f"✅ ÉXITO: Encontrados {count} nodos con account_id y workspace_id correctos.")
            logger.info(f"   Nodos encontrados: {names[:5]}...")
        else:
            logger.error("❌ FALLO: No se encontraron nodos con los IDs esperados en Neo4j.")
            
            # Debug: ver qué hay
            debug_query = "MATCH (n) RETURN n LIMIT 5"
            debug_res = await db.execute_query(debug_query)
            logger.info(f"   Muestra de nodos en DB: {debug_res}")

    except Exception as e:
        logger.error(f"❌ Error verificando Neo4j: {e}")
    finally:
        # Limpiar datos de prueba
        logger.info("\n🧹 Limpiando datos de prueba...")
        cleanup_query = "MATCH (n) WHERE n.workspace_id = $workspace_id DETACH DELETE n"
        await db.execute_query(cleanup_query, {"workspace_id": test_workspace_id})
        db.close()
        logger.info("✅ Datos de prueba eliminados.")

if __name__ == "__main__":
    asyncio.run(verify_system())
