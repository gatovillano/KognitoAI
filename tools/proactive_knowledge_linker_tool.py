# tools/proactive_knowledge_linker_tool.py

"""
Herramienta de Vinculación Proactiva de Conocimiento para KAI

Esta herramienta se activa automáticamente cada vez que se añade nueva información (nota, memoria, documento).
Analiza la nueva entrada, la compara con el conocimiento existente y genera insights proactivos sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento.
También puede ser llamada por el agente bajo demanda si el usuario lo solicita.
"""

import logging
import asyncio
import datetime
from typing import Any, Dict, List, Optional, Type
import uuid
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Importar funciones de la utilidad
from utils.proactive_knowledge_linker import (
    analyze_entry,
    run_batch_analysis_job,
    proactive_knowledge_linker_trigger,
    interpret_user_request_for_analysis
)

logger = logging.getLogger(__name__)

# --- Tool Input Schema and Class ---
class ProactiveKnowledgeLinkerInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de vinculación proactiva de conocimiento.
    Valida que los argumentos necesarios sean proporcionados por el LLM.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    new_entry_content: str = Field(
        ...,
        description="El contenido de la nueva entrada (nota, memoria, documento) a analizar para generar insights proactivos."
    )
    new_entry_title: Optional[str] = Field(
        None,
        description="El título de la nueva entrada, si está disponible."
    )
    new_entry_type: Optional[str] = Field(
        "general",
        description="El tipo de la nueva entrada (por ejemplo, 'note', 'memory', 'document')."
    )
    new_entry_category: Optional[str] = Field(
        None,
        description="La categoría de la nueva entrada, si aplica."
    )
    user_query: Optional[str] = Field(
        None,
        description="Consulta del usuario para análisis bajo demanda, si aplica."
    )

class ProactiveKnowledgeLinkerTool(BaseTool):
    """
    Una herramienta de LangChain que analiza nuevas entradas de información y genera insights proactivos
    sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento.
    """
    name: str = "proactive_knowledge_linker_tool"
    description: str = (
        "Útil para analizar nuevas entradas de información (notas, memorias, documentos) y generar insights "
        "proactivos sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento. "
        "Esta herramienta se activa automáticamente cuando se añade nueva información y también puede ser llamada "
        "bajo demanda para análisis específicos."
    )
    args_schema: Type[BaseModel] = ProactiveKnowledgeLinkerInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    def __init__(self, **kwargs):
        """Inicializa la herramienta con cualquier configuración necesaria."""
        super().__init__(**kwargs)
        logger.info("Inicializando ProactiveKnowledgeLinkerTool")

    async def _arun(self, account_id: str, new_entry_content: str, new_entry_title: Optional[str] = None, new_entry_type: Optional[str] = "general", new_entry_category: Optional[str] = None, user_query: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            new_entry_content: El contenido de la nueva entrada a analizar.
            new_entry_title: El título de la nueva entrada (opcional).
            new_entry_type: El tipo de la nueva entrada (opcional, por defecto 'general').
            new_entry_category: La categoría de la nueva entrada (opcional).
            user_query: Consulta del usuario para análisis bajo demanda (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando ProactiveKnowledgeLinkerTool para la cuenta '{account_id}'.")
        try:
            if user_query:
                # Análisis bajo demanda basado en la consulta del usuario
                analysis_request = await interpret_user_request_for_analysis(user_query)
                action = analysis_request.get("action", "no_action")
                params = analysis_request.get("parameters", {})
                
                if action == "run_full_analysis":
                    asyncio.create_task(run_batch_analysis_job(account_id_filter=account_id))
                    return "Análisis completo de conocimiento iniciado. Se generarán insights en segundo plano."
                elif action == "analyze_recent_items":
                    days_ago = params.get("days_ago", 7)
                    since_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
                    asyncio.create_task(run_batch_analysis_job(account_id_filter=account_id, since_timestamp=since_date))
                    return f"Análisis de ítems recientes (últimos {days_ago} días) iniciado. Se generarán insights en segundo plano."
                elif action == "analyze_specific_topic":
                    keywords = params.get("topic_keywords", [])
                    asyncio.create_task(run_batch_analysis_job(account_id_filter=account_id, topic_keywords=keywords))
                    return f"Análisis sobre temas específicos ({', '.join(keywords)}) iniciado. Se generarán insights en segundo plano."
                else:
                    return "No se reconoció una acción de análisis válida en tu solicitud."
            else:
                # Análisis de nueva entrada
                new_entry = {
                    'account_id': account_id,
                    'content': new_entry_content,
                    'title': new_entry_title,
                    'type': new_entry_type,
                    'category': new_entry_category,
                    'timestamp': datetime.datetime.now(datetime.timezone.utc)
                }
                # Programar el análisis como tarea en segundo plano para no bloquear
                asyncio.create_task(proactive_knowledge_linker_trigger(new_entry))
                logger.info(f"Análisis proactivo programado para la cuenta '{account_id}'.")
                return "Análisis proactivo de la nueva entrada iniciado. Se generarán insights en segundo plano."
        except Exception as e:
            logger.error(f"Error en ProactiveKnowledgeLinkerTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al iniciar el análisis proactivo: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("proactive_knowledge_linker_tool no soporta ejecución síncrona.")
