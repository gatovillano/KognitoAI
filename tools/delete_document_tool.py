# tools/delete_document_tool.py

"""
Herramienta de LangChain para eliminar documentos de la base de conocimiento
de una cuenta de usuario.

Esta herramienta permite al agente de IA borrar permanentemente todos los fragmentos
de un documento específico por su nombre de archivo, o todos los documentos
asociados a un tema. Es una operación destructiva, por lo que la descripción
de la herramienta guía al agente para que sea cauteloso.

Funciona de manera agnóstica a la plataforma, utilizando el `account_id`
universal del usuario para asegurar que solo se eliminen los documentos
pertenecientes a la cuenta correcta.
"""

import logging
from typing import Type, Optional, Any, Union

from pydantic import BaseModel, Field, root_validator
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de memoria.
from core.memory_manager import delete_document_chunks

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class DeleteDocumentInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de eliminación de documentos.
    Valida que el LLM proporcione los argumentos necesarios.
    """
    # El LLM puede proporcionar uno de estos dos, pero no ambos son obligatorios a la vez.
    file_name: Optional[str] = Field(
        None,
        description="El nombre exacto del archivo a eliminar. Se puede omitir si se proporciona un 'topic'.",
        json_schema_extra={"type": "string"}
    )
    topic: Optional[str] = Field(
        None,
        description="El tema o categoría de los documentos a eliminar. Eliminará todos los documentos asociados a este tema. Se puede omitir si se proporciona 'file_name'.",
        json_schema_extra={"type": "string"}
    )
    # Reemplazamos telegram_id por account_id para que sea universal.

    @root_validator(pre=False, skip_on_failure=True)
    def check_file_or_topic_exists(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Valida que se haya proporcionado 'file_name' o 'topic'."""
        if not values.get("file_name") and not values.get("topic"):
            raise ValueError(
                "Se debe proporcionar un 'file_name' o un 'topic' para eliminar documentos."
            )
        return values

class DeleteDocumentTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `delete_document_chunks`
    para eliminar documentos de la base de datos vectorial del usuario.
    """
    name: str = "delete_document_tool"
    description: str = (
        "Útil para eliminar permanentemente un documento por su nombre de archivo, o todos los documentos "
        "asociados a un tema de la base de conocimiento del usuario. "
        "Dado que esta es una acción destructiva, el agente debe confirmar explícitamente con el usuario antes de usar esta herramienta."
    )
    args_schema: Type[BaseModel] = DeleteDocumentInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(self, file_name: Optional[str] = None, topic: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            file_name: El nombre del archivo a eliminar (opcional).
            topic: El tema de los documentos a eliminar (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando DeleteDocumentTool para la cuenta '{self.account_id}' (Archivo: '{file_name}', Tema: '{topic}')")
        
        try:
            deleted_count = await delete_document_chunks(
                account_id=self.account_id,
                file_name=file_name,
                topic=topic
            )
            
            if file_name:
                target_desc_success = f"el documento '{file_name}'"
                target_desc_fail = f"documento con el nombre '{file_name}'"
            else: # topic must be present due to validator
                target_desc_success = f"los documentos del tema '{topic}'"
                target_desc_fail = f"documentos del tema '{topic}'"

            if deleted_count > 0:
                return f"Se han eliminado con éxito los fragmentos correspondientes a {target_desc_success} de tu base de conocimiento."
            else:
                return f"No se encontró ningún {target_desc_fail} en tu base de conocimiento. No se ha eliminado nada."
        except Exception as e:
            logger.error(f"Error en DeleteDocumentTool para la cuenta '{self.account_id}': {e}", exc_info=True)
            return f"Se produjo un error al intentar eliminar los documentos: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("delete_document_tool no soporta ejecución síncrona.")