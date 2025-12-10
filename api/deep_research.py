import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.llm_manager import get_main_llm
from langchain_core.language_models.base import BaseLanguageModel
from tools.deep_research_tool_litellm import create_deep_research_tool_litellm
from tools.web_search_tool import get_web_search_tool # Importar la función de fábrica
from tools.add_web_to_rag_tool import AddWebToRAGTool

logger = logging.getLogger(__name__)

router = APIRouter()

class DeepResearchRequest(BaseModel):
    query: str

async def get_llm_instance() -> BaseLanguageModel:
    llm = get_main_llm()
    if not llm:
        raise HTTPException(status_code=500, detail="LLM no inicializado. Por favor, contacta al administrador.")
    return llm

@router.post("/deep_research/")
async def run_deep_research(
    request: DeepResearchRequest,
    llm_instance: BaseLanguageModel = Depends(get_llm_instance) # Usar la dependencia del LLM
):
    """
    Ejecuta una investigación profunda sobre una consulta dada y devuelve un informe.
    La información relevante se añade automáticamente al sistema RAG.
    """
    logger.info(f"Recibida solicitud de investigación profunda para: {request.query}")
    try:
        web_search_tool_instance = get_web_search_tool(account_id="deep_research_agent") # Asignar un account_id para la herramienta
        add_web_to_rag_tool_instance = AddWebToRAGTool(account_id="deep_research_agent")

        # Instanciar DeepResearchToolLiteLLM
        deep_research_tool = create_deep_research_tool_litellm(
            web_search_tool=web_search_tool_instance,
            add_web_to_rag_tool=add_web_to_rag_tool_instance
        )
        
        if not deep_research_tool:
            raise HTTPException(status_code=503, detail="El módulo de Deep Research no está disponible.")

        # Ejecutar la investigación
        research_report = await deep_research_tool._run(request.query)

        if "Error" in research_report:
            raise HTTPException(status_code=500, detail=research_report)

        return {"status": "success", "report": research_report}
    except Exception as e:
        logger.error(f"Error en el endpoint /deep_research/: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")
