import logging
import asyncio # AGREGAR ESTA LÍNEA
from typing import Type, Optional, Any
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from core.memory_manager import update_document_metadata
from tools.proactive_knowledge_linker_tool import proactive_knowledge_linker_trigger

logger = logging.getLogger(__name__)

class UpdateDocumentMetadataInput(BaseModel):
    account_id: str = Field(..., description="El identificador universal (UUID) de la cuenta del usuario.")
    file_name: str = Field(..., description="El nombre exacto del archivo a actualizar.")
    new_title: Optional[str] = Field(None, description="El nuevo título para el documento.")
    new_topic: Optional[str] = Field(None, description="La nueva categoría/base de conocimiento para el documento.")

class UpdateDocumentMetadataTool(BaseTool):
    name: str = "update_document_metadata_tool"
    description: str = (
        "Permite actualizar el título y/o la categoría de un documento subido por el usuario. "
        "Proporciona el account_id, file_name y al menos uno de new_title o new_topic."
    )
    args_schema: Type[BaseModel] = UpdateDocumentMetadataInput
    return_direct: bool = False

    async def _arun(self, account_id: str, file_name: str, new_title: Optional[str] = None, new_topic: Optional[str] = None, **kwargs: Any) -> str:
        try:
            success = await update_document_metadata(account_id, file_name, new_title, new_topic)
            if success:
                # Llamada al trigger proactivo tras actualizar los metadatos del documento
                new_entry = {
                    'account_id': account_id,
                    'title': new_title or file_name,
                    'category': new_topic,
                    'type': 'document_metadata_update'
                }
                # CORRECCIÓN: Programar como tarea en segundo plano
                asyncio.create_task(proactive_knowledge_linker_trigger(new_entry))
                return "Metadatos del documento actualizados correctamente."
            else:
                return "No se encontró el documento o no se pudo actualizar."
        except Exception as e:
            logger.error(f"Error en UpdateDocumentMetadataTool: {e}", exc_info=True)
            return f"Error al actualizar metadatos: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Solo ejecución asíncrona soportada.")
