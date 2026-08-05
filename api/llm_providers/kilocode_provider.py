import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProviderStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class KilocodeProvider(LLMProviderStrategy):
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        models = []
        key = (api_key or settings.kilocode_api_key or os.getenv("KILOCODE_API_KEY") or "").strip()
        
        if key and not key.isascii():
            logger.warning("KILOCODE_API_KEY contains non-ASCII characters. Stripping them.")
            key = key.encode('ascii', 'ignore').decode('ascii')
            
        kilocode_base = "https://api.kilo.ai/api/gateway"
        
        if key:
            endpoints = [f"{kilocode_base}/v1/models", f"{kilocode_base}/models"]
            for endpoint in endpoints:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            endpoint,
                            headers={"Authorization": f"Bearer {key}"},
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            raw_models = data.get("data", [])
                            if not raw_models and isinstance(data, list):
                                raw_models = data
                            
                            for m in raw_models:
                                model_id = m.get("id", "")
                                model_name = m.get("name") or model_id
                                models.append({
                                    "id": f"kilocode/{model_id}",
                                    "name": model_name,
                                    "context_length": m.get("context_length"),
                                    "pricing": m.get("pricing", {})
                                })
                            logger.info(f"Obtenidos {len(models)} modelos de Kilocode Gateway desde {endpoint}")
                            break
                        else:
                            logger.warning(f"Kilocode ({endpoint}) respondió con error {response.status_code}")
                except Exception as e:
                    logger.warning("Error al conectar con Kilocode Gateway (%s): %s", endpoint, str(e))
        
        if not models:
            logger.info(f"No se pudieron obtener modelos de Kilocode Gateway, lista vacía.")
            
        return models
