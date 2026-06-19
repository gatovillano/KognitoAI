from pydantic import Field
# tools/scoped_rag_analysis_tool.py

"""
Herramienta que expone la utilidad de análisis RAG focalizado al agente principal.
"""

from typing import List, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# 1. Definir la Entrada con Pydantic
class ScopedRagAnalysisInput(BaseModel):
    query: str = Field(..., description="La petición o pregunta específica del usuario para el análisis.")
    content_types: str = Field(..., description="Tipos de contenido a analizar, separados por comas. Opciones: 'notes', 'documents'.")
    analysis_goal: str = Field(..., description="Describe el formato o resultado deseado para el análisis.")
    topic: str = Field(default="", description="Un tema específico para filtrar el contenido.")
    keywords: str = Field(default="", description="Palabras clave para refinar la búsqueda, separadas por comas.")

# 2. Crear la Clase para la Herramienta
class ScopedRagAnalysisTool(BaseTool):
    name: str = Field(default="scoped_rag_analysis", description="Nombre de la herramienta")
    name = "scoped_rag_analysis"
    description: str = (
        "Útil para iniciar un análisis profundo de la base de conocimiento de un usuario, "
        "permitiendo especificar los tipos de contenido (notas, documentos) y, opcionalmente, "
        "un tema o palabras clave para un análisis RAG altamente focalizado. Además, permite al usuario "
        "definir el formato o el objetivo del análisis resultante (ej. informe de conceptos, plan de trabajo, resumen ejecutivo)."
    )
    args_schema: Type[BaseModel] = ScopedRagAnalysisInput
    account_id: Optional[str] = Field(None, description="El identificador único de la cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El identificador único del espacio de trabajo del usuario.")
    telegram_id: Optional[str] = Field(None, description="El identificador único de Telegram del usuario.")
    thread_id: Optional[str] = Field(None, description="El identificador único del hilo de conversación.")

    # 3. Implementar el método _arun (asíncrono)
    async def _arun(self, query: str, content_types: str, analysis_goal: str, topic: str = "", keywords: str = "") -> str:
        """Ejecuta la herramienta de forma asíncrona, llamando a la utilidad subyacente."""
        # Aquí va la lógica para ejecutar el análisis RAG focalizado
        # utilizando las funciones o clases que ya tienes implementadas.
        # Por ejemplo:
        from utils.scoped_rag_analysis import run_scoped_rag_analysis  # Importa la función
        keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
        
        # Aseguramos que account_id no es None antes de pasarlo
        if self.account_id is None:
            raise ValueError("account_id no puede ser None para la ejecución de run_scoped_rag_analysis.")

        result = await run_scoped_rag_analysis(
            account_id=self.account_id, # Pylance ya no debería quejarse
            query=query,
            content_types=content_types.split(','),
            analysis_goal=analysis_goal,
            topic=topic or "",
            keywords=keywords_list
        )
        return result

    def _run(self, *args, **kwargs):
        """Método síncrono no soportado para esta herramienta."""
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
