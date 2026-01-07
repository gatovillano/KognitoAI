# utils/llm_logging_config.py

"""
Configuración específica para el logging detallado del LLM.
Este módulo configura loggers especializados para capturar toda la comunicación
con el LLM de manera estructurada y fácil de analizar.
"""

import logging
import os
from datetime import datetime
from typing import Optional
from utils.security import PIISanitizer

class PIIRedactionFormatter(logging.Formatter):
    """Formatter que redacta PII automáticamente de los mensajes de log."""
    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, str):
            record.msg = PIISanitizer.sanitize(record.msg)
        elif isinstance(record.msg, (dict, list)):
            record.msg = str(PIISanitizer.sanitize_dict(record.msg))
        return super().format(record)

def setup_llm_detailed_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configura logging detallado específico para las comunicaciones del LLM.

    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Archivo opcional para guardar logs específicos del LLM
    """

    # Crear un formatter específico para logs del LLM con redacción de PII
    llm_formatter = PIIRedactionFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configurar loggers específicos con propagación controlada
    loggers_config = {
        "LLMCallback": logging.INFO,  # Nuestro callback personalizado
        "core.agent": logging.INFO,   # Logs del agente
        "langchain.agents.agent": logging.WARNING,  # Mantenemos WARNING para producción
        "langchain_google_genai": logging.WARNING,  # Mantenemos WARNING para producción
        "tools.github_repo_tool": logging.INFO, # Cambiado a INFO para producción
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

        # Evitar propagación para prevenir duplicados
        if logger_name.startswith("LLMCallback"):
            logger.propagate = False

        # Solo añadir handler si no existe
        if not logger.handlers and logger_name.startswith("LLMCallback"):
            handler = logging.StreamHandler()
            handler.setFormatter(llm_formatter)
            logger.addHandler(handler)

    # Si se especifica un archivo de log, crear un handler específico para LLM
    if log_file:
        # Crear directorio si no existe
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Handler para archivo específico del LLM
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(llm_formatter)
        file_handler.setLevel(logging.DEBUG)

        # Añadir el handler solo a nuestros loggers personalizados
        llm_specific_loggers = [
            "LLMCallback",
            "core.agent"
        ]

        for logger_name in llm_specific_loggers:
            logger = logging.getLogger(logger_name)
            if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
                logger.addHandler(file_handler)

    logging.getLogger(__name__).info(f"✅ Logging detallado del LLM configurado - Nivel: {log_level}")

def create_llm_log_filename() -> str:
    """
    Crea un nombre de archivo único para los logs del LLM basado en la fecha y hora actual.
    
    Returns:
        str: Nombre del archivo de log
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"logs/llm_detailed_{timestamp}.log"

def enable_verbose_langchain_logging() -> None:
    """
    Habilita logging muy detallado para todos los componentes de LangChain.
    Útil para debugging profundo.
    """
    
    # Lista completa de loggers de LangChain para debugging
    verbose_loggers = [
        "langchain",
        "langchain.agents",
        "langchain.agents.agent",
        "langchain.agents.tools",
        "langchain.chains",
        "langchain.schema",
        "langchain.callbacks",
        "langchain.callbacks.manager",
        "langchain.memory",
        "langchain.prompts",
        "langchain_google_genai",
        "langchain_core",
        "langchain_core.agents",
        "langchain_core.callbacks",
        "langchain_core.language_models",
        "langchain_core.messages",
        "langchain_core.prompts",
        "langchain_core.runnables",
        "langchain_core.tools",
        "langchain_community",
    ]
    
    for logger_name in verbose_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING) # Cambiado a WARNING para producción
        
        # Asegurar que los mensajes se propaguen
        logger.propagate = False
    
    logging.getLogger(__name__).info("🔍 Logging verbose de LangChain habilitado")

def disable_noisy_loggers() -> None:
    """
    Desactiva loggers que pueden ser muy ruidosos y no aportan valor para el debugging del LLM.
    """
    noisy_loggers = [
        "httpx",
        "urllib3",
        "requests",
        "asyncio",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    logging.getLogger(__name__).info("🔇 Loggers ruidosos silenciados")
