"""
KAI API Client - Cliente HTTP para integración con pipeline de medición
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional
import json

class KAIClient:
    """Cliente HTTP para la API de KAI"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecutar query en KAI y obtener respuesta con métricas
        
        Args:
            query: Pregunta a KAI
            context: Contexto adicional
            
        Returns:
            Dict con:
                - response: respuesta de KAI
                - tool_calls: lista de herramientas usadas
                - metrics: métricas de rendimiento
                - elapsed_time: tiempo de respuesta
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        payload = {
            "query": query,
            "context": context or {}
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/query",
                json=payload
            ) as response:
                data = await response.json()
                return data
        except Exception as e:
            return {
                "response": "",
                "tool_calls": [],
                "metrics": {},
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        """Verificar que la API está disponible"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except:
            return False

