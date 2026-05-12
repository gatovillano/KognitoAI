"""
Deep Research Tool adaptado para usar LiteLLM de Kognito AI.

Esta versión modifica el comportamiento de Open Deep Research para usar
los modelos LLM ya configurados en Kognito AI a través de LiteLLM,
evitando la duplicación de configuración de modelos.
"""

import logging
import traceback
from typing import Type, Optional, Dict, Any
from pydantic import BaseModel, Field

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.tools import BaseTool, Tool
from core.llm_manager import get_main_llm, get_fast_llm
from core.config import settings

logger = logging.getLogger(__name__)

# Importar componentes de Open Deep Research
try:
    from external_agents.open_deep_research.src.open_deep_research.deep_researcher import (
        deep_researcher_builder,
        AgentState,
        AgentInputState
    )
    from external_agents.open_deep_research.src.open_deep_research.configuration import (
        Configuration as ResearchConfig,
        SearchAPI
    )
    DEEP_RESEARCH_AVAILABLE = True
except ImportError as e:
    logger.error(f"Error importing deep_researcher: {e}")
    traceback.print_exc()
    DEEP_RESEARCH_AVAILABLE = False


class DeepResearchToolInput(BaseModel):
    """Input schema for Deep Research Tool."""
    query: str = Field(description="The research query or topic to investigate in detail.")
    max_iterations: int = Field(
        default=6,
        description="Maximum number of research iterations (default: 6)"
    )
    max_concurrent_units: int = Field(
        default=3,
        description="Maximum number of parallel research units (default: 3)"
    )


class DeepResearchToolLiteLLM(BaseTool):
    """
    Deep Research Tool que usa los LLMs de Kognito AI (LiteLLM).
    
    Esta herramienta realiza investigación profunda multi-nivel usando
    los modelos LLM ya configurados en Kognito AI, evitando duplicación
    de configuración y aprovechando LiteLLM para flexibilidad de modelos.
    """
    
    name: str = "deep_research_litellm"
    description: str = (
        "Performs comprehensive deep research on a given query using Kognito's "
        "configured LLM models. Leverages multiple sources, parallel research units, "
        "and generates detailed reports. Results are automatically added to RAG."
    )
    args_schema: Type[BaseModel] = DeepResearchToolInput
    
    _web_search_tool: Optional[Tool] = None
    _add_web_to_rag_tool: Optional[Any] = None
    _compiled_graph: Optional[Any] = None

    # Atributos para la inyección de contexto desde el agente
    account_id: Optional[str] = None
    workspace_id: Optional[str] = None
    telegram_id: Optional[int] = None

    def __init__(
        self,
        web_search_tool: Tool,
        add_web_to_rag_tool: Any,
        **data
    ):
        """
        Initialize Deep Research Tool with LiteLLM support.
        
        Args:
            web_search_tool: Web search tool for gathering information
            add_web_to_rag_tool: Tool for adding research results to RAG
        """
        super().__init__(**data)
        self._web_search_tool = web_search_tool
        self._add_web_to_rag_tool = add_web_to_rag_tool

        if DEEP_RESEARCH_AVAILABLE:
            # Compilar el grafo de investigación
            self._compiled_graph = deep_researcher_builder.compile()
            logger.info("✅ DeepResearchToolLiteLLM initialized with Kognito's LLM models")
        else:
            logger.warning("❌ Deep Research module not available. Tool will not function.")

    async def _create_litellm_compatible_config(
        self,
        max_iterations: int = 6,
        max_concurrent_units: int = 3
    ) -> Dict[str, Any]:
        """
        Crea una configuración compatible con LiteLLM para Open Deep Research.
        """
        from core.llm_manager import get_llm_for_user
        
        # Obtener los LLMs de Kognito adaptados al usuario
        if self.account_id:
            main_llm = await get_llm_for_user(self.account_id, purpose="main")
            fast_llm = await get_llm_for_user(self.account_id, purpose="fast")
        else:
            main_llm = get_main_llm()
            fast_llm = get_fast_llm()
        
        if not main_llm:
            raise ValueError("Main LLM not initialized in Kognito AI")
        
        # Extraer el nombre del modelo de LiteLLM
        main_model_name = getattr(main_llm, 'model', settings.llm_model)
        fast_model_name = getattr(fast_llm, 'model', settings.fast_llm_model) if fast_llm else main_model_name
        
        # Mapear al formato esperado por Open Deep Research
        research_model = self._convert_to_langchain_format(main_model_name)
        compression_model = self._convert_to_langchain_format(fast_model_name)
        
        logger.info(f"🔧 Configurando Deep Research con modelos de Kognito:")
        logger.info(f"   - Research Model: {research_model} (from {main_model_name})")
        logger.info(f"   - Compression Model: {compression_model} (from {fast_model_name})")
        
        # Determinar la API Key correcta basada en el proveedor del modelo principal
        api_key = settings.openrouter_api_key
        if "google" in research_model or "gemini" in research_model:
             api_key = settings.google_api_key
        elif "openai" in research_model and "openrouter" not in research_model:
             api_key = settings.openai_api_key if hasattr(settings, 'openai_api_key') else None

        # Configurar Base URL para OpenRouter si es necesario
        if "openrouter" in main_model_name or "openrouter" in research_model:
            import os
            # Asegurar que LangChain use OpenRouter como base URL si el modelo es de OpenRouter
            # Esto es necesario porque init_chat_model con provider="openai" usa OPENAI_API_BASE
            os.environ["OPENAI_API_BASE"] = settings.llm_api_base or "https://openrouter.ai/api/v1"
            logger.info(f"   - Configurando OPENAI_API_BASE para OpenRouter: {os.environ['OPENAI_API_BASE']}")

        # Configuración para el grafo
        config = {
            "configurable": {
                # Modelos (usando los de Kognito)
                "research_model": research_model,
                "compression_model": compression_model,
                "summarization_model": compression_model,  # Usar el modelo rápido
                "final_report_model": research_model,  # Usar el modelo principal
                
                # API Keys
                "api_key": api_key,
                
                # Configuración de investigación
                "max_researcher_iterations": max_iterations,
                "max_concurrent_research_units": max_concurrent_units,
                "max_react_tool_calls": 10,
                "max_structured_output_retries": 3,
                
                # Búsqueda
                "search_api": SearchAPI.TAVILY.value,
                "tavily_api_key": settings.tavily_api_key,
                
                # Configuración de contenido
                "max_content_length": 50000,
                
                # Tokens
                "research_model_max_tokens": 10000,
                "compression_model_max_tokens": 8192,
                "summarization_model_max_tokens": 8192,
                "final_report_model_max_tokens": 10000,
                
                # Clarificación
                "allow_clarification": False,  # Deshabilitado para uso automático
            }
        }
        
        return config

    def _convert_to_langchain_format(self, litellm_model: str) -> str:
        """
        Convierte el formato de modelo de LiteLLM al formato de LangChain.
        
        LiteLLM usa: "openrouter/anthropic/claude-3.5-sonnet"
        LangChain usa: "anthropic:claude-3.5-sonnet"
        
        Args:
            litellm_model: Nombre del modelo en formato LiteLLM
            
        Returns:
            Nombre del modelo en formato LangChain
        """
        # Si ya está en formato LangChain, retornar tal cual
        if ':' in litellm_model and '/' not in litellm_model:
            return litellm_model
        
        # Mapeo de proveedores comunes
        provider_mapping = {
            'openrouter': 'openai', # OpenRouter usa cliente OpenAI
            'openai': 'openai',
            'anthropic': 'anthropic',
            'google': 'google_genai', # LangChain usa google_genai para Gemini
            'gemini': 'google_genai',
            'vertex_ai': 'google_vertexai',
        }
        
        # Manejo especial para OpenRouter
        if litellm_model.startswith('openrouter/'):
            # Formato: openrouter/provider/model -> openai:provider/model
            # OpenRouter actúa como un proxy OpenAI
            model_part = litellm_model.replace('openrouter/', '')
            return f"openai:{model_part}"

        # Manejo especial para Google/Gemini
        if litellm_model.startswith('gemini/') or litellm_model.startswith('google/'):
             # Formato: gemini/gemini-pro -> google_genai:gemini-pro
             parts = litellm_model.split('/')
             model_name = parts[-1]
             return f"google_genai:{model_name}"

        # Extraer proveedor y modelo para otros casos
        parts = litellm_model.split('/')
        
        if len(parts) >= 2:
            provider_key = parts[0]
            model_name = '/'.join(parts[1:])
            
            # Buscar mapeo de proveedor
            for key, provider in provider_mapping.items():
                if provider_key.startswith(key):
                    return f"{provider}:{model_name}"
        
        # Fallback: usar OpenAI como proveedor por defecto
        logger.warning(f"⚠️ No se pudo mapear el modelo '{litellm_model}', usando formato OpenAI")
        return f"openai:{litellm_model}"

    def _run(
        self,
        query: str,
        max_iterations: int = 6,
        max_concurrent_units: int = 3
    ) -> str:
        """
        Ejecución sincrónica (fallback).
        """
        import asyncio
        try:
            # Intentar ejecutar de forma asíncrona en el bucle actual o uno nuevo
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return "Error: Esta herramienta requiere ejecución asíncrona."
                return loop.run_until_complete(self._arun(query, max_iterations, max_concurrent_units))
            except RuntimeError:
                return asyncio.run(self._arun(query, max_iterations, max_concurrent_units))
        except Exception as e:
            return f"Error en ejecución sincrónica de Deep Research: {str(e)}"

    async def _arun(
        self,
        query: str,
        max_iterations: int = 6,
        max_concurrent_units: int = 3
    ) -> str:
        """
        Ejecuta la investigación profunda usando los LLMs de Kognito.
        
        Args:
            query: Consulta de investigación
            max_iterations: Máximo de iteraciones
            max_concurrent_units: Máximo de unidades en paralelo
            
        Returns:
            Informe de investigación completo
        """
        if not self._compiled_graph:
            return "❌ Error: Deep Research module not initialized correctly."

        logger.info(f"🚀 Iniciando investigación profunda con LiteLLM para: {query}")
        
        try:
            # Crear configuración usando los LLMs de Kognito
            config = await self._create_litellm_compatible_config(
                max_iterations=max_iterations,
                max_concurrent_units=max_concurrent_units
            )
            
            # Preparar input para el grafo
            inputs = {"messages": [("user", query)]}
            
            # Ejecutar el grafo de investigación
            logger.info("🔍 Ejecutando grafo de investigación...")
            research_result = await self._compiled_graph.ainvoke(inputs, config=config)
            
            # Extraer el informe final
            research_report = research_result.get("final_report", "No se generó un informe final.")
            
            logger.info(f"✅ Investigación completada. Longitud del informe: {len(research_report)} caracteres")
            
            # Guardar en RAG si está disponible
            if self._add_web_to_rag_tool:
                try:
                    rag_result = await self._add_web_to_rag_tool._run(
                        url="",
                        content=research_report,
                        title=f"Deep Research Report: {query}",
                        topic=query
                    )
                    logger.info(f"💾 Informe añadido a RAG: {rag_result}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo añadir a RAG: {e}")
            
            return research_report
            
        except Exception as e:
            logger.error(f"❌ Error durante la investigación profunda: {e}", exc_info=True)
            return f"Error al realizar la investigación profunda: {str(e)}"


# Factory function para crear la herramienta
def create_deep_research_tool_litellm(
    web_search_tool: Tool,
    add_web_to_rag_tool: Any
) -> Optional[DeepResearchToolLiteLLM]:
    """
    Crea una instancia de DeepResearchToolLiteLLM.
    
    Args:
        web_search_tool: Herramienta de búsqueda web
        add_web_to_rag_tool: Herramienta para añadir a RAG
        
    Returns:
        Instancia de la herramienta o None si no está disponible
    """
    if not DEEP_RESEARCH_AVAILABLE:
        logger.warning("Deep Research module not available")
        return None
    
    return DeepResearchToolLiteLLM(
        web_search_tool=web_search_tool,
        add_web_to_rag_tool=add_web_to_rag_tool
    )
