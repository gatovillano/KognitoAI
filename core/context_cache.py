# core/context_cache.py

import asyncio
import time
from typing import Dict, Optional, Tuple
import hashlib

# Cache simple en memoria (usar Redis en producción)
_context_cache: Dict[str, Tuple[str, float]] = {}
CACHE_TTL = 300  # 5 minutos

def _get_cache_key(account_id: str, user_message: str, workspace_id: Optional[str]) -> str:
    """Genera clave de cache basada en parámetros."""
    message_hash = hashlib.md5(user_message.encode()).hexdigest()[:8]
    return f"{account_id}:{workspace_id or 'none'}:{message_hash}"

async def get_cached_context(account_id: str, user_message: str, workspace_id: Optional[str] = None) -> Optional[str]:
    """Recupera contexto de cache si existe y es válido."""
    cache_key = _get_cache_key(account_id, user_message, workspace_id)
    
    if cache_key in _context_cache:
        context, timestamp = _context_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return context
        else:
            # Cache expirado
            del _context_cache[cache_key]
    
    return None

async def cache_context(account_id: str, user_message: str, context: str, workspace_id: Optional[str] = None):
    """Guarda contexto en cache."""
    cache_key = _get_cache_key(account_id, user_message, workspace_id)
    _context_cache[cache_key] = (context, time.time())

async def clear_user_cache(account_id: str):
    """Limpia cache de un usuario específico."""
    keys_to_remove = [k for k in _context_cache.keys() if k.startswith(f"{account_id}:")]
    for key in keys_to_remove:
        del _context_cache[key]
