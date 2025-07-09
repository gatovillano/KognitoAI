# tools/scoped_rag_analysis_tool.py

"""
Herramienta que expone la utilidad de análisis RAG focalizado al agente principal.
"""

import logging
from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from utils.scoped_rag_analysis import run_scoped_rag_analysis

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# 1. Definir la Entrada con Pydantic
class ScopedRagAnalysisInput(BaseModel):
    query: str = Field(..., description="La petición o pregunta específica del usuario para el análisis.")
    content_types: str = Field(..., description="Tipos de contenido a analizar, separados por comas. Opciones: 'notes', 'documents'.")
    analysis_goal: str = Field(..., description="Describe el formato o resultado deseado para el análisis.")
    topic: str = Field(default="", description="Un tema específico para filtrar el contenido.")
    keywords: str = Field(default="", description="Palabras clave para refinar la búsqueda, separadas por comas.")

# 2. Crear la Clase para la Herramienta
class ScopedRagAnalysisTool(BaseTool):
    name: str = "scoped_rag_analysis"
    description: str = (
        "Útil para iniciar un análisis profundo de la base de conocimiento de un usuario, "
        "permitiendo especificar los tipos de contenido (notas, documentos) y, opcionalmente, "
        "un tema o palabras clave para un análisis RAG altamente focalizado. Además, permite al usuario "
        "definir el formato o el objetivo del análisis resultante (ej. informe de conceptos, plan de trabajo, resumen ejecutivo)."
    )
    args_schema: Type[BaseModel] = ScopedRagAnalysisInput

    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    # 3. Implementar el método _arun (asíncrono)
    async def _arun(self, query: str, content_types: str, analysis_goal: str, topic: str = "", keywords: str = "", run_manager = None, **kwargs) -> str:
        """Ejecuta la herramienta de forma asíncrona, llamando a la utilidad subyacente."""
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

        logger.info(f"Ejecutando ScopedRagAnalysisTool para la cuenta '{account_id}' con objetivo: '{analysis_goal}'")

        try:
            # Procesar keywords
            keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]

            # Ejecutar el análisis
            result = await run_scoped_rag_analysis(
                account_id=account_id,
                query=query,
                content_types=content_types.split(','),
                analysis_goal=analysis_goal,
                topic=topic or "",
                keywords=keywords_list
            )

            logger.info(f"ScopedRagAnalysisTool completado exitosamente para la cuenta '{account_id}'")
            return result

        except Exception as e:
            logger.error(f"Error en ScopedRagAnalysisTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado durante el análisis: {e}"

    def _run(self, *args, **kwargs):
        """Método síncrono no soportado para esta herramienta."""
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
