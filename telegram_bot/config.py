# telegram_bot/config.py

"""
Módulo de Configuración Central para la Aplicación.

Este módulo define y valida todas las configuraciones necesarias para que
los diferentes servicios (bot, servidor web, agente de IA) funcionen
correctamente. Utiliza una clase `Config` para cargar variables de entorno
desde un archivo `.env`, proporcionando valores por defecto y realizando
validaciones críticas al inicio.

Responsabilidades:
- Cargar secretos y configuraciones (API keys, tokens, URLs de bases de datos).
- Definir los nombres de los modelos de IA a utilizar (texto, embeddings, imágenes).
- Configurar parámetros de la aplicación (temperatura del LLM, IDs de admin, etc.).
- Validar que las configuraciones críticas estén presentes para evitar errores en tiempo de ejecución.
"""

import os
from dotenv import load_dotenv
import logging
from typing import Optional, List

# Carga las variables de entorno desde un archivo .env en la raíz del proyecto.
load_dotenv()

# Configuración básica de logging para este módulo.
logger = logging.getLogger(__name__)


class Config:
    """
    Clase que encapsula toda la configuración de la aplicación.
    Lee las variables de entorno y las expone como atributos de la clase.
    """
    def __init__(self):
        logger.info("⚙️ Inicializando la configuración de la aplicación...")

        # --- Configuración de Modelos de Lenguaje (Priorizando Google) ---
        # El LLM principal para el agente (texto y razonamiento).
        self.google_main_model_name: str = os.getenv("GOOGLE_MAIN_MODEL_NAME", "gemini-1.5-pro-latest")
        
        # El LLM para tareas rápidas y económicas como la sumarización.
        self.google_summary_model_name: str = os.getenv("GOOGLE_SUMMARY_MODEL_NAME", "gemini-1.5-flash-latest")
        
        # El modelo de Vertex AI para la generación de imágenes (ej. Imagen 3).
        self.google_image_generation_model_name: str = os.getenv("GOOGLE_IMAGE_GENERATION_MODEL_NAME", "imagegeneration@006")
        
        # ¡NUEVO! El modelo de Vertex AI para la generación de embeddings.
        self.google_embedding_model_name: str = os.getenv("GOOGLE_EMBEDDING_MODEL_NAME", "text-embedding-004")
        
        # Temperatura para la generación de texto del LLM principal.
        self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", 0.4))


        # --- Configuración de Telegram ---
        self.telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot_username: Optional[str] = os.getenv("BOT_USERNAME")
        
        # URL de la WebApp (el panel de control).
        self.webapp_url: Optional[str] = os.getenv("TELEGRAM_WEBAPP_URL")
        
        # IDs de administrador para comandos restringidos (separados por comas).
        admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
        self.admin_telegram_ids: List[int] = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]


        # --- API Keys y Credenciales de Servicios ---
        # Clave principal para las APIs de Google (GenAI Studio, etc.).
        self.google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        
        # ID del proyecto en Google Cloud (necesario para Vertex AI).
        self.google_project_id: Optional[str] = os.getenv("GOOGLE_PROJECT_ID")
        
        # Ubicación/Región del proyecto en Google Cloud (necesario para Vertex AI).
        self.google_project_location: Optional[str] = os.getenv("GOOGLE_PROJECT_LOCATION")
        
        # Clave para la herramienta de búsqueda web.
        self.brave_search_api_key: Optional[str] = os.getenv("BRAVE_SEARCH_API_KEY")


        # --- Configuración de la Base de Datos (PostgreSQL) ---
        self.postgres_user: Optional[str] = os.getenv("POSTGRES_USER")
        self.postgres_password: Optional[str] = os.getenv("POSTGRES_PASSWORD")
        self.postgres_db: Optional[str] = os.getenv("POSTGRES_DB")
        # URL de conexión completa, construida en docker-compose.yml, pero leída aquí para validación.
        self.database_url: Optional[str] = os.getenv("DATABASE_URL")
        
        
        # --- Configuración de RAG (Chunking) ---
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", 1000))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", 200))


        # --- Prompt de Sistema por Defecto ---
        self.default_system_prompt: str = os.getenv(
            "DEFAULT_SYSTEM_PROMPT",
            """
            (Aquí va tu prompt de personalidad detallado para Fito, con sus instrucciones,
            guía de uso de herramientas, etc. Lo he omitido por brevedad, pero
            debes pegar aquí el prompt completo que ya tienes).
            """
        )

        # Realizar validación al final de la inicialización.
        self._validate_config()
        logger.info("✅ Configuración de la aplicación inicializada y validada.")

    def _validate_config(self):
        """
        Valida que todas las variables de entorno críticas estén definidas.
        Lanza un `ValueError` si falta alguna configuración esencial.
        """
        # Esenciales para el funcionamiento básico.
        if not self.telegram_bot_token:
            raise ValueError("ERROR CRÍTICO: TELEGRAM_BOT_TOKEN no está definido en el archivo .env.")
        if not self.database_url:
            raise ValueError("ERROR CRÍTICO: DATABASE_URL no está definido. La persistencia no funcionará.")

        # Esenciales para la IA de Google.
        if not self.google_api_key:
            logger.warning("⚠️ ADVERTENCIA: GOOGLE_API_KEY no está definido. Los LLMs de GenAI Studio no funcionarán.")
        if not self.google_project_id:
             raise ValueError("ERROR CRÍTICO: GOOGLE_PROJECT_ID no está definido. Vertex AI no funcionará.")
        if not self.google_project_location:
             raise ValueError("ERROR CRÍTICO: GOOGLE_PROJECT_LOCATION no está definido. Vertex AI no funcionará.")

        # Opcionales, pero importantes para funcionalidades específicas.
        if not self.brave_search_api_key:
            logger.warning("⚠️ ADVERTENCIA: BRAVE_SEARCH_API_KEY no está definido. La búsqueda web no funcionará.")
        if not self.webapp_url:
            logger.warning("⚠️ ADVERTENCIA: TELEGRAM_WEBAPP_URL no está definido. El panel de control no será accesible.")
        if not self.admin_telegram_ids:
            logger.warning("⚠️ ADVERTENCIA: ADMIN_TELEGRAM_IDS no está configurado. Ningún usuario tendrá privilegios de administrador.")


# Crear una instancia única de la configuración para que sea importada por otros módulos.
settings = Config()