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

from pydantic import BaseModel, Field
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
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )


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
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, account_id: str, file_name: Optional[str] = None, topic: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            file_name: El nombre del archivo a eliminar (opcional).
            topic: El tema de los documentos a eliminar (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        if not file_name and not topic:
            return "Error: Debes proporcionar un nombre de archivo o un tema para poder eliminar documentos."
            
        logger.info(f"Ejecutando DeleteDocumentTool para la cuenta '{account_id}' (Archivo: '{file_name}', Tema: '{topic}')")
        
        try:
            # Llama a la función de lógica de negocio, que ahora debe ser actualizada
            # para aceptar 'account_id' en lugar de 'telegram_id'.
            deleted_count = await delete_document_chunks(
                account_id=account_id,
                file_name=file_name,
                topic=topic
            )
            
            # La función devuelve un entero, por lo que la comparación es segura.
            if deleted_count > 0:
                target = f"el documento '{file_name}'" if file_name else f"los documentos del tema '{topic}'"
                message = f"Se han eliminado con éxito los fragmentos correspondientes a {target} de tu base de conocimiento."
                return message
            else:
                target = f"documento con el nombre '{file_name}'" if file_name else f"documentos del tema '{topic}'"
                return f"No se encontró ningún {target} en tu base de conocimiento. No se ha eliminado nada."
        except Exception as e:
            logger.error(f"Error en DeleteDocumentTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Se produjo un error al intentar eliminar los documentos: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("delete_document_tool no soporta ejecución síncrona.")