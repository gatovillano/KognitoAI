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
    thread_id: Optional[str] = None
    task_id: Optional[str] = None
    progress_callback: Optional[Any] = None

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
                thread_id=self.thread_id,
                task_id=self.task_id,
                progress_callback=self.progress_callback,
            )

            report = result.get("final_report", "No se pudo generar el informe final.")
            graph_info = result.get("graph_result", {})

            # Guardar en base de datos como AnalysisTask para que aparezca en las tarjetas de resultados
            saved_analysis_id = None
            if self.account_id:
                try:
                    from core.database import SessionLocal, AnalysisTask
                    from datetime import datetime
                    import uuid

                    async with SessionLocal() as db_session:
                        date_prefix = datetime.now().strftime("%Y-%m-%d")
                        title = f"Investigación Antropológica: {query[:50]} ({date_prefix})"

                        result_payload = {
                            "report": {
                                "final_report": report,
                                "summary": report[:500] if len(report) > 500 else report,
                                "graph_result": graph_info,
                                "quotes_count": len(graph_info.get("quotes", [])),
                                "codes_count": len(graph_info.get("codes", [])),
                                "categories_count": len(graph_info.get("categories", [])),
                                "theoretical_framework": theoretical_framework_content[:1500],
                                "research_question": research_question,
                                "hypothesis": hypothesis,
                                "sources": result.get("sources", []),
                            },
                            "analysis_metadata": {
                                "tool_used": "anthropological_research_tool.py",
                                "analysis_type": "anthropological_deep_research",
                                "query": query,
                                "workspace_id": self.workspace_id,
                                "created_at": datetime.now().isoformat()
                            }
                        }

                        try:
                            account_uuid = uuid.UUID(str(self.account_id))
                        except Exception:
                            account_uuid = None

                        if account_uuid:
                            new_task = AnalysisTask(
                                account_id=account_uuid,
                                file_name=title,
                                analysis_type="anthropological_deep_research",
                                status="completed",
                                result_payload=result_payload
                            )
                            db_session.add(new_task)
                            await db_session.commit()
                            saved_analysis_id = str(new_task.id)
                            logger.info(f"✅ Investigación antropológica guardada en AnalysisTask con ID: {new_task.id}")

                            # Guardar en paralelo como documento Word
                            try:
                                from utils.deep_research_word_saver import save_deep_research_as_word
                                await save_deep_research_as_word(
                                    account_id=str(self.account_id),
                                    query=f"Investigación Antropológica: {query}",
                                    report_text=report,
                                    workspace_id=self.workspace_id
                                )
                            except Exception as word_err:
                                logger.warning(f"Error guardando documento Word de investigación antropológica: {word_err}")

                except Exception as db_err:
                    logger.error(f"Error guardando investigación antropológica en DB: {db_err}", exc_info=True)

            return {
                "status": "success",
                "report": report,
                "analysis_id": saved_analysis_id,
                "quotes_count": len(graph_info.get("quotes", [])),
                "codes_count": len(graph_info.get("codes", [])),
                "categories_count": len(graph_info.get("categories", [])),
                "message": "Investigación antropológica completada exitosamente y registrada en tarjetas de resultados.",
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
