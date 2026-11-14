# tools/get_document_list_tool.py

"""
Herramienta de LangChain para listar los documentos en la base de conocimiento
de una cuenta de usuario.

Esta herramienta permite al agente de IA recuperar y mostrar una lista de todos
los documentos que un usuario ha subido previamente. Es el primer paso para que
el usuario pueda gestionar su base de conocimiento, permitiéndole ver qué
archivos tiene disponibles antes de, por ejemplo, pedir leer uno o eliminarlo.

La herramienta funciona con el `account_id` universal, asegurando que se listen
los documentos correctos para el usuario, independientemente de la plataforma
desde la que se realice la solicitud. Además, pasa la lista cruda de documentos
al `bot_manager` para que la interfaz (el panel de control) pueda paginarla
correctamente si es necesario.
"""

import logging
import asyncio
from typing import Any, List, Dict, Type, Optional, Union

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones de la lógica de negocio y gestión de estado
from core.memory_manager import list_user_documents
from utils.telegram_api import store_telegram_user_data

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Clave para almacenar la lista de documentos en user_data para paginación en el panel.
RAW_DOCUMENT_LIST_KEY = "raw_document_list_for_pagination"


class GetDocumentListInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de listado de documentos.
    """
    pass


class GetDocumentListTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `list_user_documents`
    para obtener la lista de documentos de un usuario desde la base de datos.
    """
    name: str = "get_document_list_tool"
    description: str = (
        "Recupera una lista de todos los documentos (junto con sus temas, títulos y autores) "
        "que el usuario ha subido previamente a su base de conocimiento. "
        "Permite listar documentos generales, documentos específicos de un workspace, o documentos de una colección (topic) específica. "
        "Úsala cuando el usuario pida explícitamente ver sus documentos guardados. "
        "Si el usuario menciona un 'tema', 'colección' o 'categoría', usa el parámetro 'topic'."
    )
    args_schema: Type[BaseModel] = GetDocumentListInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace (UUID en formato string) para listar documentos del workspace, inyectado automáticamente.")
    topic: Optional[str] = Field(None, description="El nombre del tema o colección para listar documentos específicos de esa colección, inyectado automáticamente.")

    async def _arun(self, **kwargs: Any) -> str:
        """
        Lógica asíncrona para listar documentos del usuario.

        Args:
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Una cadena de texto formateada con la lista de documentos para el agente.
        """
        # Evitar usar el 'topic' pasado por el LLM para que no halucine nombres
        actual_topic = self.topic if self.topic and self.topic != 'None' else None
        
        logger.info(f"Ejecutando GetDocumentListTool para la cuenta '{self.account_id}' con workspace_id: '{self.workspace_id}', topic: '{actual_topic}'.")
        try:
            logger.info(f"DEBUG: Llamando a list_user_documents con account_id={self.account_id}, workspace_id={self.workspace_id}, topic={actual_topic}")
            documents_list = await list_user_documents(account_id=self.account_id, workspace_id=self.workspace_id, topic=actual_topic)

            if self.telegram_id is not None:
                await store_telegram_user_data(
                    telegram_id=int(self.telegram_id),
                    key=RAW_DOCUMENT_LIST_KEY,
                    data=documents_list
                )
            
            if not documents_list:
                if actual_topic and self.workspace_id:
                    return f"No se encontraron documentos en la colección '{actual_topic}' dentro del workspace '{self.workspace_id}'."
                elif actual_topic:
                    return f"No se encontraron documentos en la colección '{actual_topic}'. ¡Puedes subir uno a esta colección!"
                elif self.workspace_id:
                    return f"No se encontraron documentos en el workspace '{self.workspace_id}'. ¡Puedes subir uno a este workspace!"
                else:
                    return "No tienes ningún documento guardado en tu base de conocimiento todavía. ¡Puedes subir uno cuando quieras!"

            response_message = f"He encontrado {len(documents_list)} documento(s) en tu base de conocimiento"
            if actual_topic and self.workspace_id:
                response_message += f" en la colección '{actual_topic}' del workspace '{self.workspace_id}'"
            elif actual_topic:
                response_message += f" en la colección '{actual_topic}'"
            elif self.workspace_id:
                response_message += f" para el workspace '{self.workspace_id}'"
            response_message += ". Aquí están los primeros:\n\n"
            
            for doc in documents_list[:100]:
                title = doc.get('title') or 'Sin título'
                response_message += f"- Archivo: `{doc['file_name']}` (Título: {title}, Colección: {doc.get('topic', 'N/A')})\n"
            if len(documents_list) > 100: # Cambié a 100 para ser consistente con el slicing
                response_message += "\n(Y otros más...)"
            logger.info(
                f"✅ Lista de documentos recuperada exitosamente para la cuenta '{self.account_id}' con workspace_id: '{self.workspace_id}', topic: '{self.topic}'."
            )
            return response_message
        except Exception as e:
            logger.error(
                f"Error en GetDocumentListTool para la cuenta '{self.account_id}' con workspace_id '{self.workspace_id}' y topic '{self.topic}': {e}",
                exc_info=True,
            )
            return "Ocurrió un error inesperado al intentar listar tus documentos."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_document_list_tool no soporta ejecución síncrona.")
