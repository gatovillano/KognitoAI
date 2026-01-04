# tools/crew_research_tool.py

import logging
import os
import uuid
from typing import Type, Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from core.agents.crewai_researcher import KognitoCrewResearcher
from core.citation_models import ToolOutputWithSources, Source, SourceType
from core.database import SessionLocal, AnalysisTask
from utils.db_session import DBSession
from core.config import settings

logger = logging.getLogger(__name__)

class CrewResearchInput(BaseModel):
    """Input for the Crew Research tool."""
    query: str = Field(description="The research query to be investigated in-depth using a specialized crew of agents.")

class CrewResearchTool(BaseTool):
    """
    A tool to perform in-depth research using CrewAI.
    It orchestrates multiple specialized agents (Manager, Researcher, Analyst, Writer)
    to produce a high-quality research paper.
    """
    name: str = "crew_research"
    description: str = (
        "Conduct deep research using a crew of specialized agents. "
        "Best for complex topics requiring multi-step investigation and high-quality narrative reports. "
        "Required parameter: query (string) - the research topic."
    )
    args_schema: Type[BaseModel] = CrewResearchInput
    account_id: str
    workspace_id: Optional[str] = None
    thread_id: Optional[str] = None

    async def _run(self, query: str) -> Dict[str, Any]:
        """Execute the CrewAI research process."""
        logger.info(f"🚀 Executing Crew Research for query: '{query}'")
        
        try:
            # Instanciar el investigador de CrewAI
            researcher = KognitoCrewResearcher(
                account_id=self.account_id,
                workspace_id=self.workspace_id,
                config={
                    "max_researcher_iterations": 15,
                    "max_concurrent_research_units": 3
                }
            )
            
            # Ejecutar la investigación
            # Nota: En una implementación real, podríamos pasar el historial de mensajes aquí
            result = await researcher.run_research(
                research_brief=query,
                messages=f"El usuario solicita una investigación profunda sobre: {query}"
            )
            
            report = result.get("final_report", "No se pudo generar el informe.")
            raw_sources = result.get("sources", [])
            recommendations = result.get("recommendations", [])
            
            # Convertir a objetos Source de Kognito
            sources_list = []
            for i, s in enumerate(raw_sources, 1):
                sources_list.append(Source(
                    id=i,
                    title=s.get("title", f"Fuente {i}"),
                    url=s.get("url", ""),
                    snippet=s.get("snippet", ""),
                    type=SourceType.WEB
                ))
            
            # Preparar salida para el LLM
            tool_output = ToolOutputWithSources(
                context_for_llm=report,
                sources=sources_list
            )
            
            # --- GUARDAR EN BASE DE DATOS ---
            await self._save_to_db(query, report, sources_list, recommendations)
            
            return tool_output.model_dump()

        except Exception as e:
            logger.error(f"❌ Error in CrewResearchTool: {e}", exc_info=True)
            error_msg = f"Error durante la investigación con CrewAI: {str(e)}"
            return ToolOutputWithSources(context_for_llm=error_msg, sources=[]).model_dump()

    async def _save_to_db(self, query: str, report: str, sources: List[Source], recommendations: List[str]):
        """Guarda el resultado en la base de datos de análisis."""
        try:
            async with DBSession(SessionLocal) as db_session:
                title = f"Investigación CrewAI: {query[:50]}..."
                
                formatted_sources = [{
                    "id": s.id,
                    "title": s.title,
                    "url": s.url,
                    "snippet": s.snippet,
                    "type": s.type.value if hasattr(s.type, 'value') else str(s.type)
                } for s in sources]
                
                result_payload = {
                    "report": {
                        "final_report": report,
                        "sources": formatted_sources,
                        "recommendations": recommendations
                    },
                    "tool_used": "crew_research_tool.py",
                    "analysis_metadata": {
                        "query": query,
                        "workspace_id": self.workspace_id,
                        "created_at": datetime.now().isoformat(),
                        "engine": "CrewAI"
                    }
                }

                new_task = AnalysisTask(
                    account_id=uuid.UUID(self.account_id),
                    file_name=title,
                    analysis_type="gap_development",
                    status="completed",
                    result_payload=result_payload
                )
                db_session.add(new_task)
                await db_session.commit()
                logger.info(f"✅ Crew Research saved to DB with ID: {new_task.id}")
        except Exception as e:
            logger.error(f"⚠️ Error saving Crew Research to DB: {e}")

    async def _arun(self, query: str) -> Dict[str, Any]:
        """Use the tool asynchronously."""
        return await self._run(query)
