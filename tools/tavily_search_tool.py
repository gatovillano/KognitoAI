"""
Herramienta de búsqueda web usando Tavily Search API.
Proporciona búsquedas optimizadas para LLMs con resultados de alta calidad.
"""

import os
import logging
from typing import Type, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import AsyncCallbackManagerForToolRun

# Importamos las clases necesarias
from core.citation_models import Source, ToolOutputWithSources
from core.agents.deep_researcher_utils import generate_stable_id

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logging.warning("tavily-python no está instalado. Instálalo con: pip install tavily-python")

# Configurar logging
logger = logging.getLogger(__name__)

class TavilySearchInput(BaseModel):
    """Input schema for Tavily search tool."""
    query: str = Field(
        description="La consulta de búsqueda que se enviará a Tavily",
        json_schema_extra={"type": "string"}
    )

class TavilySearchTool(BaseTool):
    """
    Herramienta de búsqueda web usando Tavily Search API.
    Esta herramienta realiza búsquedas web optimizadas para IA y devuelve
    resultados formateados con títulos, snippets y URLs.
    """
    name: str = "tavily_search_tool"
    description: str = (
        "Herramienta de búsqueda web avanzada usando Tavily. "
        "Realiza búsquedas en internet optimizadas para modelos de lenguaje, "
        "devolviendo resultados precisos con títulos, descripciones y enlaces. "
        "Es ideal para obtener información factual y actualizada de la web."
    )
    args_schema: Type[BaseModel] = TavilySearchInput
    return_direct: bool = False
    account_id: str
    workspace_id: Optional[str] = None
    telegram_id: Optional[int] = None
    thread_id: Optional[str] = None

    async def _arun(
            self,
            query: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """Ejecuta la búsqueda en Tavily de forma asíncrona."""
        logger.info(f"🔍 Realizando búsqueda en Tavily con la consulta: '{query}'")
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.error("❌ TAVILY_API_KEY no encontrada en las variables de entorno")
            return ToolOutputWithSources(
                context_for_llm="Error: La API Key de Tavily no está configurada.", 
                sources=[]
            ).model_dump()

        if not TAVILY_AVAILABLE:
            logger.error("❌ La librería tavily-python no está instalada")
            return ToolOutputWithSources(
                context_for_llm="Error: La librería tavily-python no está instalada.", 
                sources=[]
            ).model_dump()

        try:
            # Inicializar cliente de Tavily
            client = TavilyClient(api_key=api_key)
            
            # Realizar búsqueda
            # Usamos search para obtener resultados básicos optimizados
            search_results = client.search(
                query=query,
                search_depth="advanced",
                max_results=8,
                include_answer=False
            )
            
            results = search_results.get('results', [])
            
            if not results:
                logger.warning(f"⚠️ No se encontraron resultados en Tavily para: '{query}'")
                return ToolOutputWithSources(
                    context_for_llm="No se encontraron resultados de búsqueda para la consulta proporcionada.", 
                    sources=[]
                ).model_dump()

            # Formatear resultados
            formatted_results, sources = self._format_results(results, query)
            logger.info(f"✅ Resultados de búsqueda Tavily procesados exitosamente para la consulta: '{query}'")
            
            output = ToolOutputWithSources(context_for_llm=formatted_results, sources=sources)
            return output.model_dump()

        except Exception as e:
            error_msg = f"❌ Error al realizar búsqueda en Tavily: {str(e)}"
            logger.error(error_msg)
            return ToolOutputWithSources(
                context_for_llm=f"Error al realizar la búsqueda en Tavily: {str(e)}", 
                sources=[]
            ).model_dump()

    def _format_results(self, results: list, query: str) -> tuple[str, List[Source]]:
        """
        Formatea los resultados de búsqueda en un contexto para el LLM y una lista de fuentes.
        """
        from core.citation_models import format_context_with_sources, create_web_source

        sources: List[Source] = []
        for idx, result in enumerate(results, 1):
            source = create_web_source(
                source_id=generate_stable_id(result.get('url', ''), prefix="web"),
                title=result.get('title', 'Sin título'),
                url=result.get('url', ''),
                snippet=result.get('content', 'Sin descripción disponible')
            )
            sources.append(source)

        if not sources:
            return "No se encontraron resultados de búsqueda con suficiente contenido para analizar.", []

        # Usamos la función centralizada para formatear el contexto
        context_for_llm = format_context_with_sources(sources)

        return context_for_llm, sources

    def _run(self, query: str, **kwargs) -> str:
        """Versión síncrona (no implementada, usa la versión async)."""
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona. Usa _arun en su lugar.")

def create_tavily_search_tool(account_id: str) -> TavilySearchTool:
    """
    Crea una instancia de TavilySearchTool con el account_id especificado.
    """
    return TavilySearchTool(account_id=account_id)
