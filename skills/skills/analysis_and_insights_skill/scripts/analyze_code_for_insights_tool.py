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
    analysis_type: str = Field(
        "all",
        description="Tipo de análisis: 'all', 'security', 'performance', 'refactoring', 'documentation', 'structure'."
    )

class AnalyzeCodeForInsightsTool(BaseTool):
    """
    Herramienta de LangChain que realiza un análisis profundo de código o repositorios para extraer
    estructura, patrones, dependencias, posibles problemas y recomendaciones.
    """
    name: str = "analyze_code_for_insights"
    description: str = (
        "Útil para un análisis exhaustivo de un fragmento de código o repositorio. Permite análisis específicos "
        "de seguridad, rendimiento, refactorización, documentación o estructura."
    )
    args_schema: Type[BaseModel] = AnalyzeCodeInput
    return_direct: bool = False
    account_id: Optional[str] = Field(None, description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")
    telegram_id: Optional[str] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación, inyectado automáticamente.")

    async def _arun(self, code_content: str, analysis_type: str = "all", **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona, delegando en el analizador.
        """
        logger.info(f"Iniciando análisis de código ({analysis_type}) con AdvancedCodeAnalyzer...")
        try:
            # Llamamos directamente a la función de análisis, pasando el account_id
            # para que use el modelo configurado por el usuario.
            analysis_result = await analyze_code_content(
                code_content, 
                account_id=self.account_id,
                analysis_type=analysis_type
            )
            logger.info("Análisis de código completado exitosamente.")
            return self._format_result(analysis_result, analysis_type)
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

    def _format_result(self, result: CodeAnalysisResult, analysis_type: str = "all") -> str:
        """
        Formatea el resultado del análisis en una cadena legible, filtrando por tipo si es necesario.
        """
        def format_item_list(items, item_type="item"):
            if not items:
                return f"No se identificaron {item_type}."
            
            formatted_items = []
            for item in items:
                # Convertir Pydantic model a dict si es necesario
                if not isinstance(item, dict) and hasattr(item, 'model_dump'):
                    item = item.model_dump()
                elif not isinstance(item, dict) and hasattr(item, 'dict'):
                    item = item.dict()
                
                if isinstance(item, dict):
                    if 'component' in item and 'description' in item:
                        formatted_items.append(f"- **{item['component']}**: {item['description']}")
                    elif 'pattern' in item and 'description' in item:
                        formatted_items.append(f"- **{item['pattern']}**: {item['description']}")  
                    elif 'library' in item and 'description' in item:
                        formatted_items.append(f"- **{item['library']}**: {item['description']}")
                    elif 'vulnerability' in item:
                        sev = item.get('severity', 'Unknown')
                        formatted_items.append(f"- **[{sev}] {item['vulnerability']}**: {item.get('description', '')}")
                    elif 'area' in item and 'issue' in item:
                        formatted_items.append(f"- **{item['area']} - {item['issue']}**: {item.get('suggestion', '')}")
                    elif 'concept' in item:
                        formatted_items.append(f"- **{item['concept']}**: {item.get('description', '')}\n  *Beneficio*: {item.get('benefit', '')}")
                    elif 'item' in item and 'status' in item:
                        formatted_items.append(f"- **{item['item']}** ({item['status']}): {item.get('recommendation', '')}")
                    elif 'issue' in item and 'description' in item:
                        formatted_items.append(f"- **{item['issue']}**: {item['description']}")
                    elif 'recommendation' in item:
                        rec_text = f"- **{item['recommendation']}**"
                        if 'rationale' in item: rec_text += f"\n  - *Justificación*: {item['rationale']}"
                        if 'application' in item: rec_text += f"\n  - *Aplicación*: {item['application']}"
                        if 'implementation' in item: rec_text += f"\n  - *Implementación*: {item['implementation']}"
                        formatted_items.append(rec_text)
                    else:
                        formatted_items.append(f"- {str(item)}")
                else:
                    formatted_items.append(f"- {str(item)}")
            
            return "\n".join(formatted_items)

        sections = []
        
        if analysis_type in ["all", "structure"]:
            sections.append(f"**Resumen Ejecutivo:**\n{result.executive_summary}")
            sections.append(f"**Estructura del Código:**\n{format_item_list(result.code_structure, 'componentes')}")
            sections.append(f"**Patrones de Diseño:**\n{format_item_list(result.design_patterns, 'patrones')}")

        if analysis_type in ["all", "security"]:
            sections.append(f"**Análisis de Seguridad:**\n{format_item_list(result.security_analysis, 'vulnerabilidades')}")

        if analysis_type in ["all", "performance"]:
            sections.append(f"**Rendimiento y Eficiencia:**\n{format_item_list(result.performance_analysis, 'problemas de rendimiento')}")

        if analysis_type in ["all", "refactoring"]:
            sections.append(f"**Deuda Técnica y Refactorización:**\n{format_item_list(result.refactoring_opportunities, 'oportunidades')}")

        if analysis_type in ["all", "documentation"]:
            sections.append(f"**Salud de la Documentación:**\n{format_item_list(result.documentation_health, 'puntos de documentación')}")

        if analysis_type == "all":
            sections.append(f"**Dependencias:**\n{format_item_list(result.dependencies, 'dependencias')}")
            sections.append(f"**Problemas Potenciales:**\n{format_item_list(result.potential_issues, 'problemas potenciales')}")
            sections.append(f"**Recomendaciones:**\n{format_item_list(result.recommendations, 'recomendaciones')}")

        title = f"Informe de Análisis de Código ({analysis_type.upper()})"
        return f"**{title}**\n\n" + "\n\n".join(sections)
