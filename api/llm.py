# api/llm.py

import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends

from core.config import settings
from core.repositories.secret_repository import SecretRepository
from core.database import SessionLocal, Account
from utils.security import get_current_account_id

from api.llm_providers.registry import provider_registry

logger = logging.getLogger(__name__)

router = APIRouter()

# Caché simple en memoria para evitar llamadas excesivas
_models_cache: Dict[str, Dict[str, Any]] = {}

CACHE_TTL = 3600  # 1 hora


async def get_user_api_key(account_id: str, provider: str) -> Optional[str]:
    """
    Obtiene la API key del usuario desde los secretos encriptados.
    """
    try:
        async with SessionLocal() as db:
            repo = SecretRepository(db)
            key_name = f"{provider.upper()}_API_KEY"
            api_key = await repo.get_decrypted_secret(account_id, key_name)

            if not api_key and provider.lower() in ["gemini", "google"]:
                api_key = await repo.get_decrypted_secret(account_id, "GOOGLE_API_KEY")

            if not api_key:
                system_id = "00000000-0000-0000-0000-000000000000"
                api_key = await repo.get_decrypted_secret(system_id, key_name)
                if not api_key and provider.lower() in ["gemini", "google"]:
                    api_key = await repo.get_decrypted_secret(system_id, "GOOGLE_API_KEY")

            if api_key and not api_key.isascii():
                logger.warning("API key for %s contains non-ASCII characters. Stripping them.", provider)
                api_key = api_key.encode("ascii", "ignore").decode("ascii")

            return api_key
    except Exception as e:
        logger.error("Error al obtener API key para %s: %s", provider, e)
        return None


async def get_user_api_base(account_id: str) -> Optional[str]:
    """
    Obtiene la API base personalizada del usuario.
    """
    try:
        async with SessionLocal() as db:
            account = await db.get(Account, account_id)
            if account:
                return account.llm_api_base
    except Exception as e:
        logger.error("Error al obtener API base para usuario %s: %s", account_id, e)
    return None


@router.get("/llm/models/{provider}", response_model=list[dict[str, Any]])
async def get_provider_models(
    provider: str,
    api_base: Optional[str] = None,
    refresh: bool = False,
    current_account_id: str = Depends(get_current_account_id),
):
    """
    Obtiene la lista de modelos disponibles directamente desde el proveedor.
    Permite opcionalmente pasar una api_base personalizada (útil para previsualización antes de guardar).
    """
    provider = provider.lower()
    now = time.time()

    # Verificar caché (solo si no se pide refresh)
    if not refresh and provider in _models_cache:
        cache_entry = _models_cache[provider]
        # Para Ollama/local, el cache es mucho más corto (5 min) para detectar cambios locales
        ttl = 300 if provider == "ollama" else CACHE_TTL
        if now - cache_entry["timestamp"] < ttl:
            logger.info("Retornando modelos de %s desde caché.", provider)
            return cache_entry["models"]

    try:
        user_api_key = await get_user_api_key(current_account_id, provider)
        user_api_base = api_base if api_base is not None else await get_user_api_base(current_account_id)

        provider_instance = provider_registry._providers.get(provider)
        if not provider_instance:
            raise HTTPException(status_code=404, detail=f"Proveedor '{provider}' no soportado")

        models = await provider_instance.get_models(
            api_key=user_api_key,
            api_base=user_api_base,
        )

        # Guardar en caché si obtuvimos resultados
        if models:
            _models_cache[provider] = {
                "timestamp": now,
                "models": models,
            }

        return models

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error al obtener modelos de %s: %s", provider, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"No se pudieron obtener los modelos de {provider}")
