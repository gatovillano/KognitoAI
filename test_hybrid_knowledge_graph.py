#!/usr/bin/env python3
"""
Test completo del sistema híbrido Cognee + Neo4j.
"""

import asyncio
import sys
import os
import logging

# Añadir el directorio raíz al path
sys.path.append('/app')

from core.tools.knowledge_graph_tool import KnowledgeGraphTool
from knowledge_graph.cognee_integration import CogneeIntegration
from knowledge_graph.graph_database import GraphDB
from core.config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_hybrid_system():
    """Test completo del sistema híbrido."""
    logger.info("🚀 Probando sistema híbrido Cognee + Neo4j...")
    
    try:
        # 1. Crear herramienta de grafos de conocimiento
        kg_tool = KnowledgeGraphTool()
        
        # 2. Documentos de prueba más complejos
        test_documents = [
            {
                "id": "doc_ai_1",
                "content": """
                La inteligencia artificial (IA) es una tecnología revolucionaria que está transformando 
                múltiples industrias. El machine learning, una rama de la IA, permite a las máquinas 
                aprender de los datos sin ser programadas explícitamente. Los algoritmos de deep learning 
                utilizan redes neuronales artificiales para procesar información compleja.
                """,
                "metadata": {"source": "test", "type": "article", "topic": "AI"}
            },
            {
                "id": "doc_ai_2",
                "content": """
                El procesamiento de lenguaje natural (NLP) es una subdisciplina de la inteligencia artificial 
                que se enfoca en la interacción entre computadoras y lenguaje humano. Los modelos de 
                transformers, como GPT y BERT, han revolucionado el campo del NLP. Estos modelos utilizan 
                mecanismos de atención para entender el contexto en el texto.
                """,
                "metadata": {"source": "test", "type": "article", "topic": "NLP"}
            },
            {
                "id": "doc_ai_3",
                "content": """
                La visión por computadora es otra rama importante de la IA que permite a las máquinas 
                interpretar y entender el contenido visual. Las redes neuronales convolucionales (CNN) 
                son fundamentales para el reconocimiento de imágenes. Aplicaciones incluyen reconocimiento 
                facial, diagnóstico médico y vehículos autónomos.
                """,
                "metadata": {"source": "test", "type": "article", "topic": "Computer Vision"}
            }
        ]
        
        # 3. Simular IDs de documentos (normalmente vendrían de la base de datos)
        document_ids = ["doc_ai_1", "doc_ai_2", "doc_ai_3"]
        
        # 4. Crear grafo de conocimiento
        logger.info("📊 Creando grafo de conocimiento...")
        result = await kg_tool.create_knowledge_graph_from_documents(
            document_ids=document_ids,
            workspace_id="test_workspace",
            account_id="test_user",
            graph_name="ai_knowledge_graph"
        )
        
        logger.info("✅ Grafo de conocimiento creado!")
        logger.info(f"📊 Resultado: {result}")
        
        # 5. Buscar en el grafo
        logger.info("🔍 Buscando en el grafo...")
        search_result = await kg_tool.search_knowledge_graph(
            query="inteligencia artificial machine learning",
            workspace_id="test_workspace", 
            account_id="test_user",
            graph_name="ai_knowledge_graph",
            search_type="hybrid"
        )
        
        logger.info("✅ Búsqueda completada!")
        logger.info(f"🔍 Resultados de búsqueda: {search_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test híbrido: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cognee_integration_detailed():
    """Test detallado de la integración con Cognee."""
    logger.info("🧠 Test detallado de Cognee...")
    
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
        
        # Documentos de prueba con más contenido
        test_documents = [
            {
                "id": "detailed_doc_1",
                "content": """
                El aprendizaje automático es una disciplina científica del ámbito de la inteligencia artificial 
                que crea sistemas que aprenden automáticamente. Aprender en este contexto quiere decir 
                identificar patrones complejos en millones de datos. La máquina que realmente aprende es un 
                algoritmo que revisa los datos y es capaz de predecir comportamientos futuros.
                """,
                "metadata": {"source": "detailed_test", "type": "educational"}
            },
            {
                "id": "detailed_doc_2",
                "content": """
                Las redes neuronales artificiales son modelos computacionales inspirados en el funcionamiento 
                del cerebro humano. Están compuestas por neuronas artificiales conectadas entre sí, que 
                procesan información mediante la propagación de señales. El deep learning utiliza redes 
                neuronales profundas con múltiples capas ocultas.
                """,
                "metadata": {"source": "detailed_test", "type": "educational"}
            }
        ]
        
        # Procesar documentos
        result = await cognee_integration.process_documents(test_documents, "detailed_test_dataset")
        
        logger.info("✅ Procesamiento detallado completado!")
        logger.info(f"📊 Método usado: {result.get('method')}")
        logger.info(f"📊 Entidades encontradas: {len(result.get('entities', []))}")
        logger.info(f"📊 Relaciones encontradas: {len(result.get('relationships', []))}")
        
        # Mostrar algunas entidades
        entities = result.get('entities', [])
        if entities:
            logger.info("🏷️ Primeras entidades:")
            for i, entity in enumerate(entities[:3]):
                logger.info(f"  {i+1}. {entity.get('type', 'Unknown')}: {entity.get('properties', {}).get('name', 'Sin nombre')}")
        
        # Test de búsqueda detallada
        search_result = await cognee_integration.search_knowledge_graph(
            "redes neuronales aprendizaje automático", 
            "detailed_test_dataset"
        )
        logger.info(f"🔍 Búsqueda detallada: {search_result.get('status')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test detallado: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Función principal."""
    logger.info("🚀 Iniciando tests del sistema híbrido de grafos de conocimiento...")
    
    tests = [
        ("Integración Cognee Detallada", test_cognee_integration_detailed),
        ("Sistema Híbrido Completo", test_hybrid_system)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 Ejecutando: {test_name}")
        logger.info(f"{'='*60}")
        
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
    logger.info(f"\n{'='*60}")
    logger.info("📊 RESUMEN DE TESTS HÍBRIDOS")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ EXITOSO" if success else "❌ FALLÓ"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n🎯 Resultado Final: {passed}/{total} tests exitosos")
    
    if passed == total:
        logger.info("🎉 ¡Sistema híbrido funcionando correctamente!")
    else:
        logger.warning("⚠️ Algunos tests fallaron. El sistema funciona en modo fallback.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
