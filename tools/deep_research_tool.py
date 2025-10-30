import logging
import traceback # Importar traceback para imprimir el stack trace
from typing import Type, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.tools import BaseTool, Tool
from core.llm_manager import get_main_llm, get_fast_llm
from core.config import settings # Importar settings
from tools.web_search_tool import get_web_search_tool
from tools.add_web_to_rag_tool import AddWebToRAGTool # Tu herramienta para añadir a RAG

try: # Importar DeepResearcher y ResearchConfig
    from external_agents.open_deep_research.src.open_deep_research.deep_researcher import deep_researcher # Importar el ejecutable de LangGraph
    from external_agents.open_deep_research.src.open_deep_research.configuration import Configuration as ResearchConfig # Importar Configuration como ResearchConfig
except ImportError as e:
    logging.error(f"Error importing deep_researcher: {e}. Make sure the open_deep_research module is correctly placed.")
    traceback.print_exc() # Imprimir el stack trace completo
    deep_researcher = None
    ResearchConfig = None

logger = logging.getLogger(__name__)

class DeepResearchToolInput(BaseModel):
    query: str = Field(description="The research query or topic to investigate.")

class DeepResearchTool(BaseTool):
    name: str = "deep_research_tool"
    description: str = "Performs a comprehensive deep research on a given query, leveraging multiple sources and generating a detailed report. Automatically adds relevant findings to RAG."
    args_schema: Type[BaseModel] = DeepResearchToolInput
    
    _deep_researcher: Optional[any] = None
    _web_search_tool: Tool
    _add_web_to_rag_tool: AddWebToRAGTool

    def __init__(self, web_search_tool: Tool, add_web_to_rag_tool: AddWebToRAGTool, **data):
        super().__init__(**data)
        self._web_search_tool = web_search_tool
        self._add_web_to_rag_tool = add_web_to_rag_tool

        if deep_researcher:
            self._deep_researcher = deep_researcher
            logger.info("✅ DeepResearchTool inicializado con el ejecutable de LangGraph 'deep_researcher'.")
        else:
            logger.warning("❌ El ejecutable 'deep_researcher' no pudo ser importado. La herramienta no funcionará.")

    async def _run(self, query: str) -> str:
        if not self._deep_researcher:
            return "Error: DeepResearchTool no está inicializado correctamente."

        logger.info(f"🚀 Iniciando investigación profunda para: {query}")
        try:
            # Preparar la configuración para la ejecución del grafo
            # La configuración se pasa como un diccionario simple a .ainvoke()
            main_llm = get_main_llm()
            if not main_llm:
                return "Error: El LLM principal no está inicializado."

            run_config = {
                "configurable": {
                    "research_model": settings.google_main_model_name,
                    "search_tool": self._web_search_tool,
                }
            }
            
            # El input para el grafo es un diccionario
            inputs = {"messages": [("user", query)]}
            
            # invocar el grafo
            research_result = await self._deep_researcher.ainvoke(inputs, config=run_config)
            
            # Extraer el informe final del resultado
            research_report = research_result.get("final_report", "No se generó un informe final.")
            
            rag_result = await self._add_web_to_rag_tool._run(url="", content=research_report, title=f"Deep Research Report: {query}", topic=query)
            logger.info(f"✅ Informe de investigación añadido a RAG: {rag_result}")

            return research_report
        except Exception as e:
            logger.error(f"❌ Error durante la investigación profunda: {e}")
            return f"Error al realizar la investigación profunda: {e}"