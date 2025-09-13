# tools/web_search_tool.py

"""
Herramienta unificada para realizar búsquedas web utilizando Brave Search,
siguiendo el método simple de LangChain.
"""

import os
import asyncio
import logging
import json
from typing import Type, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import AsyncCallbackManagerForToolRun
from urllib.parse import urlparse, urlunparse

from core.citation_models import Source, ToolOutputWithSources
from tools.web_scraper_tool import WebScraperTool

try:
    from langchain_community.tools import BraveSearch
    BRAVE_AVAILABLE = True
except ImportError:
    BRAVE_AVAILABLE = False
    logging.warning("No se pudo importar BraveSearch. Asegúrate de que `langchain-community` está instalado correctamente.")

logger = logging.getLogger(__name__)

class WebSearchInput(BaseModel):
    """Input schema para la herramienta de búsqueda web."""
    query: str = Field(
        description="La consulta de búsqueda que se enviará al motor de búsqueda.",
        json_schema_extra={"type": "string"}
    )

class WebSearchTool(BaseTool):
    """
    Herramienta para realizar búsquedas en la web utilizando Brave Search.
    Es un wrapper simple sobre la herramienta BraveSearch de LangChain.
    """
    account_id: str
    workspace_id: Optional[str] = None
    telegram_id: Optional[int] = None
    thread_id: Optional[str] = None
    
    name: str = "web_search"
    description: str = (
        "CUÁNDO USAR: Para realizar una investigación web exhaustiva sobre un tema. "
        "Esta herramienta busca en la web, lee el contenido completo de los 10 resultados más relevantes y lo proporciona como contexto. "
        "Úsala para responder preguntas que requieran conocimiento profundo y actualizado. "
        "INSTRUCCIONES IMPORTANTES PARA TU RESPUESTA FINAL: "
        "1. Debes generar una respuesta detallada y extensa, sintetizando la información de las fuentes. No te limites a un resumen corto. "
        "2. Es OBLIGATORIO que cites las fuentes en el texto utilizando un formato similar a APA, incluyendo el título de la fuente y su identificador. Por ejemplo: (Título de la Fuente, [Fuente X]). "
        "3. Al final de tu respuesta, debes incluir una sección de 'Referencias' (o 'Fuentes') listando las fuentes citadas en un formato similar a APA, incluyendo el título y la URL completa. Por ejemplo: 'Referencias:\n[1] Título de la Fuente 1. URL de la Fuente 1\n[2] Título de la Fuente 2. URL de la Fuente 2\n...'."
    )
    args_schema: Type[BaseModel] = WebSearchInput
    return_direct: bool = False

    _brave_search_tool: Optional[BraveSearch] = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not BRAVE_AVAILABLE:
            return
            
        api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        if api_key:
            self._brave_search_tool = BraveSearch.from_api_key(api_key=api_key, search_kwargs={"count": 10})
        else:
            logger.warning(
                "BRAVE_SEARCH_API_KEY no encontrada en las variables de entorno. "
                "La herramienta de búsqueda web no estará disponible."
            )

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any
    ) -> ToolOutputWithSources:
        logger.info(f"🏹 Realizando búsqueda en Brave con la consulta: '{query}'")
        
        if not self._brave_search_tool:
            return ToolOutputWithSources(
                context_for_llm="Error: La funcionalidad de búsqueda web no está configurada en el servidor.",
                sources=[]
            )
        
        try:
            loop = asyncio.get_event_loop()
            # Accedemos al wrapper interno para obtener resultados estructurados
            search_results_str = await self._brave_search_tool.arun(query)
            
            if not search_results_str:
                return ToolOutputWithSources(
                    context_for_llm="No se encontraron resultados de búsqueda.",
                    sources=[]
                )

            try:
                search_results = json.loads(search_results_str)
            except json.JSONDecodeError:
                logger.error(f"Error al decodificar la respuesta JSON de Brave: {search_results_str}")
                return ToolOutputWithSources(
                    context_for_llm="Error al procesar los resultados de la búsqueda (formato inválido).",
                    sources=[]
                )

            # Inicializar el scraper
            scraper = WebScraperTool(account_id=self.account_id)
            
            # Procesar todos los resultados para obtener el contenido completo
            for result in search_results:
                url = result.get("link")
                if not url:
                    continue
                
                logger.info(f"🔎 Scrapeando contenido de: {url}")
                scraped_content = await scraper._arun(url=url)
                
                scraped_content = await scraper._arun(url=url)
                
                # Verificar si el scrapeo fue exitoso y el contenido es válido
                if scraped_content and \
                   not scraped_content.startswith("Ocurrió un error") and \
                   not scraped_content.startswith("No se pudo"):
                    # Reemplazamos el snippet con el contenido completo.
                    result["snippet"] = scraped_content
                    logger.info(f"✅ Scrapeo exitoso para {url}. Contenido completo utilizado.")
                else:
                    logger.warning(f"⚠️ Scrapeo fallido o contenido inválido para {url}. Usando snippet original. Error/Contenido: {scraped_content}")
                    # Mantener el snippet original si el scrapeo falla o devuelve un error
                    # No es necesario hacer nada aquí, ya que result["snippet"] ya contiene el snippet original

            formatted_results, sources = self._format_results(search_results)
            return ToolOutputWithSources(context_for_llm=formatted_results, sources=sources)

        except Exception as e:
            logger.error(f"Error al realizar búsqueda con Brave: {str(e)}", exc_info=True)
            return ToolOutputWithSources(
                context_for_llm=f"Error al realizar la búsqueda: {str(e)}",
                sources=[]
            )

    def _format_results(self, results: List[Dict[str, str]]) -> tuple[str, List[Source]]:
        if not results:
            return "No se encontraron resultados.", []

        snippets = []
        sources: List[Source] = []
        for idx, r in enumerate(results, 1):
            if r.get('snippet'):
                snippets.append(f"Fuente {idx}: {r.get('title', 'Sin título')}\nContenido: {r.get('snippet')}")
                # Asegurarse de que la URL tenga un esquema completo
                original_url = r.get('link', '')
                parsed_url = urlparse(original_url)
                if not parsed_url.scheme:
                    # Si no hay esquema, asumir https por defecto
                    full_url = urlunparse(parsed_url._replace(scheme='https'))
                else:
                    full_url = original_url

                sources.append(
                    Source(
                        id=idx,
                        title=r.get('title', 'Sin título'),
                        url=full_url, # Usar la URL completa
                        snippet=r.get('snippet', '')
                    )
                )

        if not snippets:
            return "No se encontraron resultados con suficiente contenido.", []

        return f"Resultados de la búsqueda web:\n\n" + "\n\n".join(snippets), sources

    def _run(self, query: str, **kwargs: Any) -> str:
        """La ejecución síncrona no está implementada para este wrapper."""
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")

def get_web_search_tool(account_id: str) -> WebSearchTool:
    """Función de fábrica para crear una instancia de WebSearchTool."""
    return WebSearchTool(account_id=account_id)
