# tools/scoped_rag_analysis_tool.py

"""
Herramienta que expone la utilidad de análisis RAG focalizado al agente principal.
"""

from typing import List, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Importar la utilidad principal que contiene la lógica
from utils.scoped_rag_analysis import run_scoped_rag_analysis

class ScopedRagAnalysisInput(BaseModel):
    """Define los argumentos para la herramienta de análisis RAG focalizado."""
    account_id: str = Field(..., description="El identificador único de la cuenta del usuario.")
    query: str = Field(..., description="La petición o pregunta específica del usuario para el análisis.")
    content_types: List[str] = Field(..., description="Tipos de contenido a analizar. Opciones: 'notes', 'documents'.")
    analysis_goal: str = Field(..., description="Describe el formato o resultado deseado para el análisis (ej. 'informe de conceptos', 'plan de trabajo').")
    topic: Optional[str] = Field(default=None, description="Un tema específico para filtrar el contenido.")
    keywords: Optional[List[str]] = Field(default=None, description="Una lista de palabras clave para refinar la búsqueda.")

class ScopedRagAnalysisTool(BaseTool):
    """
    Herramienta para iniciar un análisis profundo y focalizado de la base de conocimiento de un usuario.
    """
    name = "scoped_rag_analysis"
    description = (
        "Útil para iniciar un análisis profundo de la base de conocimiento de un usuario, "
        "permitiendo especificar los tipos de contenido (notas, documentos) y, opcionalmente, "
        "un tema o palabras clave para un análisis RAG altamente focalizado. Además, permite al usuario "
        "definir el formato o el objetivo del análisis resultante (ej. informe de conceptos, plan de trabajo, resumen ejecutivo)."
    )
    args_schema: Type[BaseModel] = ScopedRagAnalysisInput

    async def _arun(
        self,
        account_id: str,
        query: str,
        content_types: List[str],
        analysis_goal: str,
        topic: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> str:
        """Ejecuta la herramienta de forma asíncrona, llamando a la utilidad subyacente."""
        return await run_scoped_rag_analysis(
            account_id=account_id,
            query=query,
            content_types=content_types,
            analysis_goal=analysis_goal,
            topic=topic,
            keywords=keywords
        )
