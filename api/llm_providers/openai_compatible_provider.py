import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy

logger = logging.getLogger(__name__)

class OpenAICompatibleProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        base_url = api_base or os.getenv("OPENAI_COMPATIBLE_API_BASE")
        key = api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY")
        
        if base_url:
            try:
                async with httpx.AsyncClient() as client:
                    headers = {}
                    if key:
                        headers["Authorization"] = f"Bearer {key}"
                    
                    response = await client.get(
                        f"{base_url.rstrip('/')}/v1/models",
                        headers=headers,
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            model_id = m.get("id")
                            if model_id:
                                models.append({
                                    "id": f"openai-compatible/{model_id}",
                                    "name": model_id,
                                })
            except Exception as e:
                logger.warning(f"Error al obtener modelos compatibles con OpenAI: {e}")
        
        logger.info(f"Obtenidos {len(models)} modelos de OpenAI Compatible")
        return models
