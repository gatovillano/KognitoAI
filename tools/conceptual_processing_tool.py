import logging
import asyncio
import os
import json
import uuid
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.config import settings
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from utils.knowledge_graph_service import KnowledgeGraphService
from core.memory_manager import get_full_document_content
from tools.background_task_manager import BackgroundTaskManager
from core.database import SessionLocal, DBSession

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
    background: bool = Field(
        True,
        description="Si ejecutar el procesamiento en background (recomendado para documentos grandes). Por defecto True."
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
    
    # Dependencies are stored as private attributes to avoid pydantic serialization issues
    # These are not part of the pydantic model and will be lazy-loaded when needed

    def __init__(self, graph_integration: Optional[GraphIntegration] = None, graph_db: Optional[GraphDB] = None, knowledge_graph_service: Optional[KnowledgeGraphService] = None, **data: Any):
        super().__init__(**data)
        
        # Store dependencies as private attributes to avoid pydantic serialization issues
        # These are not part of the pydantic model schema
        object.__setattr__(self, '_graph_integration', graph_integration)
        object.__setattr__(self, '_graph_db', graph_db)
        object.__setattr__(self, '_knowledge_graph_service', knowledge_graph_service)
        object.__setattr__(self, '_executor', None)  # Will be lazy-initialized
        
        logger.info("🚀 ConceptualProcessingTool inicializada con dependencias privadas para evitar problemas de serialización.")

    def _get_graph_integration(self) -> Optional[GraphIntegration]:
        if getattr(self, '_graph_integration', None) is None:
            logger.info("🔄 Lazy loading GraphIntegration...")
            from core.tools import get_shared_dependencies
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                _graph_db, _graph_integration = loop.run_until_complete(get_shared_dependencies())
                if _graph_integration:
                    object.__setattr__(self, '_graph_integration', _graph_integration)
                    if _graph_db:
                        object.__setattr__(self, '_graph_db', _graph_db)
                else:
                    raise ValueError("No se pudo inicializar GraphIntegration desde dependencias compartidas.")
            finally:
                loop.close()
        return getattr(self, '_graph_integration', None)
    
    def _get_knowledge_graph_service(self) -> Optional[KnowledgeGraphService]:
        if getattr(self, '_knowledge_graph_service', None) is None:
            logger.info("🔄 Lazy loading KnowledgeGraphService...")
            try:
                object.__setattr__(self, '_knowledge_graph_service', KnowledgeGraphService())
            except Exception as e:
                logger.error(f"❌ Error inicializando KnowledgeGraphService: {e}")
                raise
        return getattr(self, '_knowledge_graph_service', None)

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
                    file_name=file_name,
                    workspace_id=self.workspace_id
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

        dataset_name_with_account = f"{dataset_name}_{self.account_id.replace('-', '_')}"

        # Si no se proporcionan documentos ni títulos, intentar inferirlos de la colección
        if not documents and not document_titles:
            # Usar topic explícitamente proporcionado o generar error si no está disponible
            target_topic = kwargs.get("topic")
            

            
            # Usar el KnowledgeGraphService para obtener y procesar documentos
            if target_topic:
                try:
                    knowledge_graph_service = self._get_knowledge_graph_service()
                    logger.info(f"🧠 Usando KnowledgeGraphService para procesar topic: {target_topic}")
                    
                    async with DBSession(SessionLocal) as db_session:
                        result = await knowledge_graph_service.process_documents_flow(
                            db_session=db_session,
                            documents=None,  # Dejar que el servicio busque documentos
                            dataset_name=dataset_name_with_account,
                            account_id=self.account_id,
                            processing_mode="conceptual",
                            topic=target_topic,
                            workspace_id=self.workspace_id,
                            task_id=kwargs.get("task_id") # Pasar task_id si existe
                        )
                    
                    return {
                        "status": "completed",
                        "processed_documents_count": result.get("conceptual_quotes", 0),
                        "results": [result]
                    }
                except Exception as e:
                    logger.error(f"❌ Error usando KnowledgeGraphService: {e}")
                    return {"error": f"KnowledgeGraphService no está disponible: {e}", "status": "error"}
            else:
                return {"error": "Se requiere un 'topic' cuando no se proporcionan documentos", "status": "error"}


        try:
            # Preparar documentos proporcionados explícitamente
            if documents or document_titles:
                document_info_list = []
                if documents:
                     document_info_list.extend(documents)
                if document_titles:
                    for title in document_titles:
                         document_info_list.append({"file_name": title})

                prepared_documents = await self._prepare_documents(self.account_id, document_info_list)
                if not prepared_documents:
                    return {"error": "No se pudieron preparar los documentos", "status": "error"}

                # Usar KnowledgeGraphService para procesar los documentos preparados
                try:
                    knowledge_graph_service = self._get_knowledge_graph_service()
                    if not knowledge_graph_service:
                        return {"error": "KnowledgeGraphService no está disponible", "status": "error"}
                    
                    logger.info(f"🧠 Procesando {len(prepared_documents)} documentos con KnowledgeGraphService")
                    
                    async with DBSession(SessionLocal) as db_session:
                        result = await knowledge_graph_service.process_documents_flow(
                            db_session=db_session,
                            documents=prepared_documents,
                            dataset_name=dataset_name_with_account,
                            account_id=self.account_id,
                            processing_mode="conceptual",
                            task_id=kwargs.get("task_id") # Pasar task_id si existe
                        )
                    
                    return {
                        "status": "completed",
                        "processed_documents_count": len(prepared_documents),
                        "results": [result]
                    }
                except Exception as e:
                    logger.error(f"❌ Error usando KnowledgeGraphService: {e}")
                    return {"error": f"KnowledgeGraphService no está disponible: {e}", "status": "error"}
            else:
                # Esta rama ya se manejó arriba, pero por consistencia
                return {"error": "Se requiere 'documents', 'document_titles' o 'topic'", "status": "error"}

        except Exception as e:
            logger.error(f"❌ Error en ConceptualProcessingTool: {e}", exc_info=True)
            return {"error": str(e), "status": "error"}

    def _run(self, documents: Optional[List[Dict[str, Any]]] = None, 
              document_titles: Optional[List[str]] = None, dataset_name: str = "default", 
              background: bool = True, **kwargs):
        """Ejecuta el procesamiento conceptual con soporte para background processing."""
        return self._run_background(documents, document_titles, dataset_name, background, **kwargs)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de una tarea en background."""
        return BackgroundTaskManager.get_task(task_id)
    
    def list_background_tasks(self, account_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista todas las tareas en background con filtros opcionales."""
        return BackgroundTaskManager.list_tasks(account_id=account_id, status=status, limit=limit)
    
    async def _process_documents_background(self, task_id: str, documents: Optional[List[Dict[str, Any]]] = None, 
                                          document_titles: Optional[List[str]] = None, dataset_name: str = "default", 
                                          **kwargs):
        """Procesa documentos en background y actualiza el estado."""
        try:
            logger.info(f"🚀 Iniciando procesamiento conceptual en background para tarea: {task_id}")
            
            # Preparar documentos
            document_info_list = []
            if documents:
                document_info_list.extend(documents)
            if document_titles:
                for title in document_titles:
                    document_info_list.append({"file_name": title})
            
            prepared_documents = []
            if document_info_list:
                prepared_documents = await self._prepare_documents(self.account_id, document_info_list)
            
            dataset_name_with_account = f"{dataset_name}_{self.account_id.replace('-', '_')}"
            
            # Si no hay documentos explícitos, usar topic
            if not prepared_documents and kwargs.get("topic"):
                target_topic = kwargs.get("topic")
                try:
                    knowledge_graph_service = self._get_knowledge_graph_service()
                    if not knowledge_graph_service:
                        raise ValueError("KnowledgeGraphService no está disponible")
                    
                    logger.info(f"🧠 Procesando topic: {target_topic} en background")
                    async with DBSession(SessionLocal) as db_session:
                        result = await knowledge_graph_service.process_documents_flow(
                            db_session=db_session,
                            documents=None,
                            dataset_name=dataset_name_with_account,
                            account_id=self.account_id,
                            processing_mode="conceptual",
                            topic=target_topic,
                            workspace_id=self.workspace_id,
                            task_id=task_id # Usar el task_id de la tarea en background
                        )
                except Exception as e:
                    raise ValueError(f"KnowledgeGraphService no está disponible: {e}")
            else:
                # Procesar documentos preparados
                if not prepared_documents:
                    raise ValueError("No se pudieron preparar los documentos")
                
                try:
                    knowledge_graph_service = self._get_knowledge_graph_service()
                    if not knowledge_graph_service:
                        raise ValueError("KnowledgeGraphService no está disponible")
                    
                    logger.info(f"🧠 Procesando {len(prepared_documents)} documentos en background")
                    async with DBSession(SessionLocal) as db_session:
                        result = await knowledge_graph_service.process_documents_flow(
                            db_session=db_session,
                            documents=prepared_documents,
                            dataset_name=dataset_name_with_account,
                            account_id=self.account_id,
                            processing_mode="conceptual",
                            task_id=task_id # Usar el task_id de la tarea en background
                        )
                except Exception as e:
                    raise ValueError(f"KnowledgeGraphService no está disponible: {e}")
            
            # Actualizar estado como completado
            BackgroundTaskManager.update_task(task_id, status="completed", result=result, message="Procesamiento conceptual completado")
            logger.info(f"✅ Procesamiento conceptual completado para tarea: {task_id}")
            
        except Exception as e:
            error_msg = f"Error en procesamiento conceptual: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            BackgroundTaskManager.update_task(task_id, status="failed", error=error_msg, message=error_msg)
    
    def _run_background(self, documents: Optional[List[Dict[str, Any]]] = None, 
                       document_titles: Optional[List[str]] = None, dataset_name: str = "default", 
                       background: bool = True, **kwargs):
        """Ejecuta el procesamiento en background si background=True."""
        if not background:
            # Procesamiento síncrono tradicional
            return asyncio.run(self._arun(documents, document_titles, dataset_name, **kwargs))
        
        # Crear ID de tarea único
        task_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Crear future para el procesamiento
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Crear la tarea asíncrona
            future = loop.create_task(
                self._process_documents_background(
                    task_id, documents, document_titles, dataset_name, **kwargs
                )
            )
            
            # Registrar la tarea en BackgroundTaskManager
            BackgroundTaskManager.create_task(
                task_id=task_id,
                account_id=self.account_id,
                workspace_id=self.workspace_id,
                task_type="conceptual_processing"
            )
            
            # Actualizar status a running
            BackgroundTaskManager.update_task(task_id, status="running", message="Procesamiento iniciado")
            
            # Limpiar tareas antiguas
            BackgroundTaskManager.cleanup_old_tasks()
            
            logger.info(f"📋 Tarea de procesamiento conceptual iniciada en background: {task_id}")
            
            return {
                "status": "started",
                "task_id": task_id,
                "background": True,
                "message": "Procesamiento conceptual iniciado en background",
                "start_time": start_time.isoformat(),
                "account_id": self.account_id
            }
            
        finally:
            loop.close()

    def __del__(self):
        # Cerrar GraphDB si existe
        graph_db = getattr(self, '_graph_db', None)
        if graph_db:
            try:
                graph_db.close()
            except:
                pass
        
        # Cerrar también la conexión del KnowledgeGraphService si existe
        knowledge_graph_service = getattr(self, '_knowledge_graph_service', None)
        if knowledge_graph_service and hasattr(knowledge_graph_service, 'graph_db'):
            try:
                knowledge_graph_service.graph_db.close()
            except:
                pass
        
        # Cerrar el executor
        executor = getattr(self, '_executor', None)
        if executor:
            try:
                executor.shutdown(wait=False)
            except:
                pass
