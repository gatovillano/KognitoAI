import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from core.agents.deep_researcher import compile_deep_researcher_graph
from core.llm_manager import get_main_llm
from langchain_core.language_models.base import BaseLanguageModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Compilar el grafo una sola vez al iniciar la aplicación
try:
    deep_researcher_graph = compile_deep_researcher_graph()
    logger.info("Deep Researcher graph compiled successfully.")
except Exception as e:
    logger.error(f"Failed to compile Deep Researcher graph: {e}", exc_info=True)
    deep_researcher_graph = None

class DeepResearchRequest(BaseModel):
    query: str
    account_id: str = "api_user"

async def get_llm_instance() -> BaseLanguageModel:
    llm = get_main_llm()
    if not llm:
        raise HTTPException(status_code=500, detail="LLM not initialized. Please contact administrator.")
    return llm

@router.post("/deep_research/")
async def run_deep_research(
    request: DeepResearchRequest,
    llm_instance: BaseLanguageModel = Depends(get_llm_instance) # Asegura que el LLM esté disponible
):
    """
    Ejecuta una investigación profunda sobre una consulta dada utilizando el agente LangGraph.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    logger.info(f"Received deep research request for: '{request.query}' by account '{request.account_id}'")
    
    try:
        # Configuración para el grafo
        run_id = str(uuid.uuid4())
        config = {
            "configurable": {
                "account_id": request.account_id,
                "thread_id": run_id,
            }
        }
        
        # Entradas para el grafo
        inputs = {
            "messages": [HumanMessage(content=request.query)],
            "account_id": request.account_id
        }

        logger.info(f"Invoking Deep Research graph with run_id: {run_id}")
        
        # Ejecutar el grafo
        final_state = await deep_researcher_graph.ainvoke(inputs, config=config)

        if final_state and "final_report" in final_state:
            # Manejar el caso de clarificación
            if final_state.get("final_report") == "CLARIFICATION":
                logger.info(f"Deep research for run_id {run_id} requires clarification.")
                clarification_question = "No clarification question found."
                if final_state.get("messages"):
                    clarification_question = final_state["messages"][-1].content
                return {"status": "clarification_needed", "message": clarification_question}
            
            logger.info(f"Deep research completed successfully for run_id: {run_id}")
            return {"status": "success", "report": final_state["final_report"]}
        else:
            logger.error(f"Deep research for run_id {run_id} finished without a final report.")
            return {"status": "error", "detail": "The deep research process finished, but no final report was generated."}

    except Exception as e:
        logger.error(f"Error in /deep_research/ endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")