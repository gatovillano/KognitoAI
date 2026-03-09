# core/llm_manager.py

import logging
import time
import asyncio
import os
import torch # Importar torch
from collections import deque
from threading import Lock
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import litellm # Importar litellm
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.rate_limiters import BaseRateLimiter
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import BaseMessage, HumanMessage # Importar BaseMessage y HumanMessage
from core.config import settings
from core.database import SessionLocal, Account, UserSecret
from core.repositories.secret_repository import SecretRepository
import uuid

# Asegúrate de que litellm elimine parámetros no soportados globalmente
litellm.drop_params = True

# Disable debug mode for LiteLLM to reduce logging
litellm.set_verbose = False
logging.getLogger('LiteLLM').setLevel(logging.WARNING)
logging.getLogger('LiteLLM/UniversalDeployer').setLevel(logging.WARNING)
# Silenciar los logs de "Provider List" que a veces salen por stdout
import os
os.environ["LITELLM_LOG"] = "ERROR"

# --- Configuración del Logger ---
from core.utils.logging_utils import AgentLogger
logger = AgentLogger(__name__)

# --- Rate Limiter Implementation ---

class RateLimiter(BaseRateLimiter):
    """
    A thread-safe, asyncio-compatible rate limiter that adheres to the interface
    expected by LangChain's `rate_limiter` parameter. It ensures that no more
    than a specified number of requests are made per minute.
    """
    _instance = None
    _lock = Lock()
    
    max_requests: int
    per_seconds: int
    request_timestamps: deque

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.max_requests = kwargs.get('max_requests', settings.rate_limit_max_requests)
                cls._instance.per_seconds = kwargs.get('per_seconds', settings.rate_limit_per_seconds)
                cls._instance.request_timestamps = deque()
                logger.info(
                    f"RateLimiter: {cls._instance.max_requests} req / {cls._instance.per_seconds}s | Activo: {settings.rate_limit_enabled}"
                )
            return cls._instance

    def __init__(self, max_requests: int = 20, per_seconds: int = 60):
        # Initialize attributes for pylint/pylance
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.request_timestamps = deque()
        pass # State is managed by the singleton __new__

    async def aacquire(self, **kwargs: Any) -> None:
        """
        Asynchronously waits if the rate limit is about to be exceeded.
        This method's signature matches what LangChain's async LLM calls expect.
        """
        if not settings.rate_limit_enabled:
            return

        with self._lock:
            now = time.monotonic()
            # Prune old timestamps
            while self.request_timestamps and self.request_timestamps[0] <= now - self.per_seconds:
                self.request_timestamps.popleft()

            wait_time = 0
            if len(self.request_timestamps) >= self.max_requests:
                oldest_request_time = self.request_timestamps[0]
                time_since_oldest = now - oldest_request_time
                wait_time = self.per_seconds - time_since_oldest

                if wait_time > 0:
                    logger.warning(
                        f"Rate limit of {self.max_requests}/{self.per_seconds}s reached. "
                        f"Async waiting for {wait_time:.2f} seconds."
                    )
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        with self._lock:
            self.request_timestamps.append(time.monotonic())

    def acquire(self, **kwargs: Any) -> None:
        """
        Synchronously waits if the rate limit is about to be exceeded.
        This method's signature matches what LangChain's sync LLM calls expect.
        """
        if not settings.rate_limit_enabled:
            return

        with self._lock:
            now = time.monotonic()
            while self.request_timestamps and self.request_timestamps[0] <= now - self.per_seconds:
                self.request_timestamps.popleft()

            wait_time = 0
            if len(self.request_timestamps) >= self.max_requests:
                oldest_request_time = self.request_timestamps[0]
                time_since_oldest = now - oldest_request_time
                wait_time = self.per_seconds - time_since_oldest
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Sync waiting for {wait_time:.2f}s.")
                    time.sleep(wait_time)
            
            self.request_timestamps.append(time.monotonic())

# Initialize the global rate limiter
gemini_rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_max_requests,
    per_seconds=settings.rate_limit_per_seconds
)

# --- Global LLM Instances ---
_main_agent_llm_instance: Optional[ChatLiteLLM] = None
_fast_task_llm_instance: Optional[ChatLiteLLM] = None
_vision_llm_instance: Optional[ChatLiteLLM] = None

def get_main_llm() -> Optional[ChatLiteLLM]: # More specific return type
    """Returns the initialized main agent LLM instance."""
    return _main_agent_llm_instance

def get_fast_llm() -> Optional[ChatLiteLLM]: # More specific return type
    """Returns the initialized fast task LLM instance, or the main one as a fallback."""
    return _fast_task_llm_instance or _main_agent_llm_instance

def get_vision_llm() -> Optional[ChatLiteLLM]:
    """Returns the initialized vision LLM instance for multimodal tasks."""
    return _vision_llm_instance or _main_agent_llm_instance


def normalize_openrouter_model_name(model_name: str) -> str:
    """
    Normaliza el nombre del modelo para OpenRouter.
    
    Asegura que el modelo tenga el formato 'organizacion/modelo' requerido por OpenRouter.
    Si es un modelo nativo (aurora, pony), le añade el prefijo 'openrouter/'.
    """
    # Si ya tiene el prefijo de proveedor (ej: 'openai/' o 'openrouter/'), no tocarlo
    if "/" in model_name and not model_name.startswith("openrouter/"):
        # Pero si el usuario puso algo como 'openai/gpt-4o' y estamos en OpenRouter,
        # lo dejamos pasar ya que OpenRouter acepta IDs de otros proveedores.
        return model_name

    native_models = ["aurora-alpha", "pony-alpha", "step-3.5-flash:free"]
    
    model_lower = model_name.lower()
    # Si es un modelo nativo sin prefijo, añadírselo para tener el ID completo de OpenRouter
    if any(native in model_lower for native in native_models) and not "/" in model_name:
        return f"openrouter/{model_name}"
        
    return model_name


def apply_openrouter_model_specific_logic(model_name: str, llm_kwargs: dict):
    """
    Aplica configuraciones específicas según el modelo para OpenRouter.
    Habilita el razonamiento nativo (Thinking/Reasoning) siempre que sea posible.
    """
    if "extra_body" not in llm_kwargs:
        llm_kwargs["extra_body"] = {}
    
    model_lower = model_name.lower()
    
    # 1. Detección de modelos de razonamiento (Reasoning/Thinking)
    # Solo habilitamos si el modelo es específicamente de razonamiento (o1, deepseek-r1)
    # o si se solicita explícitamente mediante una flag del sistema (que por defecto es False).
    reasoning_models = ["-r1", "o1-", "o3-", "deepseek-r1", "thinking-cloud"]
    
    is_reasoning_model = any(x in model_lower for x in reasoning_models)
    
    if is_reasoning_model or settings.global_force_reasoning:
        # Habilitamos el rastro de razonamiento nativo de OpenRouter
        llm_kwargs["extra_body"]["include_reasoning"] = True
        logger.info(f"🧠 Habilitando razonamiento nativo (Force: {settings.global_force_reasoning}) para: {model_name}")
    else:
        # Por defecto, NO incluir razonamiento para evitar romper modos JSON y estructurados
        # OpenRouter recomienda mandar False si queremos asegurar que no se cuele texto de razonamiento
        llm_kwargs["extra_body"]["include_reasoning"] = False
        logger.info(f"🧠 Razonamiento nativo DESHABILITADO para: {model_name} (estabilidad JSON)")

    # 2. Adaptadores específicos para plataformas de inferencia
    # Algunos modelos requieren flags específicos para mostrar el bloque de pensamiento
    if "glm-4.5-air" in model_lower or "glm-4" in model_lower:
        # GLM suele usar el campo 'thinking'
        llm_kwargs["extra_body"]["thinking"] = {"type": "enabled"}
        
    elif "gpt-oss-120b" in model_lower:
        # Este modelo es propenso a errores si enviamos tipos complejos, usamos solo flags simples
        llm_kwargs["extra_body"]["reasoning"] = True

    # 3. Limpieza de seguridad
    # Si el extra_body está vacío, lo eliminamos para evitar peticiones mal formadas
    if not llm_kwargs["extra_body"]:
        del llm_kwargs["extra_body"]
    else:
        # Log para depuración de los parámetros enviados a OpenRouter
        logger.info(f"⚙️ OpenRouter extra_body final: {llm_kwargs['extra_body']}")

async def get_llm_for_user(account_id: str, purpose: str = "main") -> Optional[ChatLiteLLM]:
    """
    Returns a customized LLM instance for a specific user based on their settings.
    If the user has no custom settings, returns the global default instance.
    """
    if not account_id:
        return get_main_llm()

    try:
        async with SessionLocal() as db:
            # 1. Obtener ajustes del usuario
            account = await db.get(Account, uuid.UUID(account_id))
            if not account:
                return get_main_llm()

            # Determinar qué modelo y proveedor usar
            model_target = account.llm_model
            provider_target = account.llm_provider

            if purpose == "fast":
                if account.fast_llm_model:
                    model_target = account.fast_llm_model
                if account.fast_llm_provider:
                    provider_target = account.fast_llm_provider
            elif purpose == "vision":
                if account.vision_llm_model:
                    model_target = account.vision_llm_model
                if account.vision_llm_provider:
                    provider_target = account.vision_llm_provider

            # Si el usuario no tiene proveedor o modelo configurado, usar global
            if not provider_target or not model_target:
                if purpose == "fast": return get_fast_llm()
                if purpose == "vision": return get_vision_llm()
                return get_main_llm()

            # 2. Obtener API Key de los secretos
            repo = SecretRepository(db)
            provider_env_name = provider_target.upper()
            key_name = f"{provider_env_name}_API_KEY"
            api_key = await repo.get_decrypted_secret(account.id, key_name)

            # Si no hay API key y el proveedor requiere una (casi todos menos ollama), 
            # podríamos intentar usar la global o fallar. Usaremos la global como fallback.
            
            # 3. Construir instancia personalizada
            llm_kwargs = {
                "model_name": model_target,
                "temperature": account.llm_temperature if account.llm_temperature is not None else settings.llm_temperature,
                "streaming": True,
                "verbose": False,
                "max_retries": 0,
                "rate_limiter": gemini_rate_limiter,
                "max_tokens": settings.deep_research_max_tokens,
                "timeout": settings.llm_request_timeout,
            }

            if api_key:
                llm_kwargs["api_key"] = api_key
            
            # --- FIX: Manejo específico para OpenRouter ---
            if provider_target.lower() == "openrouter":
                llm_kwargs["api_base"] = "https://openrouter.ai/api/v1"
                
                # Paso 1: Obtener el ID real del modelo (ej: 'openrouter/aurora-alpha' o 'anthropic/claude-3')
                actual_id = normalize_openrouter_model_name(model_target)
                
                # Paso 2: Para LiteLLM, el formato final debe ser 'openrouter/ID_REAL'
                # Si actual_id ya empieza por openrouter/, no lo duplicamos
                if actual_id.startswith("openrouter/"):
                    llm_kwargs["model_name"] = actual_id
                else:
                    llm_kwargs["model_name"] = f"openrouter/{actual_id}"
                
                # Forzar el proveedor para evitar errores internos de LiteLLM
                llm_kwargs["custom_llm_provider"] = "openrouter"
                
                # Aplicar lógica de adaptador universal según el modelo
                apply_openrouter_model_specific_logic(actual_id, llm_kwargs)
                
                # Headers recomendados por OpenRouter para mejor soporte y visibilidad
                if "extra_headers" not in llm_kwargs:
                    llm_kwargs["extra_headers"] = {}
                llm_kwargs["extra_headers"]["HTTP-Referer"] = "https://kognito.ai" # Identificador de la app
                llm_kwargs["extra_headers"]["X-Title"] = "Kognito AI"
                
                logger.info(f"OpenRouter: {llm_kwargs['model_name']} (Con adaptadores y headers)")
            elif account.llm_api_base and ("http" in account.llm_api_base):
                # Solo usar api_base si parece una URL válida (contiene http)
                # Esto previene el uso de valores accidentales como correos electrónicos
                llm_kwargs["api_base"] = account.llm_api_base
            elif "ollama" in provider_target.lower():
                # Fallback para ollama si no se especifica base
                llm_kwargs["api_base"] = "http://localhost:11434"

            # Configuraciones específicas por proveedor (LiteLLM)
            if "gemini" in model_target.lower() and account.llm_provider.lower() != "openrouter":
                llm_kwargs["provider"] = "google_ai_studio"

            logger.info(f"🛠️ Creando LLM personalizado para usuario {account_id}: {llm_kwargs['model_name']} ({account.llm_provider})")
            
            # Nota: ChatLiteLLM pasará extra_body a la API de OpenRouter
            return ChatLiteLLM(**llm_kwargs)

    except Exception as e:
        logger.error(f"❌ Error al obtener LLM personalizado para {account_id}: {e}", exc_info=True)
        return get_main_llm() # Fallback a global en caso de error

def get_fallback_llm() -> Optional[ChatLiteLLM]:
    """Returns a fallback LLM instance using a different provider when OpenRouter fails."""
    try:
        # Try to use Gemini as fallback if the main model is OpenRouter
        if "openrouter" in settings.llm_model.lower():
            logger.info("🔄 Switching to Gemini as fallback for OpenRouter context limit issues.")
            fallback_llm = ChatLiteLLM(
                model_name="gemini/gemini-2.0-flash-exp",
                temperature=0.0,
                streaming=True,
                verbose=False,
                max_retries=0,
                rate_limiter=gemini_rate_limiter,
            )
            return fallback_llm
        else:
            # If main model is not OpenRouter, use it as fallback
            return get_main_llm()
    except Exception as e:
        logger.error(f"❌ Failed to create fallback LLM: {e}")
        return None

async def _invoke_llm_cached(llm: BaseLanguageModel, prompt: Union[str, List[BaseMessage]]) -> Any:
    """Función wrapper para invocar el LLM, asegurando el formato de mensaje correcto."""
    if isinstance(prompt, str):
        # Envuelve el prompt de cadena en un HumanMessage para cumplir con las expectativas del modelo
        messages = [HumanMessage(content=prompt)]
    elif isinstance(prompt, list) and all(isinstance(msg, BaseMessage) for msg in prompt):
        # Si ya es una lista de BaseMessage, úsalo directamente
        messages = prompt
    else:
        raise TypeError("El prompt debe ser una cadena o una lista de objetos BaseMessage.")
    
    return await llm.ainvoke(messages)

async def initialize_llms():
    """
    Initializes the global instances of the LLMs (main and fast task)
    with a compliant rate limiter.
    """
    global _main_agent_llm_instance, _fast_task_llm_instance, _vision_llm_instance
    
    # Detectar si hay una GPU disponible
    use_gpu = torch.cuda.is_available()
    if use_gpu:
        logger.info("✅ GPU detectada. Los modelos se cargarán en la GPU (cuda).")
    else:
        logger.warning("No se detectó GPU. Cargando modelos en CPU.")

    try:
        logger.info(f"Inicializando LLM Principal: {settings.llm_model}")
        
        llm_kwargs = {
            "model_name": settings.llm_model,
            "temperature": settings.llm_temperature,
            "streaming": True,
            "verbose": False,
            "max_retries": 0, # We handle rate limiting, so disable litellm's retries for this
            "rate_limiter": gemini_rate_limiter, # Pass the compliant rate limiter
            "max_tokens": settings.deep_research_max_tokens, # Allow for massive reports
            "timeout": settings.llm_request_timeout,
        }
        
        if use_gpu:
            llm_kwargs["device"] = "cuda"
            llm_kwargs["force_redownload"] = True # Forzar la descarga para asegurar la compatibilidad de la GPU

        if settings.llm_api_base:
            llm_kwargs["api_base"] = settings.llm_api_base
        
        # Configurar proveedor específico según el formato del modelo
        model_lower = settings.llm_model.lower()
        
        if "openrouter" in model_lower:
            logger.info("🔧 Applying OpenRouter specific config for main LLM.")
            apply_openrouter_model_specific_logic(settings.llm_model, llm_kwargs)
        elif "anthropic" in model_lower:
            logger.info("🔧 Applying Anthropic specific config.")
            llm_kwargs["provider"] = "anthropic"
        elif "groq" in model_lower:
            logger.info("🔧 Applying Groq specific config.")
            llm_kwargs["provider"] = "groq"
        elif "deepseek" in model_lower:
            logger.info("🔧 Applying DeepSeek specific config.")
            llm_kwargs["provider"] = "deepseek"
        elif "mistral" in model_lower:
            logger.info("🔧 Applying Mistral specific config.")
            llm_kwargs["provider"] = "mistral"
        elif "cerebras" in model_lower:
            logger.info("🔧 Applying Cerebras specific config.")
            llm_kwargs["provider"] = "cerebras"
        elif "vertex" in model_lower or "google_vertex" in model_lower:
            logger.info("🔧 Applying Vertex AI specific config.")
            llm_kwargs["provider"] = "vertex_ai"
            if settings.google_project_id:
                llm_kwargs["vertex_project_id"] = settings.google_project_id
        elif "azure" in model_lower:
            logger.info("🔧 Applying Azure OpenAI specific config.")
            llm_kwargs["provider"] = "azure"
        elif "gemini" in model_lower:
            logger.info("🔧 Applying Gemini specific config.")
            llm_kwargs["provider"] = "google_ai_studio"
        elif "openai" in model_lower or "gpt" in model_lower:
            logger.info("🔧 Applying OpenAI/GPT specific config.")

        main_llm = ChatLiteLLM(**llm_kwargs)
        _main_agent_llm_instance = main_llm
        logger.info("Modelo LLM Principal listo.")
    except Exception as e:
        logger.error(f"❌ FATAL: Failed to initialize the main LLM: {e}", exc_info=True)
        raise

    try:
        logger.info(f"Inicializando LLM Rápido: {settings.fast_llm_model}")
        fast_llm_kwargs = {
            "model_name": settings.fast_llm_model,
            "temperature": 0.0,
            "streaming": True,
            "verbose": False,
            "max_retries": 0,
            "rate_limiter": gemini_rate_limiter, # Use the same rate limiter instance
            "timeout": settings.llm_request_timeout,
        }

        if use_gpu:
            fast_llm_kwargs["device"] = "cuda"

        if settings.llm_api_base:
            fast_llm_kwargs["api_base"] = settings.llm_api_base
        
        # Configurar proveedor específico según el formato del modelo
        fast_model_lower = settings.fast_llm_model.lower()
        
        if "openrouter" in fast_model_lower:
            logger.info("🔧 Applying OpenRouter specific config for fast LLM.")
            apply_openrouter_model_specific_logic(settings.fast_llm_model, fast_llm_kwargs)
        elif "anthropic" in fast_model_lower:
            logger.info("🔧 Applying Anthropic specific config for fast LLM.")
            fast_llm_kwargs["provider"] = "anthropic"
        elif "groq" in fast_model_lower:
            logger.info("🔧 Applying Groq specific config for fast LLM.")
            fast_llm_kwargs["provider"] = "groq"
        elif "deepseek" in fast_model_lower:
            logger.info("🔧 Applying DeepSeek specific config for fast LLM.")
            fast_llm_kwargs["provider"] = "deepseek"
        elif "mistral" in fast_model_lower:
            logger.info("🔧 Applying Mistral specific config for fast LLM.")
            fast_llm_kwargs["provider"] = "mistral"
        elif "gemini" in fast_model_lower:
            logger.info("🔧 Applying Gemini specific config for fast LLM.")
            fast_llm_kwargs["provider"] = "google_ai_studio"
        elif "openai" in fast_model_lower or "gpt" in fast_model_lower:
            logger.info("🔧 Applying OpenAI/GPT specific config for fast LLM.")

        fast_llm = ChatLiteLLM(**fast_llm_kwargs)
        _fast_task_llm_instance = fast_llm
        logger.info("Modelo LLM Rápido listo.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize the fast task LLM. The main LLM will be used as a fallback: {e}")
        _fast_task_llm_instance = _main_agent_llm_instance

    try:
        logger.info(f"Inicializando LLM Visión: {settings.vision_model}")
        vision_llm_kwargs = {
            "model_name": settings.vision_model,
            "temperature": 0.0,
            "streaming": True,
            "verbose": False,
            "max_retries": 0,
            "rate_limiter": gemini_rate_limiter,
            "timeout": settings.llm_request_timeout,
        }
        
        if use_gpu:
            vision_llm_kwargs["device"] = "cuda"
        
        # Configurar proveedor específico según el formato del modelo
        vision_model_lower = settings.vision_model.lower()
        
        if "openrouter" in vision_model_lower:
            logger.info("🔧 Applying OpenRouter specific config for vision LLM.")
            apply_openrouter_model_specific_logic(settings.vision_model, vision_llm_kwargs)
        elif "anthropic" in vision_model_lower:
            logger.info("🔧 Applying Anthropic specific config for vision LLM.")
            vision_llm_kwargs["provider"] = "anthropic"
        elif "groq" in vision_model_lower:
            logger.info("🔧 Applying Groq specific config for vision LLM.")
            vision_llm_kwargs["provider"] = "groq"
        elif "gemini" in vision_model_lower:
            logger.info("🔧 Applying Gemini specific config for vision LLM.")
            vision_llm_kwargs["provider"] = "google_ai_studio"
        elif "openai" in vision_model_lower or "gpt" in vision_model_lower:
            logger.info("🔧 Applying OpenAI/GPT specific config for vision LLM.")

        vision_llm = ChatLiteLLM(**vision_llm_kwargs)
        _vision_llm_instance = vision_llm
        logger.info("Modelo LLM Visión listo.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize the vision LLM. The main LLM will be used as a fallback: {e}")
        _vision_llm_instance = _main_agent_llm_instance

async def get_enhanced_llm_response(
    user_message: str,
    user_id: str,
    workspace_id: Optional[str] = None,
    use_knowledge_graph: bool = True
) -> Dict[str, Any]:
    """
    Obtiene respuesta del LLM enriquecida con contexto del grafo de conocimiento.

    Args:
        user_message: Mensaje del usuario
        user_id: ID del usuario
        workspace_id: ID del workspace
        use_knowledge_graph: Si usar el grafo de conocimiento

    Returns:
        Dict con respuesta enriquecida
    """
    try:
        logger.info(f"🧠 Generando respuesta enriquecida...")

        # 1. Obtener contexto enriquecido si está habilitado
        enhanced_context = None
        if use_knowledge_graph:
            enhanced_context = await _get_enhanced_context(user_message, user_id, workspace_id)

        # 2. Construir prompt enriquecido
        enriched_prompt = await _build_enriched_prompt(user_message, enhanced_context)

        # 3. Obtener respuesta del LLM
        llm = get_main_llm()
        if not llm:
            raise ValueError("LLM no inicializado")

        # Log del modelo en uso
        # Try the common attribute names for the underlying model identifier
        model_name = getattr(llm, 'model_name', getattr(llm, 'model', 'unknown'))
        logger.info(f"🤖 ENHANCED RESPONSE: Usando modelo '{model_name}' para generar respuesta.")

        logger.info(f"📝 Prompt para respuesta enriquecida enviado al LLM.") # Log del prompt
        response = await _invoke_llm_cached(llm, enriched_prompt)
        logger.info(f"🗣️ Respuesta cruda del LLM para respuesta enriquecida recibida.") # Log de la respuesta cruda del LLM

        # 4. Procesar y enriquecer la respuesta
        enhanced_response = {
            "response": response.content if hasattr(response, 'content') else str(response),
            "user_message": user_message,
            "enhanced_context": enhanced_context,
            "reasoning_used": enhanced_context is not None,
            "timestamp": datetime.now().isoformat()
        }

        # 5. Guardar memoria enriquecida
        if enhanced_context:
            await _save_enhanced_interaction(enhanced_response, user_id)

        logger.info("✅ Respuesta enriquecida generada exitosamente")
        return enhanced_response

    except Exception as e:
        logger.error(f"❌ Error generando respuesta enriquecida: {e}")
        # Fallback a respuesta tradicional
        return await _get_traditional_response(user_message)

async def _get_enhanced_context(user_message: str, user_id: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Obtiene contexto enriquecido del grafo de conocimiento."""
    try:
        from core.enhanced_memory_manager import EnhancedMemoryManager
        from knowledge_graph.graph_database import GraphDB
        from core.config import settings

        # Inicializar componentes
        if not settings.neo4j_uri:
            logger.error("NEO4J_URI no está configurado.")
            return None
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )

        enhanced_manager = EnhancedMemoryManager(graph_db=graph_db)

        # Obtener contexto enriquecido
        context = await enhanced_manager.get_enhanced_context(
            user_message, user_id, workspace_id
        )

        return context

    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo contexto enriquecido: {e}")
        return None

async def _build_enriched_prompt(user_message: str, enhanced_context: Optional[Dict[str, Any]] = None) -> str:
    """Construye un prompt enriquecido con contexto del grafo de conocimiento."""

    base_prompt = f"Usuario: {user_message}"

    if not enhanced_context:
        return base_prompt

    # Agregar contexto del grafo de conocimiento
    enriched_prompt = f"""Contexto del Grafo de Conocimiento:

"""

    # Agregar entidades relevantes
    entities = enhanced_context.get("sources", {}).get("knowledge_graph", {}).get("entities", [])
    if entities:
        enriched_prompt += "Entidades relevantes encontradas:\n"
        for entity in entities[:5]:
            enriched_prompt += f"- {entity.get('name', '')}: {entity.get('description', '')} (confianza: {entity.get('confidence', 0):.2f})\n"
        enriched_prompt += "\n"

    # Agregar relaciones relevantes
    relationships = enhanced_context.get("sources", {}).get("knowledge_graph", {}).get("relationships", [])
    if relationships:
        enriched_prompt += "Relaciones relevantes:\n"
        for rel in relationships[:3]:
            enriched_prompt += f"- {rel.get('source_name', '')} → {rel.get('target_name', '')} ({rel.get('relationship_type', '')})\n"
        enriched_prompt += "\n"

    # Agregar insights
    insights = enhanced_context.get("enhanced_insights", [])
    if insights:
        enriched_prompt += "Insights del análisis:\n"
        for insight in insights:
            enriched_prompt += f"- {insight.get('description', '')}\n"
        enriched_prompt += "\n"

    # Agregar caminos de razonamiento
    reasoning_paths = enhanced_context.get("reasoning_paths", [])
    if reasoning_paths:
        enriched_prompt += "Caminos de razonamiento identificados:\n"
        for path in reasoning_paths:
            enriched_prompt += f"- {path.get('description', '')}\n"
            for step in path.get("steps", [])[:2]:
                enriched_prompt += f"  {step.get('step', '')}: {step.get('from', '')} → {step.get('to', '')} ({step.get('relationship', '')})\n"
        enriched_prompt += "\n"

    enriched_prompt += f"""
Instrucciones:
1. Usa el contexto del grafo de conocimiento para enriquecer tu respuesta
2. Menciona conexiones relevantes cuando sea apropiado
3. Si hay caminos de razonamiento, úsalos para estructurar tu respuesta
4. Mantén un tono natural y conversacional

Usuario: {user_message}

Asistente:"""

    return enriched_prompt

async def _save_enhanced_interaction(enhanced_response: Dict[str, Any], user_id: str) -> None:
    """Guarda la interacción enriquecida para futuras referencias."""
    try:
        # Aquí integrarías con tu sistema de guardado de memorias
        logger.debug(f"💾 Guardando interacción enriquecida para usuario {user_id}")

    except Exception as e:
        logger.error(f"❌ Error guardando interacción enriquecida: {e}")

async def _get_traditional_response(user_message: str) -> Dict[str, Any]:
    """Fallback a respuesta tradicional sin contexto enriquecido."""
    try:
        llm = get_main_llm()
        if not llm:
            raise ValueError("LLM no inicializado")

        response = await _invoke_llm_cached(llm, user_message)

        return {
            "response": response.content if hasattr(response, 'content') else str(response),
            "user_message": user_message,
            "enhanced_context": None,
            "reasoning_used": False,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error en respuesta tradicional: {e}")
        return {
            "response": "Lo siento, hubo un error procesando tu solicitud.",
            "user_message": user_message,
            "enhanced_context": None,
            "reasoning_used": False,
            "error": str(e)
        }
