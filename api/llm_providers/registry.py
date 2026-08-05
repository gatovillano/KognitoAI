import asyncio
import logging
from typing import List, Dict, Any
from .base import LLMProviderStrategy
from .openrouter_provider import OpenRouterProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepseekProvider
from .mistral_provider import MistralProvider
from .groq_provider import GroqProvider
from .cerebras_provider import CerebrasProvider
from .ollama_provider import OllamaProvider
from .ollama_cloud_provider import OllamaCloudProvider
from .openai_compatible_provider import OpenAICompatibleProvider
from .azure_provider import AzureProvider
from .kilocode_provider import KilocodeProvider
from .nvidia_provider import NvidiaProvider
from .huggingface_provider import HuggingFaceProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registro y orquestador de proveedores LLM."""

    def __init__(self):
        self._providers: Dict[str, LLMProviderStrategy] = {
            "openrouter": OpenRouterProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "gemini": GeminiProvider(),
            "deepseek": DeepseekProvider(),
            "mistral": MistralProvider(),
            "groq": GroqProvider(),
            "cerebras": CerebrasProvider(),
            "ollama": OllamaProvider(),
            "ollama_cloud": OllamaCloudProvider(),
            "openai_compatible": OpenAICompatibleProvider(),
            "azure": AzureProvider(),
            "kilocode": KilocodeProvider(),
            "nvidia": NvidiaProvider(),
            "huggingface": HuggingFaceProvider(),
            # Alias para compatibilidad con llamadas existentes
            "google": GeminiProvider(),
        }

    def register_provider(self, name: str, provider: LLMProviderStrategy):
        self._providers[name] = provider

    async def get_all_models(self) -> List[Dict[str, Any]]:
        """Obtiene los modelos de todos los proveedores registrados en paralelo."""
        tasks = []
        for name, provider in self._providers.items():
            tasks.append(self._safe_get_models(name, provider))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_models = []
        for result in results:
            if isinstance(result, list):
                all_models.extend(result)
            elif isinstance(result, Exception):
                logger.error("Excepción al recolectar modelos: %s", result)

        return all_models

    async def _safe_get_models(self, name: str, provider: LLMProviderStrategy) -> List[Dict[str, Any]]:
        """Llama al proveedor de forma segura manejando excepciones."""
        try:
            # Aquí podríamos pasar api_key y api_base si los extraemos de la DB o config
            return await provider.get_models(api_key=None, api_base=None)
        except Exception as e:
            logger.error("Error en proveedor %s: %s", name, e)
            return []


# Instancia global del registry
provider_registry = ProviderRegistry()
