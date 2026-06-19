"""
Gestor de caché en memoria para resultados de correo.
 Reduce llamadas a IMAP y mejora rendimiento.
"""

import time
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Entrada individual de caché."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    ttl: int = 300  # 5 minutos por defecto
    hits: int = 0
    
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def is_valid(self) -> bool:
        """Verifica si la entrada es válida (no expirada)."""
        return not self.is_expired()
    
    def touch(self) -> None:
        """Registra un acceso (hit)."""
        self.hits += 1

class EmailCache:
    """Caché en memoria con TTL y límite de tamaño."""
    
    def __init__(self, max_entries: int = 1000, default_ttl: int = 300):
        """
        Inicializa el caché.
        
        Args:
            max_entries: Máximo número de entradas antes de limpiar las menos usadas
            default_ttl: Tiempo de vida por defecto en segundos
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def _make_key(
        self, 
        operation: str, 
        email: str, 
        folder: str = "INBOX",
        **kwargs
    ) -> str:
        """Genera clave única para la caché."""
        # Crear string determinístico
        key_parts = [
            operation,
            email.lower(),
            folder.lower()
        ]
        
        # Agregar kwargs ordenados
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")
        
        key_string = "|".join(key_parts)
        
        # Hash para evitar claves muy largas
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get(
        self, 
        operation: str, 
        email: str, 
        folder: str = "INBOX",
        **kwargs
    ) -> Optional[Any]:
        """Obtiene valor de caché si existe y es válido."""
        key = self._make_key(operation, email, folder, **kwargs)
        
        entry = self._cache.get(key)
        
        if entry is None:
            self._misses += 1
            logger.debug(f"Cache MISS: {operation} {email} {folder}")
            return None
        
        if entry.is_expired():
            self._misses += 1
            logger.debug(f"Cache EXPIRED: {operation} {email} {folder}")
            del self._cache[key]
            return None
        
        # Hit!
        entry.touch()
        self._hits += 1
        logger.debug(f"Cache HIT: {operation} {email} {folder} (hits: {entry.hits})")
        return entry.value
    
    def set(
        self, 
        operation: str, 
        email: str, 
        value: Any,
        folder: str = "INBOX",
        ttl: Optional[int] = None,
        **kwargs
    ) -> None:
        """Almacena valor en caché."""
        key = self._make_key(operation, email, folder, **kwargs)
        
        # Limpiar entradas expiradas antes de agregar
        self._cleanup_expired()
        
        # Si estamos llenos, eliminar las menos usadas
        if len(self._cache) >= self.max_entries:
            self._evict_lru()
        
        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl or self.default_ttl
        )
        
        self._cache[key] = entry
        logger.debug(f"Cache SET: {operation} {email} {folder}")
    
    def invalidate(
        self, 
        operation: str, 
        email: str, 
        folder: str = "INBOX",
        **kwargs
    ) -> bool:
        """Invalida una entrada específica de caché."""
        key = self._make_key(operation, email, folder, **kwargs)
        
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache INVALIDATED: {operation} {email} {folder}")
            return True
        
        return False
    
    def invalidate_all(self, email: str) -> int:
        """Invalida todas las entradas de un email específico."""
        keys_to_remove = [
            k for k in self._cache.keys()
            if email.lower() in k
        ]
        
        for key in keys_to_remove:
            del self._cache[key]
        
        logger.info(f"Invalidadas {len(keys_to_remove)} entradas para {email}")
        return len(keys_to_remove)
    
    def clear(self) -> None:
        """Limpia toda la caché."""
        count = len(self._cache)
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info(f"Caché limpiada: {count} entradas eliminadas")
    
    def _cleanup_expired(self) -> int:
        """Elimina entradas expiradas."""
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Limpiadas {len(expired_keys)} entradas expiradas")
        
        return len(expired_keys)
    
    def _evict_lru(self) -> int:
        """Elimina las entradas menos usadas (LRU)."""
        if not self._cache:
            return 0
        
        # Ordenar por hits (menos usadas primero)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].hits
        )
        
        # Eliminar el 10% menos usado
        to_remove = max(1, len(sorted_entries) // 10)
        
        for key, _ in sorted_entries[:to_remove]:
            del self._cache[key]
        
        logger.debug(f"Cache LRU: eliminadas {to_remove} entradas menos usadas")
        return to_remove
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de uso de caché."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        expired = sum(1 for e in self._cache.values() if e.is_expired())
        
        return {
            "entries": len(self._cache),
            "expired_entries": expired,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def __len__(self) -> int:
        return len(self._cache)
    
    def __repr__(self) -> str:
        return f"EmailCache(entries={len(self._cache)}, hits={self._hits}, misses={self._misses})"


# Instancia global de caché (por defecto)
_default_cache = EmailCache()

def get_default_cache() -> EmailCache:
    """Obtiene la instancia de caché por defecto."""
    return _default_cache
