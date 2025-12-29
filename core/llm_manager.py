# core/llm_manager.py

import logging
import time
import asyncio
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

# Asegúrate de que litellm elimine parámetros no soportados globalmente
litellm.drop_params = True

# Disable debug mode for LiteLLM to reduce logging
# litellm._turn_on_debug()

logger = logging.getLogger(__name__)

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
                    f"RateLimiter initialized: {cls._instance.max_requests} requests per {cls._instance.per_seconds} seconds. Enabled: {settings.rate_limit_enabled}"
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

def get_main_llm() -> Optional[ChatLiteLLM]: # More specific return type
    """Returns the initialized main agent LLM instance."""
    return _main_agent_llm_instance

def get_fast_llm() -> Optional[ChatLiteLLM]: # More specific return type
    """Returns the initialized fast task LLM instance, or the main one as a fallback."""
    return _fast_task_llm_instance or _main_agent_llm_instance

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
    global _main_agent_llm_instance, _fast_task_llm_instance
    
    try:
        logger.info(f"🛠️ Initializing main agent LLM with rate limiting (LiteLLM - {settings.llm_model})...")
        
        llm_kwargs = {
            "model_name": settings.llm_model,
            "temperature": settings.llm_temperature,
            "streaming": True,
            "verbose": False,
            "max_retries": 0, # We handle rate limiting, so disable litellm's retries for this
            "rate_limiter": gemini_rate_limiter, # Pass the compliant rate limiter
            "max_tokens": settings.deep_research_max_tokens, # Allow for massive reports
        }
        
        if settings.llm_api_base:
            llm_kwargs["api_base"] = settings.llm_api_base
        
        if "gpt" in settings.llm_model.lower() or "openai" in settings.llm_model.lower():
            logger.info("🔧 Applying OpenAI/GPT specific config for tool calling.")
            llm_kwargs["model_kwargs"] = {"tool_choice": "auto"}
        elif "gemini" in settings.llm_model.lower():
            logger.info("🔧 Applying Gemini specific config.")
            llm_kwargs["provider"] = "google_ai_studio"
        elif "openrouter" in settings.llm_model.lower():
            logger.info("🔧 Applying OpenRouter specific config.")
            llm_kwargs["provider"] = "openai"  # OpenRouter acts as OpenAI proxy

        main_llm = ChatLiteLLM(**llm_kwargs)
        _main_agent_llm_instance = main_llm
        logger.info("✅ Main agent LLM initialized with rate limiting.")
    except Exception as e:
        logger.error(f"❌ FATAL: Failed to initialize the main LLM: {e}", exc_info=True)
        raise

    try:
        logger.info(f"🛠️ Initializing fast task LLM with rate limiting (LiteLLM - {settings.fast_llm_model})...")
        fast_llm_kwargs = {
            "model_name": settings.fast_llm_model,
            "temperature": 0.0,
            "streaming": True,
            "verbose": False,
            "max_retries": 0,
            "rate_limiter": gemini_rate_limiter, # Use the same rate limiter instance
        }

        if settings.llm_api_base:
            fast_llm_kwargs["api_base"] = settings.llm_api_base

        if "openrouter" in settings.fast_llm_model.lower():
            logger.info("🔧 Applying OpenRouter specific config for fast LLM.")
            fast_llm_kwargs["provider"] = "openai"  # OpenRouter acts as OpenAI proxy

        fast_llm = ChatLiteLLM(**fast_llm_kwargs)
        _fast_task_llm_instance = fast_llm
        logger.info("✅ Fast task LLM initialized with rate limiting.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize the fast task LLM. The main LLM will be used as a fallback: {e}")
        _fast_task_llm_instance = _main_agent_llm_instance

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
        logger.info(f"🧠 Generando respuesta enriquecida para: '{user_message[:50]}...'")

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

        logger.info(f"📝 Prompt enviado al LLM: {enriched_prompt[:1000]}...") # Log del prompt
        response = await _invoke_llm_cached(llm, enriched_prompt)
        logger.info(f"🗣️ Respuesta cruda del LLM: {response.content[:1000]}...") # Log de la respuesta cruda del LLM

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
