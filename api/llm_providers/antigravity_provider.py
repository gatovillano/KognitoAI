import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.antigravity_client import AntigravityClient

logger = logging.getLogger(__name__)


class AntigravityProvider(LLMProviderStrategy):
    """
    Proveedor para Google Antigravity.
    Obtiene los modelos disponibles consultando la API de Google Cloud Code con la sesión activa.
    """
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        try:
            raw_models = AntigravityClient.fetch_available_models()
            for model_id, label in raw_models:
                clean_name = label.replace("🛸 ", "").strip()
                context_length = 1048576
                if "1.5" in model_id:
                    context_length = 2097152
                elif "claude" in model_id:
                    context_length = 200000
                elif "gpt-oss" in model_id:
                    context_length = 131072

                models.append({
                    "id": model_id if model_id.startswith("antigravity/") else f"antigravity/{model_id}",
                    "name": clean_name,
                    "context_length": context_length,
                    "pricing": {"prompt": "0", "completion": "0"}
                })
        except Exception as e:
            logger.warning(f"Error consultando modelos de Antigravity: {e}")

        if not models:
            models = [
                {"id": "antigravity/gemini-3-flash", "name": "Gemini 3 Flash (Antigravity)", "context_length": 1048576},
                {"id": "antigravity/gemini-3-pro", "name": "Gemini 3 Pro (Antigravity)", "context_length": 1048576},
                {"id": "antigravity/gemini-2.5-flash", "name": "Gemini 2.5 Flash (Antigravity)", "context_length": 1048576},
                {"id": "antigravity/gemini-2.5-pro", "name": "Gemini 2.5 Pro (Antigravity)", "context_length": 1048576},
                {"id": "antigravity/claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (Antigravity)", "context_length": 200000},
                {"id": "antigravity/claude-opus-4-6-thinking", "name": "Claude Opus 4.6 Thinking (Antigravity)", "context_length": 200000},
            ]

        return models
