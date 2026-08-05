import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy

logger = logging.getLogger(__name__)

class DeepseekProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if key:
            base_url = api_base or "https://api.deepseek.com"
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{base_url}/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            models.append({
                                "id": f"deepseek/{m.get('id')}",
                                "name": m.get('id'),
                                "context_length": m.get("context_length"),
                            })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de DeepSeek: {e}")
        
        if not models:
            models = [
                {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat"},
                {"id": "deepseek/deepseek-reasoner", "name": "DeepSeek Reasoner"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de DeepSeek")
        return models
