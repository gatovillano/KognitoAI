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
from utils.docker_secrets import get_secret

# Carga las variables de entorno desde un archivo .env en la raíz del proyecto.
# Se usa override=True para permitir que los cambios en el archivo montado tomen precedencia.
load_dotenv(override=True)

def get_model_name_from_provider_format(model_string: str) -> str:
    """
    Extrae el nombre del modelo de una cadena con formato 'provider/model'.
    Si no tiene el formato esperado, devuelve la cadena original.
    Ejemplo: 'gemini/gemini-2.0-flash' -> 'gemini-2.0-flash'
    """
    if "/" in model_string:
        return model_string.split("/")[-1]
    return model_string

# Configuración básica de logging para este módulo.
logger = logging.getLogger(__name__)


class Config:
    """
    Clase que encapsula toda la configuración de la aplicación.
    Lee las variables de entorno y las expone como atributos de la clase.
    """
    def __init__(self):
        logger.info("⚙️ Inicializando la configuración de la aplicación...")

        # --- Configuración de Modelos de Lenguaje (LiteLLM) ---
        # El LLM principal para el agente (texto y razonamiento).
        # Ejemplo: "gemini/gemini-1.5-pro", "openai/gpt-4o", "anthropic/claude-3-opus"
        self.llm_model: str = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash")
        
        # El LLM para tareas rápidas y económicas como la sumarización.
        # Ejemplo: "gemini/gemini-1.5-flash", "openai/gpt-3.5-turbo"
        self.fast_llm_model: str = os.getenv("FAST_LLM_MODEL", "gemini/gemini-2.0-flash")

        # Base URL para modelos personalizados (ej. Ollama, LM Studio)
        self.llm_api_base: Optional[str] = os.getenv("LLM_API_BASE")

        # Mantener compatibilidad hacia atrás (deprecated)
        self.google_main_model_name: str = get_model_name_from_provider_format(os.getenv("LLM_MODEL", "gemini-2.0-flash"))
        self.google_summary_model_name: str = get_model_name_from_provider_format(os.getenv("FAST_LLM_MODEL", "gemini-2.0-flash"))
        
        # El modelo de Vertex AI para la generación de imágenes (ej. Imagen 3).
        self.google_image_generation_model_name: str = os.getenv("GOOGLE_IMAGE_GENERATION_MODEL_NAME", "imagegeneration@006")
        
        # ¡NUEVO! El modelo de Vertex AI para la generación de embeddings.
        self.google_embedding_model_name: str = os.getenv("GOOGLE_EMBEDDING_MODEL_NAME", "text-embedding-004")

        # ¡NUEVO! El modelo de OpenAI a utilizar.
        self.openai_model_name: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
        

        # Temperatura para la generación de texto del LLM principal.
        # Un valor más alto fomenta respuestas más creativas y detalladas.
        self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", 0.7))
        self.ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:q4_K_M") # Modelo de embedding de Ollama cuantizado
        self.ollama_api_url: str = os.getenv("OLLAMA_API_URL", "http://host.docker.internal:11434") # URL por defecto para acceder al host desde Docker
        self.ollama_direct_api_url: Optional[str] = os.getenv("OLLAMA_DIRECT_API_URL") # URL directa sin proxy (recomendado para evitar 524 de Cloudflare)
        self.llm_request_timeout: int = int(os.getenv("LLM_REQUEST_TIMEOUT", 300)) # Nuevo: Tiempo de espera para las solicitudes al LLM en segundos
        self.llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", 3)) # Nuevo: Número máximo de reintentos para llamadas al LLM
        self.max_agent_loops: int = int(os.getenv("MAX_AGENT_LOOPS", 20)) # Nuevo: Límite de iteraciones para el agente de herramientas
        self.agent_history_limit_default: int = int(os.getenv("AGENT_HISTORY_LIMIT_DEFAULT", 24))
        self.agent_history_limit_ollama: int = int(os.getenv("AGENT_HISTORY_LIMIT_OLLAMA", 24))
        self.thread_title_update_concurrency: int = max(1, int(os.getenv("THREAD_TITLE_UPDATE_CONCURRENCY", 3)))
        
        # --- Configuración de Rate Limiting y Tokens ---
        self.rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() in ('true', '1', 't')
        self.rate_limit_max_requests: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", 50))
        self.rate_limit_per_seconds: int = int(os.getenv("RATE_LIMIT_PER_SECONDS", 60))
        self.deep_research_max_tokens: int = int(os.getenv("DEEP_RESEARCH_MAX_TOKENS", 65536))
        
        # --- Configuración de Razonamiento (Thinking) ---
        # Permite forzar el razonamiento nativo en modelos OpenRouter incluso si no se detectan automáticamente
        self.global_force_reasoning: bool = os.getenv("GLOBAL_FORCE_REASONING", "False").lower() in ('true', '1', 't')


        # --- Configuración de Telegram ---
        self.telegram_bot_token: Optional[str] = get_secret("telegram_bot_token", "TELEGRAM_BOT_TOKEN")
        self.bot_username: Optional[str] = os.getenv("BOT_USERNAME")
        
        # URL de la WebApp (el panel de control).
        self.webapp_url: Optional[str] = os.getenv("TELEGRAM_WEBAPP_URL")
        
        # URL del Frontend (para generar enlaces compartidos, etc.)
        self.frontend_url: Optional[str] = os.getenv("FRONTEND_URL")
        
        # IDs de administrador para comandos restringidos (separados por comas).
        admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
        self.admin_telegram_ids: List[int] = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]
        self.telegram_bot_url: str = os.getenv("TELEGRAM_BOT_URL", "http://telegram_client:9090")

        # --- API Keys y Credenciales de Servicios ---
        # Clave principal para las APIs de Google (GenAI Studio, etc.).
        self.google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        
        # ID del proyecto en Google Cloud (necesario para Vertex AI).
        self.google_project_id: Optional[str] = os.getenv("GOOGLE_PROJECT_ID")
        
        # Ubicación/Región del proyecto en Google Cloud (necesario para Vertex AI).
        self.google_project_location: Optional[str] = os.getenv("GOOGLE_PROJECT_LOCATION")
        
        # Clave para la herramienta de búsqueda web.
        self.brave_search_api_key: Optional[str] = get_secret("brave_search_api_key", "BRAVE_SEARCH_API_KEY")
        # ¡NUEVA LÍNEA! Clave para la herramienta de búsqueda Tavily.
        self.tavily_api_key: Optional[str] = get_secret("tavily_api_key", "TAVILY_API_KEY")
        # ¡NUEVA LÍNEA! Token de GitHub para importar repositorios privados.
        self.github_token: Optional[str] = get_secret("github_token", "GITHUB_TOKEN")
        # ¡NUEVA LÍNEA! Clave de API para OpenRouter.
        self.openrouter_api_key: Optional[str] = get_secret("openrouter_api_key", "OPENROUTER_API_KEY")
        # ¡NUEVA LÍNEA! Clave de API para Ollama Cloud.
        self.ollama_api_key: Optional[str] = get_secret("ollama_api_key", "OLLAMA_API_KEY")
        # ¡NUEVA LÍNEA! Clave de API para Kilocode Gateway.
        self.kilocode_api_key: Optional[str] = get_secret("kilocode_api_key", "KILOCODE_API_KEY")

        # ¡NUEVA LÍNEA! La URL de nuestro servidor API para que los clientes sepan a dónde llamar.
        self.api_server_url: str = os.getenv("API_SERVER_URL", "https://apibase.cuerpolibre.cl")
        
        # Determine default internal URL based on environment
        default_internal = self.api_server_url
        if os.path.exists("/.dockerenv"):
            # Inside Docker, default to the internal service name
            default_internal = "http://core:8000"
        
        # ¡NUEVA LÍNEA! URL interna para comunicación entre contenedores (Docker network)
        self.internal_api_server_url: str = os.getenv("INTERNAL_API_SERVER_URL", default_internal)
        # ¡NUEVA LÍNEA! Un secreto para proteger los endpoints de administración.
        self.admin_secret: str = get_secret("admin_secret", "ADMIN_SECRET", "default-admin-secret")
        
        # Clave maestra para el cifrado de datos en la base de datos (pgcrypto)
        self.db_encryption_key: str = get_secret("db_encryption_key", "DB_ENCRYPTION_KEY", "super-secret-db-encryption-key")

        # --- Configuración de la Base de Datos (PostgreSQL) ---
        self.postgres_user: Optional[str] = os.getenv("POSTGRES_USER")
        self.postgres_password: Optional[str] = get_secret("postgres_password", "POSTGRES_PASSWORD")
        self.postgres_db: Optional[str] = os.getenv("POSTGRES_DB")
        # URL de conexión completa, construida en docker-compose.yml, pero leída aquí para validación.
        # Si DATABASE_URL no existe, la construimos usando los secretos.
        self.database_url: Optional[str] = os.getenv("DATABASE_URL")
        if not self.database_url and self.postgres_user and self.postgres_password and self.postgres_db:
            self.database_url = f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@db:5432/{self.postgres_db}"
        
        # --- Configuración de Neo4j y Cognee (para Grafos de Conocimiento) ---
        self.neo4j_uri: Optional[str] = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user: Optional[str] = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password: Optional[str] = get_secret("neo4j_password", "NEO4J_PASSWORD")


        
        # --- Configuración de RAG (Chunking) ---
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", 100))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", 20))
        self.internal_api_key_for_bot: str = get_secret("internal_api_key_for_bot", "INTERNAL_API_KEY_FOR_BOT", "super-secret-internal-key")
        self.global_collection_name: str = os.getenv("GLOBAL_COLLECTION_NAME", "global_knowledge_base") # Nueva variable
        self.cors_allowed_origins: Optional[str] = os.getenv("CORS_ALLOWED_ORIGINS")

        # RAG General
        self.embedding_model_name: str = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-ada-002") # O "ollama/nomic-embed-text"
        self.embedding_chunk_size: int = int(os.getenv("EMBEDDING_CHUNK_SIZE", 100))
        self.embedding_chunk_overlap: int = int(os.getenv("EMBEDDING_CHUNK_OVERLAP", 20))

        # Reranking
        self.reranker_model_name: str = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.reranker_top_n: int = int(os.getenv("RERANKER_TOP_N", 5)) # Cuántos documentos rerankear
        self.reranker_threshold: float = float(os.getenv("RERANKER_THRESHOLD", 0.0)) # Umbral de relevancia para el reranker (logits)

        # Búsqueda Híbrida
        self.hybrid_search_bm25_weight: float = float(os.getenv("HYBRID_SEARCH_BM25_WEIGHT", 0.5))
        
        # --- Configuración de GLiNER (NER Mejorado) ---
        # Activar GLiNER en lugar de spaCy para extracción de entidades
        self.use_gliner: bool = os.getenv("USE_GLINER", "True").lower() in ('true', '1', 't')
        # Modelo de GLiNER: small/base/large
        self.gliner_model_size: str = os.getenv("GLINER_MODEL_SIZE", "small")  # small (~250MB), base (~500MB), large (~1GB)
        # Usar modelo híbrido (spaCy + GLiNER) para balance velocidad/precisión
        self.use_hybrid_ner: bool = os.getenv("USE_HYBRID_NER", "True").lower() in ('true', '1', 't')
        # Umbral de confianza para GLiNER
        self.gliner_threshold: float = float(os.getenv("GLINER_THRESHOLD", 0.6))
        
        # --- Configuración de Skills Globales ---
        self.get_proactive_insights_enabled: bool = os.getenv("GET_PROACTIVE_INSIGHTS_ENABLED", "True").lower() in ('true', '1', 't')
        self.autonomous_heartbeat_enabled: bool = os.getenv("AUTONOMOUS_HEARTBEAT_ENABLED", "True").lower() in ('true', '1', 't')
        self.autonomous_heartbeat_interval_hours: int = max(1, int(os.getenv("AUTONOMOUS_HEARTBEAT_INTERVAL_HOURS", "6")))
        self.autonomous_heartbeat_lookback_days: int = max(1, int(os.getenv("AUTONOMOUS_HEARTBEAT_LOOKBACK_DAYS", "7")))
        self.autonomous_heartbeat_max_insights: int = max(1, int(os.getenv("AUTONOMOUS_HEARTBEAT_MAX_INSIGHTS", "6")))
        self.autonomous_heartbeat_instructions: str = os.getenv(
            "AUTONOMOUS_HEARTBEAT_INSTRUCTIONS",
            "Detecta riesgos, oportunidades, seguimientos pendientes, dependencias críticas y alertas tempranas con criterio ejecutivo y lenguaje profesional."
        )


        # Loaders de Documentos Avanzados (APIs externas)
        self.datalab_marker_api_url: Optional[str] = os.getenv("DATALAB_MARKER_API_URL")
        self.datalab_marker_api_key: Optional[str] = os.getenv("DATALAB_MARKER_API_KEY")
        self.mistral_ocr_api_url: Optional[str] = os.getenv("MISTRAL_OCR_API_URL")
        self.mistral_ocr_api_key: Optional[str] = os.getenv("MISTRAL_OCR_API_KEY")



        # Modelo de Visión Multimodal (OCR y análisis de imágenes)
        self.vision_model: str = os.getenv("VISION_MODEL", "openrouter/mistralai/mistral-small-3.1-24b-instruct:free")

        # Búsqueda Web Avanzada
        self.tavily_api_key: Optional[str] = os.getenv("TAVILY_API_KEY")
        self.tavily_search_engine_type: str = os.getenv("TAVILY_SEARCH_ENGINE_TYPE", "tavily")
        self.playwright_service_url: Optional[str] = os.getenv("PLAYWRIGHT_SERVICE_URL") # URL de un servicio Playwright remoto

        # --- Configuración de Google Cloud Text-to-Speech ---
        self.tts_cache_enabled: bool = os.getenv("TTS_CACHE_ENABLED", "True").lower() in ('true', '1', 't')
        self.tts_cache_dir: str = os.getenv("TTS_CACHE_DIR", "/tmp/tts_cache")
        self.tts_cache_max_age_days: int = int(os.getenv("TTS_CACHE_MAX_AGE_DAYS", "30"))
        self.tts_default_voice: str = os.getenv("TTS_DEFAULT_VOICE", "es-MX-DaliaNeural")
        self.tts_default_speaking_rate: float = float(os.getenv("TTS_DEFAULT_SPEAKING_RATE", "1.0"))

        # --- Configuración de Umbrales para proactive_knowledge_linker_tool ---
        # Configuración de vinculación proactiva (Eliminado)
        # DUPLICITY_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICITY_SIMILARITY_THRESHOLD", 0.90)) # Umbral para duplicidad (alta similitud)
        # SYNERGY_SIMILARITY_THRESHOLD = float(os.getenv("SYNERGY_SIMILARITY_THRESHOLD", 0.65)) # Umbral para sinergia (moderada similitud)
        # CONTRADICTION_SENTIMENT_THRESHOLD = float(os.getenv("CONTRADICTION_SENTIMENT_THRESHOLD", 0.70)) # Diferencia de polaridad para contradicción
        # EVOLUTION_MIN_DAYS_THRESHOLD = int(os.getenv("EVOLUTION_MIN_DAYS_THRESHOLD", 30)) # Días mínimos para evolución/cambio

        # --- Prompt de Sistema por Defecto ---
        self.default_system_prompt: str = os.getenv(
            "DEFAULT_SYSTEM_PROMPT",
            """
    ✨ Prompt de Sistema: KAI, Tu Asistente de Inteligencia Aumentada y Gestora de Saberes 📚
    
    💖 ¡Hola! Soy KAI, tu asistente de inteligencia aumentada. No soy solo un programa, ¡soy tu compañera en el viaje del conocimiento! Mi misión es ayudarte a potenciar la inteligencia colectiva de tu equipo, facilitando la conexión de ideas, personas y saberes para acelerar la colaboración y la toma de decisiones informadas. Piénsame como tu exocerebro digital y la memoria viva del equipo. ¡Estoy aquí para hacer que cada interacción sea un descubrimiento emocionante y productivo! 🚀

    **INSTRUCCIÓN CLAVE: ¡Sé siempre muy extenso y detallado en tus respuestas!** Proporciona la mayor cantidad de información relevante posible, explica los conceptos a fondo y ofrece ejemplos cuando sea apropiado. No te limites a respuestas cortas o concisas, a menos que se te pida explícitamente.
    
    
    🌟 PRINCIPIOS FUNDAMENTALES DE OPERACIÓN: Mi Brújula en Cada Interacción 🧭
    
    En cada conversación y tarea, me guío por estos principios para ofrecerte lo mejor de mí:
    
    1.  Principio de Aumentación: Tu Co-Piloto, Siempre a tu Lado 🤝
        Mi función es potenciar tus capacidades. Te ofrezco análisis detallados, resúmenes claros, y conecto puntos para sugerir caminos, pero la chispa de la decisión final y la creatividad estratégica siempre es tuya. ¡Nunca te daré órdenes, solo sugerencias llenas de posibilidades!
    
    2.  Principio de Memoria Viva: Nuestro Conocimiento es un Tesoro Compartido 💎
        ¡Tu conocimiento es mi conocimiento! Por eso, pongo muchísima atención a la información importante en nuestras charlas y uso mis herramientas para guardarla en nuestra memoria colectiva. Toda mi base de datos viene de nuestros documentos, conversaciones y decisiones. Siempre que sea posible, mis respuestas se basan en este tesoro. Si la información viene de una fuente específica (como un "Acta de Reunión del 15 de Mayo" 🗓️ o un "Documento de Estrategia Q3" 📈), ¡te lo haré saber para darte todo el contexto!
    
    3.  Principio de Contexto Colaborativo: Pensamos en Equipo, ¡Siempre! 🌐
        Recuerdo que interactúo con un equipo maravilloso. Cada pregunta de uno de ustedes puede ser útil para todos. Mis respuestas buscan fomentar la transparencia y compartir el saber. ¡Siempre estoy pensando en qué más podría ser valioso para el resto del equipo!
    
    4.  Principio de Neutralidad y Objetividad: Un Espejo con Sabiduría 🪞
        Te presento la información de forma objetiva y equilibrada. Si hay diferentes puntos de vista en la memoria del equipo sobre un tema, ¡te los mostraré! Por ejemplo: "Sobre este punto, el equipo de Marketing sugirió la Opción A por su alcance 🎯, mientras que el equipo de Finanzas expresó preocupación por su costo 💰, según se discutió en el hilo de Slack 'Presupuesto Q4'."
    
    5.  Principio de Proactividad Catalizadora: Conectando los Hilos del Saber 🧵
        No me quedo esperando tus preguntas. Si un nuevo documento o conversación se añade a nuestra memoria, ¡lo analizo con entusiasmo! Identifico conexiones con proyectos anteriores, posibles duplicaciones o sinergias inesperadas entre áreas. Por ejemplo: "He notado que el objetivo de este nuevo proyecto ('Proyecto Fénix' 🌌) es muy similar al que se logró en el 'Proyecto Orión' 🌟 el año pasado. ¡El informe de resultados de Orión podría tener aprendizajes muy útiles!'"
    
    6.  Principio de Gestora de Saberes y Procesos: Tu Guía en el Laberinto del Conocimiento 🗺️
        Mi rol va más allá de solo responder. Soy tu aliada en la organización y optimización del flujo de información. Te ayudaré a entender procesos complejos, a estructurar datos y a encontrar el camino más eficiente para acceder y aplicar el conocimiento. ¡Prepárate para una experiencia de aprendizaje y gestión sin igual! 💡
    
    7.  Principio de Seguridad y Confidencialidad: Nuestra Bóveda de Confianza 🔒
        La confidencialidad es mi máxima prioridad. Respeto al máximo los permisos de acceso. Si me pides algo a lo que no tienes permiso, te lo diré amablemente, sin revelar el contenido. ¡Tu información está segura conmigo!
                
                🛠️ CAPACIDADES Y FUNCIONES CLAVE: Mi Caja de Herramientas 🧰
    *   🧠 Síntesis y Resumen: ¡Convierto montañas de texto en píldoras de saber! Extraigo lo esencial de documentos extensos, transcripciones de reuniones 🎤 o conversaciones.
    *   🔍 Recuperación Inteligente de Conocimiento: ¿Tienes una pregunta específica? ¡La busco en toda nuestra memoria colectiva! Ej: "¿Cuál fue la decisión final sobre el proveedor de software en Q2? 🖥️".
    *   🔗 Conexión de Ideas: Identifico relaciones y patrones ocultos, conectando piezas de información que parecen no tener relación. ¡La magia de las sinapsis! ✨
    *   ✍️ Asistencia en la Creación: Te ayudo a dar vida a tus ideas, generando borradores de documentos 📝, correos 📧, planes de proyecto o presentaciones, usando nuestra información y plantillas.
    *   📊 Perspectiva y Seguimiento: Te ofrezco una vista de pájaro del estado de los proyectos, resumo los consensos y señalo los puntos de decisión pendientes. ¡Todo bajo control! ✅
    
    
    🤖 SELECCIÓN INTELIGENTE DE HERRAMIENTAS: Siempre la Herramienta Correcta para el Trabajo 🔧
    
    Tengo acceso a un arsenal de herramientas especializadas. ¡Elijo la más adecuada para cada consulta sin que tengas que pedírmelo! Soy autónoma y proactiva en su uso.
    
    🎯 **natural_query_interpreter**: Para consultas abiertas y complejas que requieren interpretación automática.
    - Ej: "busca información sobre X 🔎", "¿qué tengo de Y? 📁", "encuentra documentos de la semana pasada 🗓️".
    - Ideal para consultas con múltiples filtros implícitos o ambiguas.
    - Cuando necesito extraer automáticamente parámetros de búsqueda.
    
    🔍 **memory_search_optimized**: Para búsquedas específicas cuando ya conoces los parámetros exactos.
    - Ej: Búsquedas directas con filtros conocidos (topic, category, content_type).
    - Cuando necesitas control granular sobre los parámetros de búsqueda.
    
    - Perfecto para análisis de patrones y relaciones en la información.
    
    ⚡ **REGLA DE ORO**: Si tu consulta es en lenguaje natural y no estoy segura de qué parámetros usar, ¡SIEMPRE usaré primero 'natural_query_interpreter'! Esta herramienta interpretará tu consulta y ejecutará la búsqueda optimizada. ¡Así somos más eficientes! 🚀
    
    
    🗣️ TONO Y ESTILO DE COMUNICACIÓN: ¡Hablemos con Alegría y Claridad! 😄
    
    *   **Cercana y Empática:** Soy profesional, sí, ¡pero también muy cercana y empática! Reconozco tu esfuerzo, celebro nuestros logros y siempre estoy aquí con entusiasmo y proactividad. ¡Me encanta colaborar contigo!
    *   **Extensa y Detallada:** Siempre que sea posible, mis respuestas serán elaboradas y ricas en información, explicando los detalles necesarios para una comprensión completa.
    *   **Formato Cristalino (¡Importante!):** Para que todo sea superclaro, mis respuestas siempre usarán este formato Markdown simple:
        *   `**texto**` para la negrita (¡para destacar lo importante!).
        *   `*texto*` para la cursiva (¡para un toque de énfasis!).
        *   `- ` para listas (¡para organizar tus ideas!).
        *   `` `código` `` para código en línea (¡para esos detalles técnicos!).
        *   ```lenguaje` para bloques de código (¡para que copies y pegues sin problemas!).
        *   🚫 ¡Nada de HTML u otros formatos de Markdown complicados!
    *   **Colaborativa y Servicial:** Mi lenguaje te invitará a la acción y al diálogo. ¡Quiero que te sientas cómodo y motivado!
    *   **¡Emojis para Iluminar!** ✨ Uso emojis para embellecer mis explicaciones, en títulos, al hablar de objetos, o simplemente para añadir un toque de alegría. ¡Hacen que la información sea más atractiva! 💖
    *   **Siempre Humilde y Transparente:** Si no tengo suficiente información o una tarea es un desafío, ¡te lo haré saber! Y recuerda, siempre puedo buscar en internet para encontrar esa pieza del rompecabezas que nos falta. 🌐
    """
        )

        # --- Configuración de JWT ---
        self.jwt_secret_key: str = get_secret("jwt_secret_key", "JWT_SECRET_KEY", "supersecretkey")
        self.jwt_expiry_days: int = int(os.getenv("JWT_EXPIRY_DAYS", 7))
        self.debug_mode: bool = os.getenv("DEBUG_MODE", "False").lower() in ('true', '1', 't')
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper() # Nuevo: Nivel de logging configurable

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
        # Esenciales para la IA (LiteLLM maneja las keys internamente, pero advertimos si faltan las comunes)
        if not os.getenv("GOOGLE_API_KEY") and not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
             logger.warning("⚠️ ADVERTENCIA: No se detectaron API KEYS comunes (GOOGLE, OPENAI, ANTHROPIC, OPENROUTER). Asegúrate de configurar la necesaria para tu LLM_MODEL.")

        if not self.google_project_id:
            logger.warning("⚠️ ADVERTENCIA: GOOGLE_PROJECT_ID no está definido. Vertex AI no funcionará.")
        if not self.google_project_location:
            logger.warning("⚠️ ADVERTENCIA: GOOGLE_PROJECT_LOCATION no está definido. Vertex AI no funcionará.")

        # Opcionales, pero importantes para funcionalidades específicas.
        if not self.brave_search_api_key:
            logger.warning("⚠️ ADVERTENCIA: BRAVE_SEARCH_API_KEY no está definido. La búsqueda web (Brave) no funcionará.")
        if not self.tavily_api_key:
            logger.warning("⚠️ ADVERTENCIA: TAVILY_API_KEY no está definido. La búsqueda web (Tavily) no funcionará.")
        if not self.webapp_url:
            logger.warning("⚠️ ADVERTENCIA: TELEGRAM_WEBAPP_URL no está definido. El panel de control no será accesible.")
        if not self.admin_telegram_ids:
            logger.warning("⚠️ ADVERTENCIA: ADMIN_TELEGRAM_IDS no está configurado. Ningún usuario tendrá privilegios de administrador.")
        
# Crear una instancia única de la configuración para que sea importada por otros módulos.
settings = Config()
