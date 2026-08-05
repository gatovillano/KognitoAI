import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        base_url = api_base or settings.ollama_base_url or "http://host.docker.internal:11434"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/api/tags",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    for m in data.get("models", []):
                        name = m.get("name")
                        if name:
                            models.append({
                                "id": f"ollama/{name}",
                                "name": name,
                                "description": f"Ollama Local Model ({m.get('details', {}).get('parameter_size', 'Unknown')})",
                                "context_length": None,
                            })
        except Exception as e:
            logger.debug(f"Ollama no está disponible en {base_url}: {e}")
            
        logger.info(f"Obtenidos {len(models)} modelos de Ollama Local")
        return models
