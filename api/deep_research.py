import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage 
from typing import List, Union 

from core.agents.deep_researcher import compile_deep_researcher_graph
from core.llm_manager import get_main_llm
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage 

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

class ClarificationResponse(BaseModel):
    run_id: str
    user_response: str
    account_id: str = "api_user"

async def get_llm_instance() -> BaseLanguageModel:
    llm = get_main_llm()
    if not llm:
        raise HTTPException(status_code=500, detail="LLM not initialized. Please contact administrator.")
    return llm

@router.post("/deep_research/")
async def run_deep_research(
    request: DeepResearchRequest,
    llm_instance: BaseLanguageModel = Depends(get_llm_instance) 
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
                # Asegurarse de que messages sea una lista y no esté vacío
                if final_state.get("messages") and isinstance(final_state["messages"], list):
                    # Buscar el último mensaje que sea AIMessage (la pregunta del LLM)
                    for msg in reversed(final_state["messages"]):
                        if isinstance(msg, AIMessage):
                            clarification_question = msg.content
                            break
                return {"status": "clarification_needed", "message": clarification_question, "run_id": run_id}
            
            logger.info(f"Deep research completed successfully for run_id: {run_id}")
            return {
                "status": "success", 
                "report": {
                    "final_report": final_state.get("final_report"),
                    "sources": final_state.get("sources", []),
                    "recommendations": final_state.get("recommendations", [])
                }
            }
        else:
            logger.error(f"Deep research for run_id {run_id} finished without a final report.")
            return {"status": "error", "detail": "The deep research process finished, but no final report was generated."}

    except Exception as e:
        logger.error(f"Error in /deep_research/ endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@router.post("/deep_research/clarify")
async def clarify_deep_research(
    request: ClarificationResponse,
    llm_instance: BaseLanguageModel = Depends(get_llm_instance)
):
    """
    Proporciona una respuesta a una pregunta de clarificación para una investigación profunda en curso.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    logger.info(f"Received clarification response for run_id: {request.run_id} with response: '{request.user_response}'")

    try:
        config = {
            "configurable": {
                "account_id": request.account_id,
                "thread_id": request.run_id,
            }
        }
        
        # El grafo se reanuda desde el último estado.
        # Añadimos la respuesta del usuario a los mensajes.
        inputs = {
            "messages": [HumanMessage(content=request.user_response)],
            "account_id": request.account_id 
        }

        logger.info(f"Re-invoking Deep Research graph with run_id: {request.run_id} after clarification.")
        
        final_state = await deep_researcher_graph.ainvoke(inputs, config=config)

        if final_state and "final_report" in final_state:
            if final_state.get("final_report") == "CLARIFICATION":
                logger.info(f"Deep research for run_id {request.run_id} still requires clarification.")
                clarification_question = "No clarification question found."
                if final_state.get("messages") and isinstance(final_state["messages"], list):
                    for msg in reversed(final_state["messages"]):
                        if isinstance(msg, AIMessage):
                            clarification_question = msg.content
                            break
                return {"status": "clarification_needed", "message": clarification_question, "run_id": request.run_id}
            
            logger.info(f"Deep research completed successfully for run_id: {request.run_id} after clarification.")
            return {
                "status": "success", 
                "report": {
                    "final_report": final_state.get("final_report"),
                    "sources": final_state.get("sources", []),
                    "recommendations": final_state.get("recommendations", [])
                }
            }
        else:
            logger.error(f"Deep research for run_id {request.run_id} finished without a final report after clarification.")
            return {"status": "error", "detail": "The deep research process finished, but no final report was generated after clarification."}

    except Exception as e:
        logger.error(f"Error in /deep_research/clarify endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")