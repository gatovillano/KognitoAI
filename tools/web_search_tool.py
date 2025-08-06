# tools/web_search_tool.py

"""
Herramienta unificada para realizar búsquedas web.
"""

import asyncio
import logging
from typing import Type, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import AsyncCallbackManagerForToolRun

from core.citation_models import Source, ToolOutputWithSources

try:
    from ddgs import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False
    logging.warning("ddgs no está instalado. Instálalo con: pip install ddgs")

logger = logging.getLogger(__name__)

class WebSearchInput(BaseModel):
    """Input schema para la herramienta de búsqueda web."""
    query: str = Field(
        description="La consulta de búsqueda que se enviará al motor de búsqueda.",
        json_schema_extra={"type": "string"}
    )

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "CUÁNDO USAR: Cuando necesites buscar información en la web pública. Es ideal para responder preguntas sobre eventos actuales, temas de conocimiento general, o cualquier cosa que no se encuentre en la base de conocimiento interna del usuario."
    args_schema: Type[BaseModel] = WebSearchInput
    return_direct: bool = False

    async def _arun(
            self,
            query: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
            **kwargs
    ) -> ToolOutputWithSources:
        logger.info(f"🦆 Realizando búsqueda web con la consulta: '{query}'")
        if not DDG_AVAILABLE:
            return ToolOutputWithSources(context_for_llm="Error: La funcionalidad de búsqueda web no está disponible en el servidor.", sources=[])
        try:
            search_results = await self._search_duckduckgo(query)
            if not search_results:
                return ToolOutputWithSources(context_for_llm="No se encontraron resultados de búsqueda.", sources=[])

            formatted_results, sources = self._format_results(search_results)
            return ToolOutputWithSources(context_for_llm=formatted_results, sources=sources)

        except Exception as e:
            logger.error(f"Error al realizar búsqueda web: {str(e)}", exc_info=True)
            return ToolOutputWithSources(context_for_llm=f"Error al realizar la búsqueda: {str(e)}", sources=[])

    async def _search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not DDG_AVAILABLE: return []
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query, max_results)

    def _sync_search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results, region='es-es'))
        return [
            {
                'id': idx,
                'title': r.get('title', 'Sin título'),
                'snippet': r.get('body', ''),
                'url': r.get('href', '')
            }
            for idx, r in enumerate(search_results, 1)
        ]

    def _format_results(self, results: list) -> tuple[str, List[Source]]:
        if not results: return "No se encontraron resultados.", []

        snippets = []
        sources: List[Source] = []
        for r in results:
            if r.get('snippet') and len(r['snippet'].strip()) > 20:
                snippets.append(f"Fuente {r['id']}: {r['title']}\nContenido: {r['snippet']}")
                sources.append(Source(id=r['id'], title=r['title'], url=r['url'], snippet=r['snippet']))

        if not snippets: return "No se encontraron resultados con suficiente contenido.", []

        return f"Resultados de la búsqueda web:\n\n" + "\n\n".join(snippets), sources

    def _run(self, query: str, **kwargs) -> str:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")

def get_web_search_tool() -> WebSearchTool:
    """Función de fábrica para crear una instancia de WebSearchTool."""
    return WebSearchTool()
