import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class AzureProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        base_url = api_base or os.getenv("AZURE_OPENAI_ENDPOINT")
        key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        
        if base_url and key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{base_url.rstrip('/')}/openai/models?api-version=2024-02-01",
                        headers={"api-key": key},
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            models.append({
                                "id": f"azure/{m.get('id')}",
                                "name": m.get('id'),
                            })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de Azure: {e}")
        
        if not models:
            models = [
                {"id": "azure/gpt-4o", "name": "GPT-4o (Azure)"},
                {"id": "azure/gpt-4o-mini", "name": "GPT-4o Mini (Azure)"},
                {"id": "azure/gpt-4-turbo", "name": "GPT-4 Turbo (Azure)"},
                {"id": "azure/gpt-35-turbo", "name": "GPT-3.5 Turbo (Azure)"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de Azure")
        return models
