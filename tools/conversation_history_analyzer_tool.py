# tools/conversation_history_analyzer_tool.py

"""
Herramienta de LangChain para analizar en segundo plano el historial de conversaciones,
extrayendo intereses y temas clave y guardándolos en el perfil del usuario.

Esta herramienta permite al agente de IA procesar el historial de conversaciones de un usuario
de manera asíncrona, identificar patrones de intereses y temas recurrentes, y actualizar
el perfil del usuario con esta información para personalización a largo plazo.
"""

import logging
from typing import Any, Optional, Type, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from core.database import ChatThread, SessionLocal
from core.llm_manager import get_fast_llm
from core.memory_manager import update_user_profile
from fastapi import BackgroundTasks
from core.config import settings

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class ConversationAnalysisInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de análisis de historial de conversaciones.
    Valida que el argumento necesario, `account_id`, sea proporcionado.
    """
    thread_ids_str: Optional[str] = Field(
        default=None,
        description="Cadena de texto opcional con IDs de hilos de chat específicos a analizar, separados por comas. Si no se proporciona, se analizarán todos los hilos del usuario.",
        json_schema_extra={"type": "string"}
    )


class ConversationHistoryAnalyzerTool(BaseTool):
    """
    Una herramienta de LangChain que analiza en segundo plano el historial de conversaciones
    de un usuario para extraer intereses y temas clave, actualizando su perfil.
    """
    name: str = "conversation_history_analyzer"
    description: str = (
        "Útil para analizar en segundo plano el historial de conversaciones de un usuario, "
        "extrayendo intereses y temas clave para actualizar su perfil. Esta herramienta "
        "se ejecuta de manera asíncrona y no interfiere con la interacción en tiempo real."
    )
    args_schema: Type[BaseModel] = ConversationAnalysisInput
    return_direct: bool = False
    account_id: str

    async def _arun(
        self,
        thread_ids_str: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
        **kwargs: Any
    ) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona, iniciando un análisis en segundo plano.

        Args:
            thread_ids: Lista opcional de IDs de hilos de chat específicos a analizar.
            background_tasks: Objeto BackgroundTasks para programar la tarea en segundo plano.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando que el análisis ha sido iniciado.
        """
        logger.info(f"Ejecutando ConversationHistoryAnalyzerTool para la cuenta '{self.account_id}'.")

        thread_ids = thread_ids_str.split(',') if thread_ids_str else None

        if background_tasks:
            background_tasks.add_task(self.analyze_conversation_history, self.account_id, thread_ids)
            logger.info(f"Análisis de historial de conversaciones programado en segundo plano para la cuenta '{self.account_id}'.")
            return "Análisis de historial de conversaciones iniciado en segundo plano. Los resultados se guardarán en tu perfil pronto."
        else:
            logger.warning(f"No se proporcionó BackgroundTasks; ejecutando análisis sincrónicamente para la cuenta '{self.account_id}'.")
            await self.analyze_conversation_history(self.account_id, thread_ids)
            return "Análisis de historial de conversaciones completado. Los resultados han sido guardados en tu perfil."


    async def analyze_conversation_history(self, account_id: str, thread_ids: Optional[List[str]] = None) -> None:
        """
        Analiza el historial de conversaciones del usuario y actualiza su perfil con los intereses y temas clave extraídos.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            thread_ids: Lista opcional de IDs de hilos de chat específicos a analizar.
        """
        try:
            logger.info(f"Iniciando análisis de historial de conversaciones para la cuenta '{account_id}'.")
            async with SessionLocal() as db_session:
                # Obtener los hilos de chat del usuario
                if thread_ids:
                    threads_query = select(ChatThread).where(
                        ChatThread.account_id == account_id,
                        ChatThread.id.in_(thread_ids)
                    )
                else:
                    threads_query = select(ChatThread).where(ChatThread.account_id == account_id)

                threads_result = await db_session.execute(threads_query)
                threads = threads_result.scalars().all()

                if not threads:
                    logger.warning(f"No se encontraron hilos de chat para la cuenta '{account_id}'.")

                    return None

                # Obtener el historial de mensajes de cada hilo
                all_messages = []
                if settings.database_url is None:
                    logger.error(f"Configuración de base de datos faltante para la cuenta '{account_id}'.")

                    return None
                db_sync_url = settings.database_url.replace("+psycopg", "")
                for thread in threads:
                    history = PostgresChatMessageHistory(
                        connection_string=db_sync_url,
                        session_id=str(thread.id),
                        table_name="langchain_chat_history",
                    )
                    messages = await history.aget_messages()
                    all_messages.extend(messages)

                if not all_messages:
                    logger.warning(f"No se encontraron mensajes en los hilos de chat para la cuenta '{account_id}'.")

                    return None

                # Preparar el texto para análisis
                conversation_text = "\n".join(
                    self._extract_message_content(msg) for msg in all_messages
                )

                # Utilizar el LLM para extraer intereses y temas clave
                llm = get_fast_llm()
                if not llm:
                    logger.error(f"No hay LLM disponible para analizar el historial de la cuenta '{account_id}'.")

                    return None

                prompt = (
                    "Analiza el siguiente historial de conversaciones y extrae los intereses y temas clave del usuario. "
                    "Devuelve un resumen en formato de texto con las categorías 'Intereses' y 'Temas Clave', "
                    "asegurándote de que cada categoría tenga una lista de elementos relevantes.\n\n"
                    f"Historial de Conversaciones:\n{conversation_text[:5000]}..."  # Limitar para no exceder tokens
                )

                response = await llm.ainvoke(prompt)
                analysis_result = response.content if hasattr(response, 'content') else str(response)

                # Extraer intereses y temas clave del resultado del análisis
                intereses = ""
                temas_clave = ""
                lines = analysis_result.split("\n")
                current_category = None
                for line in lines:
                    if "Intereses" in line:
                        current_category = "intereses"
                    elif "Temas Clave" in line or "Temas clave" in line:
                        current_category = "temas_clave"
                    elif current_category == "intereses" and line.strip():
                        intereses += line + "\n"
                    elif current_category == "temas_clave" and line.strip():
                        temas_clave += line + "\n"

                # Actualizar el perfil del usuario con la información extraída
                if intereses or temas_clave:
                    await update_user_profile(
                        account_id=account_id,
                        intereses=intereses.strip() if intereses else None,
                        otros_datos=temas_clave.strip() if temas_clave else None
                    )
                    logger.info(f"Perfil actualizado con intereses y temas clave para la cuenta '{account_id}'.")
                else:
                    logger.warning(f"No se extrajeron intereses ni temas clave para la cuenta '{account_id}'.")
                return None

        except Exception as e:
            logger.error(f"Error durante el análisis de historial de conversaciones para la cuenta '{account_id}': {e}", exc_info=True)
            return None

    def _extract_message_content(self, msg: Any) -> str:
        """
        Extrae el contenido de un mensaje, manejando diferentes formatos y tipos.

        Args:
            msg: El objeto de mensaje del historial de chat.

        Returns:
            Una cadena de texto representando el contenido del mensaje.
        """
        if hasattr(msg, 'content'):
            if isinstance(msg.content, str):
                return msg.content
            elif isinstance(msg.content, list):
                # Si el contenido es una lista, intenta extraer texto de sus elementos
                return "\n".join(
                    item.get('text', '') if isinstance(item, dict) else str(item)
                    for item in msg.content
                )
            else:
                return str(msg.content)
        return str(msg)

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("conversation_history_analyzer no soporta ejecución síncrona.")
