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
import asyncio # AGREGAR ESTA LÍNEA
from typing import Any, Type, Optional

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones de la lógica de negocio y gestión de estado
from core.memory_manager import get_full_document_content
from telegram_client.bot_manager import bot_manager
from tools.proactive_knowledge_linker_tool import proactive_knowledge_linker_trigger

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
    # Reemplazamos telegram_id por account_id para que sea universal.
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    telegram_id: Optional[int] = Field(
        None,
        description="El ID numérico original de Telegram del usuario. Es necesario para interactuar con sistemas de estado de sesión como `user_data`. Puede ser None si no aplica."
    )


class GetDocumentContentTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `get_full_document_content`
    para recuperar el texto completo de un documento de la base de datos vectorial.
    """
    name: str = "get_document_content_tool"
    description: str = (
        "Recupera el contenido textual completo de un documento previamente subido por el usuario. "
        "Úsala cuando el usuario pida 'ver', 'leer', 'muéstrame' o 'dame el texto completo' de un documento específico. "
        "Debes proporcionar el `file_name` exacto."
    )
    args_schema: Type[BaseModel] = GetDocumentContentInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, file_name: str, account_id: str, telegram_id: Optional[int] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            file_name: El nombre del archivo a recuperar.
            account_id: El ID universal de la cuenta del usuario.
            telegram_id: El ID de Telegram para la gestión de estado de sesión (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            El contenido completo del documento o un mensaje de error.
        """
        logger.info(f"Ejecutando GetDocumentContentTool para la cuenta '{account_id}' y el archivo '{file_name}'.")
        try:
            full_content = await get_full_document_content(account_id=account_id, file_name=file_name)

            if full_content:
                # Si se encuentra contenido, guardamos el nombre del archivo en user_data.
                if telegram_id is not None:
                    user_data = bot_manager.get_user_data(telegram_id)
                    user_data[DOCUMENT_NAME_KEY] = file_name
                    await bot_manager.flush_persistence()
                    logger.info(f"Guardado '{file_name}' en user_data para el usuario de Telegram {telegram_id} para paginación.")
                response_text = (
                    f"Contenido completo del documento '{file_name}':\n\n"
                    f"{full_content}"
                )
                logger.info(f"✅ Contenido de '{file_name}' recuperado exitosamente. Longitud: {len(response_text)} caracteres.")

                # Llamada al trigger proactivo tras obtener el contenido del documento
                new_entry = {
                    'account_id': account_id,
                    'content': full_content,
                    'title': file_name,
                    'type': 'document'
                }
                # CORRECCIÓN: Programar como tarea en segundo plano
                asyncio.create_task(proactive_knowledge_linker_trigger(new_entry))

                return response_text
            else:
                # Si la función no devuelve contenido, informamos al agente.
                error_message = f"No pude encontrar un documento con el nombre '{file_name}' en tu base de conocimiento. Por favor, asegúrate de que el nombre es correcto."
                logger.warning(f"⚠️ {error_message}")
                return error_message

        except Exception as e:
            logger.error(f"Error en GetDocumentContentTool para la cuenta '{account_id}' y archivo '{file_name}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al recuperar el contenido del documento."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_document_content_tool no soporta ejecución síncrona.")
