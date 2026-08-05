"""
AnthropologicalGraphProcessingTool

Wrapper de skill (BaseTool) que expone AnthropologicalGraphProcessor
como herramienta ejecutable a través del dispatcher /api/tools/run.
Sigue el mismo patrón que ConceptualProcessingTool: soporta ejecución
en background con task_id y reporte de progreso vía BackgroundTaskManager.
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from utils.background_task_manager import BackgroundTaskManager
from core.memory_manager import get_full_document_content

logger = logging.getLogger(__name__)


class AnthropologicalGraphProcessingSchema(BaseModel):
    """Schema para la herramienta de procesamiento antropológico."""
    documents: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Lista de documentos a procesar. Cada documento debe tener 'file_name'/'title' y opcionalmente 'content'."
    )
    document_titles: Optional[List[str]] = Field(
        None,
        description="Lista de nombres de archivos de documentos a procesar (sin contenido explícito)."
    )
    dataset_name: str = Field(
        "default",
        description="Nombre del dataset para el procesamiento (opcional, por defecto 'default')."
    )
    theoretical_framework: str = Field(
        ...,
        description="Texto o extractos del marco teórico que guiarán la codificación etnográfica. Requerido."
    )
    research_question: Optional[str] = Field(
        None,
        description="Pregunta de investigación cualitativa (opcional)."
    )
    hypothesis: Optional[str] = Field(
        None,
        description="Hipótesis de trabajo (opcional)."
    )
    topic: Optional[str] = Field(
        None,
        description="Topic/colección para filtrar documentos en la base vectorial (alternativa a documents/document_titles)."
    )
    background: bool = Field(
        True,
        description="Si ejecutar el procesamiento en background (recomendado para corpus grandes). Por defecto True."
    )


class AnthropologicalGraphProcessingTool(BaseTool):
    name: str = "anthropological_graph_processing"
    description: str = """
    Procesa documentos con codificación cualitativa etnográfica y antropológica exhaustiva.
    Extrae citas, las agrupa bajo códigos atómicos (relación 1:N donde un Código agrupa múltiples Citas)
    y posteriormente estructura los códigos en categorías analíticas superiores,
    todo guiado por un marco teórico, pregunta de investigación e hipótesis opcionales.
    """
    args_schema: type[BaseModel] = AnthropologicalGraphProcessingSchema
    account_id: Optional[str] = None
    workspace_id: Optional[str] = None
    telegram_id: Optional[str] = None
    thread_id: Optional[str] = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        logger.info(
            f"📜 AnthropologicalGraphProcessingTool inicializada "
            f"(account={self.account_id}, workspace={self.workspace_id})"
        )

    async def _prepare_documents(
        self,
        account_id: str,
        document_info_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Resuelve el contenido completo de cada documento a partir de titles o payloads parciales."""
        prepared_documents: List[Dict[str, Any]] = []
        for doc_info in document_info_list:
            title = "Unknown"
            try:
                title = (
                    doc_info.get("file_name")
                    or doc_info.get("title")
                    or "Unknown"
                )
                if not title or not isinstance(title, str) or title == "Unknown":
                    continue

                content = doc_info.get("content")
                if content and isinstance(content, str) and content.strip():
                    prepared_documents.append({
                        "title": title,
                        "content": content.strip(),
                    })
                    continue

                full_content = await get_full_document_content(
                    account_id=account_id,
                    file_name=title,
                    workspace_id=self.workspace_id,
                )
                if full_content and isinstance(full_content, str) and full_content.strip():
                    prepared_documents.append({
                        "title": title,
                        "content": full_content.strip(),
                    })
            except Exception as e:
                logger.error(f"❌ Error preparando documento '{title}': {e}")
        return prepared_documents

    async def _resolve_documents_from_topic(
        self,
        account_id: str,
        topic: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Carga documentos de la base vectorial filtrando por account_id + topic."""
        if not topic:
            return []

        from sqlalchemy import text
        from core.dependencies import get_db_session
        from sqlalchemy.ext.asyncio import AsyncSession

        documents: List[Dict[str, Any]] = []
        async for session in get_db_session():
            query = text("""
                SELECT DISTINCT cmetadata->>'file_name' AS file_name
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND cmetadata->>'topic' = :topic
            """)
            result = await session.execute(
                query, {"account_id": account_id, "topic": topic}
            )
            rows = result.fetchall()

        for row in rows:
            file_name = row[0]
            if not file_name:
                continue
            content = await get_full_document_content(
                account_id=account_id,
                file_name=file_name,
                workspace_id=self.workspace_id,
            )
            if content and content.strip():
                documents.append({"title": file_name, "content": content.strip()})
        return documents

    async def _arun(
        self,
        documents: Optional[List[Dict[str, Any]]] = None,
        document_titles: Optional[List[str]] = None,
        dataset_name: str = "default",
        theoretical_framework: str = "",
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
        topic: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if not self.account_id:
            return {"error": "Se requiere account_id", "status": "error"}
        if not theoretical_framework or not theoretical_framework.strip():
            return {
                "error": "Se requiere 'theoretical_framework' para el procesamiento antropológico.",
                "status": "error",
            }

        background = kwargs.get("background", True)
        task_id = kwargs.get("task_id") or str(uuid.uuid4())

        if background:
            logger.info(
                f"🚀 Iniciando procesamiento antropológico en background: {task_id}"
            )
            BackgroundTaskManager.create_task(
                task_id=task_id,
                account_id=self.account_id,
                workspace_id=self.workspace_id,
                task_type="anthropological_graph_processing",
            )
            BackgroundTaskManager.update_task(
                task_id, status="running", message="Procesamiento antropológico iniciado"
            )

            clean_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k not in {
                    "task_id",
                    "documents",
                    "document_titles",
                    "dataset_name",
                    "theoretical_framework",
                    "research_question",
                    "hypothesis",
                    "topic",
                    "background",
                }
            }

            asyncio.create_task(
                self._process_documents_background(
                    task_id,
                    documents,
                    document_titles,
                    dataset_name,
                    theoretical_framework,
                    research_question,
                    hypothesis,
                    topic,
                    **clean_kwargs,
                )
            )

            return {
                "status": "started",
                "task_id": task_id,
                "background": True,
                "message": "Procesamiento antropológico iniciado en background",
                "account_id": self.account_id,
            }

        # Ejecución síncrona (bloqueante)
        try:
            prepared_documents: List[Dict[str, Any]] = []
            if documents or document_titles:
                document_info_list: List[Dict[str, Any]] = []
                if documents:
                    document_info_list.extend(documents)
                if document_titles:
                    for t in document_titles:
                        document_info_list.append({"file_name": t})
                prepared_documents = await self._prepare_documents(
                    self.account_id, document_info_list
                )
            if not prepared_documents and topic:
                prepared_documents = await self._resolve_documents_from_topic(
                    self.account_id, topic
                )

            if not prepared_documents:
                return {
                    "error": "Se requiere 'documents', 'document_titles' o 'topic' con documentos disponibles.",
                    "status": "error",
                }

            from knowledge_graph.anthropological_graph_processor import (
                AnthropologicalGraphProcessor,
            )

            processor = AnthropologicalGraphProcessor()
            result = await processor.process_documents_anthropologically(
                documents=prepared_documents,
                theoretical_framework=theoretical_framework,
                research_question=research_question,
                hypothesis=hypothesis,
                dataset_name=dataset_name,
                account_id=self.account_id,
            )
            return {
                "status": "completed",
                "task_id": task_id,
                "data": result,
            }
        except Exception as e:
            logger.error(f"❌ Error en AnthropologicalGraphProcessingTool._arun: {e}", exc_info=True)
            return {"error": str(e), "status": "error", "task_id": task_id}

    def _run(
        self,
        documents: Optional[List[Dict[str, Any]]] = None,
        document_titles: Optional[List[str]] = None,
        dataset_name: str = "default",
        theoretical_framework: str = "",
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
        topic: Optional[str] = None,
        background: bool = True,
        **kwargs,
    ):
        """Punto de entrada síncrono. Si background=True, programa la tarea y retorna task_id."""
        if background:
            task_id = kwargs.get("task_id") or str(uuid.uuid4())
            try:
                loop = asyncio.get_running_loop()
                clean_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in {
                        "task_id",
                        "documents",
                        "document_titles",
                        "dataset_name",
                        "theoretical_framework",
                        "research_question",
                        "hypothesis",
                        "topic",
                        "background",
                    }
                }
                loop.create_task(
                    self._process_documents_background(
                        task_id,
                        documents,
                        document_titles,
                        dataset_name,
                        theoretical_framework,
                        research_question,
                        hypothesis,
                        topic,
                        **clean_kwargs,
                    )
                )
                BackgroundTaskManager.create_task(
                    task_id=task_id,
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                    task_type="anthropological_graph_processing",
                )
                BackgroundTaskManager.update_task(
                    task_id, status="running", message="Procesamiento antropológico iniciado"
                )
                return {"status": "started", "task_id": task_id, "background": True}
            except RuntimeError:
                # No hay loop corriendo (script CLI)
                return asyncio.run(
                    self._arun(
                        documents,
                        document_titles,
                        dataset_name,
                        theoretical_framework,
                        research_question,
                        hypothesis,
                        topic,
                        background=False,
                        **kwargs,
                    )
                )
        return asyncio.run(
            self._arun(
                documents,
                document_titles,
                dataset_name,
                theoretical_framework,
                research_question,
                hypothesis,
                topic,
                background=False,
                **kwargs,
            )
        )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return BackgroundTaskManager.get_task(task_id)

    async def _process_documents_background(
        self,
        task_id: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        document_titles: Optional[List[str]] = None,
        dataset_name: str = "default",
        theoretical_framework: str = "",
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
        topic: Optional[str] = None,
        **kwargs,
    ):
        """Procesa documentos en background y reporta progreso al BackgroundTaskManager."""
        try:
            logger.info(
                f"📜 Background task {task_id}: dataset={dataset_name}, "
                f"account={self.account_id}, workspace={self.workspace_id}, topic={topic}"
            )
            BackgroundTaskManager.update_task(
                task_id,
                status="running",
                message="Preparando documentos para codificación etnográfica...",
            )

            prepared_documents: List[Dict[str, Any]] = []
            if documents or document_titles:
                document_info_list: List[Dict[str, Any]] = []
                if documents:
                    document_info_list.extend(documents)
                if document_titles:
                    for t in document_titles:
                        document_info_list.append({"file_name": t})
                prepared_documents = await self._prepare_documents(
                    self.account_id, document_info_list
                )
            if not prepared_documents and topic:
                prepared_documents = await self._resolve_documents_from_topic(
                    self.account_id, topic
                )

            if not prepared_documents:
                raise ValueError(
                    "No se encontraron documentos para procesar "
                    "(documents, document_titles o topic)."
                )

            BackgroundTaskManager.update_task(
                task_id,
                status="running",
                message=f"Codificando {len(prepared_documents)} documento(s)...",
            )

            from knowledge_graph.anthropological_graph_processor import (
                AnthropologicalGraphProcessor,
            )

            processor = AnthropologicalGraphProcessor()
            result = await processor.process_documents_anthropologically(
                documents=prepared_documents,
                theoretical_framework=theoretical_framework,
                research_question=research_question,
                hypothesis=hypothesis,
                dataset_name=dataset_name,
                account_id=self.account_id,
            )

            quotes_count = len(result.get("quotes", []))
            codes_count = len(result.get("codes", []))
            categories_count = len(result.get("categories", []))
            BackgroundTaskManager.update_task(
                task_id,
                status="completed",
                result=result,
                message=(
                    f"Procesamiento antropológico completado: "
                    f"{quotes_count} citas, {codes_count} códigos, "
                    f"{categories_count} categorías."
                ),
            )
            logger.info(
                f"✅ Background task {task_id} completada: "
                f"{quotes_count} citas, {codes_count} códigos, {categories_count} categorías"
            )
        except Exception as e:
            error_msg = f"Error en procesamiento antropológico: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            BackgroundTaskManager.update_task(
                task_id, status="failed", error=error_msg, message=error_msg
            )
