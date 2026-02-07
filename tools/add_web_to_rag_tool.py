# tools/add_web_to_rag_tool.py

"""
Herramienta simple para añadir contenido web a la base de datos vectorial.

Esta herramienta combina el scraping web con el procesamiento RAG, permitiendo
al usuario añadir directamente el contenido de una URL a su base de conocimiento,
con notificaciones en tiempo real a través de WebSockets.
"""

import logging
import asyncio
import uuid
import datetime
from typing import Any, Type, Optional, Dict
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader

from core.memory_manager import process_document_for_rag
from core.websocket_manager import send_personal_message

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
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            loader = WebBaseLoader(url, requests_kwargs={"headers": headers})
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
    
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace, inyectado automáticamente.")
    telegram_id: Optional[str] = Field(None, description="ID de Telegram del usuario, inyectado automáticamente.")
    thread_id: Optional[str] = Field(None, description="ID del hilo de conversación, inyectado automáticamente.")

    async def _arun(
        self,
        url: str,
        topic: str,
        custom_title: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Ejecuta la herramienta de forma asíncrona en segundo plano, enviando actualizaciones por WebSocket."""
        
        task_id = str(uuid.uuid4())
        
        await send_personal_message(
            self.account_id,
            {
                "type": "upload_started",
                "task_id": task_id,
                "file_names": [url],
                "topic": topic,
                "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
        )

        logger.info(f"🚀 Iniciando AddWebToRAG para URL: {url}, topic: {topic}, task_id: {task_id}")
        
        try:
            if not url.startswith(('http://', 'https://')):
                raise ValueError("La URL debe comenzar con http:// o https://")
            
            await send_personal_message(
                self.account_id,
                {
                    "type": "upload_progress",
                    "task_id": task_id,
                    "progress": 10,
                    "message": "Extrayendo contenido de la web..."
                }
            )

            content, extracted_title = await self._scrape_web_content(url)
            
            if not content or len(content.strip()) < 50:
                raise ValueError("No se pudo extraer contenido suficiente de la URL")
            
            await send_personal_message(
                self.account_id,
                {
                    "type": "upload_progress",
                    "task_id": task_id,
                    "progress": 50,
                    "message": "Procesando contenido para RAG..."
                }
            )

            file_name = custom_title or extracted_title or self._extract_domain_name(url)
            
            metadata = {
                "source_url": url,
                "source_type": "web_content",
                "original_title": extracted_title,
                "domain": urlparse(url).netloc,
                "type": "document_chunk"
            }
            
            logger.info(f"📊 Procesando contenido para RAG: {file_name}")
            
            chunks_added = await process_document_for_rag(
                account_id=self.account_id,
                file_name=file_name,
                extracted_text=content,
                topic=topic,
                metadata=metadata,
                workspace_id=self.workspace_id,
            )
            
            if chunks_added <= 0:
                raise ValueError("No se pudieron procesar los chunks del contenido web")

            await send_personal_message(
                self.account_id,
                {
                    "type": "upload_completed",
                    "task_id": task_id,
                    "message": f"Contenido de '{file_name}' añadido con éxito."
                }
            )
            logger.info(f"✅ Contenido web añadido exitosamente para task_id: {task_id}")
            return f"✅ Contenido web añadido exitosamente a la colección {topic}."

        except Exception as e:
            logger.error(f"❌ Error en AddWebToRAGTool (task_id: {task_id}): {e}", exc_info=True)
            await send_personal_message(
                self.account_id,
                {
                    "type": "upload_failed",
                    "task_id": task_id,
                    "error_message": str(e)
                }
            )
            return f"❌ Error inesperado al procesar la web: {str(e)}"
    
    def _run(
        self,
        url: str,
        topic: str,
        custom_title: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Ejecuta la herramienta de forma síncrona."""
        try:
            # No es ideal para una herramienta asíncrona con tareas de fondo,
            # pero se mantiene por compatibilidad.
            # La ejecución real debería ser a través de un event loop.
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya hay un loop, creamos una tarea. No se 'await'ea aquí.
                asyncio.create_task(self._arun(url=url, topic=topic, custom_title=custom_title, **kwargs))
                return "Tarea de adición de web iniciada en segundo plano."
            else:
                # Si no hay loop, corremos uno nuevo.
                return asyncio.run(self._arun(url=url, topic=topic, custom_title=custom_title, **kwargs))
        except Exception as e:
            logger.error(f"❌ Error en ejecución síncrona de AddWebToRAGTool: {e}", exc_info=True)
            return f"❌ Error al procesar la web: {str(e)}"
