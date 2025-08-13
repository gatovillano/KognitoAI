# utils/embeddings.py

import logging
from core.config import settings # Importar settings desde core.config
from typing import Optional
import asyncio

# Importamos la clase específica de LangChain para los embeddings de Ollama.
from langchain_community.embeddings import OllamaEmbeddings

logger = logging.getLogger(__name__)

# Variable global para almacenar la única instancia del modelo de embeddings.
_embedding_model: Optional[OllamaEmbeddings] = None # Ajustar el tipo aquí


async def initialize_embeddings():
    """
    Inicializa la instancia global del modelo de embeddings desde Ollama de forma asíncrona.

    Esta función se llama una sola vez al arrancar el servicio central (`run_api.py`)
    y el servicio del bot de Telegram (`run_telegram_bot.py`).
    Crea la instancia del modelo y la almacena en una variable global para su
    reutilización, siguiendo un patrón Singleton.
    """
    global _embedding_model
    if _embedding_model is not None:
        logger.debug("El modelo de embeddings ya está inicializado.")
        return _embedding_model

    logger.info("✨ Inicializando el modelo de embeddings (usando OllamaEmbeddings directo a Ollama)...")

    if not settings.ollama_api_url:
        logger.error("❌ La variable de entorno OLLAMA_API_URL no está configurada para los embeddings.")
        raise ValueError("La variable de entorno OLLAMA_API_URL debe estar configurada para los embeddings.")

    # Asegurarse de que la URL no termine con barra para evitar dobles barras.
    ollama_base_url_cleaned = settings.ollama_api_url.rstrip('/')

    def _init_model():
        global _embedding_model
        # Usar el modelo de embedding y la URL base definidos en config
        _embedding_model = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=ollama_base_url_cleaned,
        )
        if _embedding_model is None:
            raise ValueError("No se pudo crear la instancia de OllamaEmbeddings.")
        # La prueba de inicialización síncrona se ha eliminado para acelerar el arranque.
        return _embedding_model

    try:
        # Ejecutar la inicialización en un hilo separado
        _embedding_model = await asyncio.to_thread(_init_model)
        logger.info(f"✅ Modelo de embeddings de Ollama '{_embedding_model.model}' inicializado correctamente con base URL: {ollama_base_url_cleaned}") # type: ignore
    except Exception as e:
        logger.error(f"❌ Error al inicializar el modelo de embeddings de Ollama: {e}", exc_info=True)
        
        raise

    if _embedding_model is None:
        raise ValueError("No se pudo inicializar ningún modelo de embeddings. Revisa tus configuraciones y dependencias.")

    # No es necesario devolver _embedding_model directamente aquí, ya que es global.
    # Pero si otras partes del código lo esperan como retorno, podrías mantenerlo.
    # Por consistencia con la función original, lo mantenemos.
    return _embedding_model


def get_embedding_model() -> Optional[OllamaEmbeddings]:
    """
    Devuelve la instancia global inicializada del modelo de embeddings.
    """
    return _embedding_model
