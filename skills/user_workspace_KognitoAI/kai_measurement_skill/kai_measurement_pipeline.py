"""
Pipeline de Medición para KAI
Integra la API de producción con el sistema de métricas
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics

class KAIMeasurementPipeline:
    """Pipeline para medir métricas de KAI en producción"""
    
    def __init__(self):
        self.api_url = os.getenv("NEXT_PUBLIC_API_URL", "https://apibase.cuerpolibre.cl")
        self.api_key = os.getenv("INTERNAL_API_KEY_FOR_BOT", "")
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Envía una query a la API de KAI y captura métricas"""
        payload = {
            "query": query,
            "stream": False,
            "session_id": session_id
        }
        
        try:
            async with self.session.post(
                f"{self.api_url}/api/v1/query",
                json=payload
            ) as response:
                data = await response.json()
                return {
                    "success": response.status == 200,
                    "response": data.get("response", ""),
                    "metrics": data.get("metrics", {}),
                    "tools_used": data.get("tools_used", []),
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_benchmark_suite(self) -> Dict[str, Any]:
        """Ejecuta una suite de benchmarks para medir métricas"""
        
        test_queries = [
            "¿Cuál es el estado actual de KAI en términos de alucinaciones?",
            "Explica la arquitectura de memoria híbrida de KAI",
            "¿Qué métricas de éxito tiene KAI comparada con RAG puro?",
            "¿Cómo funciona el grafo de conocimiento en KAI?",
            "Evalúa la precisión del sistema RAG en KAI"
        ]
        
        results = []
        for query in test_queries:
            result = await self.send_query(query)
            results.append(result)
            await asyncio.sleep(1)  # Evitar rate limiting
        
        return self.calculate_aggregated_metrics(results)
    
    def calculate_aggregated_metrics(self, results: List[Dict]) -> Dict[str, Any]:
        """Calcula métricas agregadas de los resultados"""
        
        successful = [r for r in results if r.get("success")]
        tool_success_rates = []
        hallucination_rates = []
        
        for r in successful:
            metrics = r.get("metrics", {})
            
            # Tasa de éxito de herramientas
            if "tool_success_rate" in metrics:
                tool_success_rates.append(metrics["tool_success_rate"])
            
            # Tasa de alucinaciones
            if "hallucination_rate" in metrics:
                hallucination_rates.append(metrics["hallucination_rate"])
        
        return {
            "total_queries": len(results),
            "successful_queries": len(successful),
            "tool_success_rate": statistics.mean(tool_success_rates) if tool_success_rates else 0,
            "hallucination_rate": statistics.mean(hallucination_rates) if hallucination_rates else 0,
            "avg_response_time": statistics.mean([r.get("response_time", 0) for r in successful]) if successful else 0,
            "timestamp": datetime.utcnow().isoformat()
        }


# Pipeline de medición específico para alucinaciones
class HallucinationMeasurementPipeline:
    """Pipeline especializado en medición de alucinaciones"""
    
    def __init__(self, kai_pipeline: KAIMeasurementPipeline):
        self.pipeline = kai_pipeline
        self.fact_check_prompts = [
            "Verifica si la siguiente afirmación es correcta: {statement}",
            "¿Esta información es fiable? {statement}",
            "Evalúa la veracidad de: {statement}"
        ]
    
    async def measure_hallucinations(self, num_samples: int = 10) -> Dict[str, float]:
        """Mide la tasa de alucinaciones"""
        
        # Queries con respuestas conocidas para verificar
        verification_queries = [
            ("¿Cuál es el capital de Francia?", "París"),
            ("¿En qué año se fundó Chile?", "1810"),
            ("¿Quién escribió Cien Años de Soledad?", "Gabriel García Márquez"),
            ("¿Cuál es la raíz cuadrada de 144?", "12"),
            ("¿Cuántos elementos hay en la tabla periódica?", "118")
        ]
        
        hallucinations = 0
        total = 0
        
        for query, expected in verification_queries[:num_samples]:
            result = await self.pipeline.send_query(query)
            if result.get("success"):
                response = result.get("response", "").lower()
                if expected.lower() not in response:
                    hallucinations += 1
                total += 1
        
        return {
            "hallucination_rate": hallucinations / total if total > 0 else 0,
            "total_verified": total,
            "hallucinations_detected": hallucinations
        }


# Pipeline de medición de éxito de herramientas
class ToolSuccessPipeline:
    """Pipeline para medir el éxito de las herramientas"""
    
    def __init__(self, kai_pipeline: KAIMeasurementPipeline):
        self.pipeline = kai_pipeline
    
    async def measure_tool_success(self) -> Dict[str, Any]:
        """Mide el porcentaje de herramientas que funcionan correctamente"""
        
        test_queries = [
            "Busca información sobre IA usando web search",
            "Analiza el código Python: print('hola')",
            "Genera una tabla con 5 elementos",
            "Crea un resumen de documentos",
            "Explica la teoría de grafos"
        ]
        
        results = []
        for query in test_queries:
            result = await self.pipeline.send_query(query)
            results.append(result)
        
        successful_tools = sum(1 for r in results if r.get("success") and r.get("tools_used"))
        total_with_tools = sum(1 for r in results if r.get("tools_used"))
        
        return {
            "tool_success_rate": successful_tools / len(test_queries) if test_queries else 0,
            "total_queries": len(test_queries),
            "queries_with_tools": total_with_tools,
            "successful_tool_calls": successful_tools
        }


async def run_measurement_pipeline():
    """Función principal para ejecutar el pipeline de medición"""
    
    async with KAIMeasurementPipeline() as pipeline:
        # Medición de métricas generales
        print("🚀 Ejecutando suite de benchmarks...")
        general_metrics = await pipeline.run_benchmark_suite()
        print(f"📊 Métricas generales: {json.dumps(general_metrics, indent=2)}")
        
        # Medición de alucinaciones
        print("\n🔍 Midiendo alucinaciones...")
        hallucination_pipeline = HallucinationMeasurementPipeline(pipeline)
        hallucination_metrics = await hallucination_pipeline.measure_hallucinations(5)
        print(f"❌ Métricas de alucinaciones: {json.dumps(hallucination_metrics, indent=2)}")
        
        # Medición de éxito de herramientas
        print("\n🔧 Midiendo éxito de herramientas...")
        tool_pipeline = ToolSuccessPipeline(pipeline)
        tool_metrics = await tool_pipeline.measure_tool_success()
        print(f"✅ Métricas de herramientas: {json.dumps(tool_metrics, indent=2)}")
        
        return {
            "general_metrics": general_metrics,
            "hallucination_metrics": hallucination_metrics,
            "tool_metrics": tool_metrics
        }


if __name__ == "__main__":
    results = asyncio.run(run_measurement_pipeline())
    print("\n📋 Resultados finales:")
    print(json.dumps(results, indent=2))
