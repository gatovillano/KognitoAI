# tools/comprehensive_web_analysis_tool.py

import logging
import asyncio
from typing import Any, Type, List, Optional
import re

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.messages import HumanMessage
from bs4 import BeautifulSoup

# Import functionalities from other tools and modules
from tools.web_search_tool import search_and_summarize_web
from tools.web_scraper_tool import WebScraperTool
from core.memory_manager import get_relevant_memories
from core.llm_manager import get_fast_llm

logger = logging.getLogger(__name__)

class ComprehensiveWebAnalysisInput(BaseModel):
    """Input schema for the Comprehensive Web Analysis Tool."""
    query: str = Field(..., description="The user's research query in natural language.")
    account_id: str = Field(..., description="The unique ID of the user's account.")

class ComprehensiveWebAnalysisTool(BaseTool):
    """
    A comprehensive tool that orchestrates web searching, scraping, and knowledge base analysis
    to provide a synthesized answer to a user's query.
    """
    name: str = "comprehensive_web_analyzer"
    description: str = (
        "Use this tool for in-depth research requests. It searches the web, reads relevant pages, "
        "cross-references the findings with the user's personal knowledge base, and provides a "
        "synthesized analysis. Ideal for queries like 'research the latest trends in AI and "
        "compare them to my notes on the topic'."
    )
    args_schema: Type[BaseModel] = ComprehensiveWebAnalysisInput
    return_direct: bool = False

    def _extract_urls(self, search_results: str) -> List[str]:
        """Extracts URLs from the formatted search results string."""
        # The search_and_summarize_web function formats sources like:
        # "1. Title - <a href='URL'>Visitar enlace</a>"
        # We use regex to find all href values within anchor tags.
        urls = re.findall(r"<a href='(.*?)'>", search_results)
        logger.info(f"Extracted {len(urls)} URLs from search results: {urls}")
        return urls

    async def _arun(
        self,
        query: str,
        account_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Executes the comprehensive analysis tool asynchronously."""
        logger.info(f"--- Running Comprehensive Web Analysis for account {account_id} ---")
        logger.info(f"Query: {query}")

        # Step 1: Web Search
        logger.info("Step 1: Performing web search...")
        search_results_str = await search_and_summarize_web(query)
        if "Error" in search_results_str or "No se encontraron" in search_results_str:
            logger.warning("Web search did not yield results or failed.")
            return search_results_str

        urls_to_scrape = self._extract_urls(search_results_str)
        if not urls_to_scrape:
            logger.warning("No URLs could be extracted from the search results.")
            # Return the snippets if no URLs are found, as they might still be useful.
            soup = BeautifulSoup(search_results_str, "html.parser")
            return f"No pude extraer URLs específicas, pero aquí tienes un resumen de la búsqueda:\n\n{soup.get_text()}"

        # Step 2: Web Scraping
        logger.info(f"Step 2: Scraping content from {len(urls_to_scrape)} URLs...")
        scraper = WebScraperTool()
        scraping_tasks = [scraper._arun(url=url) for url in urls_to_scrape[:10]]  # Increase limit to 5 pages for broader context
        scraped_contents = await asyncio.gather(*scraping_tasks, return_exceptions=True)

        combined_web_content = ""
        for i, content in enumerate(scraped_contents):
            if isinstance(content, Exception):
                logger.error(f"Error scraping URL {urls_to_scrape[i]}: {content}")
            elif content:
                combined_web_content += f"--- Contenido de {urls_to_scrape[i]} ---\n{content}\n\n"
        
        if not combined_web_content.strip():
            logger.warning("Scraping did not yield any content.")
            return "No se pudo extraer contenido de las páginas web encontradas. Puede que estén protegidas o sean incompatibles."

        # Step 3: Initial Web Synthesis
        logger.info("Step 3: Synthesizing web content...")
        synthesis_llm = get_fast_llm()
        if not synthesis_llm:
            return "Error: El modelo de lenguaje para síntesis no está disponible."

        synthesis_prompt = f"""
        Eres un analista de investigación. A continuación se presenta el contenido extraído de varias páginas web sobre el tema '{query}'.
        Tu tarea es crear un resumen ejecutivo claro y conciso de esta información.
        Identifica los puntos clave, las conclusiones principales y cualquier dato relevante.

        --- INICIO DEL CONTENIDO WEB ---
        {combined_web_content}
        --- FIN DEL CONTENIDO WEB ---

        Por favor, genera el resumen ejecutivo:
        """
        web_summary_response = await synthesis_llm.ainvoke([HumanMessage(content=synthesis_prompt)])
        web_summary = web_summary_response.content

        # Step 4: Knowledge Base Integration
        logger.info("Step 4: Searching internal knowledge base...")
        relevant_memories = await get_relevant_memories(account_id, web_summary, k=5)

        # Step 5: Final Combined Analysis
        logger.info("Step 5: Performing final combined analysis...")
        final_analysis_llm = get_fast_llm() # Use the more powerful model for the final step
        if not final_analysis_llm:
            return "Error: El modelo de lenguaje para el análisis final no está disponible."
        
        final_prompt = f"""
        Eres Kognito, un asistente de IA experto en análisis y síntesis. Tu tarea es responder a la consulta original del usuario combinando la información recién investigada de la web con el conocimiento personal relevante del usuario.

        Consulta Original del Usuario: "{query}"

        --- Resumen Ejecutivo de la Investigación Web ---
        {web_summary}
        --- Fin del Resumen Web ---

        --- Información Relevante de la Base de Conocimiento Personal del Usuario ---
        {relevant_memories if "No se encontraron" not in relevant_memories else "No se encontró información interna relevante."}
        --- Fin de la Información Interna ---

        Basándote en TODA la información anterior, por favor, elabora una respuesta final y completa para el usuario.
        - Sintetiza los hallazgos clave.
        - Si encuentras conexiones, sinergias o contradicciones entre la información web y el conocimiento del usuario, destácalas.
        - Adopta un tono de asistente útil y experto.
        - Formatea tu respuesta de manera clara y legible usando Markdown.
        - **Importante:** Al final de tu respuesta, incluye una sección titulada "**Fuentes**" donde listes todas las URLs utilizadas en la investigación web ({', '.join(urls_to_scrape[:5])}). Asegúrate de que cada URL esté en formato de enlace clickable usando Markdown.
        """
        final_response = await final_analysis_llm.ainvoke([HumanMessage(content=final_prompt)])

        return final_response.content

    def _run(self, **kwargs: Any) -> str:
        """Synchronous execution is not supported."""
        raise NotImplementedError("This tool is designed for asynchronous use only.")
