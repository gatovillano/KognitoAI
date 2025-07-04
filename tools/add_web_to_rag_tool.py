# tools/add_web_to_rag_tool.py

"""
Herramienta simple para añadir contenido web a la base de datos vectorial.

Esta herramienta combina el scraping web con el procesamiento RAG, permitiendo
al usuario añadir directamente el contenido de una URL a su base de conocimiento.
"""

import logging
import asyncio
from typing import Any, Type, Optional, Dict
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader

from core.memory_manager import process_document_for_rag

logger = logging.getLogger(__name__)


class AddWebToRAGInput(BaseModel):
    """Esquema de entrada para añadir contenido web a la base vectorial."""
    
    url: str = Field(
        ..., 
        description="La URL completa de la página web a añadir. Debe comenzar con http:// o https://",
        json_schema_extra={"type": "string"}
    )
    topic: str = Field(
        ..., 
        description="Tema o categoría bajo la cual guardar el contenido web",
        json_schema_extra={"type": "string"}
    )
    account_id: str = Field(
        ..., 
        description="ID de la cuenta del usuario",
        json_schema_extra={"type": "string"}
    )
    workspace_id: Optional[str] = Field(
        None, 
        description="ID del workspace (opcional)",
        json_schema_extra={"type": "string"}
    )
    custom_title: Optional[str] = Field(
        None, 
        description="Título personalizado para el documento (opcional, se usará el de la página si no se especifica)",
        json_schema_extra={"type": "string"}
    )


class AddWebToRAGTool(BaseTool):
    """
    Herramienta para extraer contenido de una URL y añadirlo directamente 
    a la base de conocimiento del usuario.
    
    Combina web scraping + procesamiento RAG en una sola operación.
    """
    
    name: str = "add_web_to_rag"
    description: str = (
        "🌐 AÑADIR WEB A BASE DE CONOCIMIENTO - Usa esta herramienta cuando el usuario quiera: "
        "• Guardar el contenido de una página web en su base de conocimiento "
        "• Añadir artículos, blogs, documentación web para referencia futura "
        "• Procesar y almacenar contenido web para búsquedas posteriores "
        "\n✨ FUNCIONALIDAD: "
        "• Extrae automáticamente el contenido de la URL "
        "• Lo procesa y divide en chunks optimizados "
        "• Lo almacena en la base vectorial del usuario "
        "• Permite especificar tema/categoría y workspace "
        "\n⚡ EJEMPLO: 'guarda este artículo sobre IA', 'añade esta documentación a mi base de conocimiento'"
    )
    args_schema: Type[BaseModel] = AddWebToRAGInput
    
    def _extract_domain_name(self, url: str) -> str:
        """Extrae el nombre del dominio de una URL para usarlo como nombre de archivo."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path = parsed.path.strip('/').replace('/', '_')
            
            if path:
                return f"{domain}_{path}"
            return domain
        except Exception:
            return "web_content"
    
    async def _scrape_web_content(self, url: str) -> tuple[str, str]:
        """
        Extrae el contenido de una URL usando WebBaseLoader.
        
        Returns:
            tuple: (contenido_extraído, título_de_la_página)
        """
        logger.info(f"🌐 Extrayendo contenido de: {url}")
        
        try:
            loader = WebBaseLoader(url)
            loop = asyncio.get_event_loop()
            
            # Ejecutar en hilo separado para no bloquear
            docs: list[Document] = await asyncio.wait_for(
                loop.run_in_executor(None, loader.load),
                timeout=20.0  # 20 segundos de timeout
            )
            
            if not docs:
                raise Exception("No se pudo extraer contenido de la URL")
            
            # Concatenar contenido de todos los documentos
            content = "\n\n".join([doc.page_content for doc in docs])
            
            # Intentar extraer el título de los metadatos
            title = ""
            if docs[0].metadata:
                title = docs[0].metadata.get('title', '')
            
            if not title:
                # Fallback: usar el dominio como título
                title = self._extract_domain_name(url)
            
            logger.info(f"✅ Contenido extraído exitosamente. Longitud: {len(content)} chars, Título: {title}")
            return content, title
            
        except asyncio.TimeoutError:
            raise Exception(f"Timeout al acceder a la URL: {url}")
        except Exception as e:
            logger.error(f"❌ Error extrayendo contenido de {url}: {e}")
            raise Exception(f"Error al extraer contenido: {str(e)}")
    
    async def _arun(
        self,
        url: str,
        topic: str,
        account_id: str,
        workspace_id: Optional[str] = None,
        custom_title: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Ejecuta la herramienta de forma asíncrona."""
        
        logger.info(f"🚀 Iniciando AddWebToRAG para URL: {url}, topic: {topic}, workspace: {workspace_id}")
        
        try:
            # 1. Validar URL
            if not url.startswith(('http://', 'https://')):
                return "❌ Error: La URL debe comenzar con http:// o https://"
            
            # 2. Extraer contenido web
            try:
                content, extracted_title = await self._scrape_web_content(url)
            except Exception as e:
                return f"❌ Error al extraer contenido de la web: {str(e)}"
            
            if not content or len(content.strip()) < 50:
                return "❌ Error: No se pudo extraer contenido suficiente de la URL"
            
            # 3. Preparar metadatos
            file_name = custom_title or extracted_title or self._extract_domain_name(url)
            
            metadata = {
                "source_url": url,
                "source_type": "web_content",
                "original_title": extracted_title,
                "domain": urlparse(url).netloc,
                "type": "document_chunk"
            }
            
            # 4. Procesar para RAG
            logger.info(f"📊 Procesando contenido para RAG: {file_name}")
            
            chunks_added = await process_document_for_rag(
                account_id=account_id,
                file_name=file_name,
                extracted_text=content,
                topic=topic,
                metadata=metadata,
                workspace_id=workspace_id
            )
            
            if chunks_added > 0:
                workspace_info = f" en el workspace '{workspace_id}'" if workspace_id else ""
                logger.info(f"✅ Contenido web añadido exitosamente: {chunks_added} chunks")
                return (
                    f"✅ ¡Contenido web añadido exitosamente!\n\n"
                    f"📄 **Título:** {file_name}\n"
                    f"🌐 **URL:** {url}\n"
                    f"🏷️ **Tema:** {topic}\n"
                    f"📊 **Chunks procesados:** {chunks_added}\n"
                    f"📁 **Ubicación:** Tu base de conocimiento{workspace_info}\n\n"
                    f"Ya puedes hacer preguntas sobre este contenido."
                )
            else:
                return f"❌ Error: No se pudieron procesar los chunks del contenido web"
                
        except Exception as e:
            logger.error(f"❌ Error en AddWebToRAGTool: {e}", exc_info=True)
            return f"❌ Error inesperado al procesar la web: {str(e)}"
    
    def _run(
        self,
        url: str,
        topic: str,
        account_id: str,
        workspace_id: Optional[str] = None,
        custom_title: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Ejecuta la herramienta de forma síncrona."""
        try:
            result = asyncio.run(self._arun(
                url=url,
                topic=topic,
                account_id=account_id,
                workspace_id=workspace_id,
                custom_title=custom_title,
                **kwargs
            ))
            return result
        except RuntimeError as e:
            logger.warning(f"RuntimeError en _run: {e}. Usar _arun es preferido.")
            return "❌ Error: No se pudo ejecutar en modo síncrono. Intente en contexto asíncrono."
        except Exception as e:
            logger.error(f"❌ Error en ejecución síncrona: {e}", exc_info=True)
            return f"❌ Error al procesar la web: {str(e)}"
