# tools/deep_research_tool.py

import logging
import os
from typing import Type, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from core.agents.deep_researcher import compile_deep_researcher_graph
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import litellm
from litellm.exceptions import RateLimitError, ServiceUnavailableError
import httpx

# Nuevas importaciones para el sistema de citas
from core.citation_models import ToolOutputWithSources, Source, SourceType
from core.database import SessionLocal, AnalysisTask
from utils.db_session import DBSession
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class DeepResearchInput(BaseModel):
    """Input for the Deep Research tool."""
    query: str = Field(description="The research query to be investigated in-depth.")

class DeepResearchTool(BaseTool):
    """
    A tool to perform in-depth research on a given query using a specialized agent.
    It compiles a detailed report by planning, executing research, and synthesizing findings.
    """
    name: str = "deep_research"
    description: str = (
        "Conduct deep research on complex topics. Provide a research query and get a comprehensive report. "
        "Required parameter: query (string) - the research topic to investigate."
    )
    args_schema: Type[BaseModel] = DeepResearchInput
    account_id: str
    workspace_id: Optional[str] = None
    telegram_id: Optional[str] = None
    progress_callback: Optional[Any] = Field(default=None, exclude=True)

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=(retry_if_exception_type(RateLimitError) |
               retry_if_exception_type(ServiceUnavailableError) |
               retry_if_exception_type(httpx.HTTPStatusError)),
        reraise=True
    )
    async def _run(self, query: str) -> Dict[str, Any]:
        """Use the tool."""
        logger.info(f"Executing Deep Research tool for query: '{query}' for account: {self.account_id}")
        
        try:
            logger.info("Compiling deep researcher graph...")
            graph = compile_deep_researcher_graph()
            logger.info("Deep researcher graph compiled successfully.")
            
            config = {"configurable": {"account_id": self.account_id}}
            
            # --- PROGRESS CALLBACK INTEGRATION ---
            if hasattr(self, 'progress_callback') and self.progress_callback:
                config["configurable"]["progress_callback"] = self.progress_callback
                logger.info("Progress callback injected into Deep Research graph configuration.")

            inputs = {
                "messages": [HumanMessage(content=query)],
                "account_id": self.account_id
            }

            logger.info("Invoking Deep Research graph with inputs: %s", inputs)
            final_state = await graph.ainvoke(inputs, config=config)
            logger.info(f"Deep Research graph invocation completed. Final state keys: {final_state.keys()}")
            logger.debug("Full final state received: %s", final_state)
            
            if final_state and "final_report" in final_state:
                if final_state["final_report"] == "CLARIFICATION":
                    clarification_content = final_state["messages"][-1].content
                    logger.info("Deep research requires clarification. Returning message: %s", clarification_content)
                    # Devolver en el formato esperado por el agente, pero sin fuentes
                    return ToolOutputWithSources(context_for_llm=clarification_content, sources=[]).model_dump()
                
                report = final_state["final_report"]
                raw_sources = final_state.get("sources", [])
                
                logger.info(f"Deep research completed.")
                logger.info(f"Found {len(raw_sources)} sources to process.")

                # Crear la lista de objetos Source
                sources_list: List[Source] = []
                if raw_sources:
                    for i, raw_source in enumerate(raw_sources, start=1):
                        # Asegurarse de que raw_source es un diccionario
                        if isinstance(raw_source, dict):
                            source_obj = Source(
                                id=i,
                                title=raw_source.get("title", "Fuente Desconocida"),
                                url=raw_source.get("url", ""),
                                snippet=raw_source.get("content", "No hay contenido disponible."),
                                type=SourceType.WEB # Deep research siempre usa fuentes web
                            )
                            sources_list.append(source_obj)
                        else:
                            logger.warning(f"Elemento de fuente inesperado no es un diccionario: {raw_source}")


                # Crear el objeto de salida con fuentes
                tool_output = ToolOutputWithSources(
                    context_for_llm=report,
                    sources=sources_list
                )
                
                # Devolver el diccionario serializado
                
                # --- SAVE TO DATABASE ---
                try:
                    async with DBSession(SessionLocal) as db_session:
                        # Construct a title
                        title = f"Investigación Profunda: {query[:50]}..."
                        
                        # Prepare result payload similar to api/analysis.py
                        result_payload = {
                            "report": {
                                "final_report": report,
                                "sources": raw_sources,
                                "recommendations": final_state.get("recommendations", [])
                            },
                            "tool_used": "deep_research_tool.py",
                            "analysis_metadata": {
                                "tool_used": "deep_research_tool.py",
                                "analysis_type": "gap_development",
                                "query": query,
                                "workspace_id": self.workspace_id,
                                "created_at": datetime.now().isoformat()
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
                        logger.info(f"Deep Research saved to DB with ID: {new_task.id}")
                        
                except Exception as e:
                    logger.error(f"Error saving Deep Research to DB: {e}", exc_info=True)
                    # We don't fail the tool execution just because DB save failed

                return tool_output.model_dump()
            else:
                error_message = "Error: The deep research process finished, but no final report was generated or the final state was unexpected."
                logger.error(error_message + " Final state: %s", final_state)
                return ToolOutputWithSources(context_for_llm=error_message, sources=[]).model_dump()

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for DeepResearchTool. Retrying... Details: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"HTTP 429 (Too Many Requests) encountered. Retrying... Details: {str(e)}")
                raise
            else:
                error_message = f"Error: An HTTP error occurred while trying to run the deep research. Details: {str(e)}"
                logger.error(f"An HTTP error occurred in DeepResearchTool: {e}. Response: {e.response.text if e.response else 'N/A'}", exc_info=True)
                return ToolOutputWithSources(context_for_llm=error_message, sources=[]).model_dump()
        except Exception as e:
            error_message = f"Error: An unexpected error occurred while trying to run the deep research. Details: {str(e)}"
            logger.error(f"An unexpected error occurred in DeepResearchTool: {e}", exc_info=True)
            return ToolOutputWithSources(context_for_llm=error_message, sources=[]).model_dump()

    async def _arun(self, query: str) -> Dict[str, Any]:
        """Use the tool asynchronously."""
        return await self._run(query)