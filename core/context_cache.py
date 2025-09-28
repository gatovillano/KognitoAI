# core/context_cache.py

import time
from typing import Dict, Optional, Tuple, Any
import json
import logging

logger = logging.getLogger(__name__)

# Cache simple en memoria (usar Redis en producción)
# La estructura ahora es: { key: (json_string_value, timestamp, ttl) }
_cache: Dict[str, Tuple[str, float, int]] = {}
DEFAULT_CACHE_TTL = 3600  # 1 hora por defecto

async def get_cached_context(key: str) -> Optional[Any]:
    """Recupera un objeto de la caché si existe y no ha expirado."""
    if key in _cache:
        serialized_value, timestamp, ttl = _cache[key]
        if time.time() - timestamp < ttl:
            logger.info(f"Cache HIT for key: {key}")
            try:
                return json.loads(serialized_value)
            except json.JSONDecodeError:
                logger.warning(f"Could not decode cached JSON for key {key}. Deleting.")
                del _cache[key]
                return None
        else:
            logger.info(f"Cache expired for key: {key}. Deleting.")
            del _cache[key]
    
    logger.info(f"Cache MISS for key: {key}")
    return None

async def cache_context(key: str, value: Any, ttl: Optional[int] = None):
    """Guarda un objeto serializable en caché con un TTL específico."""
    final_ttl = ttl if ttl is not None else DEFAULT_CACHE_TTL
    try:
        serialized_value = json.dumps(value)
        _cache[key] = (serialized_value, time.time(), final_ttl)
        logger.info(f"Successfully cached object with key: {key} (TTL: {final_ttl}s)")
    except TypeError as e:
        logger.warning(f"Could not serialize value for caching with key {key}. Error: {e}")

async def clear_cache():
    """Limpia toda la caché en memoria."""
    global _cache
    _cache = {}
    logger.info("In-memory cache has been cleared.")