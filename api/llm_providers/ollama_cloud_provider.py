import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy

logger = logging.getLogger(__name__)

class OllamaCloudProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        base_url = api_base or os.getenv("OLLAMA_CLOUD_BASE_URL")
        key = api_key or os.getenv("OLLAMA_CLOUD_API_KEY")
        
        if base_url:
            try:
                async with httpx.AsyncClient() as client:
                    headers = {}
                    if key:
                        headers["Authorization"] = f"Bearer {key}"
                    
                    response = await client.get(
                        f"{base_url.rstrip('/')}/api/tags",
                        headers=headers,
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("models", []):
                            name = m.get("name")
                            if name:
                                models.append({
                                    "id": f"ollama-cloud/{name}",
                                    "name": name,
                                    "description": f"Ollama Cloud Model ({m.get('details', {}).get('parameter_size', 'Unknown')})",
                                })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de Ollama Cloud: {e}")
        
        logger.info(f"Obtenidos {len(models)} modelos de Ollama Cloud")
        return models
