import logging
from typing import Any, Optional, Type
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from utils.analyze_text_for_insights import analyze_text_for_insights, analyze_text_for_insights_sync

logger = logging.getLogger(__name__)

class AnalyzeTextInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de análisis de texto.
    """
    text: str = Field(
        ...,
        description="El texto a analizar para extraer temas clave, entidades, sentimiento y resumen."
    )

class AnalyzeTextForInsightsTool(BaseTool):
    """
    Herramienta de LangChain que analiza texto para extraer insights profundos como temas clave, entidades, sentimiento y un resumen ejecutivo.
    """
    name: str = "analyze_text_for_insights"
    description: str = (
        "Útil para analizar un texto y extraer temas clave, entidades nombradas, análisis de sentimiento, un resumen ejecutivo y conexiones semánticas. "
        "Esta herramienta procesa el texto proporcionado y devuelve un análisis estructurado."
    )
    args_schema: Type[BaseModel] = AnalyzeTextInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    def __init__(self, **kwargs):
        """Inicializa la herramienta."""
        super().__init__(**kwargs)
        logger.info("Inicializando AnalyzeTextForInsightsTool")

    async def _arun(self, text: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.
        """
        logger.info(f"Ejecutando análisis de texto")
        try:
            result = await analyze_text_for_insights(text)
            logger.info("Análisis de texto completado exitosamente.")
            return self._format_result(result)
        except Exception as e:
            logger.error(f"Error durante el análisis de texto: {e}", exc_info=True)
            return f"Ocurrió un error durante el análisis de texto: {str(e)}"

    def _run(self, text: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma síncrona.
        """
        logger.info(f"Ejecutando análisis de texto sincrónico")
        try:
            task = analyze_text_for_insights_sync(text)
            import asyncio
            import inspect
            if inspect.iscoroutine(task):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result = asyncio.run_coroutine_threadsafe(task, loop).result()
                    else:
                        result = loop.run_until_complete(task)
                except RuntimeError:
                    # Fallback if no event loop is running and can't create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(task)
                    loop.close()
            elif isinstance(task, asyncio.tasks.Task) or isinstance(task, asyncio.Future):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result = loop.run_until_complete(task)
                    else:
                        result = loop.run_until_complete(task)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(task)
                    loop.close()
            else:
                result = task
            logger.info("Análisis de texto sincrónico completado exitosamente.")
            return self._format_result(result)
        except Exception as e:
            logger.error(f"Error durante el análisis de texto sincrónico: {e}", exc_info=True)
            return f"Ocurrió un error durante el análisis de texto sincrónico: {str(e)}"

    def _format_result(self, result: dict) -> str:
        """
        Formatea el resultado del análisis en una cadena legible para el usuario.
        """
        temas = ", ".join(result.get("temas_clave", []))
        entidades = ", ".join([f"{e['texto']} ({e['tipo']})" for e in result.get("entidades", [])])
        sentimiento = f"Polaridad: {result.get('sentimiento', {}).get('polarity', 0.0):.2f}, Subjetividad: {result.get('sentimiento', {}).get('subjectivity', 0.0):.2f}"
        resumen = result.get("resumen_ejecutivo", "")
        conexiones = "\n- ".join(result.get("conexiones_semanticas", []))

        formatted_result = (
            f"Análisis de Texto:\n"
            f"Temas Clave: {temas}\n"
            f"Entidades: {entidades}\n"
            f"Sentimiento: {sentimiento}\n"
            f"Resumen Ejecutivo: {resumen}\n"
        )
        if conexiones:
            formatted_result += f"Conexiones Semánticas:\n- {conexiones}\n"
        return formatted_result
