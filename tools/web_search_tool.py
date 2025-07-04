# tools/web_search_tool.py

"""
Herramienta de Búsqueda Web para el Agente de Langchain, creada mediante una función de fábrica.

Este módulo proporciona una herramienta asíncrona que realiza búsquedas en la web
utilizando la API de Brave Search. Está diseñada para ser integrada en el
agente de LangChain, permitiéndole responder a preguntas sobre eventos actuales,
información que no se encuentra en su base de conocimiento, o cualquier consulta
que requiera datos frescos de internet.

Características de Diseño Notables:
1.  **Función de Fábrica:** La herramienta se instancia a través de `get_web_search_tool()`,
    un patrón limpio que encapsula la configuración.
2.  **Procesamiento en Dos Pasos:** La herramienta no devuelve una respuesta final.
    En su lugar, recupera la información y la formatea como un prompt para que el
    agente principal la sintetice, manteniendo así el tono y el contexto de la conversación.
3.  **Asincronía Nativa:** Utiliza `aiohttp` para realizar las peticiones a la API
    de forma no bloqueante, lo cual es ideal para el rendimiento del servidor.
"""

import logging
import asyncio
import re
from bs4 import BeautifulSoup
import aiohttp

# Importaciones de LangChain y del proyecto
from langchain_core.tools import Tool
from core.config import settings

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Función de ayuda para limpiar texto, eliminando espacios en blanco múltiples."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


async def search_and_summarize_web(query: str) -> str:
    """
    Realiza una búsqueda web asíncrona, procesa los resultados y los formatea
    para que el agente de LangChain los pueda interpretar y sintetizar.

    Args:
        query: La pregunta o término de búsqueda proporcionado por el LLM.

    Returns:
        Una cadena de texto formateada con los resultados de la búsqueda,
        lista para ser procesada por el agente, o un mensaje de error.
    """
    brave_api_key = settings.brave_search_api_key
    if not brave_api_key:
        logger.error("❌ La API key de Brave Search (BRAVE_SEARCH_API_KEY) no está configurada.")
        return "Error: La funcionalidad de búsqueda web no está configurada en el servidor."

    brave_api_url = "https://api.search.brave.com/res/v1/web/search"
    params = {"q": query, "count": 10, "safesearch": "moderate"}
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": brave_api_key,
        "User-Agent": "FitoAIAssistant/2.0 (BraveSearchTool)"
    }

    logger.info(f"🌐 Realizando búsqueda en Brave con la consulta: '{query}'")

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(brave_api_url, params=params, timeout=10) as response: # type: ignore
                response.raise_for_status()
                json_resp = await response.json()

        if "web" not in json_resp or "results" not in json_resp["web"]:
            logger.warning(f"⚠️ La respuesta de Brave Search no contenía 'web' o 'results' para la consulta: '{query}'.")
            return "La búsqueda web no devolvió resultados en el formato esperado."

        raw_results = json_resp["web"]["results"]  
        if not raw_results:
            logger.info(f"ℹ️ No se encontraron resultados relevantes para la consulta: '{query}'")
            return "No se encontraron resultados relevantes para tu búsqueda."

        snippets_to_summarize = []
        source_list = []
        for idx, item in enumerate(raw_results, 1):
            title = clean_text(item.get("title", ""))
            snippet_html = item.get("description", "")
            url = item.get("url", "")
            if title and snippet_html and url:
                soup = BeautifulSoup(snippet_html, "html.parser")
                clean_snippet = soup.get_text().strip()
                snippets_to_summarize.append(f"Fuente {idx}: {title}\nContenido: {clean_snippet}")
                source_list.append(f"{idx}. {title} - <a href='{url}'>Visitar enlace</a>")

        if not snippets_to_summarize:
            return "No se encontraron resultados de búsqueda con suficiente contenido para analizar."

        combined_snippets = "\n\n".join(snippets_to_summarize)
        
        final_response = (
            "Aquí están los resultados de la búsqueda web. Por favor, envia una respuesta comppleta final para el usuario "
            "basándote en esta información. IMPORTANTE, Debes mostrar el formato que te proporciono en la lista de fuentes.\n\n"
            f"--- Contexto de los Resultados de Búsqueda ---\n{combined_snippets}\n\n"
            f"--- Lista de Fuentes ---\n" + "\n".join(source_list)
        )
        
        logger.info(f"✅ Resultados de búsqueda procesados exitosamente para la consulta: '{query}'")
        return final_response

    except aiohttp.ClientError as e:
        logger.error(f"❌ Error HTTP durante la búsqueda en Brave para '{query}': {e}", exc_info=True)
        return f"Error de conexión con el servicio de búsqueda web: {e}"
    except Exception as e:
        logger.error(f"❌ Error inesperado en search_and_summarize_web para '{query}': {e}", exc_info=True)
        return f"Ocurrió un error inesperado al realizar la búsqueda web: {e}"


def get_web_search_tool() -> Tool:
    """
    Función de fábrica que crea y devuelve la herramienta de búsqueda web de LangChain.

    Returns:
        Una instancia de `langchain_core.tools.Tool` configurada para la búsqueda web.
    """
    return Tool(
        name="web_search_tool",
        description=(
            "Una potente herramienta de búsqueda web. Úsala cuando necesites responder preguntas sobre "
            "eventos actuales, encontrar información actualizada o acceder a conocimiento más allá de "
            "tus datos internos. La entrada debe ser una consulta de búsqueda clara y específica. No es necesario que te lo soliciten explicitamente"
            "si puedes complementar la información con una búsqueda, hazlo. Siempre devuelve al final la lista de fuentes"
        ),
        coroutine=search_and_summarize_web,
        func=None
    )