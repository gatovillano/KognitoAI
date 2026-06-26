#!/usr/bin/env python3
"""
Ejemplo de uso del KAI Measurement Pipeline
"""

import asyncio
import sys
import os

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kai_measurement_pipeline import KAIMeasurementPipeline

async def demo():
    """Demostración básica del pipeline"""
    
    print("=" * 60)
    print("🧪 KAI Measurement Pipeline - Demo")
    print("=" * 60)
    
    async with KAIMeasurementPipeline() as pipeline:
        # Ejemplo simple
        print("\n📤 Enviando query de ejemplo...")
        result = await pipeline.send_query("¿Qué es KAI?")
        
        if result["success"]:
            print(f"\n✅ Respuesta: {result['response'][:100]}...")
            print(f"📊 Métricas: {result.get('metrics', {})}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown')}")
        
        # Benchmark rápido
        print("\n" + "=" * 60)
        print("📈 Ejecutando benchmark rápido...")
        metrics = await pipeline.run_benchmark_suite()
        
        print(f"\n📊 Resultados:")
        print(f"   - Queries totales: {metrics['total_queries']}")
        print(f"   - Exitosas: {metrics['successful_queries']}")
        print(f"   - Tasa de herramientas: {metrics['tool_success_rate']:.2%}")
        print(f"   - Tasa de alucinaciones: {metrics['hallucination_rate']:.2%}")

if __name__ == "__main__":
    asyncio.run(demo())
