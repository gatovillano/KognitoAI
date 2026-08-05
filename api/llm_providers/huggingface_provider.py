import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class HuggingFaceProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or settings.huggingface_api_key

        if key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://huggingface.co/api/models",
                        params={"author": "google", "filter": "text-generation", "limit": 50},
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=15.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    for m in data:
                        model_id = m.get("id", "")
                        if model_id:
                            models.append({
                                "id": f"huggingface/{model_id}",
                                "name": m.get("id", model_id),
                                "context_length": m.get("gated", False),
                            })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de HuggingFace: {e}")

        if not models:
            models = [
                {"id": "huggingface/google/gemma-2-9b-it", "name": "Gemma 2 9B IT"},
                {"id": "huggingface/meta-llama/Llama-3.1-8B-Instruct", "name": "Llama 3.1 8B Instruct"},
                {"id": "huggingface/microsoft/Phi-3-mini-4k-instruct", "name": "Phi 3 Mini 4K Instruct"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de HuggingFace")
        return models
