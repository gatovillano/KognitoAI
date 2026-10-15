import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from utils.url_safety import SAFE_HTTPX_CLIENT_OPTIONS

logger = logging.getLogger(__name__)


class InceptionLabsProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        base_url = "https://api.inceptionlabs.ai/v1"
        key = api_key or os.getenv("INCEPTIONLABS_API_KEY")

        if key:
            try:
                async with httpx.AsyncClient(**SAFE_HTTPX_CLIENT_OPTIONS) as client:
                    response = await client.get(
                        f"{base_url}/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=15.0,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            model_id = m.get("id")
                            if model_id:
                                models.append(
                                    {
                                        "id": f"inceptionlabs/{model_id}",
                                        "name": m.get("name") or model_id,
                                    }
                                )
            except Exception as e:
                logger.warning(f"Error al obtener modelos de InceptionLabs: {e}")

        logger.info(f"Obtenidos {len(models)} modelos de InceptionLabs")
        return models
