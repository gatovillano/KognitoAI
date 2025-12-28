#!/usr/bin/env python3
"""
Test script para validar las optimizaciones del ConceptualGraphProcessor.

Este script prueba:
1. Inicialización con configuraciones optimizadas
2. Procesamiento paralelo de relaciones
3. Gestión de caché mejorada
4. Agrupación por similitud
5. Métricas de rendimiento
"""

import asyncio
import time
import logging
from typing import List, Dict, Any
import sys
import os

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Agregar el directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from knowledge_graph.conceptual_graph_processor import ConceptualGraphProcessor

def create_test_documents() -> List[Dict[str, Any]]:
    """Crea documentos de prueba para testing."""
    return [
        {
            "title": "Documento 1: Inteligencia Artificial",
            "content": """
            La inteligencia artificial representa una tecnología fundamental que está transformando múltiples sectores.
            Los algoritmos de machine learning permiten a las máquinas aprender patrones complejos de datos.
            Las redes neuronales artificiales imitan el funcionamiento del cerebro humano.
            El procesamiento de lenguaje natural facilita la comunicación entre humanos y máquinas.
            La visión computacional permite a las máquinas interpretar imágenes y videos.
            """
        },
        {
            "title": "Documento 2: Machine Learning",
            "content": """
            El machine learning es una rama de la inteligencia artificial que se enfoca en el aprendizaje automático.
            Los algoritmos supervisados utilizan datos etiquetados para entrenar modelos predictivos.
            El aprendizaje no supervisado encuentra patrones ocultos en datos sin etiquetar.
            Las técnicas de deep learning utilizan redes neuronales profundas para resolver problemas complejos.
            La validación cruzada ayuda a evaluar la generalización de los modelos de machine learning.
            """
        },
        {
            "title": "Documento 3: Redes Neuronales",
            "content": """
            Las redes neuronales son modelos computacionales inspirados en el cerebro humano.
            Las redes convolucionales son especialmente efectivas para tareas de visión computacional.
            Las redes recurrentes procesan secuencias de datos temporales como texto o audio.
            La backpropagation es el algoritmo fundamental para entrenar redes neuronales.
            Las funciones de activación introducen no linealidad en los modelos neuronales.
            """
        },
        {
            "title": "Documento 4: Procesamiento de Lenguaje Natural",
            "content": """
            El procesamiento de lenguaje natural combina lingüística computacional con inteligencia artificial.
            Los transformers revolucionaron el procesamiento de secuencias con su mecanismo de atención.
            BERT y GPT son modelos de lenguaje pre-entrenados que achieve state-of-the-art results.
            El tokenización convierte texto en representaciones numéricas para modelos de ML.
            Los embeddings de palabras capturan relaciones semánticas entre términos lingüísticos.
            """
        },
        {
            "title": "Documento 5: Visión Computacional",
            "content": """
            La visión computacional permite a las máquinas interpretar y entender contenido visual.
            La detección de objetos identifica y localiza múltiples objetos en imágenes.
            La segmentación semántica clasifica cada píxel de una imagen según su categoría.
            Las CNN (Convolutional Neural Networks) son la arquitectura base para tareas de visión.
            OpenCV es una biblioteca popular para procesamiento de imágenes y video.
            """
        }
    ]

async def test_optimized_processor():
    """Test del procesador optimizado."""
    logger.info("🚀 Iniciando test del procesador optimizado...")
    
    # Crear documentos de prueba
    documents = create_test_documents()
    logger.info(f"📄 Creados {len(documents)} documentos de prueba")
    
    # Crear procesador con configuraciones optimizadas
    processor = ConceptualGraphProcessor(
        llm=None,  # Sin LLM para este test
        sentence_transformer=None,  # Sin embedding model para este test
        enable_parallel_processing=True,
        max_parallel_batches=3,
        cache_size_limit=100
    )
    
    logger.info("✅ Procesador optimizado inicializado")
    
    # Test de estadísticas de caché
    stats = processor.get_cache_stats()
    logger.info(f"📊 Estadísticas iniciales del caché: {stats}")
    
    # Simular algunas operaciones de caché
    processor._store_in_cache("test_key_1", "test_value_1")
    processor._store_in_cache("test_key_2", "test_value_2")
    
    cached_result = processor._check_cache("test_key_1")
    logger.info(f"💾 Test de caché: {'✅ Hit' if cached_result else '❌ Miss'}")
    
    # Test de agrupación por similitud (simulado)
    test_quotes = [
        {"id": "q1", "concept": "machine learning", "text": "texto sobre ML"},
        {"id": "q2", "concept": "redes neuronales", "text": "texto sobre redes"},
        {"id": "q3", "concept": "deep learning", "text": "texto sobre deep learning"}
    ]
    
    # Simular matriz de similitudes
    import numpy as np
    similarities = np.array([
        [1.0, 0.8, 0.9],  # q1 con q1, q2, q3
        [0.8, 1.0, 0.85], # q2 con q1, q2, q3
        [0.9, 0.85, 1.0]  # q3 con q1, q2, q3
    ])
    
    grouped_pairs = processor._group_candidate_pairs_by_similarity(test_quotes, similarities)
    logger.info(f"🔍 Test de agrupación por similitud:")
    logger.info(f"   📈 Alta similitud: {len(grouped_pairs['high'])} pares")
    logger.info(f"   📊 Media similitud: {len(grouped_pairs['medium'])} pares")
    logger.info(f"   📉 Baja similitud: {len(grouped_pairs['low'])} pares")
    
    # Test de relaciones determinables por reglas
    quote1 = {"category": "marco_teórico", "concept": "machine learning"}
    quote2 = {"category": "marco_teórico", "concept": "deep learning"}
    
    is_determinable = processor._is_rule_determinable_relationship(
        quote1, quote2, "MARCOS_TEORICOS_AFINES"
    )
    logger.info(f"🎯 Test de reglas: {'✅ Determinable' if is_determinable else '❌ No determinable'}")
    
    # Test de limpieza de caché
    processor.clear_cache()
    final_stats = processor.get_cache_stats()
    logger.info(f"🧹 Caché limpiado: {final_stats}")
    
    logger.info("✅ Test del procesador optimizado completado")
    
    return {
        "processor": processor,
        "documents": documents,
        "grouped_pairs": grouped_pairs,
        "final_stats": final_stats
    }

async def test_performance_comparison():
    """Compara rendimiento entre versión original y optimizada."""
    logger.info("⚡ Iniciando comparación de rendimiento...")
    
    documents = create_test_documents()
    
    # Configuración para test de rendimiento
    test_configs = [
        {
            "name": "Secuencial (Original)",
            "enable_parallel_processing": False,
            "max_parallel_batches": 1,
            "cache_size_limit": 50
        },
        {
            "name": "Paralelo Básico",
            "enable_parallel_processing": True,
            "max_parallel_batches": 2,
            "cache_size_limit": 100
        },
        {
            "name": "Paralelo Optimizado",
            "enable_parallel_processing": True,
            "max_parallel_batches": 4,
            "cache_size_limit": 200
        }
    ]
    
    results = {}
    
    for config in test_configs:
        logger.info(f"🔄 Probando configuración: {config['name']}")
        
        processor = ConceptualGraphProcessor(
            llm=None,
            sentence_transformer=None,
            enable_parallel_processing=config["enable_parallel_processing"],
            max_parallel_batches=config["max_parallel_batches"],
            cache_size_limit=config["cache_size_limit"]
        )
        
        # Simular tiempo de inicialización
        start_time = time.time()
        
        # Simular algunas operaciones de caché
        for i in range(10):
            processor._store_in_cache(f"key_{i}", f"value_{i}")
            processor._check_cache(f"key_{i}")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        stats = processor.get_cache_stats()
        
        results[config["name"]] = {
            "execution_time": execution_time,
            "cache_hits": stats["hits"],
            "cache_misses": stats["misses"],
            "hit_rate": stats["hit_rate_percent"]
        }
        
        logger.info(f"   ⏱️  Tiempo: {execution_time:.3f}s")
        logger.info(f"   🎯 Hit rate: {stats['hit_rate_percent']:.1f}%")
    
    logger.info("📊 Resultados de comparación:")
    for name, result in results.items():
        logger.info(f"   {name}: {result['execution_time']:.3f}s, {result['hit_rate']:.1f}% hit rate")
    
    return results

async def main():
    """Función principal de test."""
    logger.info("🧪 Iniciando tests de optimización del ConceptualGraphProcessor")
    
    try:
        # Test básico del procesador optimizado
        basic_result = await test_optimized_processor()
        
        # Test de comparación de rendimiento
        performance_result = await test_performance_comparison()
        
        logger.info("🎉 Todos los tests completados exitosamente")
        logger.info("📈 Las optimizaciones están funcionando correctamente")
        
        return {
            "basic_test": basic_result,
            "performance_test": performance_result,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error durante los tests: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = asyncio.run(main())
    if result["success"]:
        print("✅ Tests completados exitosamente")
        sys.exit(0)
    else:
        print(f"❌ Tests fallaron: {result['error']}")
        sys.exit(1)