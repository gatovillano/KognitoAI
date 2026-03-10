# tools/analyze_code_for_insights_tool.py

import logging
import asyncio
from typing import Any, Type, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importamos la FUNCIÓN del analizador, no una clase o instancia.
# Y también el modelo de datos para type hinting.
from utils.advanced_code_analyzer import analyze_code_content, CodeAnalysisResult

logger = logging.getLogger(__name__)

class AnalyzeCodeInput(BaseModel):
    """Define el esquema de entrada para la herramienta de análisis de código."""
    code_content: str = Field(
        ...,
        description="El contenido del código o repositorio que se va a analizar en profundidad."
    )

class AnalyzeCodeForInsightsTool(BaseTool):
    """
    Herramienta de LangChain que realiza un análisis profundo de código o repositorios para extraer
    estructura, patrones, dependencias, posibles problemas y recomendaciones.
    """
    name: str = "analyze_code_for_insights"
    description: str = (
        "Útil para un análisis exhaustivo de un fragmento de código o repositorio. Devuelve un resumen ejecutivo, "
        "la estructura del código, patrones de diseño, dependencias, posibles problemas y recomendaciones "
        "para mejorar la calidad del código."
    )
    args_schema: Type[BaseModel] = AnalyzeCodeInput
    return_direct: bool = False
    account_id: Optional[str] = Field(None, description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")
    telegram_id: Optional[str] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación, inyectado automáticamente.")

    async def _arun(self, code_content: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona, delegando en el analizador.
        """
        logger.info(f"Iniciando análisis de código con AdvancedCodeAnalyzer...")
        try:
            # Llamamos directamente a la función de análisis
            analysis_result = await analyze_code_content(code_content)
            logger.info("Análisis de código completado exitosamente.")
            return self._format_result(analysis_result)
        except Exception as e:
            logger.error(f"Error durante el análisis de código: {e}", exc_info=True)
            return f"Ocurrió un error al intentar analizar el código: {str(e)}"

    def _run(self, code_content: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma síncrona.
        Este es el patrón recomendado por LangChain para envolver una función async.
        """
        logger.info("Ejecutando análisis de código en modo síncrono...")
        try:
            result = asyncio.run(self._arun(code_content=code_content, **kwargs))
            return result
        except RuntimeError as e:
            logger.warning(f"RuntimeError en _run, podría indicar un loop de eventos activo: {e}. "
                           "El uso asíncrono (_arun) es preferido.")
            return "Error: No se pudo ejecutar el análisis en modo síncrono debido a un conflicto de loop de eventos. Intente en un contexto asíncrono."
        except Exception as e:
            logger.error(f"Error durante la ejecución síncrona del análisis de código: {e}", exc_info=True)
            return f"Ocurrió un error durante el análisis de código: {str(e)}"

    def _format_result(self, result: CodeAnalysisResult) -> str:
        """
        Formatea el resultado del análisis (un objeto CodeAnalysisResult) en una cadena legible.
        """
        def format_item_list(items, item_type="item"):
            if not items:
                return f"No se identificaron {item_type}."
            
            formatted_items = []
            for item in items:
                if isinstance(item, dict):
                    # Extraer información de objetos complejos
                    if 'component' in item and 'description' in item:
                        formatted_items.append(f"- **{item['component']}**: {item['description']}")
                    elif 'pattern' in item and 'description' in item:
                        formatted_items.append(f"- **{item['pattern']}**: {item['description']}")  
                    elif 'library' in item and 'description' in item:
                        formatted_items.append(f"- **{item['library']}**: {item['description']}")
                    elif 'issue' in item and 'description' in item:
                        formatted_items.append(f"- **{item['issue']}**: {item['description']}")
                    elif 'recommendation' in item:
                        rec_text = f"- **{item['recommendation']}**"
                        if 'rationale' in item:
                            rec_text += f"\n  - *Justificación*: {item['rationale']}"
                        if 'application' in item:
                            rec_text += f"\n  - *Aplicación*: {item['application']}"
                        if 'implementation' in item:
                            rec_text += f"\n  - *Implementación*: {item['implementation']}"
                        formatted_items.append(rec_text)
                    else:
                        # Fallback para objetos sin estructura conocida
                        formatted_items.append(f"- {str(item)}")
                else:
                    formatted_items.append(f"- {str(item)}")
            
            return "\n".join(formatted_items)

        structure = format_item_list(result.code_structure, "componentes de estructura")
        patterns = format_item_list(result.design_patterns, "patrones de diseño")
        dependencies = format_item_list(result.dependencies, "dependencias")
        issues = format_item_list(result.potential_issues, "problemas potenciales")
        recommendations = format_item_list(result.recommendations, "recomendaciones")

        formatted_result = (
            f"**Informe de Análisis de Código**\n\n"
            f"**Resumen Ejecutivo:**\n{result.executive_summary}\n\n"
            f"**Estructura del Código:**\n{structure}\n\n"
            f"**Patrones de Diseño:**\n{patterns}\n\n"
            f"**Dependencias:**\n{dependencies}\n\n"
            f"**Problemas Potenciales:**\n{issues}\n\n"
            f"**Recomendaciones:**\n{recommendations}"
        )
        return formatted_result
