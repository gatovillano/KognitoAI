# tools/comprehensive_web_analysis_tool.py

import logging
import asyncio
from typing import Any, Type, List, Optional, cast
import re

from langchain_core.tools import Tool
from core.citation_models import ToolOutputWithSources

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.messages import HumanMessage
from bs4 import BeautifulSoup

# Import functionalities from other tools and modules
from tools.web_search_tool import get_web_search_tool
from tools.web_scraper_tool import WebScraperTool
from core.memory_manager import get_relevant_memories # <-- Esta ya soporta workspace_id
from core.llm_manager import get_fast_llm

logger = logging.getLogger(__name__)

class ComprehensiveWebAnalysisInput(BaseModel):
    """Input schema for the Comprehensive Web Analysis Tool."""
    query: str = Field(..., description="The user's research query in natural language.")
    account_id: str = Field(default="", description="The unique ID of the user's account. If not provided, uses the one from agent configuration.")
    # --- NUEVO: Parámetro para el ID del workspace ---
    workspace_id: str = Field(
        default="",
        description="El ID del workspace (UUID en formato string) para cruzar la información con documentos de un workspace específico, si aplica."
)

class ComprehensiveWebAnalysisTool(BaseTool):
    """
    A comprehensive tool that orchestrates web searching, scraping, and knowledge base analysis
    to provide a synthesized answer to a user's query.
    """
    name: str = "comprehensive_web_analyzer"
    description: str = (\
        "Use this tool for in-depth research requests. It searches the web, reads relevant pages, "\
        "cross-references the findings with the user's personal knowledge base, and provides a "\
        "extended analysis. You can make another search with a second or third query to provide a better answer. Ideal for queries like 'research the latest trends in AI and "\
        "compare them to my notes on the topic'. "
        "Puede opcionalmente cruzar la información con documentos de un `workspace_id` específico." # <-- Descripción actualizada
    )
    args_schema: Type[BaseModel] = ComprehensiveWebAnalysisInput
    return_direct: bool = False
    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        """Initialize the tool with account_id."""
        super().__init__(**kwargs)
        self.account_id = account_id

    def _extract_urls(self, search_results: str) -> List[str]:
        """Extracts URLs from the formatted search results string."""
        urls = re.findall(r"<a href=\'(.*?)\'>", search_results)
        logger.info(f"Extracted {len(urls)} URLs from search results: {urls}")
        return urls

    async def _arun(\
        self,\
        query: str,\
        account_id: str = "",\
        workspace_id: Optional[str] = None, # <-- workspace_id añadido aquí
        run_manager: Optional[CallbackManagerForToolRun] = None,\
        **kwargs: Any\
    ) -> str:
        """Executes the comprehensive analysis tool asynchronously."""
        # Obtener account_id de la configuración del agente si está disponible
        config_account_id = None
        config_workspace_id = workspace_id

        # Intentar múltiples formas de obtener la configuración
        if run_manager:
            # Método 1: Acceso directo a config
            if hasattr(run_manager, 'config'):
                config = getattr(run_manager, 'config', {})
                configurable = config.get('configurable', {})
                config_account_id = configurable.get('account_id')
                if not config_workspace_id:
                    config_workspace_id = configurable.get('workspace_id')

            # Método 2: Buscar en kwargs del run_manager
            elif hasattr(run_manager, 'kwargs'):
                run_kwargs = getattr(run_manager, 'kwargs', {})
                config = run_kwargs.get('config', {})
                configurable = config.get('configurable', {})
                config_account_id = configurable.get('account_id')
                if not config_workspace_id:
                    config_workspace_id = configurable.get('workspace_id')

        # Método 3: Buscar en kwargs generales
        if not config_account_id and 'config' in kwargs:
            config = kwargs.get('config', {})
            configurable = config.get('configurable', {})
            config_account_id = configurable.get('account_id')
            if not config_workspace_id:
                config_workspace_id = configurable.get('workspace_id')

        # Usar configuración, parámetros o instancia como fallback
        effective_account_id = config_account_id or account_id or getattr(self, 'account_id', "") or ""
        effective_workspace_id = config_workspace_id

        # Log para debugging
        logger.info(f"🔍 Debug config access - account_id from config: {config_account_id}, from param: {account_id}, from instance: {getattr(self, 'account_id', None)}, effective: {effective_account_id}")

        if not effective_account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        logger.info(f"--- Running Comprehensive Web Analysis for account {effective_account_id} (Workspace: {effective_workspace_id if effective_workspace_id else 'N/A'}) ---")
        logger.info(f"Query: {query}")

        # Step 1: Web Search
        logger.info("Step 1: Performing web search...")
        web_search_tool_instance = get_web_search_tool()
        if web_search_tool_instance.coroutine is None:
            logger.error("Error: web_search_tool_instance.coroutine is None. This should not happen.")
            return "Error interno: La herramienta de búsqueda web no está configurada correctamente."
        
        search_results_obj = cast(ToolOutputWithSources, await web_search_tool_instance.coroutine(query))
        search_context = search_results_obj.context_for_llm
        if "Error" in search_context or "No se encontraron" in search_context:
            logger.warning("Web search did not yield results or failed. Returning raw search results.")
            return search_results_obj.context_for_llm

        urls_to_scrape = self._extract_urls(search_results_obj.context_for_llm)
        if not urls_to_scrape:
            logger.warning("No URLs could be extracted from the search results.")
            soup = BeautifulSoup(search_results_obj.context_for_llm, "html.parser")
            return f"No pude extraer URLs específicas, pero aquí tienes un resumen de la búsqueda:\n\n{soup.get_text()}"

        # Step 2: Web Scraping
        logger.info(f"Step 2: Scraping content from {len(urls_to_scrape)} URLs...")
        scraper = WebScraperTool()
        scraping_tasks = [scraper._arun(url=url) for url in urls_to_scrape[:10]]
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
        Tu tarea es crear un analisis claro y profundo de esta información.
        Identifica los puntos clave, las conclusiones principales y cualquier dato relevante.

        --- INICIO DEL CONTENIDO WEB ---
        {combined_web_content}
        --- FIN DEL CONTENIDO WEB ---

        Por favor, genera el analisis:
        """
        web_summary_response = await synthesis_llm.ainvoke([HumanMessage(content=synthesis_prompt)])
        web_summary = web_summary_response.content

        # Step 4: Knowledge Base Integration
        logger.info("Step 4: Searching internal knowledge base...")
        # --- MODIFICACIÓN: Pasar workspace_id a get_relevant_memories ---
        relevant_memories = await get_relevant_memories(effective_account_id, web_summary, k=5, workspace_id=effective_workspace_id)

        # Step 5: Final Combined Analysis
        logger.info("Step 5: Performing final combined analysis...")
        final_analysis_llm = get_fast_llm()
        if not final_analysis_llm:
            return "Error: El modelo de lenguaje para el análisis final no está disponible."
        
        final_prompt = f"""
        Eres Kognito, un asistente de IA experto en análisis y síntesis. Tu tarea es responder a la consulta original del usuario combinando la información recién investigada de la web con el conocimiento personal relevante del usuario.

        Consulta Original del Usuario: "{query}"

        --- Resumen Ejecutivo de la Investigación Web ---
        {web_summary}
        --- Fin del Resumen Web ---

        --- Información Relevante de la Base de Conocimiento Personal del Usuario ---
        {{relevant_memories if "No se encontraron" not in relevant_memories else "No se encontró información interna relevante."}}\\n
        --- Fin de la Información Interna ---

        Basándote en TODA la información anterior, por favor, elabora una respuesta final y completa para el usuario.
        - Sintetiza los hallazgos clave.
        - Si encuentras conexiones, sinergias o contradicciones entre la información web y el conocimiento del usuario, destácalas.
        - Adopta un tono de asistente útil y experto.
        - Formatea tu respuesta de manera clara y legible usando Markdown.\n
        - **Importante:** Al final de tu respuesta, incluye una sección titulada "**Fuentes** donde listes todas las URLs utilizadas en la investigación web ({', '.join([f'[{url.split("//")[1].split("/")[0]}](<{url}>)' for url in urls_to_scrape[:5]])}). Asegúrate de que cada URL esté en formato de enlace clickable usando Markdown.\n
        """
        final_response = await final_analysis_llm.ainvoke([HumanMessage(content=final_prompt)])

        return final_response.content

    def _run(self, **kwargs: Any) -> str:
        """Redirige la ejecución síncrona al método asíncrono."""
        logger.warning("⚠️ Método síncrono _run de ComprehensiveWebAnalysisTool fue llamado. Redirigiendo al método asíncrono.")
        import asyncio
        return asyncio.run(self._arun(**kwargs))
