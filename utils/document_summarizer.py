import logging
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import update, text

from core.database import SessionLocal, AnalysisTask
from utils.db_session import DBSession
from core.memory_manager import get_full_document_content
from utils.advanced_text_analyzer import text_analyzer
from utils.analysis_progress import persist_analysis_progress, send_analysis_progress
import asyncio

logger = logging.getLogger(__name__)

async def run_document_summary_and_save(task_id: str, account_id: str, file_name: str, workspace_id: Optional[str] = None):
    """
    Función de utilidad pesada que se ejecuta en segundo plano para generar un resumen
    estructurado y completo del documento.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            await persist_analysis_progress(
                db_session,
                task_id,
                status="processing",
                phase="initializing",
                message=f'Preparando resumen de "{file_name}"...',
                progress_percent=5,
                analysis_type="document_summary",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="initializing",
                message=f'Preparando resumen de "{file_name}"...',
                progress_percent=5,
                file_name=file_name,
                analysis_type="document_summary",
            )

            logger.info(f"Iniciando resumen de documento para tarea {task_id}...")
            await persist_analysis_progress(
                db_session,
                task_id,
                phase="reconstructing_content",
                message="Cargando contenido del documento para resumir...",
                progress_percent=18,
                analysis_type="document_summary",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="reconstructing_content",
                message="Cargando contenido del documento para resumir...",
                progress_percent=18,
                file_name=file_name,
                analysis_type="document_summary",
            )
            text_content = await get_full_document_content(account_id, file_name)
            if not text_content: 
                raise ValueError("Contenido del documento no encontrado.")
            
            # 2. Generar el resumen estructurado específico
            await persist_analysis_progress(
                db_session,
                task_id,
                phase="summarizing",
                message="Generando resumen estructurado con IA...",
                progress_percent=35,
                analysis_type="document_summary",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="summarizing",
                message="Generando resumen estructurado con IA...",
                progress_percent=35,
                file_name=file_name,
                analysis_type="document_summary",
            )

            _llm_done = asyncio.Event()

            async def _progress_ticker():
                steps = [
                    (46, "Extrayendo estructura principal..."),
                    (58, "Sintetizando ideas centrales..."),
                    (70, "Refinando resumen ejecutivo..."),
                    (82, "Construyendo síntesis final..."),
                    (88, "Revisando claridad del resumen..."),
                ]
                for pct, msg in steps:
                    try:
                        await asyncio.wait_for(_llm_done.wait(), timeout=6.0)
                        break
                    except asyncio.TimeoutError:
                        pass
                    if _llm_done.is_set():
                        break
                    await persist_analysis_progress(
                        db_session,
                        task_id,
                        phase="summarizing",
                        message=msg,
                        progress_percent=pct,
                        analysis_type="document_summary",
                        file_name=file_name,
                    )
                    await send_analysis_progress(
                        account_id,
                        task_id,
                        phase="summarizing",
                        message=msg,
                        progress_percent=pct,
                        file_name=file_name,
                        analysis_type="document_summary",
                    )

            async def _run_llm():
                result = await text_analyzer.summarize_document(
                    text_content,
                    document_title=file_name,
                    account_id=str(account_id),
                )
                _llm_done.set()
                return result

            analysis_result, _ = await asyncio.gather(_run_llm(), _progress_ticker())

            # 3. Guardar el resultado y marcar como 'completed'
            # Asegurarse de que el resultado sea un diccionario
            result_payload = analysis_result if isinstance(analysis_result, dict) else analysis_result.dict()

            await persist_analysis_progress(
                db_session,
                task_id,
                phase="saving_to_neo4j",
                message="Guardando resumen generado...",
                progress_percent=94,
                analysis_type="document_summary",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="saving_to_neo4j",
                message="Guardando resumen generado...",
                progress_percent=94,
                file_name=file_name,
                analysis_type="document_summary",
            )

            # Intentar obtener el título real del documento de base de datos
            document_title = file_name
            try:
                title_query = text("""
                    SELECT cmetadata->>'title' AS title 
                    FROM langchain_pg_embedding 
                    WHERE account_id = CAST(:account_id AS UUID) 
                      AND cmetadata->>'file_name' = :file_name 
                      AND cmetadata->>'type' = 'document_chunk' 
                    LIMIT 1
                """)
                title_res = await db_session.execute(title_query, {"account_id": account_id, "file_name": file_name})
                title_row = title_res.mappings().first()
                if title_row and title_row.get("title"):
                    document_title = title_row["title"]
                    logger.info(f"Título recuperado para metadata del resumen de {file_name}: {document_title}")
            except Exception as title_err:
                logger.error(f"Error al recuperar título para {file_name}: {title_err}")

            # Agregar metadata de herramienta utilizada
            result_payload["tool_used"] = "advanced_text_analyzer.py"
            result_payload["analysis_metadata"] = {
                "tool_used": "advanced_text_analyzer.py",
                "analysis_type": "document_summary",
                "file_name": file_name,
                "title": document_title,
                "workspace_id": workspace_id,
                "created_at": datetime.now().isoformat()
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Resumen de documento para tarea {task_id} completado.")
            await send_analysis_progress(
                account_id,
                task_id,
                phase="completed",
                message="¡Resumen del documento completado!",
                progress_percent=100,
                file_name=file_name,
                analysis_type="document_summary",
                is_complete=True,
            )

        except Exception as e:
            logger.error(f"Fallo en tarea de resumen de documento {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()
            await persist_analysis_progress(
                db_session,
                task_id,
                phase="error",
                message="El resumen del documento falló.",
                progress_percent=100,
                status="failed",
                analysis_type="document_summary",
                file_name=file_name,
                has_error=True,
                error=str(e),
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="error",
                message="El resumen del documento falló.",
                progress_percent=100,
                file_name=file_name,
                analysis_type="document_summary",
                has_error=True,
                error=str(e),
            )
