# tools/vector_db_query_tool.py

"""
Herramienta de LangChain para realizar consultas a la base de datos vectorial mediante similitud semántica con embeddings.

Esta herramienta permite al agente de IA buscar documentos o fragmentos de texto similares a una consulta dada,
utilizando la utilidad de consulta vectorial definida en utils/vector_db_query.py.
"""

import logging
from typing import Type, Optional, Any, List, Dict

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importar la función de consulta vectorial
from utils.vector_db_query import query_vector_db

logger = logging.getLogger(__name__)

class VectorDBQueryInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de consulta a la base de datos vectorial.
    Valida que los argumentos necesarios sean proporcionados por el LLM.
    """
    query: str = Field(
        ...,
        description="El texto de la consulta para buscar documentos o fragmentos similares en la base de datos vectorial."
    )
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    k: int = Field(
        default=5,
        description="El número de resultados similares a devolver. Por defecto es 5."
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="El nombre de la colección específica a buscar. Si no se proporciona, se usará la colección de memorias del usuario por defecto."
    )
    topic: Optional[str] = Field(
        default=None,
        description="Filtra los resultados por un tema específico dentro de los metadatos del documento (usando operadores JSONB)."
    )
    workspace_id: Optional[str] = Field(
        default=None,
        description="Filtra los resultados por un ID de workspace específico dentro de los metadatos del documento (usando operadores JSONB)."
    )

class VectorDBQueryTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `query_vector_db` para realizar consultas
    a la base de datos vectorial basadas en similitud semántica con embeddings.
    """
    name: str = "vector_db_query_tool"
    description: str = (
        "Útil para buscar documentos o fragmentos de texto similares a una consulta dada en la base de datos vectorial del usuario. "
        "Utiliza embeddings para encontrar contenido relevante mediante similitud semántica. "
        "Permite especificar el número de resultados, una colección específica y filtros de metadatos usando operadores JSONB."
    )
    args_schema: Type[BaseModel] = VectorDBQueryInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, query: str, run_manager = None, **kwargs k: int = 5, collection_name: Optional[str] = None, topic: Optional[str] = None, workspace_id: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            query: El texto de la consulta para buscar similitudes.
            account_id: El ID universal de la cuenta del usuario.
            k: Número de resultados similares a devolver. Por defecto es 5.
            collection_name: Nombre de la colección específica a buscar (opcional).
            topic: Filtro por tema en los metadatos (opcional).
            workspace_id: Filtro por ID de workspace en los metadatos (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto con los resultados formateados o un mensaje de error.
        """
                # Obtener account_id del contexto de configuración o instancia
        account_id = None
        account_id_source = "unknown"
        
        # Intentar obtener del contexto del run_manager
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
            if account_id:
                account_id_source = "run_manager.config.configurable"
        
        # Fallback: obtener de la instancia
        if not account_id:
            account_id = getattr(self, 'account_id', "")
            if account_id:
                account_id_source = "self.account_id"

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

logger.info(
            f"Ejecutando VectorDBQueryTool para la cuenta '{account_id}' con consulta: '{query[:50]}...'"
            f"{f', topic: {topic}' if topic else ''}{f', workspace_id: {workspace_id}' if workspace_id else ''}"
        )
        try:
            # Llamar a la función de consulta vectorial
            results = await query_vector_db(
                query=query,
                account_id=account_id,
                k=k,
                collection_name=collection_name,
                topic=topic,
                workspace_id=workspace_id
            )
            
            if not results:
                logger.info(f"No se encontraron resultados para la consulta '{query[:50]}...' en la cuenta '{account_id}'.")
                return f"No se encontraron resultados similares para tu consulta en la base de datos vectorial."
            
            # Formatear los resultados para el agente
            formatted_results = ["Resultados de la búsqueda en la base de datos vectorial:"]
            for idx, result in enumerate(results, 1):
                content = result.get("content", "Contenido no disponible")
                metadata = result.get("metadata", {})
                similarity_score = result.get("similarity_score", 0.0)
                formatted_results.append(f"\n{idx}. Fragmento (Puntuación de similitud: {similarity_score:.2f}):")
                formatted_results.append(f"   Contenido: {content[:200]}..." if len(content) > 200 else f"   Contenido: {content}")
                if metadata:
                    formatted_results.append(f"   Metadatos: {metadata}")
            
            logger.info(f"Se devolvieron {len(results)} resultados para la consulta en la cuenta '{account_id}'.")
            return "\n".join(formatted_results)
        except Exception as e:
            logger.error(f"Error en VectorDBQueryTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error al realizar la búsqueda en la base de datos vectorial: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("vector_db_query_tool no soporta ejecución síncrona.")