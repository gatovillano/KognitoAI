# tools/analyze_text_for_insights_tool.py

import logging
import asyncio
from typing import Any, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importamos la INSTANCIA del analizador, no la función.
# Y también el modelo de datos para type hinting.
from utils.advanced_text_analyzer import text_analyzer, SingleTextAnalysis

logger = logging.getLogger(__name__)

# El esquema de entrada sigue siendo el mismo.
class AnalyzeTextInput(BaseModel):
    """Define el esquema de entrada para la herramienta de análisis de texto."""
    text: str = Field(
        ...,
        description="El texto que se va a analizar en profundidad."
    )

class AnalyzeTextForInsightsTool(BaseTool):
    """
    Herramienta de LangChain que realiza un análisis profundo de un texto para extraer
    resumen, temas, sentimiento, tono y posibles brechas de conocimiento.
    """
    name: str = "analyze_text_for_insights"
    description: str = (
        "Útil para un análisis exhaustivo de un fragmento de texto. Devuelve un resumen ejecutivo, "
        "los temas clave, el sentimiento general, el tono del autor y preguntas que invitan a la reflexión "
        "sobre las brechas de conocimiento del texto. "
        "ACTUALIZADO: Los resultados pueden almacenarse con tipo 'text_insights' para seguimiento."
    )
    args_schema: Type[BaseModel] = AnalyzeTextInput
    # La respuesta es rica y estructurada, mejor que el agente la procese.
    return_direct: bool = False

    # El __init__ ya no es necesario, BaseTool se encarga.

    async def _arun(self, text: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona, delegando en el analizador.
        """
        logger.info(f"Delegando análisis de texto al AdvancedTextAnalyzer...")
        try:
            # La llamada es ahora a un método de la instancia del analizador.
            analysis_result = await text_analyzer.analyze_single_text(text)
            logger.info("Análisis de texto completado exitosamente.")
            # El formateo ahora usa el nuevo objeto de resultado.
            return self._format_result(analysis_result)
        except Exception as e:
            logger.error(f"Error durante el análisis de texto: {e}", exc_info=True)
            return f"Ocurrió un error al intentar analizar el texto: {str(e)}"

    def _run(self, text: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma síncrona.
        Este es el patrón recomendado por LangChain para envolver una función async.
        """
        logger.info("Ejecutando análisis de texto en modo síncrono...")
        try:
            # asyncio.run() es la forma más segura de ejecutar una corutina desde un contexto síncrono.
            # Nota: Esto solo funciona si no hay un loop de eventos ya corriendo en el hilo actual.
            # LangChain a menudo maneja esto internamente.
            result = asyncio.run(self._arun(text=text, **kwargs))
            return result
        except RuntimeError as e:
             # Si ya hay un loop corriendo (ej. en un entorno Jupyter), este error puede ocurrir.
             logger.warning(f"RuntimeError en _run, podría indicar un loop de eventos activo: {e}. "
                            "El uso asíncrono (_arun) es preferido.")
             return "Error: No se pudo ejecutar el análisis en modo síncrono debido a un conflicto de loop de eventos. Intente en un contexto asíncrono."
        except Exception as e:
            logger.error(f"Error durante la ejecución síncrona del análisis de texto: {e}", exc_info=True)
            return f"Ocurrió un error durante el análisis de texto: {str(e)}"


    def _format_result(self, result: SingleTextAnalysis) -> str:
        """
        Formatea el resultado del análisis (un objeto SingleTextAnalysis) en una cadena legible.
        """
        # Formatear temas clave manejando objetos ThemeReference
        if result.key_themes:
            themes_formatted = []
            for theme in result.key_themes:
                if hasattr(theme, 'theme'):
                    # Es un objeto ThemeReference
                    theme_text = f"{theme.theme}"
                    if hasattr(theme, 'related_quotes') and theme.related_quotes:
                        quote_count = len(theme.related_quotes)
                        theme_text += f" ({quote_count} cita{'s' if quote_count > 1 else ''})"
                    themes_formatted.append(theme_text)
                else:
                    # Es un string u otro tipo
                    themes_formatted.append(str(theme))
            themes = ", ".join(themes_formatted)
        else:
            themes = "No se identificaron temas clave."
        
        # Construimos las preguntas con viñetas para mayor claridad.
        questions_list = [f"- {q}" for q in result.knowledge_gaps]
        questions = "\n".join(questions_list) if questions_list else "No se identificaron brechas de conocimiento."

        # Ensamblamos el informe final.
        formatted_result = (
            f"**Informe de Análisis de Texto**\n\n"
            f"**Resumen Ejecutivo:**\n{result.executive_summary}\n\n"
            f"**Análisis General:**\n"
            f"- **Temas Clave:** {themes}\n"
            f"- **Disciplina:** {result.discipline}\n"
            f"- **Tono del Autor:** {result.authorial_tone}\n\n"
            f"**Preguntas para Explorar (Brechas de Conocimiento):**\n{questions}\n\n"
            f"**Reflexiones Finales:**\n{result.final_reflections}"
        )
        return formatted_result