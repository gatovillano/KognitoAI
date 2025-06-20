# utils/embeddings.py

"""
Módulo de inicialización para los modelos de embeddings de Google Vertex AI.

Este módulo centraliza la creación de la instancia del modelo de embeddings,
asegurando que se inicialice una sola vez (patrón Singleton) y esté disponible
para toda la aplicación, principalmente para el `memory_manager` que se encarga
de la lógica RAG (Retrieval-Augmented Generation).

En esta nueva arquitectura, se migra de Ollama a VertexAIEmbeddings para
consolidar todos los servicios de IA bajo el ecosistema de Google Cloud.
Esto proporciona un rendimiento, escalabilidad y gestión unificados.
La función `initialize_embeddings` lee la configuración necesaria desde el
módulo `telegram_bot.config` para conectarse al modelo correcto.
"""

import logging
from typing import Optional

# Importamos la clase específica de LangChain para los embeddings de Vertex AI.
from langchain_google_vertexai import VertexAIEmbeddings

# Importamos nuestro objeto de configuración centralizado.
from core.config import settings

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Variable global para almacenar la única instancia del modelo de embeddings.
# Esto evita tener que recargar el modelo en cada llamada.
_embedding_model: Optional[VertexAIEmbeddings] = None


def initialize_embeddings():
    """
    Inicializa la instancia global del modelo de embeddings desde Vertex AI.

    Esta función se llama una sola vez al arrancar el `web_server`. Crea la
    instancia del modelo y la almacena en una variable global para su
    reutilización, siguiendo un patrón Singleton.
    """
    global _embedding_model
    if _embedding_model is not None:
        logger.debug("El modelo de embeddings ya está inicializado.")
        return

    try:
        logger.info(f"🛠️ Inicializando modelo de embeddings de Vertex AI ({settings.google_embedding_model_name})...")
        
        # 1. Crear la instancia del modelo.
        # La propia creación de la instancia ya valida las credenciales y la configuración.
        embedding_model_instance = VertexAIEmbeddings(
            model_name=settings.google_embedding_model_name,
            project=settings.google_project_id,
            location=settings.google_project_location,
        )

        # 2. ¡CORREGIDO! Asignar la instancia a la variable global DESPUÉS de crearla.
        _embedding_model = embedding_model_instance
        
        logger.info("✅ Modelo de embeddings de Vertex AI inicializado exitosamente.")

    except Exception as e:
        # Si la inicialización falla, _embedding_model seguirá siendo None.
        logger.error(f"❌ FATAL: Fallo al inicializar el modelo de embeddings de Vertex AI: {e}", exc_info=True)
        # No relanzamos la excepción para permitir que el resto de la app intente arrancar,
        # pero la función `embed_text` lanzará un error si se intenta usar.
