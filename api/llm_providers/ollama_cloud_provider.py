import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings
from core.ollama_direct import normalize_ollama_base_url
from utils.url_safety import SAFE_HTTPX_CLIENT_OPTIONS

logger = logging.getLogger(__name__)

class OllamaCloudProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        
        base_url = api_base or os.getenv("OLLAMA_CLOUD_BASE_URL") or getattr(settings, "ollama_cloud_base_url", None) or "https://api.ollama.com"
        key = api_key or os.getenv("OLLAMA_CLOUD_API_KEY") or os.getenv("OLLAMA_API_KEY") or getattr(settings, "ollama_api_key", None)
        
        headers = {}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        # 1. Intentar consultar endpoint remoto /api/tags o /v1/models de Ollama Cloud
        for url_path in ["/api/tags", "/v1/models"]:
            try:
                norm_base = normalize_ollama_base_url(base_url)
                async with httpx.AsyncClient(**SAFE_HTTPX_CLIENT_OPTIONS) as client:
                    response = await client.get(
                        f"{norm_base}{url_path}",
                        headers=headers,
                        timeout=7.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        raw_models = data.get("models") or data.get("data") or []
                        for m in raw_models:
                            name = m.get("name") or m.get("id")
                            if name:
                                param_size = m.get("details", {}).get("parameter_size", "Cloud") if isinstance(m.get("details"), dict) else "Cloud"
                                models.append({
                                    "id": f"ollama-cloud/{name}",
                                    "name": name,
                                    "description": f"Ollama Cloud Model ({param_size})",
                                })
                        if models:
                            logger.info(f"Obtenidos {len(models)} modelos de Ollama Cloud vía {norm_base}{url_path}")
                            return models
            except Exception as e:
                logger.debug(f"No se pudo consultar Ollama Cloud en {base_url}{url_path}: {e}")

        # 2. Fallback: Si no se obtuvieron modelos desde la nube directamente, consultar en el servidor Ollama local por modelos remotos/cloud
        local_urls = ["http://localhost:11434", "http://127.0.0.1:11434", "http://host.docker.internal:11434"]
        for local_url in local_urls:
            try:
                async with httpx.AsyncClient(**SAFE_HTTPX_CLIENT_OPTIONS) as client:
                    response = await client.get(f"{local_url}/api/tags", timeout=3.0)
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("models", []):
                            name = m.get("name", "")
                            if ":cloud" in name or m.get("remote_host") or m.get("remote_model"):
                                param_size = m.get("details", {}).get("parameter_size", "Cloud") if isinstance(m.get("details"), dict) else "Cloud"
                                models.append({
                                    "id": f"ollama-cloud/{name}",
                                    "name": name,
                                    "description": f"Ollama Cloud Model ({param_size})",
                                })
                        if models:
                            logger.info(f"Obtenidos {len(models)} modelos de Ollama Cloud desde servidor Ollama local ({local_url})")
                            return models
            except Exception:
                pass

        logger.info(f"Obtenidos {len(models)} modelos de Ollama Cloud")
        return models
