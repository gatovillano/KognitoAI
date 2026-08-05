import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or settings.openai_api_key
        
        if key:
            try:
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {key}"}
                    response = await client.get(
                        "https://api.openai.com/v1/models", 
                        headers=headers, 
                        timeout=15.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    raw_models = data.get("data", [])
                    
                    for m in raw_models:
                        model_id = m.get("id")
                        if any(x in model_id.lower() for x in ["gpt", "chat", "o1"]):
                            models.append({
                                "id": f"openai/{model_id}", 
                                "name": model_id,
                                "context_length": m.get("context_length"),
                                "pricing": m.get("pricing", {})
                            })
            except Exception as e:
                logger.warning(f"Error al obtener modelos de OpenAI: {e}")
        
        if not models:
            models = [
                {"id": "openai/gpt-4o", "name": "gpt-4o"},
                {"id": "openai/gpt-4o-mini", "name": "gpt-4o-mini"},
                {"id": "openai/o1-mini", "name": "o1-mini"},
                {"id": "openai/gpt-4-turbo", "name": "gpt-4-turbo"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de OpenAI")
        return models
