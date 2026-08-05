import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy

logger = logging.getLogger(__name__)

class CerebrasProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or os.getenv("CEREBRAS_API_KEY")
        
        if key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.cerebras.ai/v1/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            models.append({
                                "id": f"cerebras/{m.get('id')}",
                                "name": m.get('id'),
                            })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de Cerebras: {e}")
        
        if not models:
            models = [
                {"id": "cerebras/llama3.1-70b", "name": "Llama 3.1 70B"},
                {"id": "cerebras/llama3.1-8b", "name": "Llama 3.1 8B"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de Cerebras")
        return models
