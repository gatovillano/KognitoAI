import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class OpenRouterProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        try:
            async with httpx.AsyncClient() as client:
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                elif settings.openrouter_api_key:
                    headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
                
                response = await client.get(
                    "https://openrouter.ai/api/v1/models", 
                    headers=headers, 
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                raw_models = data.get("data", [])
                
                for m in raw_models:
                    raw_id = m.get("id", "")
                    models.append({
                        "id": f"openrouter/{raw_id}" if raw_id else raw_id,
                        "name": m.get("name") or raw_id,
                        "description": m.get("description", ""),
                        "context_length": m.get("context_length"),
                        "pricing": m.get("pricing", {})
                    })
        except Exception as e:
            logger.warning(f"Error al obtener modelos de OpenRouter: {e}")
        
        if not models:
            models = [
                {"id": "openrouter/meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B Instruct (Free)"},
                {"id": "openrouter/google/gemini-2.5-flash:free", "name": "Gemini 2.5 Flash (Free)"},
                {"id": "openrouter/deepseek/deepseek-chat", "name": "DeepSeek V3"},
                {"id": "openrouter/anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de OpenRouter")
        return models
