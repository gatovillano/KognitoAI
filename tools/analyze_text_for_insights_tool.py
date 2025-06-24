from langchain_core.tools import BaseTool
from utils.analyze_text_for_insights import analyze_text_for_insights

class AnalyzeTextForInsightsTool(BaseTool):
    name = "analyze_text_for_insights"
    description = (
        "Herramienta de análisis avanzado de texto: identifica temas clave, entidades, sentimiento y genera un resumen ejecutivo a partir de un texto largo. "
        "Ideal para procesar transcripciones, informes o hilos de comunicación."
    )
    
    def _run(self, query: str) -> str:
        result = analyze_text_for_insights(query)
        if isinstance(result, dict):
            return str(result)
        return result
        
    async def _arun(self, query: str) -> str:
        result = analyze_text_for_insights(query)
        if isinstance(result, dict):
            return str(result)
        return result
