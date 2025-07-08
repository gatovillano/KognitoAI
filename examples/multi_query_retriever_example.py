# examples/multi_query_retriever_example.py

"""
Ejemplo de uso del MultiQueryRetriever en Kognito AI.
Demuestra cómo usar la nueva funcionalidad de búsqueda con múltiples consultas reformuladas.
"""

import asyncio
import logging
from utils.multi_query_retriever import MultiQueryRetriever, multi_query_search

# Configurar logging para ver el proceso
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ejemplo_basico():
    """
    Ejemplo básico de uso del MultiQueryRetriever.
    """
    print("🚀 Ejemplo básico de MultiQueryRetriever")
    print("=" * 50)

    # Configuración del ejemplo
    account_id = "usuario_ejemplo"
    consulta_original = "técnicas de machine learning para análisis de texto"

    # Usar la función de conveniencia
    resultados = await multi_query_search(
        account_id=account_id,
        query=consulta_original,
        content_type="user_documents",  # Buscar solo en documentos
        k=5,  # Top 5 resultados
        num_queries=3,  # Generar 3 consultas alternativas
        fusion_method="rrf"  # Usar Reciprocal Rank Fusion
    )

    print(f"📝 Consulta original: {consulta_original}")
    print(f"📊 Resultados encontrados: {len(resultados)}")

    for i, resultado in enumerate(resultados, 1):
        print(f"\n{i}. {resultado.get('document', '')[:100]}...")
        print(f"   Topic: {resultado.get('topic', 'N/A')}")
        print(f"   Score: {resultado.get('similarity_score', 'N/A')}")

async def ejemplo_avanzado():
    """
    Ejemplo avanzado mostrando diferentes configuraciones.
    """
    print("\n🔬 Ejemplo avanzado de MultiQueryRetriever")
    print("=" * 50)
    
    # Crear instancia personalizada
    retriever = MultiQueryRetriever(
        num_queries=4,  # Más consultas para mayor cobertura
        fusion_method="rrf"  # Reciprocal Rank Fusion
    )
    
    account_id = "usuario_ejemplo"
    consulta = "estrategias de optimización de bases de datos"
    
    # Búsqueda con filtros específicos
    resultados = await retriever.search_with_multiple_queries(
        account_id=account_id,
        original_query=consulta,
        content_type="user_documents",
        topic="tecnologia",  # Filtrar por topic
        workspace_id="workspace_dev",  # Filtrar por workspace
        k=8  # Más resultados
    )
    
    print(f"📝 Consulta: {consulta}")
    print(f"🎯 Filtros: topic='tecnologia', workspace='workspace_dev'")
    print(f"📊 Resultados: {len(resultados)}")

async def ejemplo_comparacion():
    """
    Ejemplo comparando búsqueda simple vs MultiQuery.
    """
    print("\n⚖️ Comparación: Búsqueda Simple vs MultiQuery")
    print("=" * 50)
    
    from core.memory_manager import search_vector_db_optimized
    
    account_id = "usuario_ejemplo"
    consulta = "mejores prácticas de seguridad en aplicaciones web"
    
    # Búsqueda simple
    print("🔍 Búsqueda simple:")
    resultados_simple = await search_vector_db_optimized(
        account_id=account_id,
        query=consulta,
        k=5
    )
    print(f"   Resultados: {len(resultados_simple)}")
    
    # Búsqueda MultiQuery
    print("\n🚀 Búsqueda MultiQuery:")
    resultados_multi = await multi_query_search(
        account_id=account_id,
        query=consulta,
        k=5,
        num_queries=3
    )
    print(f"   Resultados: {len(resultados_multi)}")
    
    # Analizar diferencias
    contenidos_simple = {r.get('document', '')[:50] for r in resultados_simple}
    contenidos_multi = {r.get('document', '')[:50] for r in resultados_multi}
    
    unicos_multi = contenidos_multi - contenidos_simple
    print(f"\n📈 Resultados únicos encontrados por MultiQuery: {len(unicos_multi)}")

def ejemplo_uso_en_herramienta():
    """
    Ejemplo de cómo usar la herramienta desde el sistema de agentes.
    """
    print("\n🛠️ Uso desde herramientas del agente")
    print("=" * 50)
    
    from tools.multi_query_search_tool import MultiQuerySearchTool
    
    # Crear instancia de la herramienta
    tool = MultiQuerySearchTool()
    
    # Ejemplo de parámetros que recibiría del agente
    parametros = {
        "account_id": "usuario_ejemplo",
        "query": "análisis de sentimientos en redes sociales",
        "content_type": "user_documents",
        "topic": "ia",
        "k": 5,
        "num_queries": 3,
        "fusion_method": "rrf"
    }
    
    print("📋 Parámetros de la herramienta:")
    for key, value in parametros.items():
        print(f"   {key}: {value}")
    
    print("\n💡 El agente usaría esta herramienta automáticamente cuando:")
    print("   • Necesite búsquedas más exhaustivas")
    print("   • La consulta sea compleja o ambigua")
    print("   • Quiera capturar diferentes aspectos de un tema")

async def ejemplo_integracion_comprehensive_web():
    """
    Ejemplo de cómo integrar MultiQuery en comprehensive_web_analysis_tool.
    """
    print("\n🌐 Integración con Comprehensive Web Analysis")
    print("=" * 50)
    
    # Simulación de cómo se podría integrar
    consulta_web = "últimas tendencias en inteligencia artificial 2024"
    account_id = "usuario_ejemplo"
    
    print(f"📝 Consulta web: {consulta_web}")
    print("\n🔄 Proceso de integración:")
    print("1. Análisis web inicial")
    print("2. Generación de resumen web")
    print("3. 🆕 Búsqueda MultiQuery en knowledge base")
    print("4. Fusión de información web + knowledge base")
    print("5. Análisis final combinado")
    
    # Ejemplo de búsqueda en knowledge base con MultiQuery
    print("\n🔍 Búsqueda MultiQuery en knowledge base:")
    resultados_kb = await multi_query_search(
        account_id=account_id,
        query=f"inteligencia artificial tendencias {consulta_web}",
        content_type="user_documents",
        k=3,
        num_queries=2  # Menos consultas para complementar, no dominar
    )
    
    print(f"   Resultados de knowledge base: {len(resultados_kb)}")
    print("   ✅ Información combinada para análisis más completo")

async def main():
    """
    Ejecuta todos los ejemplos.
    """
    print("🎯 Ejemplos de MultiQueryRetriever en Kognito AI")
    print("=" * 60)
    
    try:
        await ejemplo_basico()
        await ejemplo_avanzado()
        await ejemplo_comparacion()
        ejemplo_uso_en_herramienta()
        await ejemplo_integracion_comprehensive_web()
        
        print("\n✅ Todos los ejemplos completados exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error en los ejemplos: {e}")
        logger.error("Error ejecutando ejemplos", exc_info=True)

if __name__ == "__main__":
    # Ejecutar ejemplos
    asyncio.run(main())
