"""
Herramienta de búsqueda web usando DuckDuckGo Search.
Alternativa a Brave Search con funcionalidades similares.
"""

import asyncio
import logging
from typing import Type, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import AsyncCallbackManagerForToolRun

try:
    from ddgs import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False
    logging.warning("ddgs no está instalado. Instálalo con: pip install ddgs")

# Configurar logging
logger = logging.getLogger(__name__)

class DuckDuckGoSearchInput(BaseModel):
    """Input schema for DuckDuckGo search tool."""
    query: str = Field(
        description="La consulta de búsqueda que se enviará a DuckDuckGo",
        json_schema_extra={"type": "string"}
    )

class DuckDuckGoSearchTool(BaseTool):
    """
    Herramienta de búsqueda web usando DuckDuckGo Search API.
    
    Esta herramienta realiza búsquedas web usando DuckDuckGo y devuelve
    resultados formateados con títulos, snippets y URLs.
    """
    
    name: str = "ddg_search_tool"
    description: str = (
        "Herramienta de búsqueda web usando DuckDuckGo. "
        "Realiza búsquedas en internet y devuelve resultados con títulos, "
        "descripciones y enlaces. Ideal para obtener información actualizada "
        "de múltiples fuentes web. Alternativa a Brave Search."
    )
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput
    return_direct: bool = False
    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """Ejecuta la búsqueda en DuckDuckGo de forma asíncrona."""
        
        logger.info(f"🦆 Realizando búsqueda en DuckDuckGo con la consulta: '{query}'")
        
        try:
            # Realizar búsqueda usando DuckDuckGo
            search_results = await self._search_duckduckgo(query)
            
            if not search_results:
                logger.warning(f"⚠️ No se encontraron resultados para la consulta: '{query}'")
                return "No se encontraron resultados de búsqueda para la consulta proporcionada."
            
            # Formatear resultados
            formatted_results = self._format_results(search_results, query)
            
            logger.info(f"✅ Resultados de búsqueda DuckDuckGo procesados exitosamente para la consulta: '{query}'")
            return formatted_results
            
        except Exception as e:
            error_msg = f"❌ Error al realizar búsqueda en DuckDuckGo: {str(e)}"
            logger.error(error_msg)
            return f"Error al realizar la búsqueda: {str(e)}"

    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """
        Realiza la búsqueda usando DuckDuckGo Search.
        """
        if not DDG_AVAILABLE:
            logger.error("ddgs no está disponible")
            return []

        try:
            # Ejecutar búsqueda en un hilo separado para evitar bloqueo
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self._sync_search, query)
            return results

        except Exception as e:
            logger.error(f"Error al realizar búsqueda en DuckDuckGo: {str(e)}")
            return []

    def _sync_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Realiza la búsqueda síncrona usando DuckDuckGo.
        """
        try:
            with DDGS() as ddgs:
                # Realizar búsqueda web
                search_results = list(ddgs.text(
                    keywords=query,
                    max_results=10,
                    region='es-es',  # Región en español
                    safesearch='moderate',
                    timelimit=None
                ))

                results = []
                for result in search_results:
                    results.append({
                        'title': result.get('title', 'Sin título'),
                        'snippet': result.get('body', 'Sin descripción disponible'),
                        'url': result.get('href', ''),
                        'source': 'DuckDuckGo Web'
                    })

                return results

        except Exception as e:
            logger.error(f"Error en búsqueda síncrona DuckDuckGo: {str(e)}")
            return []

    def _format_results(self, results: list, query: str) -> str:
        """
        Formatea los resultados de búsqueda en un formato legible.
        """
        if not results:
            return "No se encontraron resultados de búsqueda."
        
        snippets_to_summarize = []
        source_list = []
        
        for idx, result in enumerate(results, 1):
            title = result.get('title', 'Sin título')
            snippet = result.get('snippet', 'Sin descripción disponible')
            url = result.get('url', '')
            source = result.get('source', 'DuckDuckGo')
            
            # Limpiar y preparar el snippet
            if snippet and len(snippet.strip()) > 20:
                # Información detallada para el LLM
                detailed_info = f"**Fuente {idx}: {title}**\n"
                detailed_info += f"Contenido: {snippet}\n"
                if url:
                    detailed_info += f"URL: {url}\n"
                detailed_info += f"Proveedor: {source}\n"
                
                snippets_to_summarize.append(detailed_info)
                
                # Lista de fuentes formateada para mostrar al usuario
                source_entry = f"**{idx}. {title}**"
                source_entry += f" (Fuente: {source})"
                if url:
                    source_entry += f"\n   🔗 [Ver fuente completa]({url})"
                else:
                    source_entry += f"\n   📄 Información de DuckDuckGo"
                source_list.append(source_entry)
        
        if not snippets_to_summarize:
            return "No se encontraron resultados de búsqueda con suficiente contenido para analizar."
        
        combined_snippets = "\n\n".join(snippets_to_summarize)
        
        final_response = (
            "Aquí están los resultados de la búsqueda web con DuckDuckGo. INSTRUCCIONES IMPORTANTES para tu respuesta:\n\n"
            "1. Proporciona una respuesta DETALLADA y COMPLETA basada en la información encontrada\n"
            "2. NO resumas excesivamente - incluye detalles específicos, datos, fechas y contexto relevante\n"
            "3. SIEMPRE incluye la sección 'Fuentes' al final con los enlaces exactos que te proporciono\n"
            "4. Organiza la información de manera clara con subtítulos si es necesario\n"
            "5. Si hay información contradictoria entre fuentes, menciónalo\n"
            "6. Mantén un tono conversacional pero informativo\n\n"
            f"--- INFORMACIÓN DETALLADA DE LAS FUENTES ---\n{combined_snippets}\n\n"
            f"--- FUENTES (INCLUIR OBLIGATORIAMENTE AL FINAL) ---\n" + "\n".join(source_list) + "\n\n"
            "RECUERDA: Tu respuesta debe ser detallada, informativa y SIEMPRE incluir la sección de fuentes con los enlaces."
        )
        
        logger.info(f"✅ Resultados de búsqueda DuckDuckGo procesados exitosamente para la consulta: '{query}'")
        return final_response

    def _run(self, query: str, **kwargs) -> str:
        """Versión síncrona (no implementada, usa la versión async)."""
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona. Usa _arun en su lugar.")


# Función para crear la herramienta con account_id
def create_ddg_search_tool(account_id: str) -> DuckDuckGoSearchTool:
    """
    Crea una instancia de DuckDuckGoSearchTool con el account_id especificado.
    
    Args:
        account_id: ID de la cuenta del usuario
        
    Returns:
        DuckDuckGoSearchTool: Instancia configurada de la herramienta
    """
    return DuckDuckGoSearchTool(account_id=account_id)
