import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings
from core.ollama_direct import normalize_ollama_base_url
from utils.url_safety import SAFE_HTTPX_CLIENT_OPTIONS

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        
        candidate_urls = []
        if api_base and api_base.strip():
            candidate_urls.append(api_base.strip())
            
        ollama_url_cfg = getattr(settings, "ollama_api_url", None) or getattr(settings, "ollama_direct_api_url", None)
        if ollama_url_cfg:
            candidate_urls.append(ollama_url_cfg)
            
        if os.path.exists("/.dockerenv"):
            candidate_urls.extend(["http://host.docker.internal:11434", "http://127.0.0.1:11434", "http://localhost:11434"])
        else:
            candidate_urls.extend(["http://localhost:11434", "http://127.0.0.1:11434", "http://host.docker.internal:11434"])

        normalized_urls = []
        for url in candidate_urls:
            norm = normalize_ollama_base_url(url)
            if norm not in normalized_urls:
                normalized_urls.append(norm)

        for base_url in normalized_urls:
            try:
                async with httpx.AsyncClient(**SAFE_HTTPX_CLIENT_OPTIONS) as client:
                    response = await client.get(
                        f"{base_url}/api/tags",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("models", []):
                            name = m.get("name")
                            if name:
                                param_size = m.get("details", {}).get("parameter_size") or "Unknown"
                                models.append({
                                    "id": f"ollama/{name}",
                                    "name": name,
                                    "description": f"Ollama Local Model ({param_size})",
                                    "context_length": m.get("details", {}).get("context_length"),
                                })
                        if models:
                            logger.info(f"Obtenidos {len(models)} modelos de Ollama Local desde {base_url}")
                            return models
            except Exception as e:
                logger.debug(f"Ollama local no disponible en {base_url}: {e}")
            
        logger.info(f"Obtenidos {len(models)} modelos de Ollama Local")
        return models
