# core/llm_manager.py

import logging
import time
import asyncio
import os
try:
    import torch
except ImportError:
    torch = None
from collections import deque
from threading import Lock
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import litellm  # Importar litellm
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.rate_limiters import BaseRateLimiter
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
)  # Importar BaseMessage y HumanMessage
from core.config import settings
from core.database import SessionLocal, Account, UserSecret
from core.repositories.secret_repository import SecretRepository
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SYSTEM_ACCOUNT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def ensure_system_account(db: AsyncSession) -> Account:
    account = await db.get(Account, SYSTEM_ACCOUNT_ID)
    if not account:
        account = Account(
            id=SYSTEM_ACCOUNT_ID,
            name="System Global",
            username="system_global",
            email="system@kognito.ai",
            is_admin=True,
            is_active=False,
        )
        db.add(account)
        await db.commit()
    return account


async def get_global_llm_settings(db: AsyncSession) -> dict:
    from core.database import SystemSettings

    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "global_llm_settings")
    )
    row = result.scalar_one_or_none()
    if row and row.value:
        try:
            import json

            return json.loads(row.value)
        except Exception as e:
            logger.error(f"Error parsing global_llm_settings JSON: {e}")
    return {}


async def get_global_api_key(db: AsyncSession, provider: str) -> Optional[str]:
    secret_repo = SecretRepository(db)
    api_key_name = None
    if provider.lower().replace("_", "-") in ["gemini", "google"]:
        api_key_name = "GEMINI_API_KEY"
    elif provider.lower().replace("_", "-") == "ollama-cloud":
        api_key_name = "OLLAMA_API_KEY"

    key_to_search = api_key_name or f"{provider.upper().replace('-', '_')}_API_KEY"
    await ensure_system_account(db)
    api_key = await secret_repo.get_decrypted_secret(SYSTEM_ACCOUNT_ID, key_to_search)
    if not api_key and provider.lower() in ["gemini", "google"]:
        api_key = await secret_repo.get_decrypted_secret(
            SYSTEM_ACCOUNT_ID, "GOOGLE_API_KEY"
        )
    return api_key


# Asegúrate de que litellm elimine parámetros no soportados globalmente
litellm.drop_params = True


# --- Registro de Proveedores Custom ---
# Esto permite que LiteLLM reconozca el prefijo kilocode/ y llm7/ sin lanzar BadRequestError
def _register_custom_providers():
    try:
        # Añadir kilocode y llm7 a la lista de proveedores conocidos como compatible con OpenAI
        if "kilocode" not in litellm.provider_list:
            litellm.provider_list.append("kilocode")
        if "llm7" not in litellm.provider_list:
            litellm.provider_list.append("llm7")
        if "nvidia" not in litellm.provider_list:
            litellm.provider_list.append("nvidia")

        # Mapear dinámicamente modelos de kilocode, llm7 y nvidia a la lógica de openai
        # LiteLLM usa esto para determinar qué clase de cliente instanciar
        litellm.custom_provider_map = getattr(litellm, "custom_provider_map", [])

        kilocode_map = {"provider": "kilocode", "custom_handler": "openai"}
        if kilocode_map not in litellm.custom_provider_map:
            litellm.custom_provider_map.append(kilocode_map)

        llm7_map = {"provider": "llm7", "custom_handler": "openai"}
        if llm7_map not in litellm.custom_provider_map:
            litellm.custom_provider_map.append(llm7_map)

        nvidia_map = {"provider": "nvidia", "custom_handler": "openai"}
        if nvidia_map not in litellm.custom_provider_map:
            litellm.custom_provider_map.append(nvidia_map)

        logger.info("📡 Proveedores KiloCode y LLM7 registrados globalmente en LiteLLM")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo registrar los proveedores custom: {e}")


def detect_provider_from_model(model_name: str) -> str:
    """
    Detecta el proveedor basándose en el nombre del modelo, incluso sin prefijo.

    Args:
        model_name: Nombre del modelo (ej: "gemini-2.0-flash", "gpt-4o", "claude-3-opus")

    Returns:
        Proveedor detectado (ej: "gemini", "openai", "anthropic", etc.)
    """
    if not model_name:
        return "openai"

    model_lower = model_name.lower()

    # Modelos de Gemini/Google
    if any(x in model_lower for x in ["gemini", "google"]):
        return "gemini"

    # Modelos de OpenAI
    if any(x in model_lower for x in ["gpt-", "o1-", "o3-", "openai"]):
        return "openai"

    # Modelos de Anthropic
    if any(x in model_lower for x in ["claude", "anthropic"]):
        return "anthropic"

    # Modelos de NVIDIA
    if any(x in model_lower for x in ["nvidia", "nemotron"]) or model_lower.startswith("nvidia/"):
        return "nvidia"

    # Modelos de Groq
    if any(x in model_lower for x in ["groq", "llama-", "mixtral", "gemma-"]):
        return "groq"

    # Modelos de DeepSeek
    if any(x in model_lower for x in ["deepseek"]):
        return "deepseek"

    # Modelos de Mistral
    if any(x in model_lower for x in ["mistral", "pixtral"]):
        return "mistral"

    # Modelos de Cerebras
    if any(x in model_lower for x in ["cerebras"]):
        return "cerebras"

    # Modelos de Ollama (locales)
    if any(
        x in model_lower for x in ["ollama", "llama3", "phi3", "qwen", "nomic-embed"]
    ):
        return "ollama"

    # Modelos de OpenRouter (tienen formato org/modelo)
    if "/" in model_name and not model_lower.startswith(
        (
            "gemini/",
            "openai/",
            "anthropic/",
            "groq/",
            "deepseek/",
            "mistral/",
            "cerebras/",
        )
    ):
        return "openrouter"

    # Modelos de Kilocode
    if model_lower.startswith("kilocode/"):
        return "kilocode"

    # Modelos de LLM7
    if model_lower.startswith("llm7/"):
        return "llm7"

    # Por defecto, asumir OpenAI compatible
    return "openai"


def get_provider_from_model_or_fallback(
    model_name: str, explicit_provider: str = None
) -> str:
    """
    Obtiene el proveedor del modelo, usando el explícito si existe,
    o detectándolo del nombre del modelo.

    Args:
        model_name: Nombre del modelo
        explicit_provider: Proveedor configurado explícitamente (opcional)

    Returns:
        Proveedor a utilizar
    """
    if explicit_provider:
        return explicit_provider.lower()

    # Si el modelo tiene prefijo de proveedor (ej: "gemini/gemini-2.0-flash"), usarlo
    if model_name and "/" in model_name:
        prefix = model_name.split("/")[0].lower()
        # Validar que sea un proveedor conocido
        known_providers = [
            "gemini",
            "google",
            "openai",
            "anthropic",
            "groq",
            "deepseek",
            "mistral",
            "cerebras",
            "openrouter",
            "kilocode",
            "llm7",
            "ollama",
            "vertex_ai",
            "azure",
            "google_ai_studio",
        ]
        if prefix in known_providers:
            return prefix

    # Detectar por nombre del modelo
    return detect_provider_from_model(model_name)


# --- Configuración del Logger ---
from core.utils.logging_utils import AgentLogger

logger = AgentLogger(__name__)

# Registrar proveedores al importar el módulo
_register_custom_providers()

# Disable debug mode for LiteLLM to reduce logging
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("LiteLLM/UniversalDeployer").setLevel(logging.WARNING)
# Silenciar los logs de "Provider List" que a veces salen por stdout
import os

os.environ["LITELLM_LOG"] = "ERROR"

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
                cls._instance.max_requests = kwargs.get(
                    "max_requests", settings.rate_limit_max_requests
                )
                cls._instance.per_seconds = kwargs.get(
                    "per_seconds", settings.rate_limit_per_seconds
                )
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
        pass  # State is managed by the singleton __new__

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
            while (
                self.request_timestamps
                and self.request_timestamps[0] <= now - self.per_seconds
            ):
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
            while (
                self.request_timestamps
                and self.request_timestamps[0] <= now - self.per_seconds
            ):
                self.request_timestamps.popleft()

            wait_time = 0
            if len(self.request_timestamps) >= self.max_requests:
                oldest_request_time = self.request_timestamps[0]
                time_since_oldest = now - oldest_request_time
                wait_time = self.per_seconds - time_since_oldest
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached. Sync waiting for {wait_time:.2f}s."
                    )
                    time.sleep(wait_time)

            self.request_timestamps.append(time.monotonic())


# Initialize the global rate limiter
gemini_rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_max_requests,
    per_seconds=settings.rate_limit_per_seconds,
)

# --- Global LLM Instances ---
_main_agent_llm_instance: Optional[ChatLiteLLM] = None
_fast_task_llm_instance: Optional[ChatLiteLLM] = None
_vision_llm_instance: Optional[ChatLiteLLM] = None

# --- LLM Instance Cache ---
# Cache LLM instances per user to avoid repeated DB queries
# Key: (account_id, purpose) -> (instance, timestamp)
_llm_cache: Dict[tuple, tuple] = {}
_LLM_CACHE_TTL = 300  # 5 minutes


def clear_user_llm_cache(account_id: Union[str, uuid.UUID]):
    """
    Limpia las instancias de LLM en caché para un usuario específico.
    """
    acc_id_str = str(account_id)
    keys_to_remove = [k for k in _llm_cache.keys() if str(k[0]) == acc_id_str]
    for k in keys_to_remove:
        _llm_cache.pop(k, None)
    logger.info(f"🧹 Cache de LLM limpiado para el usuario {acc_id_str}")


def get_main_llm() -> Optional[ChatLiteLLM]:  # More specific return type
    """Returns the initialized main agent LLM instance."""
    return _main_agent_llm_instance


def get_fast_llm() -> Optional[ChatLiteLLM]:  # More specific return type
    """Returns the initialized fast task LLM instance, or the main one as a fallback."""
    return _fast_task_llm_instance or _main_agent_llm_instance


def get_vision_llm() -> Optional[ChatLiteLLM]:
    """Returns the initialized vision LLM instance for multimodal tasks."""
    return _vision_llm_instance or _main_agent_llm_instance


def _get_llm_signature(
    llm: Optional[ChatLiteLLM],
) -> tuple[Optional[str], Optional[str]]:
    """Obtiene una firma simple para comparar dos configuraciones de LLM."""
    if llm is None:
        return (None, None)

    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", None)
    provider = getattr(llm, "provider", None) or getattr(
        llm, "custom_llm_provider", None
    )
    return (
        str(model_name) if model_name is not None else None,
        str(provider) if provider is not None else None,
    )


def _is_distinct_llm(
    primary_llm: Optional[ChatLiteLLM], candidate_llm: Optional[ChatLiteLLM]
) -> bool:
    """Indica si el candidato representa una configuración diferente al LLM primario."""
    if candidate_llm is None:
        return False
    return _get_llm_signature(primary_llm) != _get_llm_signature(candidate_llm)


def _get_global_llm_for_purpose(purpose: str) -> Optional[ChatLiteLLM]:
    """Devuelve el LLM global correspondiente al propósito solicitado."""
    if purpose == "fast":
        return get_fast_llm()
    if purpose == "vision":
        return get_vision_llm()
    return get_main_llm()


def normalize_openrouter_model_name(model_name: str) -> str:
    """
    Normaliza el nombre del modelo para OpenRouter.

    Asegura que el modelo tenga el formato 'organizacion/modelo' requerido por OpenRouter.
    Si es un modelo nativo (aurora, pony), le añade el prefijo 'openrouter/'.
    Para Step 3.5 Flash, le añade el prefijo 'stepfun/'.
    Elimina el prefijo 'openrouter/' de modelos que no son nativos de OpenRouter.
    """
    # Si ya tiene el prefijo de proveedor (ej: 'openai/' o 'openrouter/'), no tocarlo
    if "/" in model_name and not model_name.startswith("openrouter/"):
        # Pero si el usuario puso algo como 'openai/gpt-4o' y estamos en OpenRouter,
        # lo dejamos pasar ya que OpenRouter acepta IDs de otros proveedores.
        return model_name

    native_models = ["aurora-alpha", "pony-alpha"]
    stepfun_models = ["step-3.5-flash:free"]

    model_lower = model_name.lower()

    # Si tiene prefijo 'openrouter/', verificar si es un modelo nativo
    if model_name.startswith("openrouter/"):
        model_without_prefix = model_name[len("openrouter/") :]
        model_without_prefix_lower = model_without_prefix.lower()

        # Si es un modelo nativo (aurora/pony), mantener el prefijo
        if any(native in model_without_prefix_lower for native in native_models):
            return model_name
        else:
            # Para otros modelos, eliminar el prefijo 'openrouter/'
            return model_without_prefix

    # Si es un modelo de StepFun sin prefijo, añadir 'stepfun/'
    if (
        any(stepfun in model_lower for stepfun in stepfun_models)
        and not "/" in model_name
    ):
        return f"stepfun/{model_name}"

    # Si es un modelo nativo de OpenRouter sin prefijo, añadir 'openrouter/'
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
        logger.info(
            f"🧠 Habilitando razonamiento nativo (Force: {settings.global_force_reasoning}) para: {model_name}"
        )
    else:
        # Por defecto, NO incluir razonamiento para evitar romper modos JSON y estructurados
        # OpenRouter recomienda mandar False si queremos asegurar que no se cuele texto de razonamiento
        llm_kwargs["extra_body"]["include_reasoning"] = False
        logger.info(
            f"🧠 Razonamiento nativo DESHABILITADO para: {model_name} (estabilidad JSON)"
        )

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


def _sanitize_ascii(value: Any) -> Any:
    """
    Ensures that a value is a strictly ASCII string.
    If it's a string, it strips any non-ASCII characters.
    This prevents UnicodeEncodeError when values are used in HTTP headers.
    """
    if isinstance(value, str):
        return value.encode("ascii", "ignore").decode("ascii")
    return value


def _sanitize_llm_kwargs(kwargs: dict) -> dict:
    """
    Sanitizes common LLM kwargs that end up in HTTP headers or cause LiteLLM kwarg conflicts.
    """
    if "api_key" in kwargs:
        kwargs["api_key"] = _sanitize_ascii(kwargs["api_key"])

    if "headers" in kwargs and isinstance(kwargs["headers"], dict):
        kwargs["headers"] = {
            k: _sanitize_ascii(v) for k, v in kwargs["headers"].items()
        }

    if "extra_headers" in kwargs and isinstance(kwargs["extra_headers"], dict):
        kwargs["extra_headers"] = {
            k: _sanitize_ascii(v) for k, v in kwargs["extra_headers"].items()
        }

    # Remover el kwarg 'provider' que causa conflictos en LiteLLM/OpenAI SDK
    if "provider" in kwargs:
        prov_val = kwargs.pop("provider")
        if prov_val in ("google_ai_studio", "google", "gemini"):
            prov_val = "gemini"
        if prov_val and "custom_llm_provider" not in kwargs:
            kwargs["custom_llm_provider"] = prov_val

    # Normalizar custom_llm_provider si es google_ai_studio o google
    if kwargs.get("custom_llm_provider") in ("google_ai_studio", "google"):
        kwargs["custom_llm_provider"] = "gemini"

    return kwargs



async def get_llm_for_user(
    account_id: str, purpose: str = "main"
) -> Optional[ChatLiteLLM]:
    """
    Returns a customized LLM instance for a specific user based on their settings.
    If the user has no custom settings, returns the global default instance.
    """
    if not account_id:
        return get_main_llm()

    # Check cache first to avoid repeated DB queries
    cache_key = (account_id, purpose)
    if cache_key in _llm_cache:
        instance, ts = _llm_cache[cache_key]
        if time.time() - ts < _LLM_CACHE_TTL:
            return instance
        else:
            del _llm_cache[cache_key]

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

            # Auto-detección de proveedor Kilocode por prefijo de modelo
            if (
                model_target
                and model_target.startswith("kilocode/")
                and provider_target != "kilocode"
            ):
                logger.info(
                    f"Detectado modelo Kilocode: {model_target}. Forzando provider a 'kilocode'."
                )
                provider_target = "kilocode"

            # Auto-detección de proveedor NVIDIA por prefijo de modelo
            if (
                model_target
                and model_target.startswith("nvidia/")
                and provider_target != "nvidia"
            ):
                logger.info(
                    f"Detectado modelo NVIDIA: {model_target}. Forzando provider a 'nvidia'."
                )
                provider_target = "nvidia"

            # Si el usuario no tiene proveedor configurado, detectarlo del nombre del modelo
            if not provider_target and model_target:
                provider_target = detect_provider_from_model(model_target)
                logger.info(
                    f"🔍 Proveedor detectado automáticamente para modelo '{model_target}': {provider_target}"
                )

            # Si el usuario no tiene proveedor o modelo configurado, usar global
            if not provider_target or not model_target:
                if purpose == "fast":
                    return get_fast_llm()
                if purpose == "vision":
                    return get_vision_llm()
                return get_main_llm()

            # 2. Obtener API Key de los secretos
            secret_repo = SecretRepository(db)
            api_key_name = None
            if provider_target.lower().replace("_", "-") in ["gemini", "google"]:
                api_key_name = "GEMINI_API_KEY"
            elif provider_target.lower().replace("_", "-") == "ollama-cloud":
                api_key_name = "OLLAMA_API_KEY"

            key_to_search = (
                api_key_name or f"{provider_target.upper().replace('-', '_')}_API_KEY"
            )

            # Intentar obtener la API key del usuario
            api_key = await secret_repo.get_decrypted_secret(account.id, key_to_search)
            if api_key:
                logger.info(
                    f"🔑 Clave encontrada para {key_to_search}: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}"
                )
            else:
                # Si no está en el usuario, intentar en los secretos globales del sistema
                await ensure_system_account(db)
                api_key = await secret_repo.get_decrypted_secret(
                    SYSTEM_ACCOUNT_ID, key_to_search
                )
                if api_key:
                    logger.info(
                        f"🔑 Clave GLOBAL encontrada para {key_to_search}: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}"
                    )
                else:
                    logger.warning(
                        f"⚠️ No se encontró clave para {key_to_search} en la cuenta del usuario ni en los secretos globales."
                    )

            # Fallback para Google AI Studio: buscar GOOGLE_API_KEY
            if not api_key and provider_target.lower() in ["gemini", "google"]:
                api_key = await secret_repo.get_decrypted_secret(
                    account.id, "GOOGLE_API_KEY"
                )
                if not api_key:
                    api_key = await secret_repo.get_decrypted_secret(
                        SYSTEM_ACCOUNT_ID, "GOOGLE_API_KEY"
                    )
                # Último fallback: usar variable de entorno global
                if not api_key and settings.google_api_key:
                    api_key = settings.google_api_key

            # Fallback para Ollama Cloud
            if (
                not api_key
                and provider_target.lower().replace("_", "-") == "ollama-cloud"
            ):
                if settings.ollama_api_key:
                    api_key = settings.ollama_api_key

            # Fallback para Kilocode Gateway
            if not api_key and provider_target.lower() == "kilocode":
                if settings.kilocode_api_key:
                    api_key = settings.kilocode_api_key

            # Fallback para NVIDIA
            if not api_key and provider_target.lower() == "nvidia":
                if settings.nvidia_api_key:
                    api_key = settings.nvidia_api_key
                elif os.getenv("NVIDIA_API_KEY"):
                    api_key = os.getenv("NVIDIA_API_KEY")

            # Fallbacks genéricos para otros proveedores desde variables de entorno
            if not api_key:
                if provider_target.lower() == "openai":
                    api_key = settings.openai_api_key
                elif provider_target.lower() == "openrouter":
                    api_key = settings.openrouter_api_key
                elif provider_target.lower() == "groq":
                    api_key = os.getenv("GROQ_API_KEY")
                elif provider_target.lower() == "anthropic":
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                elif provider_target.lower() == "deepseek":
                    api_key = os.getenv("DEEPSEEK_API_KEY")
                elif provider_target.lower() == "mistral":
                    api_key = os.getenv("MISTRAL_API_KEY")
                elif provider_target.lower() == "cerebras":
                    api_key = os.getenv("CEREBRAS_API_KEY")

            api_key = _sanitize_ascii(api_key) if api_key else None

            # Si el proveedor requiere API Key y no existe ninguna disponible, caer al modelo de administrador
            providers_requiring_key = [
                "gemini",
                "google",
                "google_ai_studio",
                "openai",
                "openrouter",
                "anthropic",
                "groq",
                "deepseek",
                "mistral",
                "cerebras",
                "kilocode",
                "nvidia",
                "ollama-cloud",
            ]
            if not api_key and provider_target.lower() in providers_requiring_key:
                logger.warning(
                    f"⚠️ El modelo configurado por el usuario '{model_target}' (proveedor '{provider_target}') "
                    f"requiere API Key pero no se encontró ninguna disponible. Usando automáticamente el modelo configurado por el administrador."
                )
                admin_llm = _get_global_llm_for_purpose(purpose)
                if admin_llm:
                    _llm_cache[cache_key] = (admin_llm, time.time())
                    return admin_llm

            # 3. Construir instancia personalizada
            llm_kwargs = {
                "model_name": model_target,
                "temperature": account.llm_temperature
                if account.llm_temperature is not None
                else settings.llm_temperature,
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

                # Paso 1: Obtener el ID real del modelo
                actual_id = normalize_openrouter_model_name(model_target)

                # Paso 2: Añadir prefijo openrouter/ para LiteLLM
                llm_kwargs["model_name"] = f"openrouter/{actual_id}"

                # No forzar provider=openai para que LiteLLM reconozca openrouter/ y elimine el prefijo al enviar
                if "provider" in llm_kwargs:
                    del llm_kwargs["provider"]

                # Aplicar lógica de adaptador universal según el modelo
                apply_openrouter_model_specific_logic(actual_id, llm_kwargs)

                # Headers recomendados por OpenRouter para mejor soporte y visibilidad
                if "extra_headers" not in llm_kwargs:
                    llm_kwargs["extra_headers"] = {}
                llm_kwargs["extra_headers"]["HTTP-Referer"] = (
                    "https://kognito.ai"  # Identificador de la app
                )
                llm_kwargs["extra_headers"]["X-Title"] = "Kognito AI"

                logger.info(
                    f"OpenRouter: {llm_kwargs['model_name']} (Con adaptadores y headers)"
                )

                logger.info(
                    f"OpenRouter: {llm_kwargs['model_name']} (Con adaptadores y headers)"
                )

            elif provider_target.lower() == "openai-compatible":
                # Servidor local compatible con OpenAI: Local AI, LM Studio, etc.
                # LiteLLM requiere una api_key aunque el servidor no la necesite
                if not llm_kwargs.get("api_key"):
                    llm_kwargs["api_key"] = "local-key"
                if account.llm_api_base:
                    llm_kwargs["api_base"] = account.llm_api_base.rstrip("/")
                else:
                    logger.warning(
                        "openai-compatible requiere una API Base URL pero no está configurada."
                    )
                # Asegurarnos de que el model_name tenga prefijo openai/ para LiteLLM
                if not model_target.startswith("openai/"):
                    llm_kwargs["model_name"] = f"openai/{model_target.split('/')[-1]}"
                logger.info(
                    f"🖥️ Local AI (openai-compatible): {llm_kwargs['model_name']} en {llm_kwargs.get('api_base')}"
                )

            elif provider_target.lower().replace("_", "-") == "ollama-cloud":
                # Ollama Cloud: https://docs.ollama.com/cloud
                # API base: https://api.ollama.com/v1 (o la personalizada del usuario)

                api_base_str = account.llm_api_base
                if api_base_str:
                    if not api_base_str.startswith("http"):
                        # Si no tiene protocolo, detectar si es local o público
                        is_likely_local = any(
                            x in api_base_str.lower()
                            for x in [
                                "localhost",
                                "127.0.0.1",
                                "host.docker.internal",
                                "192.168.",
                                "10.",
                                "172.",
                            ]
                        )
                        protocol = "http" if is_likely_local else "https"
                        api_base_str = f"{protocol}://{api_base_str}"
                    api_base_str = api_base_str.rstrip("/")

                    logger.info(f"☁️ Ollama URL final: {api_base_str}")

                    llm_kwargs["api_base"] = api_base_str
                else:
                    llm_kwargs["api_base"] = "https://api.ollama.com/v1"

                # Autenticación: Bearer token en header
                if api_key:
                    llm_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
                    logger.info(
                        f"☁️ Ollama Cloud: API Key configurada (len={len(api_key)})"
                    )
                else:
                    logger.warning("☁️ Ollama Cloud: SIN API Key!")

                # Usar ollama_chat/ para forzar endpoint /api/chat
                # Pero el modelo real debe enviarse en el campo "model"
                actual_model = model_target.split("/")[-1].strip()
                llm_kwargs["model_name"] = f"ollama_chat/{actual_model}"
                llm_kwargs["custom_llm_provider"] = "ollama"
                # Forzar que el modelo real se envíe a Ollama
                llm_kwargs["extra_body"] = {"model": actual_model}

                logger.info(
                    f"☁️ Ollama Cloud: model={llm_kwargs['model_name']}, actual={actual_model}, base={llm_kwargs.get('api_base')}"
                )

            elif "ollama" in provider_target.lower():
                # Usar la URL configurada en settings como fallback para ollama local
                logger.info(
                    f"DEBUG OLLAMA: account.llm_api_base={account.llm_api_base}, settings.ollama_api_url={settings.ollama_api_url}"
                )
                api_base_str = (
                    account.llm_api_base
                    or settings.ollama_api_url
                    or "http://host.docker.internal:11434"
                )

                if api_base_str and not api_base_str.startswith("http"):
                    # Si no tiene protocolo, detectar si es local o público
                    is_likely_local = any(
                        x in api_base_str.lower()
                        for x in [
                            "localhost",
                            "127.0.0.1",
                            "host.docker.internal",
                            "192.168.",
                            "10.",
                            "172.",
                        ]
                    )
                    protocol = "http" if is_likely_local else "https"
                    api_base_str = f"{protocol}://{api_base_str}"

                api_base_str = api_base_str.rstrip("/")

                logger.info(f"☁️ Ollama Local URL: {api_base_str}")

                llm_kwargs["api_base"] = api_base_str

                # Usar ollama_chat/ para forzar endpoint /api/chat
                actual_model = model_target.split("/")[-1].strip()
                llm_kwargs["model_name"] = f"ollama_chat/{actual_model}"
                llm_kwargs["custom_llm_provider"] = "ollama"
                # Forzar que el modelo real se envíe a Ollama
                llm_kwargs["extra_body"] = {"model": actual_model}

                logger.info(
                    f"☁️ Ollama Local URL: {api_base_str}, model: {llm_kwargs['model_name']}, actual: {actual_model}"
                )

                # Si el usuario NO está usando ollama-cloud pero proporcionó una API Key,
                # a veces es mejor NO enviarla si es local para evitar errores de 401.
                if api_key:
                    logger.info("ℹ️ Ignorando API Key para Ollama local.")
                    llm_kwargs.pop("api_key", None)

            elif provider_target.lower() == "kilocode":
                # Kilocode Gateway - API unificada de IA (OpenAI-compatible)
                llm_kwargs["api_base"] = "https://api.kilo.ai/api/gateway"

                # Autenticación
                if api_key:
                    llm_kwargs["api_key"] = api_key

                # Normalizar modelo
                actual_model = model_target
                if actual_model.startswith("kilocode/"):
                    actual_model = actual_model[len("kilocode/") :]

                # Para LiteLLM, el modelo debe tener el prefijo 'openai/'
                # y el custom_llm_provider debe ser 'openai'
                llm_kwargs["model_name"] = f"openai/{actual_model}"
                llm_kwargs["custom_llm_provider"] = "openai"

                # IMPORTANTE: Remover cualquier 'provider' explícito que pudiera causar conflicto
                if "provider" in llm_kwargs:
                    del llm_kwargs["provider"]

                logger.info(
                    f"🚀 Kilocode Gateway configurado: {llm_kwargs['model_name']} en {llm_kwargs['api_base']}"
                )

            elif provider_target.lower() == "nvidia":
                # NVIDIA AI Catalog / NIM API (OpenAI-compatible)
                llm_kwargs["api_base"] = account.llm_api_base or "https://integrate.api.nvidia.com/v1"

                if api_key:
                    llm_kwargs["api_key"] = api_key

                actual_model = model_target
                if actual_model.startswith("nvidia/"):
                    actual_model = actual_model[len("nvidia/") :]

                # Para LiteLLM, el modelo usa prefijo 'openai/' con el endpoint de NVIDIA
                llm_kwargs["model_name"] = f"openai/{actual_model}"
                llm_kwargs["custom_llm_provider"] = "openai"

                if "provider" in llm_kwargs:
                    del llm_kwargs["provider"]

                # Habilitar/forzar extra_body razonamiento si está activo globalmente o en modelos R1/Nemotron/Reasoning
                if "extra_body" not in llm_kwargs:
                    llm_kwargs["extra_body"] = {}

                reasoning_models = ["-r1", "r1", "reasoning", "thinking", "nemotron"]
                is_reasoning = any(x in actual_model.lower() for x in reasoning_models)
                if is_reasoning or settings.global_force_reasoning:
                    llm_kwargs["extra_body"]["include_reasoning"] = True
                    logger.info(f"🧠 Razonamiento habilitado para NVIDIA: {actual_model} (Force: {settings.global_force_reasoning})")

                logger.info(
                    f"🟢 NVIDIA AI Catalog configurado: {llm_kwargs['model_name']} en {llm_kwargs['api_base']}"
                )

            elif account.llm_api_base and ("http" in account.llm_api_base):
                # Solo usar api_base si parece una URL válida (contiene http)
                # Esto previene el uso de valores accidentales como correos electrónicos
                llm_kwargs["api_base"] = account.llm_api_base

            # Configuraciones específicas por proveedor (LiteLLM)
            if (
                "gemini" in model_target.lower()
                or provider_target.lower() in ["gemini", "google"]
            ) and provider_target.lower() != "openrouter":
                llm_kwargs["provider"] = "google_ai_studio"

            # --- FIX: Asegurar que Google AI Studio use el endpoint correcto y no Vertex AI ---
            if provider_target.lower() in ("google_ai_studio", "gemini"):
                current_api_base = llm_kwargs.get("api_base")
                # Forzar siempre el endpoint de Google AI Studio, ignorando api_base heredada (ej. Ollama)
                llm_kwargs["api_base"] = (
                    "https://generativelanguage.googleapis.com/v1beta"
                )
                # Limpiar cualquier rastro de Vertex AI
                llm_kwargs.pop("vertex_project_id", None)
                llm_kwargs.pop("vertex_location", None)
                # Asegurar formato de modelo gemini/
                if not llm_kwargs["model_name"].startswith("gemini/"):
                    llm_kwargs["model_name"] = f"gemini/{llm_kwargs['model_name']}"
                logger.info(
                    f"🔧 Google AI Studio: endpoint forzado a generativelanguage.googleapis.com, modelo={llm_kwargs['model_name']}"
                )

            logger.info(
                f"🛠️ Creando LLM personalizado para usuario {account_id}: {llm_kwargs['model_name']} ({provider_target})"
            )

            # --- FIX: Sanitize kwargs to prevent UnicodeEncodeError in headers ---
            llm_kwargs = _sanitize_llm_kwargs(llm_kwargs)

            # Nota: ChatLiteLLM pasará extra_body a la API de OpenRouter
            llm_instance = ChatLiteLLM(**llm_kwargs)
            if "custom_llm_provider" in llm_kwargs:
                llm_instance.custom_llm_provider = llm_kwargs["custom_llm_provider"]
            elif provider_target.lower() == "openrouter":
                llm_instance.custom_llm_provider = "openrouter"
            # Cache the instance for future calls
            _llm_cache[cache_key] = (llm_instance, time.time())
            return llm_instance

    except Exception as e:
        logger.error(
            f"❌ Error al obtener LLM personalizado para {account_id}: {e}. Usando modelo global de administrador.",
            exc_info=True,
        )
        return _get_global_llm_for_purpose(purpose)


async def get_configured_fallback_llm(
    account_id: Optional[str] = None, failed_purpose: str = "main"
) -> Optional[ChatLiteLLM]:
    """
    Devuelve un fallback respetando la configuración del sistema.
    Si el modelo del usuario falla o no está disponible, cae automáticamente al modelo de administrador.
    """
    primary_llm = (
        await get_llm_for_user(account_id, purpose=failed_purpose)
        if account_id
        else _get_global_llm_for_purpose(failed_purpose)
    )

    candidate_purposes = ["main"] if failed_purpose in {"fast", "vision"} else ["fast"]

    if account_id:
        for purpose in candidate_purposes:
            candidate_llm = await get_llm_for_user(account_id, purpose=purpose)
            if _is_distinct_llm(primary_llm, candidate_llm):
                logger.info(
                    "🔄 Usando fallback configurado del usuario | account_id=%s | from=%s | to=%s",
                    account_id,
                    failed_purpose,
                    purpose,
                )
                return candidate_llm

    for purpose in candidate_purposes:
        candidate_llm = _get_global_llm_for_purpose(purpose)
        if _is_distinct_llm(primary_llm, candidate_llm):
            logger.info(
                "🔄 Usando fallback global de administrador | from=%s | to=%s",
                failed_purpose,
                purpose,
            )
            return candidate_llm

    # Fallback final al modelo de administrador correspondiente o al principal global
    admin_fallback = _get_global_llm_for_purpose(failed_purpose) or get_main_llm()
    if admin_fallback:
        logger.info(
            "🔄 Usando modelo de administrador como fallback final | account_id=%s | purpose=%s",
            account_id,
            failed_purpose,
        )
        return admin_fallback

    logger.warning(
        "⚠️ No hay un fallback LLM alternativo configurado | account_id=%s | failed_purpose=%s",
        account_id,
        failed_purpose,
    )
    return None


def get_fallback_llm() -> Optional[ChatLiteLLM]:
    """Returns a global fallback LLM without forcing a provider not configured."""
    try:
        primary_llm = get_main_llm()
        fallback_llm = get_fast_llm()
        if _is_distinct_llm(primary_llm, fallback_llm):
            logger.info("🔄 Using configured global fast LLM as fallback.")
            return fallback_llm
        logger.warning("⚠️ No hay fallback global alternativo configurado.")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to create fallback LLM: {e}")
        return None


async def _invoke_llm_cached(
    llm: BaseLanguageModel, prompt: Union[str, List[BaseMessage]]
) -> Any:
    """Función wrapper para invocar el LLM, asegurando el formato de mensaje correcto."""
    if isinstance(prompt, str):
        # Envuelve el prompt de cadena en un HumanMessage para cumplir con las expectativas del modelo
        messages = [HumanMessage(content=prompt)]
    elif isinstance(prompt, list) and all(
        isinstance(msg, BaseMessage) for msg in prompt
    ):
        # Si ya es una lista de BaseMessage, úsalo directamente
        messages = prompt
    else:
        raise TypeError(
            "El prompt debe ser una cadena o una lista de objetos BaseMessage."
        )

    return await llm.ainvoke(messages)


async def initialize_llms():
    """
    Initializes the global instances of the LLMs (main and fast task)
    with a compliant rate limiter.
    """
    global _main_agent_llm_instance, _fast_task_llm_instance, _vision_llm_instance

    # Detectar si hay una GPU disponible
    use_gpu = torch.cuda.is_available() if torch is not None else False
    if use_gpu:
        logger.info("✅ GPU detectada. Los modelos se cargarán en la GPU (cuda).")
    else:
        logger.warning("No se detectó GPU. Cargando modelos en CPU.")

    # 1. Cargar configuraciones globales desde la base de datos (SystemSettings)
    global_llm_provider = None
    global_llm_model = None
    global_llm_temperature = None
    global_llm_api_base = None
    global_fast_llm_model = None
    global_fast_llm_provider = None
    global_vision_llm_model = None
    global_vision_llm_provider = None
    global_use_prompt_tooling = None

    try:
        async with SessionLocal() as db:
            db_settings = await get_global_llm_settings(db)
            global_llm_provider = db_settings.get("llm_provider")
            global_llm_model = db_settings.get("llm_model")
            global_llm_temperature = db_settings.get("llm_temperature")
            global_llm_api_base = db_settings.get("llm_api_base")
            global_fast_llm_model = db_settings.get("fast_llm_model")
            global_fast_llm_provider = db_settings.get("fast_llm_provider")
            global_vision_llm_model = db_settings.get("vision_llm_model")
            global_vision_llm_provider = db_settings.get("vision_llm_provider")
            global_use_prompt_tooling = db_settings.get("use_prompt_tooling")
    except Exception as e:
        logger.error(
            f"Error loading global LLM settings from DB in initialize_llms: {e}"
        )

    eff_llm_model = global_llm_model or settings.llm_model
    eff_llm_provider = get_provider_from_model_or_fallback(
        eff_llm_model, global_llm_provider
    )
    eff_llm_temperature = (
        global_llm_temperature
        if global_llm_temperature is not None
        else settings.llm_temperature
    )
    eff_llm_api_base = global_llm_api_base or settings.llm_api_base

    eff_fast_llm_model = global_fast_llm_model or settings.fast_llm_model
    eff_fast_llm_provider = get_provider_from_model_or_fallback(
        eff_fast_llm_model, global_fast_llm_provider
    )

    eff_vision_llm_model = global_vision_llm_model or settings.vision_model
    eff_vision_llm_provider = get_provider_from_model_or_fallback(
        eff_vision_llm_model, global_vision_llm_provider
    )

    # 2. Cargar API Keys globales desde los secretos de la base de datos
    main_api_key = None
    fast_api_key = None
    vision_api_key = None

    try:
        async with SessionLocal() as db:
            if eff_llm_provider:
                main_api_key = await get_global_api_key(db, eff_llm_provider)
            if eff_fast_llm_provider:
                fast_api_key = await get_global_api_key(db, eff_fast_llm_provider)
            if eff_vision_llm_provider:
                vision_api_key = await get_global_api_key(db, eff_vision_llm_provider)
    except Exception as e:
        logger.error(f"Error loading global API keys from DB in initialize_llms: {e}")

    # Fallback to environment variables if no database API key was found
    if not main_api_key and eff_llm_provider:
        p = eff_llm_provider.lower()
        if p == "openai":
            main_api_key = settings.openai_api_key
        elif p == "openrouter":
            main_api_key = settings.openrouter_api_key
        elif p in ["gemini", "google"]:
            main_api_key = settings.google_api_key
        elif p == "kilocode":
            main_api_key = settings.kilocode_api_key
        elif p == "groq":
            main_api_key = os.getenv("GROQ_API_KEY")
        elif p == "anthropic":
            main_api_key = os.getenv("ANTHROPIC_API_KEY")
        elif p == "deepseek":
            main_api_key = os.getenv("DEEPSEEK_API_KEY")
        elif p == "mistral":
            main_api_key = os.getenv("MISTRAL_API_KEY")
        elif p == "cerebras":
            main_api_key = os.getenv("CEREBRAS_API_KEY")

    if not fast_api_key and eff_fast_llm_provider:
        p = eff_fast_llm_provider.lower()
        if p == "openai":
            fast_api_key = settings.openai_api_key
        elif p == "openrouter":
            fast_api_key = settings.openrouter_api_key
        elif p in ["gemini", "google"]:
            fast_api_key = settings.google_api_key
        elif p == "kilocode":
            fast_api_key = settings.kilocode_api_key
        elif p == "groq":
            fast_api_key = os.getenv("GROQ_API_KEY")
        elif p == "anthropic":
            fast_api_key = os.getenv("ANTHROPIC_API_KEY")
        elif p == "deepseek":
            fast_api_key = os.getenv("DEEPSEEK_API_KEY")
        elif p == "mistral":
            fast_api_key = os.getenv("MISTRAL_API_KEY")
        elif p == "cerebras":
            fast_api_key = os.getenv("CEREBRAS_API_KEY")

    if not vision_api_key and eff_vision_llm_provider:
        p = eff_vision_llm_provider.lower()
        if p == "openai":
            vision_api_key = settings.openai_api_key
        elif p == "openrouter":
            vision_api_key = settings.openrouter_api_key
        elif p in ["gemini", "google", "google_ai_studio"]:
            vision_api_key = settings.google_api_key
        elif p == "kilocode":
            vision_api_key = settings.kilocode_api_key
        elif p == "groq":
            vision_api_key = os.getenv("GROQ_API_KEY")
        elif p == "anthropic":
            vision_api_key = os.getenv("ANTHROPIC_API_KEY")
        elif p == "deepseek":
            vision_api_key = os.getenv("DEEPSEEK_API_KEY")
        elif p == "mistral":
            vision_api_key = os.getenv("MISTRAL_API_KEY")
        elif p == "cerebras":
            vision_api_key = os.getenv("CEREBRAS_API_KEY")

    main_api_key = _sanitize_ascii(main_api_key) if main_api_key else None
    fast_api_key = _sanitize_ascii(fast_api_key) if fast_api_key else None
    vision_api_key = _sanitize_ascii(vision_api_key) if vision_api_key else None

    # --- INICIALIZACIÓN DE MODELOS ---
    try:
        logger.info(f"Inicializando LLM Principal: {eff_llm_model}")

        llm_kwargs = {
            "model_name": eff_llm_model,
            "temperature": eff_llm_temperature,
            "streaming": True,
            "verbose": False,
            "max_retries": 0,  # We handle rate limiting, so disable litellm's retries for this
            "rate_limiter": gemini_rate_limiter,  # Pass the compliant rate limiter
            "max_tokens": settings.deep_research_max_tokens,  # Allow for massive reports
            "timeout": settings.llm_request_timeout,
        }

        if use_gpu:
            llm_kwargs["device"] = "cuda"
            llm_kwargs["force_redownload"] = (
                True  # Forzar la descarga para asegurar la compatibilidad de la GPU
            )

        if eff_llm_api_base:
            llm_kwargs["api_base"] = eff_llm_api_base

        if main_api_key:
            llm_kwargs["api_key"] = main_api_key

        # Configurar proveedor específico según el formato del modelo
        model_lower = eff_llm_model.lower()

        if "openrouter" in model_lower:
            logger.info("🔧 Applying OpenRouter specific config for main LLM.")
            llm_kwargs["api_base"] = "https://openrouter.ai/api/v1"

            # Normalizar el nombre del modelo - eliminar prefijo openrouter/ para evitar duplicados
            actual_id = normalize_openrouter_model_name(eff_llm_model)

            # Configurar el nombre del modelo con el prefijo openrouter/ necesario para LiteLLM
            llm_kwargs["model_name"] = f"openrouter/{actual_id}"

            # No forzar provider=openai para que LiteLLM reconozca openrouter/ y elimine el prefijo al enviar
            if "provider" in llm_kwargs:
                del llm_kwargs["provider"]

            # Aplicar lógica de adaptador universal según el modelo
            apply_openrouter_model_specific_logic(actual_id, llm_kwargs)

            # Headers recomendados por OpenRouter para mejor soporte y visibilidad
            if "extra_headers" not in llm_kwargs:
                llm_kwargs["extra_headers"] = {}
            llm_kwargs["extra_headers"]["HTTP-Referer"] = (
                "https://kognito.ai"  # Identificador de la app
            )
            llm_kwargs["extra_headers"]["X-Title"] = "Kognito AI"
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
            llm_kwargs["api_base"] = "https://generativelanguage.googleapis.com/v1beta"
            llm_kwargs.pop("vertex_project_id", None)
            llm_kwargs.pop("vertex_location", None)
            if not llm_kwargs["model_name"].startswith("gemini/"):
                llm_kwargs["model_name"] = f"gemini/{llm_kwargs['model_name']}"
            logger.info(
                f"🔧 Google AI Studio: endpoint forzado, modelo={llm_kwargs['model_name']}"
            )

        elif "openai" in model_lower or "gpt" in model_lower:
            logger.info("🔧 Applying OpenAI/GPT specific config.")
        elif "kilocode" in model_lower:
            logger.info("🔧 Applying Kilocode Gateway specific config for main LLM.")
            kilocode_base = "https://api.kilo.ai/api/gateway"
            llm_kwargs["api_base"] = kilocode_base

            # Autenticación: Usar API key
            if main_api_key:
                llm_kwargs["api_key"] = main_api_key

            # Normalizar el nombre del modelo
            actual_model = eff_llm_model
            if actual_model.startswith("kilocode/"):
                actual_model = actual_model[len("kilocode/") :]

            # Asegurarnos de que el model_name tenga prefijo openai/ para LiteLLM
            llm_kwargs["model_name"] = f"openai/{actual_model}"
            llm_kwargs["custom_llm_provider"] = "openai"

        # --- FIX: Sanitize kwargs to prevent UnicodeEncodeError in headers ---
        llm_kwargs = _sanitize_llm_kwargs(llm_kwargs)

        main_llm = ChatLiteLLM(**llm_kwargs)
        # Patch the instance explicitly if LiteLLM didn't pick it up
        if hasattr(main_llm, "custom_llm_provider") and llm_kwargs.get(
            "custom_llm_provider"
        ):
            main_llm.custom_llm_provider = llm_kwargs["custom_llm_provider"]
        elif "openrouter" in model_lower:
            main_llm.custom_llm_provider = "openrouter"
        _main_agent_llm_instance = main_llm
        logger.info("Modelo LLM Principal listo.")

    except Exception as e:
        logger.error(f"❌ FATAL: Failed to initialize the main LLM: {e}", exc_info=True)
        raise

    try:
        logger.info(f"Inicializando LLM Rápido: {eff_fast_llm_model}")
        fast_llm_kwargs = {
            "model_name": eff_fast_llm_model,
            "temperature": 0.0,
            "streaming": True,
            "verbose": False,
            "max_retries": 0,
            "rate_limiter": gemini_rate_limiter,  # Use the same rate limiter instance
            "timeout": settings.llm_request_timeout,
        }

        if use_gpu:
            fast_llm_kwargs["device"] = "cuda"

        if eff_llm_api_base:
            fast_llm_kwargs["api_base"] = eff_llm_api_base

        if fast_api_key:
            fast_llm_kwargs["api_key"] = fast_api_key

        # Configurar proveedor específico según el formato del modelo
        fast_model_lower = eff_fast_llm_model.lower()

        if "openrouter" in fast_model_lower:
            logger.info("🔧 Applying OpenRouter specific config for fast LLM.")
            fast_llm_kwargs["api_base"] = "https://openrouter.ai/api/v1"
            actual_id = normalize_openrouter_model_name(eff_fast_llm_model)
            fast_llm_kwargs["model_name"] = f"openrouter/{actual_id}"
            if "provider" in fast_llm_kwargs:
                del fast_llm_kwargs["provider"]
            apply_openrouter_model_specific_logic(actual_id, fast_llm_kwargs)
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
            fast_llm_kwargs["api_base"] = (
                "https://generativelanguage.googleapis.com/v1beta"
            )
            fast_llm_kwargs.pop("vertex_project_id", None)
            fast_llm_kwargs.pop("vertex_location", None)
            if not fast_llm_kwargs["model_name"].startswith("gemini/"):
                fast_llm_kwargs["model_name"] = (
                    f"gemini/{fast_llm_kwargs['model_name']}"
                )
            logger.info(
                f"🔧 Google AI Studio (fast): endpoint forzado, modelo={fast_llm_kwargs['model_name']}"
            )

        elif "openai" in fast_model_lower or "gpt" in fast_model_lower:
            logger.info("🔧 Applying OpenAI/GPT specific config for fast LLM.")
        elif "kilocode" in fast_model_lower:
            logger.info("🔧 Applying Kilocode Gateway specific config for fast LLM.")
            kilocode_base = "https://api.kilo.ai/api/gateway"
            fast_llm_kwargs["api_base"] = kilocode_base

            # Autenticación
            if fast_api_key:
                fast_llm_kwargs["api_key"] = fast_api_key

            # Normalizar el nombre del modelo
            actual_model = eff_fast_llm_model
            if actual_model.startswith("kilocode/"):
                actual_model = actual_model[len("kilocode/") :]

            # Asegurarnos de que el model_name tenga prefijo openai/ para LiteLLM
            fast_llm_kwargs["model_name"] = f"openai/{actual_model}"
            fast_llm_kwargs["custom_llm_provider"] = "openai"

        # --- FIX: Sanitize kwargs to prevent UnicodeEncodeError in headers ---
        fast_llm_kwargs = _sanitize_llm_kwargs(fast_llm_kwargs)

        fast_llm = ChatLiteLLM(**fast_llm_kwargs)
        # Patch the instance explicitly if LiteLLM didn't pick it up
        if hasattr(fast_llm, "custom_llm_provider") and fast_llm_kwargs.get(
            "custom_llm_provider"
        ):
            fast_llm.custom_llm_provider = fast_llm_kwargs["custom_llm_provider"]
        elif "openrouter" in fast_model_lower:
            fast_llm.custom_llm_provider = "openrouter"
        _fast_task_llm_instance = fast_llm
        logger.info("Modelo LLM Rápido listo.")
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to initialize the fast task LLM. The main LLM will be used as a fallback: {e}"
        )
        _fast_task_llm_instance = _main_agent_llm_instance

    try:
        logger.info(f"Inicializando LLM Visión: {eff_vision_llm_model}")
        vision_llm_kwargs = {
            "model_name": eff_vision_llm_model,
            "temperature": 0.0,
            "streaming": True,
            "verbose": False,
            "max_retries": 0,
            "rate_limiter": gemini_rate_limiter,
            "timeout": settings.llm_request_timeout,
        }

        if use_gpu:
            vision_llm_kwargs["device"] = "cuda"

        if vision_api_key:
            vision_llm_kwargs["api_key"] = vision_api_key

        # Configurar proveedor específico según el formato del modelo
        vision_model_lower = eff_vision_llm_model.lower()

        if "openrouter" in vision_model_lower:
            logger.info("🔧 Applying OpenRouter specific config for vision LLM.")
            vision_llm_kwargs["api_base"] = "https://openrouter.ai/api/v1"
            actual_id = normalize_openrouter_model_name(eff_vision_llm_model)
            vision_llm_kwargs["model_name"] = f"openrouter/{actual_id}"
            if "provider" in vision_llm_kwargs:
                del vision_llm_kwargs["provider"]
            apply_openrouter_model_specific_logic(actual_id, vision_llm_kwargs)
        elif "anthropic" in vision_model_lower:
            logger.info("🔧 Applying Anthropic specific config for vision LLM.")
            vision_llm_kwargs["provider"] = "anthropic"
        elif "groq" in vision_model_lower:
            logger.info("🔧 Applying Groq specific config for vision LLM.")
            vision_llm_kwargs["provider"] = "groq"
        elif "gemini" in vision_model_lower:
            logger.info("🔧 Applying Gemini specific config for vision LLM.")
            vision_llm_kwargs["provider"] = "google_ai_studio"
            vision_llm_kwargs["api_base"] = (
                "https://generativelanguage.googleapis.com/v1beta"
            )
            vision_llm_kwargs.pop("vertex_project_id", None)
            vision_llm_kwargs.pop("vertex_location", None)
            if not vision_llm_kwargs["model_name"].startswith("gemini/"):
                vision_llm_kwargs["model_name"] = (
                    f"gemini/{vision_llm_kwargs['model_name']}"
                )
            logger.info(
                f"🔧 Google AI Studio (vision): endpoint forzado, modelo={vision_llm_kwargs['model_name']}"
            )

        elif "openai" in vision_model_lower or "gpt" in vision_model_lower:
            logger.info("🔧 Applying OpenAI/GPT specific config for vision LLM.")
        elif "kilocode" in vision_model_lower:
            logger.info("🔧 Applying Kilocode Gateway specific config for vision LLM.")
            kilocode_base = "https://api.kilo.ai/api/gateway"
            vision_llm_kwargs["api_base"] = kilocode_base

            # Autenticación
            if vision_api_key:
                vision_llm_kwargs["api_key"] = vision_api_key

            # Normalizar el nombre del modelo
            actual_model = eff_vision_llm_model
            if actual_model.startswith("kilocode/"):
                actual_model = actual_model[len("kilocode/") :]

            # Asegurarnos de que el model_name tenga prefijo openai/ para LiteLLM
            vision_llm_kwargs["model_name"] = f"openai/{actual_model}"
            vision_llm_kwargs["custom_llm_provider"] = "openai"

        # --- FIX: Sanitize kwargs to prevent UnicodeEncodeError in headers ---
        vision_llm_kwargs = _sanitize_llm_kwargs(vision_llm_kwargs)

        vision_llm = ChatLiteLLM(**vision_llm_kwargs)
        # Patch the instance explicitly if LiteLLM didn't pick it up
        if hasattr(vision_llm, "custom_llm_provider") and vision_llm_kwargs.get(
            "custom_llm_provider"
        ):
            vision_llm.custom_llm_provider = vision_llm_kwargs["custom_llm_provider"]
        elif "openrouter" in vision_model_lower:
            vision_llm.custom_llm_provider = "openrouter"
        _vision_llm_instance = vision_llm
        logger.info("Modelo LLM Visión listo.")
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to initialize the vision LLM. The main LLM will be used as a fallback: {e}"
        )
        _vision_llm_instance = _main_agent_llm_instance


async def get_enhanced_llm_response(
    user_message: str,
    user_id: str,
    workspace_id: Optional[str] = None,
    use_knowledge_graph: bool = True,
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
            enhanced_context = await _get_enhanced_context(
                user_message, user_id, workspace_id
            )

        # 2. Construir prompt enriquecido
        enriched_prompt = await _build_enriched_prompt(user_message, enhanced_context)

        # 3. Obtener respuesta del LLM
        llm = get_main_llm()
        if not llm:
            raise ValueError("LLM no inicializado")

        # Log del modelo en uso
        # Try the common attribute names for the underlying model identifier
        model_name = getattr(llm, "model_name", getattr(llm, "model", "unknown"))
        logger.info(
            f"🤖 ENHANCED RESPONSE: Usando modelo '{model_name}' para generar respuesta."
        )

        logger.info(
            f"📝 Prompt para respuesta enriquecida enviado al LLM."
        )  # Log del prompt
        response = await _invoke_llm_cached(llm, enriched_prompt)
        logger.info(
            f"🗣️ Respuesta cruda del LLM para respuesta enriquecida recibida."
        )  # Log de la respuesta cruda del LLM

        # 4. Procesar y enriquecer la respuesta
        enhanced_response = {
            "response": response.content
            if hasattr(response, "content")
            else str(response),
            "user_message": user_message,
            "enhanced_context": enhanced_context,
            "reasoning_used": enhanced_context is not None,
            "timestamp": datetime.now().isoformat(),
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


async def _get_enhanced_context(
    user_message: str, user_id: str, workspace_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
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
            password=settings.neo4j_password,
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


async def _build_enriched_prompt(
    user_message: str, enhanced_context: Optional[Dict[str, Any]] = None
) -> str:
    """Construye un prompt enriquecido con contexto del grafo de conocimiento."""

    base_prompt = f"Usuario: {user_message}"

    if not enhanced_context:
        return base_prompt

    # Agregar contexto del grafo de conocimiento
    enriched_prompt = f"""Contexto del Grafo de Conocimiento:

"""

    # Agregar entidades relevantes
    entities = (
        enhanced_context.get("sources", {})
        .get("knowledge_graph", {})
        .get("entities", [])
    )
    if entities:
        enriched_prompt += "Entidades relevantes encontradas:\n"
        for entity in entities[:5]:
            enriched_prompt += f"- {entity.get('name', '')}: {entity.get('description', '')} (confianza: {entity.get('confidence', 0):.2f})\n"
        enriched_prompt += "\n"

    # Agregar relaciones relevantes
    relationships = (
        enhanced_context.get("sources", {})
        .get("knowledge_graph", {})
        .get("relationships", [])
    )
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


async def _save_enhanced_interaction(
    enhanced_response: Dict[str, Any], user_id: str
) -> None:
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
            "response": response.content
            if hasattr(response, "content")
            else str(response),
            "user_message": user_message,
            "enhanced_context": None,
            "reasoning_used": False,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error en respuesta tradicional: {e}")
        return {
            "response": "Lo siento, hubo un error procesando tu solicitud.",
            "user_message": user_message,
            "enhanced_context": None,
            "reasoning_used": False,
            "error": str(e),
        }
