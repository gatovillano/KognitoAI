# tools/web_scraper_tool.py

"""
Herramienta de LangChain para extraer el contenido textual de una página web.

Esta herramienta permite al agente de IA "leer" una página web proporcionada por el
usuario. Utiliza la librería `WebBaseLoader` de LangChain, que a su vez usa
`BeautifulSoup` para obtener el contenido principal de una URL, eliminando
elementos de navegación, anuncios, etc.

A diferencia de otras herramientas, esta no depende de un `account_id` ya que
la acción de leer una página web pública es independiente del usuario que la solicita.

Una consideración clave en la implementación es ejecutar la operación de red
(que es síncrona en `WebBaseLoader`) en un executor de hilos para no bloquear
el bucle de eventos principal (event loop) de nuestra aplicación asíncrona.
"""

import logging
import asyncio
from typing import Any, Type, List

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.documents import Document

# WebBaseLoader es una forma conveniente y robusta de cargar contenido web.
from langchain_community.document_loaders import WebBaseLoader
from core.config import settings
from core.database import *
from core.agent import *
from core.memory_manager import *
from core.notes_manager import *
from core.agenda_manager import *
from core.reminders_manager import *

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class WebScraperInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de scraping web.
    Valida que el LLM proporcione una URL válida.
    """
    url: str = Field(
        ...,
        description="La URL completa de la página web que se va a leer. Debe comenzar con http:// o https://."
    )


class WebScraperTool(BaseTool):
    """
    Una herramienta de LangChain que utiliza WebBaseLoader para obtener el
    contenido textual de una URL.
    """
    name: str = "web_scraper_tool"
    description: str = (
        "Una herramienta para obtener y leer el contenido de una URL de una página web específica. "
        "Úsala cuando el usuario proporcione una URL y quiera que la analices, resumas o respondas "
        "preguntas sobre su contenido. La entrada DEBE ser una URL válida."
    )
    args_schema: Type[BaseModel] = WebScraperInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, url: str, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            url: La URL de la página web a leer.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            El contenido textual de la página web o un mensaje de error.
        """
        logger.info(f"Ejecutando WebScraperTool para la URL: '{url}'")
        try:
            # WebBaseLoader.load() es una operación síncrona (bloqueante).
            # Para no congelar nuestro servidor asíncrono, la ejecutamos en
            # un hilo separado usando el executor del event loop.
            loader = WebBaseLoader(url)
            loop = asyncio.get_event_loop()
            
            # Ejecuta la función bloqueante en el pool de hilos por defecto con un timeout.
            docs: List[Document] = await asyncio.wait_for(
                loop.run_in_executor(
                    None,  # None usa el ThreadPoolExecutor por defecto.
                    loader.load
                ),
                timeout=15.0  # 15 segundos de timeout
            )

            if not docs:
                logger.warning(f"WebBaseLoader no devolvió documentos para la URL: {url}")
                return "No se pudo cargar ningún contenido desde esa URL. Podría estar vacía o protegida."

            # Concatenar el contenido de todos los documentos cargados (usualmente es solo uno).
            content = "\n\n".join([doc.page_content for doc in docs])
            
            # Truncar el contenido si es excesivamente largo para no sobrecargar el contexto del LLM.
            # 15,000 caracteres es un límite razonable.
            max_chars = 15000
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n... (contenido truncado para preservar el contexto)"
            
            logger.info(f"✅ Contenido extraído exitosamente de '{url}'. Longitud: {len(content)} caracteres.")
            return content
        except asyncio.TimeoutError:
            logger.error(f"Timeout en WebScraperTool para la URL '{url}'")
            return f"Ocurrió un error de timeout al intentar leer el contenido de la URL: {url}"
        except Exception as e:
            logger.error(f"Error en WebScraperTool para la URL '{url}': {e}", exc_info=True)
            return f"Ocurrió un error al intentar leer el contenido de la URL: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("web_scraper_tool no soporta ejecución síncrona.")
