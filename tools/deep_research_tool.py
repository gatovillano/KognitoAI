# tools/deep_research_tool.py

import logging
import os
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from core.agents.deep_researcher import compile_deep_researcher_graph
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted
import httpx

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

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60), # Espera exponencial entre 4 y 60 segundos
        stop=stop_after_attempt(5), # Reintentar un máximo de 5 veces
        retry=(retry_if_exception_type(ResourceExhausted) | # Reintentar si es un error de cuota de Google
               retry_if_exception_type(httpx.HTTPStatusError)), # Reintentar si es un error HTTP
        reraise=True # Volver a lanzar la excepción si todos los reintentos fallan
    )
    async def _run(self, query: str) -> str:
        """Use the tool."""
        logger.info(f"Executing Deep Research tool for query: '{query}' for account: {self.account_id}")
        
        try:
            # Compilar el grafo del agente de investigación profunda
            graph = compile_deep_researcher_graph()
            
            # Configuración para la ejecución del grafo
            config = {"configurable": {"account_id": self.account_id}}
            
            # Entradas para el grafo
            inputs = {
                "messages": [HumanMessage(content=query)],
                "account_id": self.account_id
            }

            logger.info("Invoking Deep Research graph...")
            final_state = await graph.ainvoke(inputs, config=config)
            
            if final_state and "final_report" in final_state:
                if final_state["final_report"] == "CLARIFICATION":
                    logger.info("Deep research requires clarification from the user.")
                    # The last message should be the clarification question
                    return final_state["messages"][-1].content
                
                logger.info("Deep research completed successfully.")
                return final_state["final_report"]
            else:
                logger.error("Deep research finished without a final report.")
                return "Error: The deep research process finished, but no final report was generated."

        except ResourceExhausted as e:
            logger.warning(f"Rate limit exceeded for DeepResearchTool. Retrying... Details: {str(e)}")
            raise # Re-lanzar para que tenacity lo capture
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"HTTP 429 (Too Many Requests) encountered for DeepResearchTool. Retrying... Details: {str(e)}")
                raise # Re-lanzar para que tenacity lo capture
            else:
                logger.error(f"An HTTP error occurred in DeepResearchTool: {e}", exc_info=True)
                return f"Error: An HTTP error occurred while trying to run the deep research. Details: {str(e)}"
        except Exception as e:
            logger.error(f"An unexpected error occurred in DeepResearchTool: {e}", exc_info=True)
            return f"Error: An unexpected error occurred while trying to run the deep research. Details: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        return await self._run(query)