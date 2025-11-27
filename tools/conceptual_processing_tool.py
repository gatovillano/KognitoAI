# tools/conceptual_processing_tool.py
"""
Herramienta para procesar documentos conceptualmente usando GraphIntegration.
Reemplaza la herramienta anterior basada en Cognee.
"""

import logging
import asyncio
import os
import json
import uuid
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.config import settings
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from core.memory_manager import get_full_document_content

logger = logging.getLogger(__name__)

class ConceptualProcessingSchema(BaseModel):
    """Schema para la herramienta de procesamiento conceptual."""
    documents: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Lista de documentos a procesar. Cada documento debe tener 'file_name' y opcionalmente 'content'."
    )
    document_titles: Optional[List[str]] = Field(
        None,
        description="Lista de nombres de archivos de documentos a procesar (sin contenido explícito)."
    )
    dataset_name: str = Field(
        "default",
        description="Nombre del dataset para el procesamiento (opcional, por defecto 'default')"
    )

class ConceptualProcessingTool(BaseTool):
    name: str = "conceptual_processing"
    description: str = """
    Procesa documentos de forma conceptual, extrayendo citas importantes,
    relaciones temáticas y perfiles de ideas. Crea un grafo de conocimiento
    detallado para entender mejor el contenido semántico y las conexiones
    entre ideas de los documentos.
    """
    args_schema: type[BaseModel] = ConceptualProcessingSchema
    account_id: str = Field(..., description="El ID de cuenta del usuario.")
    workspace_id: Optional[str] = None
    telegram_id: Optional[str] = None
    thread_id: Optional[str] = None
    _graph_integration: Optional[GraphIntegration] = None
    _graph_db: Optional[GraphDB] = None

    def __init__(self, graph_integration: Optional[GraphIntegration] = None, graph_db: Optional[GraphDB] = None, **data: Any):
        super().__init__(**data)
        self._graph_integration = graph_integration
        self._graph_db = graph_db
        
        if self._graph_integration is None or self._graph_db is None:
            logger.warning("⚠️ GraphIntegration o GraphDB no inyectados. Inicializando internamente.")
            if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
                logger.error("❌ Configuración de Neo4j incompleta.")
                raise ValueError("Configuración de Neo4j incompleta.")
            
            self._graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            self._graph_db.connect()
            self._graph_integration = GraphIntegration(self._graph_db)

    def _get_graph_integration(self) -> GraphIntegration:
        if self._graph_integration is None:
            raise ValueError("GraphIntegration no está inicializada.")
        return self._graph_integration

    async def _prepare_documents(self, account_id: str, document_info_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prepared_documents = []
        for doc_info in document_info_list:
            try:
                file_name = doc_info.get("file_name") or doc_info.get("title")
                if not file_name or not isinstance(file_name, str):
                     continue 

                content = doc_info.get("content")
                if content and isinstance(content, str) and len(content.strip()) > 0:
                    prepared_documents.append({
                        "file_name": file_name,
                        "content": content.strip(),
                        "metadata": {"account_id": account_id, "file_name": file_name}
                    })
                    continue

                full_content = await get_full_document_content(
                    account_id=account_id,
                    file_name=file_name
                )

                if full_content and isinstance(full_content, str) and len(full_content.strip()) > 0:
                    prepared_documents.append({
                        "file_name": file_name,
                        "content": full_content.strip(),
                        "metadata": {"account_id": account_id, "file_name": file_name}
                    })
            except Exception as e:
                logger.error(f"❌ Error preparando documento {file_name}: {e}")

        return prepared_documents

    async def _arun(self, documents: Optional[List[Dict[str, Any]]] = None, document_titles: Optional[List[str]] = None, dataset_name: str = "default", **kwargs) -> Dict[str, Any]:
        if not self.account_id:
            return {"error": "Se requiere account_id", "status": "error"}

        if not documents and not document_titles:
            return {"error": "Se requieren documentos", "status": "error"}

        document_info_list = []
        if documents:
             document_info_list.extend(documents)
        if document_titles:
            for title in document_titles:
                 document_info_list.append({"file_name": title})

        try:
            prepared_documents = await self._prepare_documents(self.account_id, document_info_list)
            if not prepared_documents:
                return {"error": "No se pudieron preparar los documentos", "status": "error"}

            graph_integration = self._get_graph_integration()
            dataset_name_with_account = f"{dataset_name}_{self.account_id.replace('-', '_')}"

            # Procesar documentos uno por uno para evitar rate limiting
            all_results = []
            total_docs = len(prepared_documents)
            for i, doc in enumerate(prepared_documents):
                logger.info(f"Procesando documento {i+1}/{total_docs}: {doc.get('file_name')}")
                
                # Usar graph_integration.process_documents que ya maneja la lógica conceptual
                result = await graph_integration.process_documents(
                    documents=[doc],
                    dataset_name=dataset_name_with_account,
                    account_id=self.account_id
                )
                all_results.append(result)

                if i < total_docs - 1:
                    await asyncio.sleep(2) # Pequeña pausa

            return {
                "status": "completed",
                "processed_documents_count": len(all_results),
                "results": all_results
            }

        except Exception as e:
            logger.error(f"❌ Error en ConceptualProcessingTool: {e}", exc_info=True)
            return {"error": str(e), "status": "error"}

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    def __del__(self):
        if self._graph_db:
            try:
                self._graph_db.close()
            except:
                pass
