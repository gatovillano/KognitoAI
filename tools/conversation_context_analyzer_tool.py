# tools/conversation_context_analyzer_tool.py

"""
Herramienta de Análisis de Contexto de Conversaciones para KAI

Esta herramienta analiza el contexto de las conversaciones y memorias del usuario para generar insights
sobre patrones, temas recurrentes, emociones y posibles brechas de conocimiento. Se activa automáticamente
cuando se detectan nuevas interacciones significativas o puede ser llamada bajo demanda.
"""

import logging
import asyncio
import datetime
from typing import Any, Dict, List, Optional, Type
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importar utilidades necesarias para el análisis de contexto
from utils.advanced_text_analyzer import text_analyzer

logger = logging.getLogger(__name__)

# --- Tool Input Schema and Class ---
class ConversationContextAnalyzerInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de análisis de contexto de conversaciones.
    Valida que los argumentos necesarios sean proporcionados por el LLM.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    conversation_history: Optional[str] = Field(
        None,
        description="El historial de conversación a analizar. Si no se proporciona, se analizarán las memorias y conversaciones recientes del usuario."
    )
    user_query: Optional[str] = Field(
        None,
        description="Consulta del usuario para análisis bajo demanda, si aplica."
    )

class ConversationContextAnalyzerTool(BaseTool):
    """
    Una herramienta de LangChain que analiza el contexto de conversaciones y memorias del usuario
    para generar insights sobre patrones, temas recurrentes, emociones y brechas de conocimiento.
    """
    name: str = "conversation_context_analyzer_tool"
    description: str = (
        "Útil para analizar el contexto de conversaciones y memorias del usuario, generando insights "
        "sobre patrones, temas recurrentes, emociones y posibles brechas de conocimiento. Esta herramienta "
        "se activa automáticamente con nuevas interacciones significativas y también puede ser llamada "
        "bajo demanda para análisis específicos."
    )
    args_schema: Type[BaseModel] = ConversationContextAnalyzerInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    def __init__(self, **kwargs):
        """Inicializa la herramienta con cualquier configuración necesaria."""
        super().__init__(**kwargs)
        logger.info("Inicializando ConversationContextAnalyzerTool")

    async def _arun(self, account_id: str, conversation_history: Optional[str] = None, user_query: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            conversation_history: El historial de conversación a analizar (opcional).
            user_query: Consulta del usuario para análisis bajo demanda (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando ConversationContextAnalyzerTool para la cuenta '{account_id}'.")
        try:
            if user_query:
                # Análisis bajo demanda basado en la consulta del usuario
                logger.info(f"Análisis bajo demanda con consulta: {user_query}")
                return await self._analyze_with_query(account_id, user_query)
            elif conversation_history:
                # Análisis de historial de conversación proporcionado
                logger.info(f"Análisis de historial de conversación proporcionado para la cuenta '{account_id}'.")
                return await self._analyze_conversation_history(account_id, conversation_history)
            else:
                # Análisis automático de conversaciones y memorias recientes
                logger.info(f"Análisis automático de contexto para la cuenta '{account_id}'.")
                return await self._analyze_recent_context(account_id)
        except Exception as e:
            logger.error(f"Error en ConversationContextAnalyzerTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al iniciar el análisis de contexto: {e}"

    async def _analyze_with_query(self, account_id: str, user_query: str) -> str:
        """
        Analiza el contexto basado en una consulta específica del usuario.
        """
        # Aquí se implementaría la lógica para interpretar la consulta del usuario
        # y realizar un análisis específico. Por ahora, simulamos una respuesta.
        return f"Análisis de contexto basado en la consulta '{user_query}' iniciado. Se generarán insights en segundo plano."

    async def _analyze_conversation_history(self, account_id: str, conversation_history: str) -> str:
        """
        Analiza un historial de conversación proporcionado.
        """
        try:
            analysis_result = await text_analyzer.analyze_single_text(conversation_history)
            formatted_result = self._format_result(analysis_result)
            logger.info(f"Análisis de historial de conversación completado para la cuenta '{account_id}'.")
            return formatted_result
        except Exception as e:
            logger.error(f"Error durante el análisis de historial de conversación: {e}", exc_info=True)
            return f"Ocurrió un error al analizar el historial de conversación: {str(e)}"

    async def _analyze_recent_context(self, account_id: str) -> str:
        """
        Analiza las conversaciones y memorias recientes del usuario.
        """
        # Aquí se implementaría la lógica para recuperar y analizar el contexto reciente.
        # Por ahora, simulamos una respuesta.
        return "Análisis de contexto reciente iniciado. Se generarán insights sobre conversaciones y memorias en segundo plano."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Redirige la ejecución síncrona a la método asíncrono."""
        logger.warning("⚠️ Método síncrono _run de ConversationContextAnalyzerTool fue llamado. Redirigiendo al método asíncrono.")
        import asyncio
        return asyncio.run(self._arun(**kwargs))

    def _format_result(self, result: Any) -> str:
        """
        Formatea el resultado del análisis en una cadena legible.
        """
        # Usamos .join para manejar listas vacías de forma elegante.
        themes = ", ".join(result.key_themes) if result.key_themes else "No se identificaron temas clave."
        
        # Construimos las preguntas con viñetas para mayor claridad.
        questions_list = [f"- {q}" for q in result.knowledge_gaps]
        questions = "\n".join(questions_list) if questions_list else "No se identificaron brechas de conocimiento."

        # Ensamblamos el informe final.
        formatted_result = (
            f"**Informe de Análisis de Contexto de Conversación**\n\n"
            f"**Resumen Ejecutivo:**\n{result.executive_summary}\n\n"
            f"**Análisis General:**\n"
            f"- **Temas Clave:** {themes}\n"
            f"- **Sentimiento Detectado:** {result.sentiment_analysis}\n"
            f"- **Tono del Autor:** {result.authorial_tone}\n\n"
            f"**Preguntas para Explorar (Brechas de Conocimiento):**\n{questions}"
        )
        return formatted_result
