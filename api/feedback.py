import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import Account, BetaFeedback, Base, engine
from core.dependencies import get_db_session
from utils.security import get_current_account_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["beta-feedback"])

STORAGE_FEEDBACK_DIR = os.path.join(os.getcwd(), "storage", "feedback")
os.makedirs(STORAGE_FEEDBACK_DIR, exist_ok=True)


# --- Dependencias de Autenticación y Rol ---

async def get_current_account(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
) -> Account:
    try:
        account_uuid = uuid.UUID(current_account_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de cuenta inválido.")

    account = await db.get(Account, account_uuid)
    if not account or not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta inactiva o no encontrada.")
    return account


async def get_current_admin_account(
    account: Account = Depends(get_current_account)
) -> Account:
    if not bool(account.is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador.")
    return account


# --- Schemas Pydantic ---

class FeedbackResponse(BaseModel):
    id: str
    account_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    feedback_type: str
    title: str
    description: str
    has_attachment: bool
    attachment_filename: Optional[str] = None
    system_metadata: Optional[Dict[str, Any]] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AdminUpdateFeedbackRequest(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = None


# --- Inicialización de Tablas en Inicio ---

@router.on_event("startup")
async def ensure_feedback_table_exists():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning(f"No se pudo verificar la tabla beta_feedback en startup: {e}")


# --- Endpoints Públicos / Usuarios Beta ---

@router.post("", response_model=Dict[str, Any])
async def create_feedback(
    feedback_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    system_metadata: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Crea una nueva entrada de feedback/error reportado por un usuario Beta.
    """
    if feedback_type not in ["bug", "suggestion", "ux_experience"]:
        raise HTTPException(status_code=400, detail="Tipo de feedback inválido.")

    if not title.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="El título y la descripción son obligatorios.")

    parsed_metadata = None
    if system_metadata:
        try:
            parsed_metadata = json.loads(system_metadata)
        except Exception:
            parsed_metadata = {"raw": system_metadata}

    saved_filepath = None
    if file and file.filename:
        # Validar tamaño y extensión
        allowed_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Formato de imagen no permitido. Usa PNG, JPG, WEBP o GIF.")

        feedback_uuid = uuid.uuid4()
        safe_filename = f"{feedback_uuid}_{file.filename.replace(' ', '_')}"
        saved_filepath = os.path.join(STORAGE_FEEDBACK_DIR, safe_filename)

        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10 MB limit
            raise HTTPException(status_code=400, detail="El archivo adjunto excede el límite de 10 MB.")

        with open(saved_filepath, "wb") as f:
            f.write(content)

    new_feedback = BetaFeedback(
        id=uuid.uuid4(),
        account_id=account.id,
        feedback_type=feedback_type,
        title=title.strip(),
        description=description.strip(),
        attachment_path=saved_filepath,
        system_metadata=parsed_metadata,
        status="new",
        admin_notes=None
    )

    db.add(new_feedback)
    await db.commit()
    await db.refresh(new_feedback)

    return {
        "success": True,
        "message": "Feedback enviado correctamente. ¡Muchas gracias por ayudarnos a mejorar KognitoAI!",
        "feedback_id": str(new_feedback.id)
    }


@router.get("/me", response_model=List[FeedbackResponse])
async def get_my_feedbacks(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Devuelve los comentarios de feedback enviados por el usuario actual.
    """
    stmt = (
        select(BetaFeedback)
        .where(BetaFeedback.account_id == account.id)
        .order_by(desc(BetaFeedback.created_at))
    )
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()

    output = []
    for f in feedbacks:
        output.append(FeedbackResponse(
            id=str(f.id),
            account_id=str(f.account_id),
            user_name=account.name or account.username,
            user_email=account.email,
            feedback_type=f.feedback_type,
            title=f.title,
            description=f.description,
            has_attachment=bool(f.attachment_path and os.path.exists(f.attachment_path)),
            attachment_filename=os.path.basename(f.attachment_path) if f.attachment_path else None,
            system_metadata=f.system_metadata,
            status=f.status,
            admin_notes=f.admin_notes,
            created_at=f.created_at.isoformat() if f.created_at else "",
            updated_at=f.updated_at.isoformat() if f.updated_at else ""
        ))
    return output


# --- Endpoints de Administración ---

@router.get("/admin/all", response_model=List[FeedbackResponse])
async def admin_get_all_feedbacks(
    status_filter: Optional[str] = Query(None, alias="status"),
    type_filter: Optional[str] = Query(None, alias="type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene todos los feedbacks recibidos en la plataforma para administradores.
    """
    stmt = (
        select(BetaFeedback, Account)
        .join(Account, BetaFeedback.account_id == Account.id)
        .order_by(desc(BetaFeedback.created_at))
    )

    if status_filter:
        stmt = stmt.where(BetaFeedback.status == status_filter)
    if type_filter:
        stmt = stmt.where(BetaFeedback.feedback_type == type_filter)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.all()

    output = []
    for f, acc in rows:
        output.append(FeedbackResponse(
            id=str(f.id),
            account_id=str(f.account_id),
            user_name=acc.name or acc.username or "Sin Nombre",
            user_email=acc.email or "Sin email",
            feedback_type=f.feedback_type,
            title=f.title,
            description=f.description,
            has_attachment=bool(f.attachment_path and os.path.exists(f.attachment_path)),
            attachment_filename=os.path.basename(f.attachment_path) if f.attachment_path else None,
            system_metadata=f.system_metadata,
            status=f.status,
            admin_notes=f.admin_notes,
            created_at=f.created_at.isoformat() if f.created_at else "",
            updated_at=f.updated_at.isoformat() if f.updated_at else ""
        ))
    return output


@router.patch("/admin/{feedback_id}", response_model=Dict[str, Any])
async def admin_update_feedback(
    feedback_id: str,
    req: AdminUpdateFeedbackRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Permite al administrador actualizar el estado o notas internas de un feedback.
    """
    try:
        f_uuid = uuid.UUID(feedback_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de feedback inválido.")

    feedback = await db.get(BetaFeedback, f_uuid)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback no encontrado.")

    if req.status is not None:
        if req.status not in ["new", "in_review", "resolved", "archived"]:
            raise HTTPException(status_code=400, detail="Estado inválido.")
        feedback.status = req.status

    if req.admin_notes is not None:
        feedback.admin_notes = req.admin_notes

    feedback.updated_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Feedback actualizado correctamente."}


@router.delete("/admin/{feedback_id}", response_model=Dict[str, Any])
async def admin_delete_feedback(
    feedback_id: str,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Permite al administrador eliminar un registro de feedback.
    """
    try:
        f_uuid = uuid.UUID(feedback_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de feedback inválido.")

    feedback = await db.get(BetaFeedback, f_uuid)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback no encontrado.")

    if feedback.attachment_path and os.path.exists(feedback.attachment_path):
        try:
            os.remove(feedback.attachment_path)
        except Exception as e:
            logger.warning(f"No se pudo eliminar el archivo adjunto {feedback.attachment_path}: {e}")

    await db.delete(feedback)
    await db.commit()

    return {"success": True, "message": "Feedback eliminado exitosamente."}


@router.get("/attachment/{feedback_id}")
async def get_feedback_attachment(
    feedback_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Descarga o muestra la imagen adjunta a un reporte de feedback.
    """
    try:
        f_uuid = uuid.UUID(feedback_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de feedback inválido.")

    feedback = await db.get(BetaFeedback, f_uuid)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback no encontrado.")

    # Solo el autor o un admin pueden ver el adjunto
    if not account.is_admin and feedback.account_id != account.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver este archivo.")

    if not feedback.attachment_path or not os.path.exists(feedback.attachment_path):
        raise HTTPException(status_code=404, detail="El archivo adjunto no existe o fue eliminado.")

    return FileResponse(feedback.attachment_path)
