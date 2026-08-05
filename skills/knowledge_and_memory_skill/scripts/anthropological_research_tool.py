"""
Herramienta de Investigación Antropológica Profunda para el Agente (AnthropologicalResearchTool).
Permite al agente ejecutar el grafo de investigación etnográfica profunda mediante lenguaje natural.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.agents.anthropological_deep_researcher import run_anthropological_deep_research

logger = logging.getLogger(__name__)


class AnthropologicalResearchSchema(BaseModel):
    """Schema para la herramienta de investigación antropológica profunda."""
    query: str = Field(..., description="Consulta o tema de investigación antropológica a indagar.")
    theoretical_framework_content: str = Field(
        ...,
        description="Texto o conceptos clave del marco teórico que servirán como lente analítico."
    )
    ethnographic_material_content: Optional[str] = Field(
        None,
        description="Material etnográfico o corpus de análisis (entrevistas, diarios de campo, textos, etc.)."
    )
    deepen_theoretical_framework: bool = Field(
        False,
        description="Si es True, el agente profundizará y ampliará los conceptos del marco teórico antes/durante la investigación."
    )
    research_question: Optional[str] = Field(
        None,
        description="Pregunta de investigación cualitativa (opcional)."
    )
    hypothesis: Optional[str] = Field(
        None,
        description="Hipótesis de trabajo (opcional)."
    )


class AnthropologicalResearchTool(BaseTool):
    name: str = "anthropological_deep_research"
    description: str = """
    Ejecuta una investigación antropológica y cualitativa profunda.
    Utiliza el marco teórico provisto, pregunta e hipótesis para investigar sobre un tema
    y generar un informe de síntesis etnográfica con codificación cualitativa exhaustiva.
    """
    args_schema: type[BaseModel] = AnthropologicalResearchSchema
    account_id: Optional[str] = None
    workspace_id: Optional[str] = None

    async def _arun(
        self,
        query: str,
        theoretical_framework_content: str,
        ethnographic_material_content: Optional[str] = None,
        deepen_theoretical_framework: bool = False,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        logger.info(f"📜 Ejecutando herramienta 'anthropological_deep_research' para query: '{query}'")

        try:
            result = await run_anthropological_deep_research(
                query_or_topic=query,
                theoretical_framework_content=theoretical_framework_content,
                ethnographic_material_content=ethnographic_material_content,
                deepen_theoretical_framework=deepen_theoretical_framework,
                research_question=research_question,
                hypothesis=hypothesis,
                account_id=self.account_id,
            )

            report = result.get("final_report", "No se pudo generar el informe final.")
            graph_info = result.get("graph_result", {})

            return {
                "status": "success",
                "report": report,
                "quotes_count": len(graph_info.get("quotes", [])),
                "codes_count": len(graph_info.get("codes", [])),
                "categories_count": len(graph_info.get("categories", [])),
                "message": "Investigación antropológica completada exitosamente.",
            }

        except Exception as e:
            logger.error(f"❌ Error en AnthropologicalResearchTool: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _run(
        self,
        query: str,
        theoretical_framework_content: str,
        ethnographic_material_content: Optional[str] = None,
        deepen_theoretical_framework: bool = False,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
        **kwargs
    ):
        return asyncio.run(
            self._arun(
                query=query,
                theoretical_framework_content=theoretical_framework_content,
                ethnographic_material_content=ethnographic_material_content,
                deepen_theoretical_framework=deepen_theoretical_framework,
                research_question=research_question,
                hypothesis=hypothesis,
                **kwargs
            )
        )
