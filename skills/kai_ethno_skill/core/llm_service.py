"""
LLM Service - Interface unificada para invocación de LLMs en los agentes de KAI-Ethno
Integrado directamente con KognitoAI Core (core/llm_manager.py) y fallback a LangChain autónomo.
"""

import os
import sys
import logging
import asyncio
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)

# Intentar agregar la raíz del proyecto KognitoAI al sys.path si no está
kognito_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if os.path.exists(os.path.join(kognito_root, "core", "llm_manager.py")):
    if kognito_root not in sys.path:
        sys.path.insert(0, kognito_root)

# Importar funciones de KognitoAI si están disponibles
_has_kognito_llm_manager = False
try:
    from core.llm_manager import get_main_llm, get_fast_llm, get_fallback_llm, get_llm_for_user
    _has_kognito_llm_manager = True
except Exception as e:
    logger.debug(f"KognitoAI core.llm_manager no disponible: {e}")
    _has_kognito_llm_manager = False


class LLMService:
    """
    Servicio unificado de LLM para los agentes de KAI-Ethno.
    Utiliza el LLMManager de KognitoAI si está disponible, o cae a LangChain/APIs públicas.
    """

    def __init__(
        self,
        account_id: Optional[str] = None,
        purpose: str = "main",
        model_name: Optional[str] = None,
        temperature: float = 0.3
    ):
        self.account_id = account_id
        self.purpose = purpose
        self.temperature = temperature
        self.model_name = model_name
        self.llm = self._initialize_llm()

    def _initialize_llm(self) -> Optional[Any]:
        """Intenta inicializar el cliente LLM según KognitoAI Core o claves de API."""
        # 1. Intentar KognitoAI Central LLM Manager
        if _has_kognito_llm_manager:
            try:
                if self.purpose == "fast":
                    llm_inst = get_fast_llm()
                else:
                    llm_inst = get_main_llm()

                if not llm_inst:
                    llm_inst = get_fallback_llm()

                if llm_inst:
                    logger.info("LLMService: Usando LLMManager central de KognitoAI")
                    return llm_inst
            except Exception as e:
                logger.warning(f"Error obteniendo LLM de KognitoAI LLMManager: {e}")

        # 2. Intentar OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                from langchain_openai import ChatOpenAI
                model = self.model_name or "gpt-4o-mini"
                logger.info(f"LLMService: Inicializando ChatOpenAI ({model})")
                return ChatOpenAI(model=model, temperature=self.temperature)
            except ImportError:
                try:
                    from langchain_community.chat_models import ChatOpenAI
                    model = self.model_name or "gpt-4o-mini"
                    return ChatOpenAI(model_name=model, temperature=self.temperature)
                except ImportError:
                    pass

        # 3. Intentar Google Gemini
        if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                model = self.model_name or "gemini-1.5-flash"
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                logger.info(f"LLMService: Inicializando ChatGoogleGenerativeAI ({model})")
                return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=self.temperature)
            except ImportError:
                pass

        logger.info("LLMService: Sin LLM activo. Modo heurístico como fallback.")
        return None

    def is_available(self) -> bool:
        """Retorna True si hay un modelo de lenguaje cargado y funcional."""
        return self.llm is not None

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Ejecuta una consulta al LLM de forma asíncrona.
        Retorna la respuesta en formato texto o None si falla / no está disponible.
        """
        # Si tenemos account_id y KognitoAI manager, consultar LLM personalizado del usuario
        if self.account_id and _has_kognito_llm_manager:
            try:
                user_llm = await get_llm_for_user(self.account_id, purpose=self.purpose)
                if user_llm:
                    self.llm = user_llm
            except Exception as e:
                logger.warning(f"Error obteniendo LLM de usuario {self.account_id}: {e}")

        if not self.llm:
            return None

        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            if hasattr(self.llm, "ainvoke"):
                response = await self.llm.ainvoke(messages)
                return response.content if hasattr(response, "content") else str(response)
            elif hasattr(self.llm, "invoke"):
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, self.llm.invoke, messages)
                return response.content if hasattr(response, "content") else str(response)
            else:
                return None

        except Exception as e:
            logger.error(f"Error invocando LLMService: {e}", exc_info=True)
            return None


# Helper singleton opcional para resolución rápida
_default_llm_service: Optional[LLMService] = None

def get_default_llm_service(account_id: Optional[str] = None) -> LLMService:
    global _default_llm_service
    if _default_llm_service is None or account_id != _default_llm_service.account_id:
        _default_llm_service = LLMService(account_id=account_id)
    return _default_llm_service
