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
from typing import Any, List, Dict, Type, Optional, Union

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones de la lógica de negocio y gestión de estado
from core.memory_manager import list_user_documents
from telegram_client.bot_manager import bot_manager

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Clave para almacenar la lista de documentos en user_data para paginación en el panel.
RAW_DOCUMENT_LIST_KEY = "raw_document_list_for_pagination"


class GetDocumentListInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de listado de documentos.
    Valida que el LLM proporcione el identificador de la cuenta.
    """
    # Reemplazamos telegram_id por account_id para que sea universal.
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    # --- NUEVO: Parámetro para el ID del workspace ---
    workspace_id: Optional[str] = Field(
        None,
        description="El ID del workspace (UUID en formato string) para listar documentos del workspace, si aplica.",
        json_schema_extra={"type": "string"}
    )


class GetDocumentListTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `list_user_documents`
    para obtener la lista de documentos de un usuario desde la base de datos.
    """
    name: str = "get_document_list_tool"
    description: str = (
        "Recupera una lista de todos los documentos (junto con sus temas, títulos y autores) "
        "que el usuario ha subido previamente a su base de conocimiento. "
        "ACTUALIZADO: Permite listar documentos generales o documentos específicos de un workspace con aislamiento optimizado. "
        "Úsala cuando el usuario pida explícitamente ver sus documentos guardados."
    )
    args_schema: Type[BaseModel] = GetDocumentListInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, account_id: str, telegram_id: Optional[int] = None, workspace_id: Optional[str] = None, **kwargs: Any) -> str: # <-- workspace_id añadido aquí
        """
        Lógica asíncrona para listar documentos del usuario.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            telegram_id: El ID de Telegram del usuario, si está disponible.
            workspace_id: El ID del workspace para filtrar documentos (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Una cadena de texto formateada con la lista de documentos para el agente.
        """
        logger.info(f"Ejecutando GetDocumentListTool para la cuenta '{account_id}' con workspace_id: '{workspace_id}'.")
        try:
            # --- MODIFICACIÓN: Pasar workspace_id a list_user_documents ---
            documents_list = await list_user_documents(account_id=account_id, team_id=None, workspace_id=workspace_id)
            
            if telegram_id is not None:
                user_data = bot_manager.get_user_data(telegram_id)
                user_data[RAW_DOCUMENT_LIST_KEY] = documents_list
                await bot_manager.flush_persistence()
            
            if not documents_list:
                logger.info(f"No se encontraron documentos para la cuenta '{account_id}' en el workspace '{workspace_id}'." if workspace_id else f"No se encontraron documentos para la cuenta '{account_id}'.")
                return "No tienes ningún documento guardado en tu base de conocimiento todavía. ¡Puedes subir uno cuando quieras!" if not workspace_id else f"No se encontraron documentos en el workspace '{workspace_id}'. ¡Puedes subir uno a este workspace!"
            
            response_message = f"He encontrado {len(documents_list)} documento(s) en tu base de conocimiento"
            if workspace_id:
                response_message += f" para el workspace '{workspace_id}'"
            response_message += ". Aquí están los primeros:\n\n"
            
            for doc in documents_list[:100]:
                title = doc.get('title') or 'Sin título'
                response_message += f"- Archivo: `{doc['file_name']}` (Título: {title})\\n"
            if len(documents_list) > 5:
                response_message += "\n(Y otros más...)"
            
            logger.info(f"✅ Lista de documentos recuperada exitosamente para la cuenta '{account_id}' con workspace_id: '{workspace_id}'.")
            return response_message
        except Exception as e:
            logger.error(f"Error en GetDocumentListTool para la cuenta '{account_id}' con workspace_id '{workspace_id}': {e}", exc_info=True)
            return "Ocurrió un error inesperado al intentar listar tus documentos."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_document_list_tool no soporta ejecución síncrona.")
