import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy

logger = logging.getLogger(__name__)

class GroqProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or os.getenv("GROQ_API_KEY")
        
        if key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.groq.com/openai/v1/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            models.append({
                                "id": f"groq/{m.get('id')}",
                                "name": m.get('id'),
                                "context_length": m.get("context_window"),
                            })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de Groq: {e}")
        
        if not models:
            models = [
                {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile"},
                {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant"},
                {"id": "groq/mixtral-8x7b-32768", "name": "Mixtral 8x7b"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de Groq")
        return models
