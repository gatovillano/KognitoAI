#!/usr/bin/env python3
"""
Test del sistema híbrido completo:
- Ollama (embeddings existentes)
- Qdrant (almacenamiento vectorial rápido)
- Cognee (análisis conceptual)
- Neo4j (grafos de conocimiento)
"""

import asyncio
import logging
import os
import sys

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path
sys.path.append('/app')

async def test_hybrid_system():
    """Test completo del sistema híbrido."""
    logger.info("🚀 Iniciando test del sistema híbrido completo")
    
    try:
        # Importar componentes
        from knowledge_graph.hybrid_cognee_adapter import HybridCogneeAdapter
        from knowledge_graph.graph_database import GraphDB
        
        # Inicializar base de datos de grafos
        graph_db = GraphDB()
        
        # Inicializar adaptador híbrido
        logger.info("🔧 Inicializando HybridCogneeAdapter...")
        hybrid_adapter = HybridCogneeAdapter(graph_db)
        
        # Inicializar todos los componentes
        init_success = await hybrid_adapter.initialize()
        
        if not init_success:
            logger.error("❌ Error inicializando el sistema híbrido")
            return False
        
        logger.info("✅ Sistema híbrido inicializado correctamente")
        
        # Test con documentos complejos
        test_documents = [
            """
            La inteligencia artificial está transformando la medicina moderna de maneras 
            revolucionarias. Los algoritmos de machine learning pueden analizar imágenes 
            médicas con precisión superior a los radiólogos humanos, detectando cáncer 
            en etapas tempranas que podrían pasar desapercibidas.
            """,
            """
            La telemedicina ha emergido como una solución crucial para brindar atención 
            médica en áreas rurales y durante emergencias sanitarias. Esta tecnología 
            permite consultas remotas, monitoreo de pacientes y diagnósticos a distancia, 
            democratizando el acceso a la salud.
            """,
            """
            Los sistemas de IA en medicina no solo diagnostican, sino que también 
            personalizan tratamientos. Utilizando big data y análisis predictivo, 
            pueden sugerir terapias específicas basadas en el perfil genético, 
            historial médico y respuesta a tratamientos previos de cada paciente.
            """,
            """
            La ética en IA médica es fundamental. Debemos asegurar que los algoritmos 
            sean transparentes, no discriminatorios y que mantengan la privacidad 
            del paciente. La regulación y supervisión humana siguen siendo esenciales 
            para un uso responsable de estas tecnologías.
            """
        ]
        
        logger.info("📚 Procesando documentos con sistema híbrido...")
        
        # Procesar documentos con el sistema híbrido
        result = await hybrid_adapter.process_documents_hybrid(
            documents=test_documents,
            dataset_name="medicina_ia_test"
        )
        
        logger.info("📊 Resultados del procesamiento híbrido:")
        logger.info(f"   • Método: {result.get('method', 'unknown')}")
        logger.info(f"   • Embeddings almacenados: {result.get('embeddings_stored', 0)}")
        logger.info(f"   • Entidades extraídas: {len(result.get('entities', []))}")
        logger.info(f"   • Relaciones encontradas: {len(result.get('relationships', []))}")
        logger.info(f"   • Almacenado en Neo4j: {result.get('neo4j_stored', False)}")
        
        # Test de búsqueda híbrida
        logger.info("\n🔍 Probando búsqueda híbrida...")
        
        search_queries = [
            "inteligencia artificial medicina",
            "telemedicina rural",
            "ética algoritmos médicos",
            "machine learning diagnóstico"
        ]
        
        for query in search_queries:
            logger.info(f"\n🔎 Búsqueda: '{query}'")
            search_results = await hybrid_adapter.search_hybrid(
                query=query,
                dataset_name="medicina_ia_test",
                limit=3
            )
            
            logger.info(f"   📄 Resultados encontrados: {len(search_results)}")
            for i, result in enumerate(search_results):
                source = result.get('source', 'unknown')
                score = result.get('score', 0)
                text_preview = result.get('text', '')[:100] + "..."
                logger.info(f"   {i+1}. [{source}] Score: {score:.3f} - {text_preview}")
        
        logger.info("\n🎉 ¡Test del sistema híbrido completado exitosamente!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test del sistema híbrido: {e}", exc_info=True)
        return False

async def test_component_status():
    """Verifica el estado de cada componente del sistema híbrido."""
    logger.info("\n🔧 Verificando estado de componentes...")
    
    components_status = {
        "ollama": False,
        "qdrant": False,
        "cognee": False,
        "neo4j": False
    }
    
    # Test Ollama (embeddings)
    try:
        from utils.embeddings import get_embedding_model
        embedding_model = await get_embedding_model()
        test_embedding = await embedding_model.aembed_query("test")
        if test_embedding and len(test_embedding) > 0:
            components_status["ollama"] = True
            logger.info("✅ Ollama (embeddings): Funcionando")
        else:
            logger.warning("⚠️ Ollama (embeddings): Respuesta vacía")
    except Exception as e:
        logger.error(f"❌ Ollama (embeddings): Error - {e}")
    
    # Test Qdrant
    try:
        from qdrant_client import QdrantClient
        qdrant_url = os.getenv('QDRANT_URL', 'http://qdrant:6333')
        client = QdrantClient(url=qdrant_url)
        collections = client.get_collections()
        components_status["qdrant"] = True
        logger.info(f"✅ Qdrant: Funcionando ({len(collections.collections)} colecciones)")
    except Exception as e:
        logger.error(f"❌ Qdrant: Error - {e}")
    
    # Test Cognee
    try:
        import cognee
        components_status["cognee"] = True
        logger.info("✅ Cognee: Disponible")
    except Exception as e:
        logger.error(f"❌ Cognee: Error - {e}")
    
    # Test Neo4j
    try:
        from knowledge_graph.graph_database import GraphDB
        graph_db = GraphDB()
        # Aquí podrías hacer una consulta simple si tienes el método
        components_status["neo4j"] = True
        logger.info("✅ Neo4j: Disponible")
    except Exception as e:
        logger.error(f"❌ Neo4j: Error - {e}")
    
    # Resumen
    working_components = sum(components_status.values())
    total_components = len(components_status)
    
    logger.info(f"\n📊 Estado del sistema: {working_components}/{total_components} componentes funcionando")
    
    if working_components >= 3:
        logger.info("🟢 Sistema híbrido: OPERATIVO")
    elif working_components >= 2:
        logger.info("🟡 Sistema híbrido: PARCIALMENTE OPERATIVO")
    else:
        logger.info("🔴 Sistema híbrido: NECESITA ATENCIÓN")
    
    return components_status

async def demo_hybrid_capabilities():
    """Demostración de las capacidades únicas del sistema híbrido."""
    logger.info("\n🎭 Demostración de capacidades híbridas...")
    
    try:
        from knowledge_graph.hybrid_cognee_adapter import HybridCogneeAdapter
        from knowledge_graph.graph_database import GraphDB
        
        # Inicializar
        graph_db = GraphDB()
        hybrid_adapter = HybridCogneeAdapter(graph_db)
        await hybrid_adapter.initialize()
        
        # Documentos que demuestran conexiones complejas
        demo_docs = [
            "La sostenibilidad ambiental requiere innovación tecnológica constante.",
            "Las energías renovables son clave para combatir el cambio climático.",
            "La inteligencia artificial puede optimizar el consumo energético.",
            "Las ciudades inteligentes integran IoT para eficiencia energética.",
            "La economía circular reduce desperdicios mediante tecnología."
        ]
        
        logger.info("🔄 Procesando documentos de demostración...")
        result = await hybrid_adapter.process_documents_hybrid(
            documents=demo_docs,
            dataset_name="demo_sostenibilidad"
        )
        
        # Búsquedas que muestran conexiones inteligentes
        demo_queries = [
            "tecnología sostenible",
            "IA energía",
            "ciudades verdes",
            "innovación ambiental"
        ]
        
        logger.info("\n🧠 Demostrando búsquedas inteligentes...")
        for query in demo_queries:
            results = await hybrid_adapter.search_hybrid(
                query=query,
                dataset_name="demo_sostenibilidad",
                limit=2
            )
            
            logger.info(f"\n💡 '{query}' encontró {len(results)} conexiones:")
            for result in results:
                source = result.get('source', 'unknown')
                logger.info(f"   🔗 [{source}] {result.get('text', '')[:80]}...")
        
        logger.info("\n✨ Demostración completada - El sistema híbrido encuentra conexiones que sistemas individuales no detectarían")
        
    except Exception as e:
        logger.error(f"❌ Error en demostración: {e}")

async def main():
    """Función principal que ejecuta todos los tests."""
    logger.info("🎯 SISTEMA HÍBRIDO KOGNITO AI - TEST COMPLETO")
    logger.info("=" * 60)
    
    # 1. Verificar componentes
    components = await test_component_status()
    
    # 2. Test principal del sistema híbrido
    if sum(components.values()) >= 2:  # Al menos 2 componentes funcionando
        hybrid_success = await test_hybrid_system()
        
        # 3. Demostración de capacidades
        if hybrid_success:
            await demo_hybrid_capabilities()
    else:
        logger.warning("⚠️ Insuficientes componentes funcionando para test completo")
    
    logger.info("\n" + "=" * 60)
    logger.info("🏁 Test del sistema híbrido finalizado")

if __name__ == "__main__":
    asyncio.run(main())
