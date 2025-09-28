import logging
import traceback # Importar traceback para imprimir el stack trace
from typing import Type, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models.base import BaseLanguageModel # Importar BaseLanguageModel
from langchain_core.tools import BaseTool, Tool # Importar Tool
from tools.ddg_search_tool import create_ddg_search_tool # Importar la función de fábrica
from tools.add_web_to_rag_tool import AddWebToRAGTool # Tu herramienta para añadir a RAG

try:
    from external_agents.open_deep_research.deep_researcher import DeepResearcher
    from external_agents.open_deep_research.configuration import ResearchConfig
except ImportError as e:
    logging.error(f"Error importing DeepResearcher: {e}. Make sure the open_deep_research module is correctly placed.")
    traceback.print_exc() # Imprimir el stack trace completo
    DeepResearcher = None
    ResearchConfig = None

logger = logging.getLogger(__name__)

class DeepResearchToolInput(BaseModel):
    query: str = Field(description="The research query or topic to investigate.")

class DeepResearchTool(BaseTool):
    name: str = "deep_research_tool"
    description: str = "Performs a comprehensive deep research on a given query, leveraging multiple sources and generating a detailed report. Automatically adds relevant findings to RAG."
    args_schema: Type[BaseModel] = DeepResearchToolInput
    
    _deep_researcher: Optional[DeepResearcher] = None
    _llm_instance: BaseLanguageModel
    _ddg_search_tool: Tool
    _add_web_to_rag_tool: AddWebToRAGTool

    def __init__(self, llm_instance: BaseLanguageModel, ddg_search_tool: Tool, add_web_to_rag_tool: AddWebToRAGTool, **data):
        super().__init__(**data) # Pasamos solo los kwargs que BaseTool espera
        self._llm_instance = llm_instance
        self._ddg_search_tool = ddg_search_tool
        self._add_web_to_rag_tool = add_web_to_rag_tool

        if DeepResearcher:
            llm_for_researcher = self._llm_instance
            
            config = ResearchConfig(
                llm=llm_for_researcher,
                search_tool=self._ddg_search_tool # Esto es una simplificación, podría requerir un wrapper
            )
            
            self._deep_researcher = DeepResearcher(config=config)
            logger.info("✅ DeepResearchTool inicializado con DeepResearcher.")
        else:
            logger.warning("❌ DeepResearcher no pudo ser importado. La herramienta no funcionará.")

    async def _run(self, query: str) -> str:
        if not self._deep_researcher:
            return "Error: DeepResearchTool no está inicializado correctamente."

        logger.info(f"🚀 Iniciando investigación profunda para: {query}")
        try:
            research_report = await self._deep_researcher.run(query)
            
            rag_result = await self._add_web_to_rag_tool._run(url=None, content=research_report, title=f"Deep Research Report: {query}")
            logger.info(f"✅ Informe de investigación añadido a RAG: {rag_result}")

            return research_report
        except Exception as e:
            logger.error(f"❌ Error durante la investigación profunda: {e}")
            return f"Error al realizar la investigación profunda: {e}"