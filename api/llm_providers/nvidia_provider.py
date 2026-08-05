import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class NvidiaProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or settings.nvidia_api_key

        if key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://integrate.api.nvidia.com/v1/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=15.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    for m in data.get("data", []):
                        model_id = m.get("id", "")
                        models.append({
                            "id": f"nvidia/{model_id}",
                            "name": m.get("name") or model_id,
                            "context_length": m.get("context_length"),
                            "pricing": m.get("pricing", {}),
                        })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de NVIDIA: {e}")

        if not models:
            models = [
                {"id": "nvidia/llama-3.1-405b-instruct", "name": "Llama 3.1 405B Instruct"},
                {"id": "nvidia/llama-3.1-70b-instruct", "name": "Llama 3.1 70B Instruct"},
                {"id": "nvidia/nemotron-4-340b-instruct", "name": "Nemotron 4 340B Instruct"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de NVIDIA")
        return models
