import logging
import asyncio
from typing import List, Dict, Any, Optional
import uuid

# Importaciones necesarias para las tareas
from core.database import SessionLocal, UploadTask, DBSession
from sqlalchemy import update
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, update_document_metadata
from core.websocket_manager import send_personal_message # Importar send_personal_message
from tools.cognee_knowledge_graph_tool import CogneeKnowledgeGraphTool
from sqlalchemy import text

logger = logging.getLogger(__name__)

async def process_upload_task(task_id: str, account_id: str, file_data_list: List[Dict], topic: str, workspace_id: Optional[str] = None):
    """
    Procesa la subida de documentos en segundo plano de forma asíncrona.
    """
    logger.info(f"Iniciando procesamiento de subida para tarea {task_id}...")
    
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
            processed_files_count = 0

            async def _process_single_file(file_data: Dict) -> bool:
                try:
                    file_name_str = file_data.get('filename', "unknown_file")
                    
                    loop = asyncio.get_running_loop()
                    extracted_text, metadata = await loop.run_in_executor(
                        None,
                        extract_text_and_metadata_from_document,
                        file_name_str,
                        file_data['content']
                    )

                    if not extracted_text:
                        logger.warning(f"No se pudo extraer texto del archivo '{file_name_str}'. Omitiendo.")
                        return False

                    await process_document_for_rag(
                        account_id=account_id,
                        file_name=file_name_str,
                        extracted_text=extracted_text,
                        topic=topic,
                        metadata={"original_filename": file_name_str},
                        workspace_id=workspace_id
                    )
                    return True
                except Exception as e:
                    logger.error(f"Error al procesar archivo {file_data.get('filename', 'unknown')}: {e}", exc_info=True)
                    return False

            for i, file_data in enumerate(file_data_list):
                result = await _process_single_file(file_data)
                if result:
                    processed_files_count += 1
                
                progress = 5 + int(((i + 1) / total_files) * 90)
                async with DBSession(SessionLocal) as progress_session:
                    stmt_progress = update(UploadTask).where(UploadTask.id == uuid.UUID(task_id)).values(
                        progress=progress
                    )
                    await progress_session.execute(stmt_progress)
                    await progress_session.commit()

                await send_personal_message(
                    account_id,
                    {
                        "type": "upload_progress",
                        "task_id": task_id,
                        "progress": progress,
                        "message": f"Procesando archivo {i + 1}/{total_files}..."
                    }
                )

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
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"account_id": account_id}

            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic
            if workspace_id:
                clauses.append("workspace_id = :workspace_id")
                params["workspace_id"] = workspace_id
            if team_id:
                clauses.append("team_id = :team_id")
                params["team_id"] = team_id
            if file_name:
                clauses.append("cmetadata->>'file_name' = :file_name")
                params["file_name"] = file_name

            select_sql = text("SELECT * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
            result = await db.execute(select_sql, params)
            chunks = result.mappings().all()

            if not chunks:
                logger.info("No se encontraron fragmentos de documentos para procesar.")
                return 0

            documents = {}
            for chunk in chunks:
                file_name = chunk['cmetadata'].get('file_name')
                if file_name:
                    if file_name not in documents:
                        documents[file_name] = []
                    documents[file_name].append(chunk)

            for file_name, doc_chunks in documents.items():
                full_content = "".join([c['document'] for c in sorted(doc_chunks, key=lambda x: x['cmetadata'].get('chunk_index', 0))])
                new_title = None
                if full_content:
                    lines = [line.strip() for line in full_content.split('\n') if line.strip()]
                    if lines:
                        first_line = lines[0]
                        if 5 < len(first_line) < 100:
                            new_title = first_line
                        else:
                            for line in lines[:5]:
                                if len(line) > 10 and len(line) < 150 and line.isupper() and line.count(' ') < len(line)/3:
                                    new_title = line.title()
                                    break
                        if not new_title and len(lines) > 1:
                            combined_lines = " ".join(lines[:2])
                            if 10 < len(combined_lines) < 150:
                                new_title = combined_lines

                if new_title and new_title != doc_chunks[0]['cmetadata'].get('title'):
                    if file_name: # Asegurarse de que file_name no sea None
                        success = await update_document_metadata(account_id, file_name, new_title=new_title, new_topic=None, team_id=team_id, workspace_id=workspace_id)
                        if success:
                            updated_count += 1
                    else:
                        logger.warning(f"No se pudo actualizar el título para un documento sin nombre de archivo.")
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

        # Preparar documentos para Cognee
        cognee_documents = []
        for doc in documents:
            cognee_documents.append({
                "content": doc.get("content", ""),
                "title": doc.get("file_name", "Documento sin título"),
                "metadata": {
                    "file_name": doc.get("file_name"),
                    "topic": doc.get("topic"),
                    "account_id": account_id
                }
            })

        tool = CogneeKnowledgeGraphTool(account_id=account_id)
        tool_input = {
            "action": "process_documents",
            "documents": cognee_documents,
            "dataset_name": f"kognito_{account_id}"
        }
        result = await tool._arun(
            action=tool_input["action"],
            documents=tool_input.get("documents"),
            dataset_name=tool_input.get("dataset_name", f"kognito_{account_id}")
        )
        logger.info(f"Procesamiento de grafo completado para {account_id}: {result}")
        return {"message": f"Procesamiento de grafo de conocimiento completado para {len(cognee_documents)} documentos.", "result": result}

    except Exception as e:
        logger.error(f"Error en procesamiento de grafo para {account_id}: {e}", exc_info=True)
        return {"message": f"Error al procesar el grafo de conocimiento: {str(e)}", "error": str(e)}