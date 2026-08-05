import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = api_key or settings.google_api_key
        
        if key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("models", []):
                            methods = m.get("supportedGenerationMethods", [])
                            if "generateContent" in methods or "generateImages" in methods or "imagen" in m.get("name", "").lower():
                                models.append({
                                    "id": f"gemini/{m.get('name').replace('models/', '')}",
                                    "name": m.get('name').replace('models/', ''),
                                    "description": m.get('description', ''),
                                    "context_length": m.get("inputTokenLimit"),
                                    "pricing": {}
                                })
            except Exception as e:
                logger.debug(f"Error obteniendo modelos de Gemini API: {e}")
        
        if not models:
            models = [
                {"id": "gemini/gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash Exp"},
                {"id": "gemini/gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
                {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
                {"id": "gemini/imagen-3.0-generate-002", "name": "imagen-3.0-generate-002"},
                {"id": "gemini/imagen-3.0-fast-generate-002", "name": "imagen-3.0-fast-generate-002"},
            ]
        logger.info(f"Obtenidos {len(models)} modelos de Google/Gemini")
        return models
