# core/llm_manager.py

import logging
from typing import Optional
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings

logger = logging.getLogger(__name__)

# --- Global LLM Instances ---
# These are initialized by `initialize_llms` when the server starts.
_main_agent_llm_instance: Optional[BaseLanguageModel] = None
_fast_task_llm_instance: Optional[BaseLanguageModel] = None

def get_main_llm() -> Optional[BaseLanguageModel]:
    """Returns the initialized main agent LLM instance."""
    return _main_agent_llm_instance

def get_fast_llm() -> Optional[BaseLanguageModel]:
    """Returns the initialized fast task LLM instance, or the main one as a fallback."""
    return _fast_task_llm_instance or _main_agent_llm_instance

async def initialize_llms():
    """
    Initializes the global instances of the LLMs (main and fast task).
    This function is called once when the web_server starts.
    """
    global _main_agent_llm_instance, _fast_task_llm_instance
    
    if not settings.google_api_key:
        logger.error("FATAL ERROR! GOOGLE_API_KEY is not configured. The agent cannot function.")
        raise ValueError("Google API key has not been configured.")

    try:
        logger.info(f"🛠️ Initializing main agent LLM (ChatGoogleGenerativeAI - {settings.google_main_model_name})...")
        main_llm = ChatGoogleGenerativeAI(
            model=settings.google_main_model_name,
            temperature=settings.llm_temperature,
            google_api_key=settings.google_api_key,
            disable_streaming=False,  # Habilita streaming (False = streaming activado)
        )
        await main_llm.ainvoke("Test prompt")
        _main_agent_llm_instance = main_llm
        logger.info("✅ Main agent LLM initialized.")
    except Exception as e:
        logger.error(f"❌ FATAL: Failed to initialize the main LLM: {e}", exc_info=True)
        raise

    try:
        logger.info(f"🛠️ Initializing fast task LLM (ChatGoogleGenerativeAI - {settings.google_summary_model_name})...")
        fast_llm = ChatGoogleGenerativeAI(
            model=settings.google_summary_model_name,
            temperature=0.0,
            google_api_key=settings.google_api_key,
            disable_streaming=False,  # Habilita streaming (False = streaming activado)
        )
        await fast_llm.ainvoke("Test prompt")
        _fast_task_llm_instance = fast_llm
        logger.info("✅ Fast task LLM initialized.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize the fast task LLM. The main LLM will be used as a fallback: {e}")
        _fast_task_llm_instance = _main_agent_llm_instance
