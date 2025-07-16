#!/usr/bin/env python3
# scripts/test_complete_cognee_pipeline.py

"""
Script para probar el pipeline completo de Cognee con integración a Neo4j.
"""

import asyncio
import logging
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.graph_database import GraphDB
from knowledge_graph.cognee_integration import CogneeIntegration
from core.config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_neo4j_connection():
    """Prueba la conexión básica con Neo4j."""
    logger.info("🔌 Probando conexión con Neo4j...")
    
    try:
        # Inicializar GraphDB
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        
        # Conectar
        graph_db.connect()
        logger.info("✅ Conexión establecida")
        
        # Probar query básico
        result = await graph_db.execute_query("RETURN 'Hello Neo4j' as message")
        logger.info(f"✅ Query de prueba: {result}")
        
        # Obtener estadísticas
        stats = await graph_db.execute_query("""
            MATCH (n) 
            OPTIONAL MATCH ()-[r]-() 
            RETURN count(DISTINCT n) as nodes, count(DISTINCT r) as relationships
        """)
        
        if stats:
            logger.info(f"📊 Estadísticas actuales: {stats[0]['nodes']} nodos, {stats[0]['relationships']} relaciones")
        
        return graph_db
        
    except Exception as e:
        logger.error(f"❌ Error conectando con Neo4j: {e}")
        raise

async def test_cognee_integration(graph_db):
    """Prueba la integración con Cognee."""
    logger.info("🧠 Probando integración con Cognee...")
    
    try:
        # Inicializar CogneeIntegration
        cognee_integration = CogneeIntegration(graph_db)
        logger.info("✅ CogneeIntegration inicializado")
        
        # Crear documentos de prueba
        test_documents = [
            {
                "file_name": "test_doc_1.txt",
                "title": "Documento de Prueba 1",
                "topic": "Tecnología",
                "document_id": "test_1",
                "workspace_id": "test_workspace",
                "team_id": None,
                "team_shared": False
            },
            {
                "file_name": "test_doc_2.txt", 
                "title": "Documento de Prueba 2",
                "topic": "Ciencia",
                "document_id": "test_2",
                "workspace_id": "test_workspace",
                "team_id": None,
                "team_shared": False
            }
        ]
        
        logger.info(f"📄 Procesando {len(test_documents)} documentos de prueba...")
        
        # Procesar con Cognee
        result = await cognee_integration.process_documents_with_cognee(
            test_documents, 
            "test_workspace"
        )
        
        logger.info(f"✅ Procesamiento completado:")
        logger.info(f"   - Entidades: {len(result.get('entities', []))}")
        logger.info(f"   - Relaciones: {len(result.get('relationships', []))}")
        logger.info(f"   - Método: {result.get('metadata', {}).get('processing_method', 'unknown')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en integración Cognee: {e}")
        raise

async def verify_neo4j_data(graph_db):
    """Verifica que los datos se guardaron correctamente en Neo4j."""
    logger.info("🔍 Verificando datos en Neo4j...")
    
    try:
        # Contar nodos
        nodes_result = await graph_db.execute_query("MATCH (n) RETURN count(n) as total")
        total_nodes = nodes_result[0]["total"] if nodes_result else 0
        
        # Contar relaciones
        rels_result = await graph_db.execute_query("MATCH ()-[r]-() RETURN count(r) as total")
        total_rels = rels_result[0]["total"] if rels_result else 0
        
        # Obtener tipos de entidades
        types_result = await graph_db.execute_query("""
            MATCH (n) 
            RETURN DISTINCT n.type as type, count(n) as count 
            ORDER BY count DESC
        """)
        
        logger.info(f"📊 Datos en Neo4j:")
        logger.info(f"   - Total nodos: {total_nodes}")
        logger.info(f"   - Total relaciones: {total_rels}")
        logger.info(f"   - Tipos de entidades:")
        
        for type_info in types_result:
            logger.info(f"     * {type_info['type']}: {type_info['count']}")
        
        # Mostrar algunos nodos de ejemplo
        sample_nodes = await graph_db.execute_query("""
            MATCH (n) 
            RETURN n.name as name, n.type as type, n.confidence as confidence 
            LIMIT 5
        """)
        
        logger.info(f"🔍 Nodos de ejemplo:")
        for node in sample_nodes:
            logger.info(f"   - {node['name']} ({node['type']}) - Confianza: {node['confidence']}")
        
        return {
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "entity_types": types_result,
            "sample_nodes": sample_nodes
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando datos: {e}")
        raise

async def main():
    """Función principal que ejecuta todas las pruebas."""
    logger.info("🚀 Iniciando prueba completa del pipeline Cognee + Neo4j")
    
    try:
        # 1. Probar conexión Neo4j
        graph_db = await test_neo4j_connection()
        
        # 2. Probar integración Cognee
        result = await test_cognee_integration(graph_db)
        
        # 3. Verificar datos en Neo4j
        verification = await verify_neo4j_data(graph_db)
        
        # 4. Resumen final
        logger.info("🎉 ¡PRUEBA COMPLETADA EXITOSAMENTE!")
        logger.info("=" * 50)
        logger.info(f"✅ Entidades procesadas: {len(result.get('entities', []))}")
        logger.info(f"✅ Relaciones procesadas: {len(result.get('relationships', []))}")
        logger.info(f"✅ Nodos en Neo4j: {verification['total_nodes']}")
        logger.info(f"✅ Relaciones en Neo4j: {verification['total_relationships']}")
        logger.info(f"✅ Tipos de entidades: {len(verification['entity_types'])}")
        logger.info("=" * 50)
        
        # Cerrar conexión
        graph_db.close()
        
    except Exception as e:
        logger.error(f"❌ Error en la prueba: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
