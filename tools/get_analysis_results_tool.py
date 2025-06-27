# tools/get_analysis_results_tool.py

"""
Herramienta de LangChain para recuperar y mostrar los resultados de análisis guardados
en la tabla AnalysisTask para una cuenta de usuario.

Esta herramienta permite al agente de IA acceder a los resultados de análisis de documentos
y colecciones almacenados y presentarlos en el contexto de un chat, proporcionando
información sobre resúmenes, temas clave, conceptos centrales y relaciones.
"""

import logging
from typing import Type, Any, List, Dict
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import AnalysisTask, SessionLocal
from utils.db_session import DBSession
import uuid
import datetime

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

class GetAnalysisResultsInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de recuperación de resultados de análisis.
    Valida que el argumento necesario sea proporcionado por el LLM.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    limit: int = Field(
        5,
        description="El número máximo de resultados de análisis a recuperar. Por defecto es 5."
    )
    document_name: str = Field(
        "",
        description="El nombre del documento para filtrar los resultados de análisis. Si no se proporciona, se devuelven todos los análisis."
    )


class GetAnalysisResultsTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la base de datos para recuperar los resultados
    de análisis asociados a una cuenta de usuario y los formatea para su visualización en un chat.
    """
    name: str = "get_analysis_results_tool"
    description: str = (
        "Útil para recuperar y mostrar los resultados de análisis de documentos y colecciones "
        "guardados para el usuario. Estos resultados incluyen resúmenes ejecutivos, temas clave, "
        "conceptos centrales y relaciones basadas en la información analizada."
    )
    args_schema: Type[BaseModel] = GetAnalysisResultsInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    def __init__(self, **kwargs):
        """Inicializa la herramienta con cualquier configuración necesaria."""
        super().__init__(**kwargs)
        logger.info("Inicializando GetAnalysisResultsTool")

    async def _arun(self, account_id: str, limit: int = 5, document_name: str = "", **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            limit: El número máximo de resultados de análisis a recuperar (por defecto 5).
            document_name: El nombre del documento para filtrar los resultados (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto con los resultados de análisis formateados o un mensaje indicando que no hay resultados.
        """
        logger.info(f"Ejecutando GetAnalysisResultsTool para la cuenta '{account_id}' con límite de {limit} resultados y documento '{document_name}'.")
        try:
            async with DBSession(SessionLocal) as db:
                account_uuid = uuid.UUID(account_id)
                stmt = (
                    select(AnalysisTask)
                    .where(AnalysisTask.account_id == account_uuid, AnalysisTask.status == "completed")
                )
                if document_name:
                    stmt = stmt.where(AnalysisTask.file_name == document_name)
                stmt = stmt.order_by(AnalysisTask.updated_at.desc()).limit(limit)
                result = await db.execute(stmt)
                analyses = result.scalars().all()

                if not analyses:
                    logger.info(f"No se encontraron resultados de análisis para la cuenta '{account_id}' con documento '{document_name}'.")
                    if document_name:
                        return f"No se encontraron resultados de análisis para el documento '{document_name}' en tu base de conocimiento. ¡A medida que realices más análisis, los guardaré para que puedas consultarlos!"
                    return "No se encontraron resultados de análisis guardados en tu base de conocimiento. ¡A medida que realices más análisis, los guardaré para que puedas consultarlos!"

                response_lines = ["Aquí están los resultados de análisis más recientes guardados en tu base de conocimiento:"]
                for idx, analysis in enumerate(analyses, 1):
                    response_lines.append(f"\n{idx}. **Análisis de: {analysis.file_name}** - Actualizado: {analysis.updated_at.strftime('%Y-%m-%d %H:%M')}")
                    if analysis.result_payload:
                        if 'executive_summary' in analysis.result_payload:
                            response_lines.append(f"   - **Resumen Ejecutivo**: {analysis.result_payload['executive_summary']}")
                        elif 'resumen_ejecutivo' in analysis.result_payload:
                            response_lines.append(f"   - **Resumen Ejecutivo**: {analysis.result_payload['resumen_ejecutivo']}")
                        
                        if 'key_themes' in analysis.result_payload and analysis.result_payload['key_themes']:
                            response_lines.append("   - **Temas Clave**:")
                            for theme in analysis.result_payload['key_themes']:
                                response_lines.append(f"     - {theme}")
                        elif 'temas_clave_avanzados' in analysis.result_payload and analysis.result_payload['temas_clave_avanzados']:
                            response_lines.append("   - **Temas Clave**:")
                            for theme in analysis.result_payload['temas_clave_avanzados']:
                                response_lines.append(f"     - {theme}")

                        if 'central_concepts' in analysis.result_payload and analysis.result_payload['central_concepts']:
                            response_lines.append("   - **Conceptos Centrales**:")
                            for concept in analysis.result_payload['central_concepts']:
                                response_lines.append(f"     - {concept}")
                        elif 'conceptos_centrales' in analysis.result_payload and analysis.result_payload['conceptos_centrales']:
                            response_lines.append("   - **Conceptos Centrales**:")
                            for concept in analysis.result_payload['conceptos_centrales']:
                                response_lines.append(f"     - {concept}")

                        if 'concept_relationships' in analysis.result_payload and analysis.result_payload['concept_relationships']:
                            response_lines.append("   - **Relaciones entre Conceptos**:")
                            for relation in analysis.result_payload['concept_relationships']:
                                response_lines.append(f"     - {relation}")
                        elif 'relaciones_conceptos' in analysis.result_payload and analysis.result_payload['relaciones_conceptos']:
                            response_lines.append("   - **Relaciones entre Conceptos**:")
                            for relation in analysis.result_payload['relaciones_conceptos']:
                                response_lines.append(f"     - {relation}")

                        if 'knowledge_gaps' in analysis.result_payload and analysis.result_payload['knowledge_gaps']:
                            response_lines.append("   - **Preguntas para Explorar**:")
                            for question in analysis.result_payload['knowledge_gaps']:
                                response_lines.append(f"     - {question}")
                        elif 'preguntas_para_explorar' in analysis.result_payload and analysis.result_payload['preguntas_para_explorar']:
                            response_lines.append("   - **Preguntas para Explorar**:")
                            for question in analysis.result_payload['preguntas_para_explorar']:
                                response_lines.append(f"     - {question}")

                if len(analyses) == limit:
                    response_lines.append(f"\n(Mostrando los {limit} más recientes. Si deseas ver más, puedo buscarlos.)")

                logger.info(f"Recuperados {len(analyses)} resultados de análisis para la cuenta '{account_id}'.")
                return "\n".join(response_lines)
        except Exception as e:
            logger.error(f"Error en GetAnalysisResultsTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar recuperar tus resultados de análisis: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_analysis_results_tool no soporta ejecución síncrona.")
