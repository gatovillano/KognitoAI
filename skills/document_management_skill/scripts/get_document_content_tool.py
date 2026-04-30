# tools/get_document_content_tool.py

"""
Herramienta de LangChain para recuperar el contenido textual completo de un documento
almacenado en la base de conocimiento de un usuario.

Esta herramienta es esencial para permitir que el agente "lea" o "consulte"
el contenido íntegro de un archivo que el usuario ha subido previamente.
A diferencia de la búsqueda semántica (RAG), que busca fragmentos relevantes,
esta herramienta recupera todo el texto del documento.

Funciona de manera agnóstica a la plataforma, utilizando el `account_id`
universal del usuario. Además, se comunica con el `bot_manager` para guardar
el nombre del archivo solicitado. Esto permite que el `message_handler`, al
recibir la respuesta, sepa que el texto debe ser paginado y pueda mostrar un
título adecuado en la paginación.
"""

import logging
import asyncio
from typing import Any, Type, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones de la lógica de negocio y gestión de estado
from core.memory_manager import get_full_document_content
from telegram_client.bot_manager import bot_manager


# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Clave constante para guardar el nombre del archivo en user_data.
# Esto permite que el message_handler sepa qué paginar.
DOCUMENT_NAME_KEY = "current_document_name_for_pagination"


class GetDocumentContentInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de obtención de contenido.
    Valida que el LLM proporcione los argumentos necesarios.
    """
    file_name: str = Field(
        ...,
        description="El nombre exacto del archivo del cual se debe recuperar el contenido completo."
    )


class GetDocumentContentTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `get_full_document_content`
    para recuperar el texto completo de un documento de la base de datos vectorial.
    """
    name: str = "get_document_content_tool"
    description: str = (
        "La herramienta principal para leer y recuperar el contenido textual completo de un documento específico "
        "que ha sido subido previamente por el usuario. Esencial para tareas que requieren analizar, "
        "resumir, o procesar el contenido de un archivo. Úsala siempre que el usuario pida explícitamente "
        "leer, ver, analizar o trabajar con el contenido de un documento por su `file_name`."
    )
    args_schema: Type[BaseModel] = GetDocumentContentInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="El ID numérico original de Telegram del usuario, inyectado automáticamente.")
    thread_id: Optional[str] = Field(None, description="El ID del thread de conversación, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace (UUID en formato string) para recuperar el documento de un workspace específico, inyectado automáticamente.")

    async def _arun(self, file_name: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            file_name: El nombre del archivo a recuperar.
            run_manager: El gestor de ejecución que contiene la configuración del agente.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            El contenido completo del documento o un mensaje de error.
        """
        logger.info(f"Ejecutando GetDocumentContentTool para la cuenta '{self.account_id}' y el archivo '{file_name}' en workspace: '{self.workspace_id}'.")
        try:
            full_content = await get_full_document_content(
                account_id=self.account_id,
                file_name=file_name,
                workspace_id=self.workspace_id # <-- Pasar el workspace_id
            )

            if full_content:
                if self.telegram_id is not None:
                    user_data = bot_manager.get_user_data(self.telegram_id)
                    user_data[DOCUMENT_NAME_KEY] = file_name
                    await bot_manager.flush_persistence()
                    logger.info(f"Guardado '{file_name}' en user_data para el usuario de Telegram {self.telegram_id} para paginación.")
                
                workspace_info = f" (Workspace: {self.workspace_id})" if self.workspace_id else ""
                response_text = f"Contenido completo del documento '{file_name}'{workspace_info}:\n\n{full_content}"
                logger.info(f"✅ Contenido de '{file_name}' recuperado exitosamente. Longitud: {len(response_text)} caracteres.")
                return response_text
            else:
                error_message = f"No pude encontrar un documento con el nombre '{file_name}'"
                if self.workspace_id:
                    error_message += f" en el workspace '{self.workspace_id}'"
                error_message += " en tu base de conocimiento. Por favor, asegúrate de que el nombre es correcto."
                logger.warning(f"⚠️ {error_message}")
                return error_message

        except Exception as e:
            logger.error(f"Error en GetDocumentContentTool para la cuenta '{self.account_id}' y archivo '{file_name}' (workspace: {self.workspace_id}): {e}", exc_info=True)
            return f"Ocurrió un error inesperado al recuperar el contenido del documento: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_document_content_tool no soporta ejecución síncrona.")
