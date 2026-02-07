# api/llm.py

import logging
import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from core.config import settings
from utils.security import get_current_account_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Caché simple en memoria para evitar llamadas excesivas
_models_cache: Dict[str, Dict[str, Any]] = {}
import time

CACHE_TTL = 3600  # 1 hora

@router.get("/llm/models/{provider}", response_model=List[Dict[str, Any]])
async def get_provider_models(provider: str, current_account_id: str = Depends(get_current_account_id)):
    """
    Obtiene la lista de modelos disponibles directamente desde el proveedor.
    """
    provider = provider.lower()
    now = time.time()
    
    # Verificar caché
    if provider in _models_cache:
        cache_entry = _models_cache[provider]
        if now - cache_entry["timestamp"] < CACHE_TTL:
            logger.info(f"Retornando modelos de {provider} desde caché.")
            return cache_entry["models"]

    models = []
    
    try:
        if provider == "openrouter":
            async with httpx.AsyncClient() as client:
                headers = {}
                if settings.openrouter_api_key:
                    headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
                
                response = await client.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                raw_models = data.get("data", [])
                
                # Formatear para el frontend
                for m in raw_models:
                    models.append({
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "description": m.get("description", ""),
                        "context_length": m.get("context_length"),
                        "pricing": m.get("pricing", {})
                    })

        elif provider == "openai":
            if settings.openai_api_key:
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
                    response = await client.get("https://api.openai.com/v1/models", headers=headers, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    raw_models = data.get("data", [])
                    # Filtrar solo modelos de chat comunes
                    for m in raw_models:
                        model_id = m.get("id")
                        if "gpt" in model_id:
                            models.append({"id": f"openai/{model_id}", "name": model_id})
            else:
                # Fallback estático si no hay llave global
                models = [
                    {"id": "openai/gpt-4o", "name": "GPT-4o"},
                    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini"},
                    {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo"},
                ]

        elif provider == "google":
            # Gemini a veces es difícil de listar sin una llave válida y permisos específicos
            # Usamos una lista de los más comunes pero podrías expandirla
            models = [
                {"id": "gemini/gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
                {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            ]
            
        elif provider == "ollama":
            # Esto asume que Ollama está corriendo localmente en el servidor
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{settings.llm_api_base or 'http://localhost:11434'}/api/tags", timeout=2.0)
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("models", []):
                            name = m.get("name")
                            models.append({"id": f"ollama/{name}", "name": name})
            except Exception:
                # Si falla Ollama local, enviamos lista vacía o comunes
                models = [{"id": "ollama/llama3", "name": "Llama 3 (Local)"}]

        # Guardar en caché si obtuvimos resultados
        if models:
            _models_cache[provider] = {
                "timestamp": now,
                "models": models
            }
            
        return models

    except Exception as e:
        logger.error(f"Error al obtener modelos de {provider}: {e}")
        # En caso de error, devolver lista vacía o error
        raise HTTPException(status_code=500, detail=f"No se pudieron obtener los modelos de {provider}")
