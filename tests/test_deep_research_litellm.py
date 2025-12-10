"""
Script de prueba para Deep Research Tool con LiteLLM.

Este script demuestra cómo usar la nueva versión de Deep Research
que se integra con los LLMs de Kognito AI.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_manager import initialize_llms, get_main_llm, get_fast_llm
from core.config import settings
from tools.deep_research_tool_litellm import create_deep_research_tool_litellm

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_deep_research_litellm():
    """
    Prueba la integración de Deep Research con LiteLLM.
    """
    logger.info("=" * 80)
    logger.info("🧪 PRUEBA: Deep Research Tool con LiteLLM")
    logger.info("=" * 80)
    
    # 1. Verificar configuración
    logger.info("\n📋 Verificando configuración...")
    logger.info(f"   LLM Model: {settings.llm_model}")
    logger.info(f"   Fast LLM Model: {settings.fast_llm_model}")
    logger.info(f"   OpenRouter API Key: {'✅ Configurada' if settings.openrouter_api_key else '❌ No configurada'}")
    logger.info(f"   Tavily API Key: {'✅ Configurada' if settings.tavily_api_key else '❌ No configurada'}")
    
    # 2. Inicializar LLMs
    logger.info("\n🛠️ Inicializando LLMs de Kognito...")
    try:
        await initialize_llms()
        main_llm = get_main_llm()
        fast_llm = get_fast_llm()
        
        if main_llm:
            logger.info(f"   ✅ Main LLM inicializado: {getattr(main_llm, 'model', 'unknown')}")
        else:
            logger.error("   ❌ Main LLM no inicializado")
            return
        
        if fast_llm:
            logger.info(f"   ✅ Fast LLM inicializado: {getattr(fast_llm, 'model', 'unknown')}")
        else:
            logger.warning("   ⚠️ Fast LLM no inicializado, usando Main LLM")
            
    except Exception as e:
        logger.error(f"   ❌ Error inicializando LLMs: {e}")
        return
    
    # 3. Crear herramientas mock (para prueba)
    logger.info("\n🔧 Creando herramientas...")
    
    # Mock de web search tool
    class MockWebSearchTool:
        name = "web_search"
        async def ainvoke(self, *args, **kwargs):
            return "Mock search results"
    
    # Mock de add to RAG tool
    class MockAddToRAGTool:
        async def _run(self, **kwargs):
            logger.info(f"   📝 Mock: Añadiendo a RAG - {kwargs.get('title', 'Sin título')}")
            return "Mock: Añadido a RAG exitosamente"
    
    web_search = MockWebSearchTool()
    add_to_rag = MockAddToRAGTool()
    
    # 4. Crear Deep Research Tool
    logger.info("\n🔬 Creando Deep Research Tool con LiteLLM...")
    try:
        deep_research = create_deep_research_tool_litellm(
            web_search_tool=web_search,
            add_web_to_rag_tool=add_to_rag
        )
        
        if deep_research:
            logger.info("   ✅ Deep Research Tool creado exitosamente")
        else:
            logger.error("   ❌ No se pudo crear Deep Research Tool")
            return
            
    except Exception as e:
        logger.error(f"   ❌ Error creando Deep Research Tool: {e}")
        return
    
    # 5. Probar conversión de modelos
    logger.info("\n🔄 Probando conversión de formatos de modelo...")
    test_models = [
        "openrouter/anthropic/claude-3.5-sonnet",
        "openrouter/openai/gpt-4",
        "openrouter/google/gemini-pro",
        "openai/gpt-4",
        "anthropic:claude-3-opus",
        "gemini/gemini-2.0-flash",
        "google/gemini-1.5-pro",
        "openrouter/moonshotai/kimi-k2-0905:exacto"
    ]
    
    for model in test_models:
        converted = deep_research._convert_to_langchain_format(model)
        logger.info(f"   {model} → {converted}")
    
    # 6. Probar configuración
    logger.info("\n⚙️ Probando creación de configuración...")
    try:
        config = deep_research._create_litellm_compatible_config(
            max_iterations=4,
            max_concurrent_units=2
        )
        
        logger.info("   ✅ Configuración creada exitosamente")
        logger.info(f"   Research Model: {config['configurable']['research_model']}")
        logger.info(f"   Compression Model: {config['configurable']['compression_model']}")
        logger.info(f"   Max Iterations: {config['configurable']['max_researcher_iterations']}")
        logger.info(f"   Max Concurrent Units: {config['configurable']['max_concurrent_research_units']}")
        
    except Exception as e:
        logger.error(f"   ❌ Error creando configuración: {e}")
        return
    
    # 7. Prueba de ejecución (opcional, comentado por defecto)
    logger.info("\n" + "=" * 80)
    logger.info("💡 Para ejecutar una investigación real, descomenta la sección de prueba")
    logger.info("   en el código y proporciona una consulta de investigación.")
    logger.info("=" * 80)
    
    # Descomentar para ejecutar una investigación real:
    """
    logger.info("\n🚀 Ejecutando investigación de prueba...")
    try:
        result = await deep_research._run(
            query="¿Cuáles son las últimas tendencias en IA generativa?",
            max_iterations=2,  # Reducido para prueba rápida
            max_concurrent_units=1  # Solo 1 unidad para prueba
        )
        
        logger.info("\n📊 Resultado de la investigación:")
        logger.info("-" * 80)
        logger.info(result[:500] + "..." if len(result) > 500 else result)
        logger.info("-" * 80)
        
    except Exception as e:
        logger.error(f"   ❌ Error durante la investigación: {e}")
    """
    
    logger.info("\n✅ Prueba completada exitosamente")


if __name__ == "__main__":
    asyncio.run(test_deep_research_litellm())
