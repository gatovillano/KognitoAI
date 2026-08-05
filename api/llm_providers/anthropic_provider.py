import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy

logger = logging.getLogger(__name__)

class AnthropicProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if key:
            try:
                async with httpx.AsyncClient() as client:
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01"
                    }
                    response = await client.get(
                        "https://api.anthropic.com/v1/models",
                        headers=headers,
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            models.append({
                                "id": f"anthropic/{m.get('id')}",
                                "name": m.get('display_name', m.get('id')),
                                "description": m.get('description', ''),
                                "context_length": m.get('context_length'),
                            })
                    elif response.status_code == 404:
                        # Anthropic no tiene endpoint público para modelos en algunas versiones
                        pass
            except Exception as e:
                logger.warning(f"Error al obtener modelos de Anthropic: {e}")
        
        if not models:
            models = [
                {"id": "anthropic/claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
                {"id": "anthropic/claude-3-5-sonnet-20240620", "name": "Claude 3.5 Sonnet (Jun 2024)"},
                {"id": "anthropic/claude-3-opus-20240229", "name": "Claude 3 Opus"},
                {"id": "anthropic/claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de Anthropic")
        return models
