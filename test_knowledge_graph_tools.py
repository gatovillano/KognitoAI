#!/usr/bin/env python3
# test_knowledge_graph_tools.py

"""
Script de prueba para las nuevas herramientas de grafos de conocimiento.
Prueba la conectividad con Neo4j y las funcionalidades básicas.
"""

import asyncio
import logging
import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from knowledge_graph.graph_database import GraphDB
from knowledge_graph.knowledge_models import Node, Relationship
from knowledge_graph.cognee_integration import CogneeIntegration
from tools.text_to_knowledge_graph_tool import TextToKnowledgeGraphTool
from tools.mindmap_to_graph_tool import MindmapToGraphTool
from core.config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_neo4j_connection():
    """Prueba la conexión básica con Neo4j."""
    logger.info("🔍 Probando conexión con Neo4j...")
    
    try:
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        
        graph_db.connect()
        logger.info("✅ Conexión con Neo4j exitosa!")
        
        # Crear un nodo de prueba
        test_node = Node(
            label="TestNode",
            properties={
                "name": "Nodo de Prueba",
                "created_at": "2024-01-01T00:00:00Z",
                "test": True
            }
        )
        
        created_node = graph_db.create_node(test_node)
        logger.info(f"✅ Nodo de prueba creado: {created_node}")
        
        # Limpiar nodo de prueba
        graph_db.delete_node("TestNode", "name", "Nodo de Prueba")
        logger.info("🧹 Nodo de prueba eliminado")
        
        graph_db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error conectando con Neo4j: {e}")
        return False

async def test_cognee_integration():
    """Prueba la integración real con Cognee."""
    logger.info("🧠 Probando integración con Cognee...")

    try:
        # Crear instancia de GraphDB
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )

        # Crear integración con Cognee
        cognee_integration = CogneeIntegration(graph_db)

        logger.info(f"📊 Cognee disponible: {cognee_integration.cognee_available}")

        # Documentos de prueba
        test_documents = [
            {
                "id": "doc_1",
                "content": "La inteligencia artificial es una tecnología revolucionaria que está transformando múltiples industrias.",
                "metadata": {"source": "test", "type": "article"}
            },
            {
                "id": "doc_2",
                "content": "El machine learning es una rama de la inteligencia artificial que permite a las máquinas aprender de los datos.",
                "metadata": {"source": "test", "type": "article"}
            }
        ]

        # Procesar documentos
        result = await cognee_integration.process_documents(test_documents, "test_dataset")

        logger.info("✅ Cognee integration test exitoso!")
        logger.info(f"📊 Método usado: {result.get('method')}")
        logger.info(f"📊 Entidades: {len(result.get('entities', []))}")
        logger.info(f"📊 Relaciones: {len(result.get('relationships', []))}")

        # Test de búsqueda
        search_result = await cognee_integration.search_knowledge_graph("inteligencia artificial", "test_dataset")
        logger.info(f"🔍 Búsqueda completada: {search_result.get('status')}")

        return True

    except Exception as e:
        logger.error(f"❌ Error en integración con Cognee: {e}")
        return False

async def test_text_to_knowledge_graph():
    """Prueba la herramienta de texto a grafo de conocimiento."""
    logger.info("🧠 Probando TextToKnowledgeGraphTool...")
    
    try:
        tool = TextToKnowledgeGraphTool(account_id="test_user")
        
        test_text = """
        La inteligencia artificial es una rama de la informática que se centra en crear sistemas 
        capaces de realizar tareas que normalmente requieren inteligencia humana. Incluye subcampos 
        como el aprendizaje automático, el procesamiento de lenguaje natural y la visión por computadora.
        El aprendizaje automático utiliza algoritmos para permitir que las máquinas aprendan de los datos.
        """
        
        result = await tool._arun(
            text=test_text,
            workspace_id="test_workspace",
            graph_name="test_ai_graph",
            create_graph=True,
            use_cognee=False  # Usar extracción directa para la prueba
        )
        
        logger.info("✅ TextToKnowledgeGraphTool ejecutada exitosamente!")
        logger.info(f"📊 Resultado: {result[:200]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en TextToKnowledgeGraphTool: {e}")
        return False

async def test_mindmap_to_graph():
    """Prueba la herramienta de mapa mental a grafo."""
    logger.info("🗺️ Probando MindmapToGraphTool...")
    
    try:
        tool = MindmapToGraphTool(account_id="test_user")
        
        test_document = """
        El cambio climático es uno de los desafíos más importantes de nuestro tiempo. 
        Las principales causas incluyen las emisiones de gases de efecto invernadero, 
        la deforestación y la industrialización. Los efectos incluyen el aumento de 
        temperaturas, el derretimiento de glaciares y cambios en los patrones climáticos.
        Las soluciones incluyen energías renovables, eficiencia energética y políticas ambientales.
        """
        
        result = await tool._arun(
            document_content=test_document,
            workspace_id="test_workspace",
            topic_hint="Cambio Climático",
            concept_query="causas, efectos y soluciones del cambio climático",
            save_to_graph=True
        )
        
        logger.info("✅ MindmapToGraphTool ejecutada exitosamente!")
        logger.info(f"📊 Resultado: {result[:200]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en MindmapToGraphTool: {e}")
        return False

async def test_graph_queries():
    """Prueba consultas básicas al grafo."""
    logger.info("🔍 Probando consultas al grafo...")
    
    try:
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        
        graph_db.connect()
        
        # Consultar todos los nodos creados por las pruebas
        query = """
        MATCH (n)
        WHERE n.account_id = $account_id
        RETURN n.name as name, labels(n) as labels, n.created_at as created_at
        LIMIT 10
        """
        
        results = graph_db.execute_query(query, {"account_id": "test_user"})
        
        logger.info(f"✅ Consulta ejecutada. Encontrados {len(results)} nodos:")
        for result in results:
            logger.info(f"  - {result.get('name', 'Sin nombre')} ({result.get('labels', [])})")
        
        graph_db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en consultas al grafo: {e}")
        return False

async def cleanup_test_data():
    """Limpia los datos de prueba."""
    logger.info("🧹 Limpiando datos de prueba...")
    
    try:
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        
        graph_db.connect()
        
        # Eliminar todos los nodos de prueba
        cleanup_query = """
        MATCH (n)
        WHERE n.account_id = $account_id
        DETACH DELETE n
        """
        
        graph_db.execute_query(cleanup_query, {"account_id": "test_user"})
        logger.info("✅ Datos de prueba eliminados")
        
        graph_db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error limpiando datos: {e}")
        return False

async def main():
    """Función principal que ejecuta todas las pruebas."""
    logger.info("🚀 Iniciando pruebas de herramientas de grafos de conocimiento...")
    
    tests = [
        ("Conexión Neo4j", test_neo4j_connection),
        ("Integración Cognee", test_cognee_integration),
        ("Texto a Grafo", test_text_to_knowledge_graph),
        ("Mapa Mental a Grafo", test_mindmap_to_graph),
        ("Consultas al Grafo", test_graph_queries),
        ("Limpieza", cleanup_test_data)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Ejecutando: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = await test_func()
            results.append((test_name, success))
            
            if success:
                logger.info(f"✅ {test_name}: EXITOSO")
            else:
                logger.error(f"❌ {test_name}: FALLÓ")
                
        except Exception as e:
            logger.error(f"💥 {test_name}: ERROR CRÍTICO - {e}")
            results.append((test_name, False))
    
    # Resumen final
    logger.info(f"\n{'='*50}")
    logger.info("📊 RESUMEN DE PRUEBAS")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ EXITOSO" if success else "❌ FALLÓ"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n🎯 Resultado Final: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        logger.info("🎉 ¡Todas las pruebas pasaron! Las herramientas están listas para usar.")
    else:
        logger.warning("⚠️ Algunas pruebas fallaron. Revisa la configuración.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
