import logging
import uuid
from typing import Any, Optional

from core.database import AnalysisTask

logger = logging.getLogger(__name__)


def build_analysis_progress_payload(
    existing_payload: Optional[dict[str, Any]] = None,
    *,
    phase: str,
    message: str,
    progress_percent: int,
    analysis_type: Optional[str] = None,
    file_name: Optional[str] = None,
    topic: Optional[str] = None,
    processing_mode: str = "conceptual",
    is_complete: bool = False,
    has_error: bool = False,
    error: Optional[str] = None,
) -> dict[str, Any]:
    payload = dict(existing_payload or {})
    metadata = dict(payload.get("analysis_metadata") or {})

    if analysis_type:
        metadata["analysis_type"] = analysis_type
    if file_name:
        metadata["file_name"] = file_name
    if topic:
        metadata["topic"] = topic

    if metadata:
        payload["analysis_metadata"] = metadata

    payload["analysis_progress"] = {
        "phase": phase,
        "message": message,
        "progress_percent": progress_percent,
        "is_complete": is_complete,
        "has_error": has_error,
        "error": error,
        "processing_mode": processing_mode,
        "topic": topic,
        "file_name": file_name,
        "analysis_type": analysis_type,
    }
    return payload


async def persist_analysis_progress(
    db_session: Any,
    task_id: str,
    *,
    phase: str,
    message: str,
    progress_percent: int,
    status: Optional[str] = None,
    analysis_type: Optional[str] = None,
    file_name: Optional[str] = None,
    topic: Optional[str] = None,
    processing_mode: str = "conceptual",
    is_complete: bool = False,
    has_error: bool = False,
    error: Optional[str] = None,
) -> None:
    task = await db_session.get(AnalysisTask, uuid.UUID(task_id))
    if not task:
        logger.warning("No se encontró AnalysisTask para persistir progreso: %s", task_id)
        return

    task.result_payload = build_analysis_progress_payload(
        task.result_payload if isinstance(task.result_payload, dict) else None,
        phase=phase,
        message=message,
        progress_percent=progress_percent,
        analysis_type=analysis_type,
        file_name=file_name,
        topic=topic,
        processing_mode=processing_mode,
        is_complete=is_complete,
        has_error=has_error,
        error=error,
    )

    if status:
        task.status = status

    await db_session.commit()


async def send_analysis_progress(
    account_id: str,
    task_id: str,
    *,
    phase: str,
    message: str,
    progress_percent: int,
    topic: Optional[str] = None,
    file_name: Optional[str] = None,
    analysis_type: Optional[str] = None,
    processing_mode: str = "conceptual",
    is_complete: bool = False,
    has_error: bool = False,
    error: Optional[str] = None,
) -> None:
    try:
        from core.websocket_manager import send_personal_message

        payload = {
            "type": "analysis_progress",
            "data": {
                "task_id": task_id,
                "phase": phase,
                "message": message,
                "progress_percent": progress_percent,
                "is_complete": is_complete,
                "has_error": has_error,
                "error": error,
                "processing_mode": processing_mode,
                "topic": topic,
                "file_name": file_name,
                "type": "document" if analysis_type in {"document", "document_summary"} else "analysis",
                "analysis_type": analysis_type,
            },
        }
        await send_personal_message(account_id, payload)
    except Exception as ws_err:
        logger.warning("No se pudo enviar progreso de análisis vía WebSocket: %s", ws_err)
