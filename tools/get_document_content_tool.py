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
from typing import Any, Type, Optional, Union

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones de la lógica de negocio y gestión de estado
from core.memory_manager import get_full_document_content
from telegram_client.bot_manager import bot_manager
from tools.proactive_knowledge_linker_tool import proactive_knowledge_linker_trigger # Mantener si se usa en el módulo, aunque no directamente en esta función.

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
    # --- NUEVO: Parámetro para el ID del workspace ---
    workspace_id: Optional[str] = Field(
        None,
        description="El ID del workspace (UUID en formato string) para recuperar el documento de un workspace específico, si aplica.",
        json_schema_extra={"type": "string"}
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



    async def _arun(self, file_name: str, workspace_id: Optional[str] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            file_name: El nombre del archivo a recuperar.
            account_id: El ID universal de la cuenta del usuario.
            telegram_id: El ID de Telegram para la gestión de estado de sesión (opcional).
            workspace_id: El ID del workspace para filtrar documentos (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            El contenido completo del documento o un mensaje de error.
        """
        # Obtener valores de la configuración del agente si están disponibles
        config_account_id = None
        config_telegram_id = None
        config_workspace_id = workspace_id

        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            config_account_id = configurable.get('account_id')
            config_telegram_id = configurable.get('telegram_id')
            if not config_workspace_id:
                config_workspace_id = configurable.get('workspace_id')

        # Usar valores de configuración o instancia
        effective_account_id = config_account_id or getattr(self, 'account_id', "")
        effective_telegram_id = config_telegram_id or getattr(self, 'telegram_id', None)
        effective_workspace_id = config_workspace_id

        if not effective_account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        logger.info(f"Ejecutando GetDocumentContentTool para la cuenta '{effective_account_id}' y el archivo '{file_name}' en workspace: '{effective_workspace_id}'.")
        try:
            # --- MODIFICACIÓN: Pasar workspace_id a get_full_document_content ---
            full_content = await get_full_document_content(
                account_id=effective_account_id,
                file_name=file_name,
                team_id=None, # Mantener None o pasar team_id si aplica en tu lógica
                workspace_id=effective_workspace_id # <-- Pasar el workspace_id
            )

            if full_content:
                if effective_telegram_id is not None:
                    user_data = bot_manager.get_user_data(effective_telegram_id)
                    user_data[DOCUMENT_NAME_KEY] = file_name
                    await bot_manager.flush_persistence()
                    logger.info(f"Guardado '{file_name}' en user_data para el usuario de Telegram {effective_telegram_id} para paginación.")
                
                response_text = (
                    f"Contenido completo del documento '{file_name}'"
                    f" (Workspace: {effective_workspace_id})" if effective_workspace_id else ""
                    f":\n\n{full_content}"
                )
                logger.info(f"✅ Contenido de '{file_name}' recuperado exitosamente. Longitud: {len(response_text)} caracteres.")
                return response_text
            else:
                error_message = f"No pude encontrar un documento con el nombre '{file_name}'"
                if effective_workspace_id:
                    error_message += f" en el workspace '{effective_workspace_id}'"
                error_message += " en tu base de conocimiento. Por favor, asegúrate de que el nombre es correcto."
                logger.warning(f"⚠️ {error_message}")
                return error_message

        except Exception as e:
            logger.error(f"Error en GetDocumentContentTool para la cuenta '{effective_account_id}' y archivo '{file_name}' (workspace: {effective_workspace_id}): {e}", exc_info=True)
            return f"Ocurrió un error inesperado al recuperar el contenido del documento: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_document_content_tool no soporta ejecución síncrona.")
