#!/usr/bin/env python3
"""
Script de prueba para Cognee en KognitoAI
Demuestra cómo usar Cognee para procesar documentos y crear grafos de conocimiento.
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.graph_database import GraphDB
from knowledge_graph.cognee_integration import CogneeIntegration
from core.config import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cognee_basic():
    """Prueba básica de Cognee con documentos de ejemplo."""
    
    # Validar configuración
    if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
        print("❌ Error: Configuración de Neo4j incompleta")
        print("Asegúrate de configurar NEO4J_URI, NEO4J_USER y NEO4J_PASSWORD en tu .env")
        return
    
    if not settings.google_api_key:
        print("❌ Error: GOOGLE_API_KEY no configurada")
        print("Cognee necesita una API key de Google para funcionar")
        return
    
    print("🚀 Iniciando prueba de Cognee...")
    
    # Conectar a Neo4j
    graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    
    try:
        graph_db.connect()
        print("✅ Conectado a Neo4j")
        
        # Inicializar Cognee
        cognee_integration = CogneeIntegration(graph_db)
        print("✅ CogneeIntegration inicializada")
        
        # Documentos de ejemplo
        documents = [
            {
                "id": "doc1",
                "title": "Introducción a la Inteligencia Artificial",
                "content": """
                La inteligencia artificial (IA) es una rama de la informática que se ocupa de la
                creación de sistemas capaces de realizar tareas que normalmente requieren
                inteligencia humana. Esto incluye el aprendizaje automático, el procesamiento
                del lenguaje natural y la visión por computadora.
                """,
                "metadata": {"author": "Dr. Smith", "year": 2024, "account_id": "test_user"}
            },
            {
                "id": "doc2",
                "title": "Machine Learning y Deep Learning",
                "content": """
                El machine learning es un subconjunto de la inteligencia artificial que permite
                a las máquinas aprender sin ser programadas explícitamente. El deep learning,
                por su parte, utiliza redes neuronales artificiales con múltiples capas para
                modelar y entender datos complejos.
                """,
                "metadata": {"author": "Dr. Johnson", "year": 2024, "account_id": "test_user"}
            }
        ]
        
        print(f"📄 Procesando {len(documents)} documentos...")
        
        # Procesar documentos con Cognee
        result = await cognee_integration.process_documents(
            documents=documents,
            dataset_name="test_kognito"
        )
        
        print("✅ Documentos procesados exitosamente")
        print(f"📊 Resultado: {result}")
        
        # Buscar en el grafo de conocimiento
        print("\n🔍 Probando búsqueda en el grafo...")
        search_result = await cognee_integration.search_knowledge_graph(
            query="¿Qué es machine learning?",
            dataset_name="test_kognito"
        )
        
        print("✅ Búsqueda completada")
        print(f"🎯 Resultados de búsqueda: {search_result}")
        
    except Exception as e:
        logger.error(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        graph_db.close()
        print("🔌 Conexión a Neo4j cerrada")

async def test_cognee_with_real_documents():
    """Prueba Cognee con documentos reales del sistema."""
    
    print("🚀 Probando Cognee con documentos del sistema...")
    
    # Aquí podrías integrar con tu sistema de documentos existente
    # Por ejemplo, obtener documentos de la base de datos PostgreSQL
    
    # TODO: Implementar integración con documentos reales
    print("⚠️ Esta función requiere integración con tu sistema de documentos")

if __name__ == "__main__":
    print("🧠 Script de Prueba de Cognee para KognitoAI")
    print("=" * 50)
    
    # Ejecutar prueba básica
    asyncio.run(test_cognee_basic())
    
    print("\n" + "=" * 50)
    print("✅ Prueba completada")
    print("\n💡 Próximos pasos:")
    print("1. Revisa los logs para ver el procesamiento detallado")
    print("2. Accede a Neo4j Browser en http://localhost:7474 para ver el grafo")
    print("3. Integra Cognee en tus herramientas existentes")
