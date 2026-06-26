"""
KAI Measurement Engine - Motor de medición de métricas
"""
import asyncio
import time
from typing import Dict, List, Any, Tuple
from .api_client import KAIClient

class MeasurementEngine:
    """Motor de medición de métricas de KAI"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results: List[Dict[str, Any]] = []
    
    async def measure_hallucinations(self, test_dataset: List[Dict[str, str]]) -> Dict[str, float]:
        """
        Medir tasa de alucinaciones
        
        Args:
            test_dataset: Lista de {query, expected_answer}
            
        Returns:
            Dict con hallucination_rate
        """
        async with KAIClient(self.api_url) as client:
            correct = 0
            total = len(test_dataset)
            
            for item in test_dataset:
                result = await client.query(item["query"])
                if self._is_correct(result["response"], item["expected_answer"]):
                    correct += 1
            
            hallucination_rate = (total - correct) / total if total > 0 else 0
            return {
                "hallucination_rate": hallucination_rate,
                "correct_answers": correct,
                "total_questions": total
            }
    
    async def measure_tool_success(self, queries: List[str]) -> Dict[str, float]:
        """
        Medir tasa de éxito de herramientas
        
        Args:
            queries: Lista de queries para ejecutar
            
        Returns:
            Dict con tool_success_rate
        """
        async with KAIClient(self.api_url) as client:
            total_calls = 0
            successful_calls = 0
            
            for query in queries:
                result = await client.query(query)
                tool_calls = result.get("tool_calls", [])
                total_calls += len(tool_calls)
                
                for call in tool_calls:
                    if call.get("status") == "success":
                        successful_calls += 1
            
            tool_success_rate = successful_calls / total_calls if total_calls > 0 else 0
            return {
                "tool_success_rate": tool_success_rate,
                "successful_calls": successful_calls,
                "total_calls": total_calls
            }
    
    def _is_correct(self, response: str, expected: str) -> bool:
        """Verificar si la respuesta es correcta"""
        # Normalizar respuestas
        response_lower = response.lower().strip()
        expected_lower = expected.lower().strip()
        
        # Coincidencia exacta o contenga la palabra clave
        return expected_lower in response_lower or response_lower == expected_lower
    
    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Ejecutar benchmark completo"""
        # Dataset de prueba para alucinaciones
        test_dataset = [
            {
                "query": "¿Cuál es el capital social de Kognito AI Labs?",
                "expected_answer": "500000"
            },
            {
                "query": "¿Cuál es el recall@5 de KAI?",
                "expected_answer": "0.72"
            },
            {
                "query": "¿Qué tecnología usa KAI para su grafo de conocimiento?",
                "expected_answer": "Neo4j"
            }
        ]
        
        # Queries para medir éxito de herramientas
        tool_queries = [
            "Crea una tabla con los estudiantes",
            "Busca información sobre IA en Chile",
            "Genera un resumen ejecutivo"
        ]
        
        # Ejecutar mediciones
        hallucination_metrics = await self.measure_hallucinations(test_dataset)
        tool_metrics = await self.measure_tool_success(tool_queries)
        
        return {
            "hallucination_metrics": hallucination_metrics,
            "tool_metrics": tool_metrics,
            "timestamp": time.time()
        }

