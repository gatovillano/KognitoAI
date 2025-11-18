# tools/comprehensive_web_analysis_tool.py

import json
import logging
import asyncio
from typing import Any, Type, List, Optional, cast
import re

from langchain_core.tools import Tool
from core.citation_models import ToolOutputWithSources, Source # <-- Añadir Source aquí

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.messages import HumanMessage
from core.prompts import KNOWLEDGE_SHARE_PRROMPT
from bs4 import BeautifulSoup

# Import functionalities from other tools and modules
from tools.web_search_tool import get_web_search_tool
from tools.web_scraper_tool import WebScraperTool
from core.memory_manager import get_relevant_memories # <-- Esta ya soporta workspace_id
from core.llm_manager import get_fast_llm
from utils.multi_query_retriever import MultiQueryRetriever, multi_query_search

logger = logging.getLogger(__name__)

class ComprehensiveWebAnalysisInput(BaseModel):
    """Input schema for the Comprehensive Web Analysis Tool."""
    query: str = Field(..., description="The user's research query in natural language.")
    
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
    account_id: Optional[str] = Field(None, description="ID de la cuenta asociada a esta herramienta.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace (UUID en formato string) para cruzar la información con documentos de un workspace específico, si aplica.")
    telegram_id: Optional[str] = Field(None, description="El ID del usuario de Telegram, si la solicitud proviene de Telegram.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación, si aplica.")

    def _extract_urls(self, search_results: List[Source]) -> List[str]:
        """Extracts URLs from a list of Source objects."""
        urls = [source['url'] for source in search_results if 'url' in source and source['url']]
        logger.info(f"Extracted {len(urls)} URLs from search results: {urls}")
        return urls

    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any
    ) -> str:
        """Executes the comprehensive analysis tool asynchronously."""
        # Usar account_id y workspace_id de los atributos de la instancia
        effective_account_id = self.account_id
        effective_workspace_id = self.workspace_id

        # Log para debugging
        logger.info(f"🔍 Debug config access - effective account_id: {effective_account_id}, effective workspace_id: {effective_workspace_id}")

        if not effective_account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        logger.info(f"--- Running Comprehensive Web Analysis for account {effective_account_id} (Workspace: {effective_workspace_id if effective_workspace_id else 'N/A'}) ---")
        logger.info(f"Query: {query}")

        max_iterations = 3
        iteration_count = 0
        combined_web_content_accumulated = ""
        urls_to_scrape_accumulated = []
        original_query = query # Guardar la consulta original

        # Bucle para decisiones impulsadas por LLM
        while iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"--- Iteration {iteration_count} of {max_iterations} ---")

            # Step 1: Web Search
            logger.info("Step 1: Performing web search...")
            web_search_tool_instance = get_web_search_tool(account_id=effective_account_id)
            if web_search_tool_instance._arun is None:
                logger.error("Error: web_search_tool_instance._arun is None. This should not happen.")
                return "Error interno: La herramienta de búsqueda web no está configurada correctamente."
            
            # Solicitamos 80 resultados como se pidió
            search_results_obj = cast(ToolOutputWithSources, await web_search_tool_instance._arun(query, max_results=80))
            search_context = search_results_obj.get('context_for_llm', '')
            if "Error" in search_context or "No se encontraron" in search_context:
                logger.warning("Web search did not yield results or failed. Returning raw search results.")
                # Si no hay resultados de búsqueda, no tiene sentido continuar el bucle.
                if not combined_web_content_accumulated.strip():
                    return search_results_obj.context_for_llm
                else:
                    break # Si ya hay contenido acumulado, intentar finalizar con lo que se tiene.

            urls_to_scrape = self._extract_urls(search_results_obj.get('sources', []))
            if not urls_to_scrape:
                logger.warning("No URLs could be extracted from the search results.")
                soup = BeautifulSoup(search_results_obj.get('context_for_llm', ''), "html.parser")
                # Si no hay URLs pero sí contenido de búsqueda, acumular el texto plano de la búsqueda.
                if soup.get_text().strip():
                    combined_web_content_accumulated += f"--- Resumen de Búsqueda (Iteración {iteration_count}) ---\n{soup.get_text()}\n\n"
                if not combined_web_content_accumulated.strip():
                    return f"No pude extraer URLs específicas, pero aquí tienes un resumen de la búsqueda:\n\n{soup.get_text()}"
                else:
                    break # Si ya hay contenido acumulado, intentar finalizar con lo que se tiene.

            # Step 2: Web Scraping
            logger.info(f"Step 2: Scraping content from {len(urls_to_scrape)} URLs...")
            scraper = WebScraperTool()
            scraping_tasks = [scraper._arun(url=url) for url in urls_to_scrape[:10]]
            scraped_contents = await asyncio.gather(*scraping_tasks, return_exceptions=True)

            current_iteration_web_content = ""
            for i, content in enumerate(scraped_contents):
                if isinstance(content, Exception):
                    logger.error(f"Error scraping URL {urls_to_scrape[i]}: {content}")
                elif content:
                    current_iteration_web_content += f"--- Contenido de {urls_to_scrape[i]} ---\n{content}\n\n"
                    urls_to_scrape_accumulated.append(urls_to_scrape[i]) # Acumular URLs

            if not current_iteration_web_content.strip():
                logger.warning("Scraping did not yield any content for this iteration.")
                if not combined_web_content_accumulated.strip():
                    return "No se pudo extraer contenido de las páginas web encontradas. Puede que estén protegidas o sean incompatibles."
                else:
                    break # Si ya hay contenido acumulado, intentar finalizar con lo que se tiene.
            
            combined_web_content_accumulated += current_iteration_web_content # Acumular contenido web

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
            {current_iteration_web_content}
            --- FIN DEL CONTENIDO WEB ---

            Por favor, genera el analisis:
            """
            web_summary_response = await synthesis_llm.ainvoke([HumanMessage(content=synthesis_prompt)])
            web_summary = web_summary_response.content

            # Step 4: Knowledge Base Integration
            logger.info("Step 4: Searching internal knowledge base using MultiQueryRetriever...")
            # Integración de MultiQueryRetriever
            # Se usa web_summary directamente para la consulta de RAG, ya que es concisa.
            relevant_memories_obj = await multi_query_search(
                account_id=effective_account_id,
                query=web_summary,
                workspace_id=effective_workspace_id,
                k=20,
                # El LLM para la generación de sub-queries es manejado internamente por MultiQueryRetriever
            )
            # Formatear los resultados de multi_query_search para el prompt final
            relevant_memories = "\n\n".join([mem.get('snippet', '') for mem in relevant_memories_obj if mem.get('snippet')])
            if not relevant_memories:
                relevant_memories = "No se encontró información interna relevante."

            # Step 5: LLM Decision Logic
            logger.info("Step 5: Querying LLM for decision on more search...")
            decision_llm = get_fast_llm()
            if not decision_llm:
                return "Error: El modelo de lenguaje para la decisión no está disponible."

            decision_prompt = f"""
            Eres un asistente de IA cuya única tarea es decidir si se necesita más información de la web para responder a una consulta original del usuario.
            Evalúa la siguiente información:

            Consulta Original del Usuario: "{original_query}"

            Resumen Acumulado de la Web:
            {combined_web_content_accumulated}

            Resumen de la Iteración Actual de la Web:
            {web_summary}

            Información Relevante de la Base de Conocimiento Personal del Usuario:
            {relevant_memories if "No se encontró" not in relevant_memories else "No se encontró información interna relevante."}

            Considera si la 'Consulta Original del Usuario' puede ser respondida completamente con el 'Resumen Acumulado de la Web' (que incluye el resumen de la iteración actual) y la 'Información Relevante de la Base de Conocimiento Personal'.
            Si la información es suficiente, responde con `needs_more_search: false`.
            Si la información no es suficiente y se necesita una nueva búsqueda, responde con `needs_more_search: true` y una `new_query` refinada basada en lo que falta.
            Asegúrate de que tu respuesta sea un objeto JSON válido.

            Ejemplo de respuesta si se necesita más búsqueda:
            ```json
            {{
              "needs_more_search": true,
              "new_query": "consulta refinada para la próxima búsqueda",
              "reason": "razón por la que se necesita más búsqueda"
            }}
            ```

            Ejemplo de respuesta si no se necesita más búsqueda:
            ```json
            {{
              "needs_more_search": false,
              "reason": "razón por la que no se necesita más búsqueda"
            }}
            ```

            Tu respuesta JSON:
            """
            decision_response = await decision_llm.ainvoke([HumanMessage(content=decision_prompt)])
            
            try:
                # Buscar el inicio del JSON (primer '{' o '[') y limpiar el contenido desde ahí.
                json_start_index = -1
                for char_index, char in enumerate(decision_response.content):
                    if char == '{' or char == '[':
                        json_start_index = char_index
                        break

                if json_start_index != -1:
                    cleaned_content = decision_response.content[json_start_index:].strip()
                else:
                    # Si no se encuentra un inicio de JSON, intentar con la limpieza original o dejarlo como está si no hay nada.
                    cleaned_content = re.sub(r'^.*?\|\s*', '', decision_response.content, flags=re.MULTILINE).strip()
                    logger.warning(f"No JSON start char found, falling back to regex cleaning. Raw content: {decision_response.content}")

                decision = json.loads(cleaned_content)
                logger.info(f"LLM Decision: {decision}")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM decision JSON: {e}. Raw response: {decision_response.content}")
                # Si el LLM no devuelve un JSON válido, asumimos que no se necesita más búsqueda para evitar un bucle infinito.
                decision = {"needs_more_search": False, "reason": "Error al parsear la respuesta del LLM, asumiendo que no se necesita más búsqueda."}

            # Step 6: Control Flow based on LLM Decision
            if decision.get('needs_more_search') and iteration_count < max_iterations:
                query = decision.get('new_query', query) # Actualizar la consulta para la próxima iteración
                logger.info(f"LLM requests more search. New query for next iteration: {query}")
                # El bucle continuará automáticamente
            else:
                logger.info("LLM indicates no more search needed or max iterations reached. Exiting loop.")
                break # Salir del bucle

        # --- Fin del Bucle de Decisión ---

        # Step 7: Final Combined Analysis (Ahora usa los acumulados)
        logger.info("Step 7: Performing final combined analysis...")
        final_analysis_llm = get_fast_llm()
        if not final_analysis_llm:
            return "Error: El modelo de lenguaje para el análisis final no está disponible."
        
        # Generar las fuentes en formato Markdown con enlaces, adaptado al nuevo formato del prompt
        formatted_sources = ""
        if urls_to_scrape_accumulated:
            for i, url in enumerate(urls_to_scrape_accumulated):
                # Para simplificar, usamos el dominio como título y "Desconocido" para autor.
                # En un caso real, se podría intentar extraer más metadatos de la URL.
                display_name = url.split("//")[1].split("/")[0] # Usar el dominio como título
                formatted_sources += (
                    f"    Fuente {i+1}: [**{display_name}**](<{url}>)\n"
                    f"        Autor: [Desconocido/No aplicable]\n"
                    f"        Relevancia: [Esta fuente fue relevante para el análisis general de la consulta original.]\n\n"
                )

        # Construir el prompt final para el análisis completo
        final_prompt = f"""
        Eres KAI, tu asistente de inteligencia aumentada. Tu tarea es generar un informe detallado y exhaustivo basado en la siguiente información recopilada.
        DEBES seguir la estructura y los principios del KNOWLEDGE_SHARE_PROMPT que se te proporcionó.
        Asegúrate de integrar toda la información relevante de forma coherente y detallada en cada sección del informe.

        --- Consulta Original del Usuario ---
        {original_query}

        --- Contenido Web Acumulado ---
        {combined_web_content_accumulated}

        --- Información Relevante de la Base de Conocimiento Personal del Usuario ---
        {relevant_memories if "No se encontró" not in relevant_memories else "No se encontró información interna relevante."}

        --- Fuentes Analizadas ---
        {formatted_sources if formatted_sources else "No se pudieron extraer fuentes específicas."}

        --- Estructura del Informe (KNOWLEDGE_SHARE_PRROMPT) ---
        {KNOWLEDGE_SHARE_PRROMPT}

        Por favor, genera el informe detallado ahora, rellenando la estructura con la información anterior:
        """
        final_response = await final_analysis_llm.ainvoke([HumanMessage(content=final_prompt)])

        return final_response.content

    def _run(self, **kwargs: Any) -> str:
        """Redirige la ejecución síncrona al método asíncrono."""
        logger.warning("⚠️ Método síncrono _run de ComprehensiveWebAnalysisTool fue llamado. Redirigiendo al método asíncrono.")
        import asyncio
        return asyncio.run(self._arun(**kwargs))
