from langchain_core.tools import Tool
from utils.analyze_text_for_insights import analyze_text_for_insights

class AnalyzeTextForInsightsTool(Tool):
    name = "analyze_text_for_insights"
    description = (
        "Herramienta de análisis avanzado de texto: identifica temas clave, entidades, sentimiento y genera un resumen ejecutivo a partir de un texto largo. "
        "Ideal para procesar transcripciones, informes o hilos de comunicación."
    )


    def __init__(self):
            # Call the parent class's constructor with the required arguments
            super().__init__(
                name=self.name,
                description=self.description,
                func=self._run # Pass the instance method as the callable function
            )

    def _run(self, text: str) -> dict:
        """
        Procesa el texto y retorna un dict con temas clave, entidades, sentimiento y resumen.
        """
        return analyze_text_for_insights(text)
