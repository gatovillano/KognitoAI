import logging
import asyncio
import os
from typing import List, Dict, Any, Optional
import uuid

# Importaciones necesarias para las tareas
# Importaciones necesarias para las tareas
from core.database import SessionLocal, UploadTask, DBSession, AnalysisTask, Document, DocumentFolder
from sqlalchemy import update, select, text
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, process_multiple_documents_for_rag, list_user_documents, update_document_metadata
from core.websocket_manager import send_personal_message # Importar send_personal_message
from skills.knowledge_and_memory_skill.scripts.knowledge_graph_tool import KnowledgeGraphTool
from core.config import settings
from core.onlyoffice_storage import build_onlyoffice_relative_path, ensure_onlyoffice_account_dir
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def get_or_create_onlyoffice_folder(
    db_session,
    account_id: str,
    topic: str,
    workspace_id: Optional[str] = None
) -> uuid.UUID:
    acc_id = uuid.UUID(account_id)
    ws_id = uuid.UUID(workspace_id) if workspace_id else None
    
    stmt = select(DocumentFolder).where(
        DocumentFolder.account_id == acc_id,
        DocumentFolder.name == topic,
        DocumentFolder.parent_id == None
    )
    if ws_id:
        stmt = stmt.where(DocumentFolder.workspace_id == ws_id)
    else:
        stmt = stmt.where(DocumentFolder.workspace_id == None)
        
    result = await db_session.execute(stmt)
    folder = result.scalars().first()
    
    if not folder:
        folder = DocumentFolder(
            account_id=acc_id,
            workspace_id=ws_id,
            name=topic,
            parent_id=None
        )
        db_session.add(folder)
        await db_session.flush()
        
    return folder.id


async def process_upload_task(task_id: str, account_id: str, file_data_list: List[Dict], topic: str, workspace_id: Optional[str] = None):
    """
    Procesa la subida de documentos en segundo plano de forma asíncrona y simultánea.
    """
    logger.info(f"Iniciando procesamiento de subida para tarea {task_id} con {len(file_data_list)} archivos...")
    
    async with DBSession(SessionLocal) as db_session:
        try:
            # 1. Marcar la tarea como 'processing'
            stmt_processing = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                status="processing",
                progress=5
            )
            await db_session.execute(stmt_processing)
            await db_session.commit()
            logger.info(f"Marcada tarea {task_id} como 'processing'.")

            total_files = len(file_data_list)
            documents_to_process = []

            # Extraer texto y metadatos para todos los archivos en paralelo
            extraction_tasks = []
            for file_data in file_data_list:
                file_name_str = file_data.get('filename', 'unknown_file')
                extraction_tasks.append(extract_text_and_metadata_from_document(
                    file_name_str,
                    file_data['content']
                ))
            
            extracted_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

            # Directorio base para documentos físicos.
            # Debe ser idéntico al que usa api/onlyoffice.py (settings.onlyoffice_docs_root)
            # para que el servidor de OnlyOffice pueda leer los archivos subidos desde RAG.
            DOCUMENTS_ROOT = settings.onlyoffice_docs_root
            os.makedirs(DOCUMENTS_ROOT, exist_ok=True)

            # Obtener o crear la carpeta OnlyOffice para la colección
            folder_id = None
            try:
                folder_id = await get_or_create_onlyoffice_folder(
                    db_session,
                    account_id,
                    topic,
                    workspace_id
                )
            except Exception as folder_err:
                logger.error(f"Error al obtener/crear carpeta OnlyOffice para la colección '{topic}': {folder_err}")

            for i, result in enumerate(extracted_results):
                file_name_str = file_data_list[i].get('filename', 'unknown_file')
                file_content = file_data_list[i].get('content')

                if isinstance(result, Exception):
                    logger.error(f"Error al extraer texto del archivo '{file_name_str}': {result}", exc_info=True)
                    await send_personal_message(
                        account_id,
                        {
                            "type": "upload_progress",
                            "task_id": task_id,
                            "progress": 5 + int(((i + 1) / total_files) * 90),
                            "message": f"Error al procesar {file_name_str}: {str(result)}"
                        }
                    )
                    continue
                
                extracted_text, metadata = result
                
                # --- GUARDADO FÍSICO DEL ARCHIVO (OnlyOffice) ---
                # Usamos settings.onlyoffice_docs_root para que el archivo quede en la
                # misma raíz que usa api/onlyoffice.py al servir/descargar documentos.
                extension = file_name_str.split('.')[-1].lower() if '.' in file_name_str else ""
                unique_filename = f"{uuid.uuid4()}.{extension}"
                user_dir = ensure_onlyoffice_account_dir(account_id)
                
                clean_topic = topic.replace("/", "_").replace("\\", "_")
                collection_dir = user_dir / clean_topic
                collection_dir.mkdir(parents=True, exist_ok=True)
                
                physical_file_path = collection_dir / unique_filename
                try:
                    with open(physical_file_path, "wb") as f:
                        f.write(file_content)
                    logger.info(f"Archivo físico guardado en: {physical_file_path}")
                except Exception as save_err:
                    logger.error(f"Error al guardar archivo físico {file_name_str}: {save_err}")
                
                # Registrar en la tabla Document para que sea visible en OnlyOffice
                new_doc = Document(
                    account_id=uuid.UUID(account_id),
                    workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                    filename=file_name_str,
                    extension=extension,
                    file_path=build_onlyoffice_relative_path(account_id, f"{clean_topic}/{unique_filename}"),  # Ruta relativa a DOCUMENTS_ROOT
                    folder_id=folder_id
                )
                db_session.add(new_doc)
                await db_session.flush()  # Para obtener el ID antes del commit final
                
                document_id = str(new_doc.id)
                logger.info(f"Documento '{file_name_str}' registrado en OnlyOffice con ID {document_id}")
                # ------------------------------------------

                if not extracted_text:
                    logger.warning(f"No se pudo extraer texto del archivo '{file_name_str}'. Solo guardado en OnlyOffice.")
                    await send_personal_message(
                        account_id,
                        {
                            "type": "upload_progress",
                            "task_id": task_id,
                            "progress": 5 + int(((i + 1) / total_files) * 90),
                            "message": f"Archivo {file_name_str} guardado en OnlyOffice (sin texto para RAG)."
                        }
                    )
                    continue

                documents_to_process.append({
                    "file_name": file_name_str,
                    "extracted_text": extracted_text,
                    "topic": topic,
                    "account_id": account_id,
                    "metadata": {
                        "original_filename": file_name_str, 
                        "task_id": task_id,
                        "document_id": document_id
                    },
                    "workspace_id": workspace_id
                })
            
            # Commit de todos los documentos físicos registrados en OnlyOffice
            await db_session.commit()

            if not documents_to_process:
                # Los archivos se guardaron físicamente pero no tienen texto para RAG (ej. binarios)
                logger.warning("No se encontró texto extraíble en ningún archivo. Los archivos quedan disponibles en OnlyOffice.")
                processed_files_count = 0
            else:
                # Procesar todos los documentos extraídos simultáneamente para RAG
                processed_chunks_counts = await process_multiple_documents_for_rag(documents_to_process)
                processed_files_count = sum(1 for count in processed_chunks_counts if count > 0)

                # Extraer títulos automáticamente para los archivos procesados
                try:
                    title_tasks = []
                    for idx, doc_data in enumerate(documents_to_process):
                        if idx < len(processed_chunks_counts) and processed_chunks_counts[idx] > 0:
                            file_name_str = doc_data.get("file_name")
                            if file_name_str:
                                logger.info(f"Programando extracción automática de título para '{file_name_str}'...")
                                title_tasks.append(
                                    extract_titles_and_update_metadata(
                                        account_id=account_id,
                                        topic=topic,
                                        workspace_id=workspace_id,
                                        file_name=file_name_str
                                    )
                                )
                    if title_tasks:
                        logger.info(f"Ejecutando extracción automática de títulos para {len(title_tasks)} archivos en paralelo...")
                        await asyncio.gather(*title_tasks, return_exceptions=True)
                        logger.info("Finalizada extracción automática de títulos.")
                except Exception as title_err:
                    logger.error(f"Error al extraer títulos automáticamente en process_upload_task: {title_err}", exc_info=True)

            result_message = f"{processed_files_count}/{total_files} archivo(s) procesado(s) y añadido(s) a la colección '{topic}'."
            result_payload = {
                "processed_files": processed_files_count,
                "total_files": total_files,
                "topic": topic,
                "message": result_message
            }

            stmt_completed = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                status="completed",
                progress=100,
                result_payload=result_payload
            )
            await db_session.execute(stmt_completed)
            await db_session.commit()

            await send_personal_message(
                account_id,
                {
                    "type": "upload_completed",
                    "task_id": task_id,
                    "message": result_message
                }
            )

            logger.info(f"Tarea de subida {task_id} completada exitosamente.")

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error en la tarea de subida {task_id}: {error_message}", exc_info=True)
            stmt_failed = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                status="failed",
                error_message=error_message
            )
            await db_session.execute(stmt_failed)
            await db_session.commit()

            await send_personal_message(
                account_id,
                {
                    "type": "upload_failed",
                    "task_id": task_id,
                    "error_message": error_message
                }
            )

async def extract_titles_and_update_metadata(account_id: str, topic: Optional[str] = None, workspace_id: Optional[str] = None, team_id: Optional[str] = None, file_name: Optional[str] = None):
    """
    Extrae títulos de documentos y actualiza sus metadatos de forma asíncrona.
    """
    logger.info(f"Iniciando extracción de títulos para cuenta {account_id}, tema: {topic}, workspace: {workspace_id}")
    updated_count = 0
    async with DBSession(SessionLocal) as db:
        try:
            clauses = [
                "account_id = CAST(:account_id AS UUID)",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"account_id": account_id}

            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic
            if workspace_id:
                clauses.append("workspace_id = CAST(:workspace_id AS UUID)")
                params["workspace_id"] = workspace_id
            if team_id:
                clauses.append("team_id = CAST(:team_id AS UUID)")
                params["team_id"] = team_id
            if file_name:
                clauses.append("cmetadata->>'file_name' = :file_name")
                params["file_name"] = file_name

            select_sql = text("SELECT * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
            result = await db.execute(select_sql, params)
            chunks = result.mappings().all()

            if not chunks:
                logger.info(f"No se encontraron fragmentos de documentos para procesar para la cuenta {account_id}.")
                return 0

            logger.info(f"Se encontraron {len(chunks)} fragmentos para procesar.")

            documents = {}
            for chunk in chunks:
                file_name_chunk = chunk['cmetadata'].get('file_name')
                if file_name_chunk:
                    if file_name_chunk not in documents:
                        documents[file_name_chunk] = []
                    documents[file_name_chunk].append(chunk)
            
            logger.info(f"Documentos identificados: {list(documents.keys())}")

            for file_name_doc, doc_chunks in documents.items():
                logger.info(f"Procesando documento: {file_name_doc} con {len(doc_chunks)} fragmentos.")
                # Ordenar chunks por índice para reconstruir el inicio del documento
                sorted_chunks = sorted(doc_chunks, key=lambda x: x['cmetadata'].get('chunk_index', 0))
                full_content = "".join([c['document'] for c in sorted_chunks])
                
                new_title = None
                if full_content:
                    # Usar el LLM para una extracción inteligente como método principal
                    logger.info(f"Iniciando extracción inteligente con LLM para '{file_name_doc}'...")
                    try:
                        from core.llm_manager import get_llm_for_user, _invoke_llm_cached
                        llm = await get_llm_for_user(account_id, purpose="fast")
                        if llm:
                            # Tomar una muestra significativa del inicio del documento (aprox 3000 caracteres para más contexto)
                            sample_text = full_content[:3000]
                            prompt = f"""Analiza el siguiente fragmento de un documento y determina su título real, formal y representativo.
Instrucciones:
1. El título debe ser corto (máximo 10 palabras).
2. Debe ser el título oficial que aparece en el documento, no un resumen.
3. Si el documento no tiene un título claro, usa el nombre del archivo como base para crear uno limpio: {file_name_doc}
4. Solo devuelve el título, sin explicaciones, sin comillas y sin prefijos como 'Título:'.

Fragmento del documento:
---
{sample_text}
---
"""
                            response = await _invoke_llm_cached(llm, prompt)
                            if response and hasattr(response, 'content'):
                                extracted_title = response.content.strip().strip('"').strip("'").strip()
                                if extracted_title and len(extracted_title) > 2:
                                    new_title = extracted_title
                                    logger.info(f"✅ Título extraído por LLM para '{file_name_doc}': {new_title}")
                    except Exception as llm_err:
                        logger.error(f"Error al usar LLM para extraer título de '{file_name_doc}': {llm_err}")
                
                # Si el LLM falla por completo, usamos el nombre del archivo como último recurso
                if not new_title:
                    new_title = file_name_doc
                    logger.info(f"⚠️ Usando nombre de archivo como título para '{file_name_doc}' (LLM falló).")

                current_title = doc_chunks[0]['cmetadata'].get('title')
                logger.info(f"Título actual: '{current_title}', Título nuevo propuesto: '{new_title}'")

                if new_title and new_title != current_title:
                    if file_name_doc: # Asegurarse de que file_name no sea None
                        logger.info(f"Intentando actualizar metadatos para '{file_name_doc}' con título '{new_title}'")
                        success = await update_document_metadata(account_id, file_name_doc, new_title=new_title, new_topic=None, workspace_id=workspace_id)
                        if success:
                            updated_count += 1
                            logger.info(f"✅ Documento '{file_name_doc}' actualizado exitosamente.")
                            
                            # Notificar al frontend vía WebSocket para actualización en tiempo real
                            try:
                                target_account_id = str(account_id)
                                logger.info(f"Enviando notificación WebSocket a la cuenta {target_account_id} para el archivo '{file_name_doc}'")
                                await send_personal_message(
                                    target_account_id,
                                    {
                                        "type": "title_updated",
                                        "file_name": file_name_doc,
                                        "new_title": new_title,
                                        "workspace_id": workspace_id
                                    }
                                )
                                logger.info(f"✅ Notificación WebSocket enviada exitosamente.")
                            except Exception as ws_err:
                                logger.error(f"❌ Error al enviar notificación WebSocket: {ws_err}", exc_info=True)
                        else:
                            logger.warning(f"❌ Falló la actualización de metadatos para '{file_name_doc}'.")
                    else:
                        logger.warning(f"No se pudo actualizar el título para un documento sin nombre de archivo.")
                else:
                    logger.info(f"No se requiere actualización para '{file_name_doc}' (título igual o no detectado).")
        except Exception as e:
            logger.error(f"Error en la tarea de extracción de títulos {account_id}: {e}", exc_info=True)
            # Manejo de errores, notificaciones, etc.

    logger.info(f"Tarea de extracción de títulos completada. Documentos actualizados: {updated_count}")
    return updated_count

async def process_knowledge_graph(account_id: str, topic: Optional[str] = None):
    """
    Procesa documentos y crea grafos de conocimiento con Cognee de forma asíncrona.
    """
    logger.info(f"Iniciando procesamiento de grafo para cuenta {account_id}, tema: {topic}")
    try:
        # Obtener documentos del usuario
        if topic:
            documents = await list_user_documents(account_id, topic=topic)
        else:
            documents = await list_user_documents(account_id)

        if not documents:
            logger.info("No se encontraron documentos para procesar en el grafo.")
            return {"message": "No se encontraron documentos para procesar."}

        # Preparar documentos para KnowledgeGraphTool
        kg_documents = []
        for doc in documents:
            kg_documents.append({
                "content": doc.get("content", ""),
                "file_name": doc.get("file_name", "Documento sin título"),
                "metadata": {
                    "file_name": doc.get("file_name"),
                    "topic": doc.get("topic"),
                    "account_id": account_id
                }
            })

        tool = KnowledgeGraphTool(account_id=account_id)
        tool_input = {
            "action": "process_documents",
            "documents": kg_documents,
            "dataset_name": f"kognito_{account_id}"
        }
        result = await tool._arun(
            action=tool_input["action"],
            documents=tool_input.get("documents"),
            dataset_name=tool_input.get("dataset_name", f"kognito_{account_id}")
        )
        logger.info(f"Procesamiento de grafo completado para {account_id}: {result}")
        return {"message": f"Procesamiento de grafo de conocimiento completado para {len(kg_documents)} documentos.", "result": result}

    except Exception as e:
        logger.error(f"Error en procesamiento de grafo para {account_id}: {e}", exc_info=True)
        return {"message": f"Error al procesar el grafo de conocimiento: {str(e)}", "error": str(e)}

async def start_knowledge_graph_analysis(account_id: str, topic: str, workspace_id: Optional[str] = None) -> str:
    """
    Inicia una tarea de análisis de grafo de conocimiento en segundo plano.
    """
    task_id = uuid.uuid4()
    async with DBSession(SessionLocal) as db_session:
        new_task = AnalysisTask(
            id=task_id,
            account_id=uuid.UUID(account_id),
            file_name=topic,  # Usamos el topic como referencia
            analysis_type='knowledge_graph',
            status='pending'
        )
        db_session.add(new_task)
        await db_session.commit()

    # Iniciar el procesamiento real en segundo plano
    loop = asyncio.get_running_loop()
    loop.create_task(run_knowledge_graph_analysis(task_id, account_id, topic, workspace_id))

    return str(task_id)

async def run_knowledge_graph_analysis(task_id: uuid.UUID, account_id: str, topic: str, workspace_id: Optional[str] = None):
    """
    Ejecuta el análisis de grafo de conocimiento y actualiza el estado de la tarea.
    """
    async with DBSession(SessionLocal) as db_session:
        try:
            # 1. Marcar la tarea como 'processing'
            await db_session.execute(
                update(AnalysisTask)
                .where(AnalysisTask.id == task_id)
                .values(status='processing')
            )
            await db_session.commit()

            # 2. Ejecutar el procesamiento del grafo
            result = await process_knowledge_graph(account_id=account_id, topic=topic)

            # 3. Marcar la tarea como 'completed'
            await db_session.execute(
                update(AnalysisTask)
                .where(AnalysisTask.id == task_id)
                .values(status='completed', result_payload=result)
            )
            await db_session.commit()
            logger.info(f"Tarea de análisis de grafo de conocimiento {task_id} completada.")

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error en la tarea de análisis de grafo de conocimiento {task_id}: {error_message}", exc_info=True)
            await db_session.execute(
                update(AnalysisTask)
                .where(AnalysisTask.id == task_id)
                .values(status='failed', error_message=error_message)
            )
            await db_session.commit()
