# tools/update_document_metadata_tool.py

"""
Herramienta de LangChain para actualizar los metadatos (título, tema)
de un documento en la base de conocimiento del usuario.

Esta herramienta permite al agente de IA modificar la información descriptiva
asociada a un documento previamente subido. Es útil para corregir errores,
refinar la categorización o añadir un título más descriptivo después de
que el documento ha sido procesado.

La actualización se realiza directamente sobre los metadatos almacenados
en la base de datos vectorial (pgvector), asegurando que la información
sea consistente con los chunks del documento.
"""

import logging
from typing import Any, Type, Optional

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importación de la lógica de negocio para actualizar metadatos
from core.memory_manager import update_document_metadata

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class UpdateDocumentMetadataInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de actualización de metadatos.
    Valida que el LLM proporcione los argumentos necesarios.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    file_name: str = Field(
        ...,
        description="El nombre exacto del archivo del cual se desea actualizar los metadatos."
    )
    new_title: Optional[str] = Field(
        None,
        description="El nuevo título para el documento. Si se proporciona, reemplazará el título existente."
    )
    new_topic: Optional[str] = Field(
        None,
        description="La nueva categoría o tema para el documento. Si se proporciona, reemplazará el tema existente."
    )
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")


class UpdateDocumentMetadataTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `update_document_metadata`
    para modificar los metadatos de un documento en la base de conocimiento.
    """
    name: str = "update_document_metadata_tool"
    description: str = (
        "Actualiza el título y/o la categoría (topic) de un documento existente en la base de conocimiento del usuario. "
        "Permite especificar el documento por su `file_name` y el `account_id` del usuario. "
        "También puede operar en documentos dentro de un `workspace_id` específico. " # <-- Descripción actualizada
        "Se debe proporcionar al menos `new_title` o `new_topic`."
    )
    args_schema: Type[BaseModel] = UpdateDocumentMetadataInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, account_id: str, file_name: str, new_title: Optional[str] = None, new_topic: Optional[str] = None, team_id: Optional[str] = None, workspace_id: Optional[str] = None, **kwargs: Any) -> str: # <-- workspace_id añadido aquí
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            file_name: El nombre del archivo a actualizar.
            new_title: El nuevo título para el documento.
            new_topic: La nueva categoría o tema para el documento.
            team_id: El ID del equipo (UUID en formato string) si el documento pertenece a un equipo.
            workspace_id: El ID del workspace para filtrar documentos (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de confirmación o error.
        """
        logger.info(
            f"Ejecutando UpdateDocumentMetadataTool para cuenta '{account_id}', archivo '{file_name}'. "
            f"Nuevo título: '{new_title}', Nuevo tema: '{new_topic}'. Workspace ID: '{workspace_id}'."
        )
        if not new_title and not new_topic:
            return "Debe proporcionar al menos un nuevo título o un nuevo tema para actualizar."

        try:
            # --- MODIFICACIÓN: Pasar workspace_id a update_document_metadata ---
            success = await update_document_metadata(
                account_id=account_id,
                file_name=file_name,
                new_title=new_title,
                new_topic=new_topic,
                team_id=team_id, # Mantener team_id si aplica
                workspace_id=workspace_id # <-- Pasar el workspace_id
            )

            if success:
                logger.info(f"✅ Metadatos del documento '{file_name}' (workspace: {workspace_id if workspace_id else 'N/A'}) actualizados exitosamente.")
                return f"Metadatos del documento '{file_name}' actualizados correctamente."
            else:
                logger.warning(f"⚠️ No se pudieron actualizar los metadatos del documento '{file_name}' (workspace: {workspace_id if workspace_id else 'N/A'}).")
                return f"No se pudo actualizar los metadatos del documento '{file_name}'. Asegúrate de que el archivo existe y el nombre es correcto."

        except Exception as e:
            logger.error(f"Error en UpdateDocumentMetadataTool para cuenta '{account_id}', archivo '{file_name}' (workspace: {workspace_id}): {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar actualizar los metadatos del documento: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("update_document_metadata_tool no soporta ejecución síncrona.")
