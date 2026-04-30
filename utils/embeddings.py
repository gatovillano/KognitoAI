# utils/embeddings.py

import logging
from typing import List, Optional
import asyncio
import uuid

from core.config import settings
from core.embedding_manager import EmbeddingService, EmbeddingServiceFactory
from core.database import SessionLocal # Necesario para obtener la configuración del usuario
from core.database import Account # Necesario para obtener la configuración del usuario

logger = logging.getLogger(__name__)

# Variable global para almacenar la única instancia del servicio de embeddings.
_embedding_service: Optional[EmbeddingService] = None


async def initialize_embeddings(account_id: Optional[uuid.UUID] = None):
    """
    Inicializa la instancia global del servicio de embeddings.

    Esta función se llama una sola vez al arrancar el servicio central (`run_api.py`)
    y el servicio del bot de Telegram (`run_telegram_bot.py`).
    Crea la instancia del servicio y la almacena en una variable global para su
    reutilización, siguiendo un patrón Singleton.
    """
    global _embedding_service
    if _embedding_service is not None:
        logger.debug("El servicio de embeddings ya está inicializado.")
        return _embedding_service

    logger.info("✨ Inicializando el servicio de embeddings...")

    # Obtener la configuración de embeddings del usuario si se proporciona account_id
    user_embedding_config = None
    if account_id:
        async with SessionLocal() as db:
            account = await db.get(Account, account_id)
            if account:
                user_embedding_config = {
                    "provider": account.embedding_provider,
                    "model": account.embedding_model,
                    "api_key_name": account.embedding_api_key_name,
                    "api_base": account.embedding_api_base,
                }
                logger.debug(f"Configuración de embeddings del usuario {account_id}: {user_embedding_config}")

    # Usar la configuración del usuario o valores por defecto
    provider = user_embedding_config.get("provider") if user_embedding_config else "kognito-internal"
    model = user_embedding_config.get("model") if user_embedding_config else None
    api_key_name = user_embedding_config.get("api_key_name") if user_embedding_config else None
    api_base = user_embedding_config.get("api_base") if user_embedding_config else None

    # INICIO CAMBIO: Inicialización síncrona/asíncrona manejada correctamente
    # EmbeddingServiceFactory.get_service es async, así que esto es correcto.
    try:
        _embedding_service = await EmbeddingServiceFactory.get_service(
            provider=provider,
            model_name=model,
            api_key_name=api_key_name,
            api_base=api_base,
            account_id=account_id
        )
        logger.info(f"✅ Servicio de embeddings '{provider}' inicializado correctamente.")
    except Exception as e:
        logger.error(f"❌ Error al inicializar el servicio de embeddings: {e}", exc_info=True)
        # Fallback a interno si falla
        # ...
        logger.warning("⚠️ La API arrancará sin servicio de embeddings. Revisa tus configuraciones y dependencias.")
        _embedding_service = None # Asegurarse de que sea None si falla la inicialización
        return None

    return _embedding_service


def get_embedding_service() -> Optional[EmbeddingService]:
    """
    Devuelve la instancia global inicializada del servicio de embeddings.
    """
    return _embedding_service


def get_embedding_model() -> Optional[EmbeddingService]:
    """
    Alias para get_embedding_service para compatibilidad con código existente.
    """
    return get_embedding_service()


async def aembed_query(query: str, account_id: Optional[uuid.UUID] = None) -> Optional[List[float]]:
    """
    Genera el embedding para una consulta dada utilizando el servicio de embeddings.
    """
    embedding_service = get_embedding_service()
    if not embedding_service:
        # Si el servicio no está inicializado, intentar inicializarlo con el account_id
        if account_id:
            embedding_service = await initialize_embeddings(account_id=account_id)
        if not embedding_service:
            logger.error("El servicio de embeddings no está inicializado y no se pudo inicializar con el account_id proporcionado.")
            return None
    
    try:
        return await embedding_service.aembed_query(query)
    except Exception as e:
        logger.error(f"❌ Error al generar embedding para la consulta: {e}", exc_info=True)
        return None

async def aembed_documents(texts: List[str], account_id: Optional[uuid.UUID] = None) -> Optional[List[List[float]]]:
    """
    Genera embeddings para una lista de textos utilizando el servicio de embeddings.
    """
    embedding_service = get_embedding_service()
    if not embedding_service:
        # Si el servicio no está inicializado, intentar inicializarlo con el account_id
        if account_id:
            embedding_service = await initialize_embeddings(account_id=account_id)
        if not embedding_service:
            logger.error("El servicio de embeddings no está inicializado y no se pudo inicializar con el account_id proporcionado.")
            return None
    
    try:
        return await embedding_service.aembed_documents(texts)
    except Exception as e:
        logger.error(f"❌ Error al generar embeddings para los documentos: {e}", exc_info=True)
        return None


# Cache simple para embeddings de consultas
_embedding_cache: dict = {}

async def get_cached_embedding(text: str, account_id: Optional[uuid.UUID] = None) -> Optional[List[float]]:
    """
    Genera el embedding para un texto con caché simple.
    
    Utiliza un caché en memoria para evitar regenerar embeddings para el mismo texto.
    """
    # Crear clave de caché
    cache_key = f"{text}:{account_id}"
    
    # Verificar si está en caché
    if cache_key in _embedding_cache:
        logger.debug(f"✅ Embedding encontrado en caché para texto: {text[:50]}...")
        return _embedding_cache[cache_key]
    
    # Generar nuevo embedding
    embedding = await aembed_query(text, account_id)
    
    if embedding:
        # Guardar en caché
        _embedding_cache[cache_key] = embedding
        logger.debug(f"✅ Embedding generado y cacheado para texto: {text[:50]}...")
    
    return embedding

# --- Adapter for LangChain ---
from langchain_core.embeddings import Embeddings

class KognitoEmbeddingAdapter(Embeddings):
    """
    Adaptador para hacer que el EmbeddingService sea compatible con LangChain.
    """
    def __init__(self, service: EmbeddingService):
        self.service = service

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Nota: Esto puede fallar si se llama desde un loop asíncrono.
        # Idealmente, usa métodos asíncronos siempre que sea posible.
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
             # Estamos en un loop corriendo, pero necesitamos bloquear.
             # Esto es un anti-patrón pero necesario si una lib sync de langchain lo llama.
             # Para ahora, lanzamos error avisando que usen async.
             raise NotImplementedError("Use aembed_documents instead inside an async loop/context")
        
        return asyncio.run(self.service.aembed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
             raise NotImplementedError("Use aembed_query instead inside an async loop/context")

        return asyncio.run(self.service.aembed_query(text))

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return await self.service.aembed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return await self.service.aembed_query(text)

async def get_text_embedding(text: str, account_id: Optional[uuid.UUID] = None) -> Optional[List[float]]:
    """
    Wrapper para generar el embedding de un texto. 
    Mantiene compatibilidad con el código que antes importaba esto desde proactive_knowledge_linker.
    """
    return await aembed_query(text, account_id)

def get_embedding_model() -> Optional[Embeddings]:
    """
    Devuelve una instancia compatible con LangChain (Embeddings) que usa el servicio global.
    """
    service = get_embedding_service()
    if not service:
        return None
    return KognitoEmbeddingAdapter(service)
