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
from telegram_bot.config import settings

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Variable global para almacenar la única instancia del modelo de embeddings.
# Esto evita tener que recargar el modelo en cada llamada.
_embedding_model: Optional[VertexAIEmbeddings] = None


def initialize_embeddings() -> VertexAIEmbeddings:
    """
    Inicializa y devuelve el modelo de embeddings de Vertex AI.

    Utiliza un patrón singleton para asegurar que el modelo se cargue solo una vez.
    Lee la configuración (ID del proyecto, ubicación, nombre del modelo) desde
    el objeto `settings`. Realiza una prueba de conexión al inicializar.

    Raises:
        ValueError: Si la configuración necesaria de Google Cloud no está definida
                    o si el modelo no se puede inicializar por alguna razón.

    Returns:
        Una instancia funcional de VertexAIEmbeddings.
    """
    global _embedding_model

    # Si el modelo ya ha sido inicializado, simplemente lo devolvemos.
    if _embedding_model is not None:
        return _embedding_model

    logger.info(f"✨ Inicializando el modelo de embeddings de Vertex AI: '{settings.google_embedding_model_name}'...")

    # Validación crítica: Asegurarse de que tenemos los datos del proyecto.
    if not settings.google_project_id or not settings.google_project_location:
        logger.error("❌ La configuración de Google Cloud (GOOGLE_PROJECT_ID, GOOGLE_PROJECT_LOCATION) es incompleta.")
        raise ValueError("El ID del proyecto y la ubicación de Google Cloud deben estar definidos en la configuración.")

    try:
        # Instanciamos la clase de embeddings de Vertex AI con los parámetros de nuestra configuración.
        _embedding_model = VertexAIEmbeddings(
            model_name=settings.google_embedding_model_name,
            project=settings.google_project_id,
            location=settings.google_project_location,
        )

        # Realizamos una pequeña prueba de conexión para verificar que todo funciona.
        # Esto lanzará una excepción si hay problemas de autenticación o configuración.
        logger.debug("Realizando una prueba de embedding para verificar la conexión...")
        _embedding_model.embed_query("Prueba de inicialización de embeddings.")
        
        logger.info(f"✅ Modelo de embeddings de Vertex AI '{settings.google_embedding_model_name}' inicializado correctamente.")

    except Exception as e:
        logger.error(f"❌ Error fatal al inicializar el modelo de embeddings de Vertex AI: {e}", exc_info=True)
        # Relanzamos la excepción porque los embeddings son una parte crítica de la aplicación.
        # Si no funcionan, el sistema de memoria RAG estará roto.
        raise ValueError(f"No se pudo inicializar el modelo de embeddings de Vertex AI: {e}") from e

    if _embedding_model is None:
        # Esta es una comprobación de seguridad final. No debería ocurrir si el try/except funciona bien.
        raise ValueError("Falló la inicialización del modelo de embeddings por una razón desconocida.")

    return _embedding_model
