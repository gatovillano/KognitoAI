"""
Router API para el módulo de correo electrónico.

Endpoints:
- Cuentas: CRUD + test IMAP/SMTP
- Carpetas: listar + sync
- Emails: listar, detalle, flags, eliminar
- Envío: send email
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal
from core.email_manager import EmailManager
from utils.security import get_current_account_id
from core.dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


# ------------------------------------------------------------------
# Modelos Pydantic
# ------------------------------------------------------------------
class EmailAccountCreateRequest(BaseModel):
    name: str = Field(..., description="Nombre amigable de la cuenta")
    email_address: EmailStr = Field(..., description="Dirección de correo")
    provider: Optional[str] = Field(None, description="Proveedor: gmail, outlook, yahoo, disroot, generic")
    imap_host: Optional[str] = Field(None)
    imap_port: int = Field(993, ge=1, le=65535)
    imap_use_ssl: bool = Field(True)
    smtp_host: Optional[str] = Field(None)
    smtp_port: int = Field(587, ge=1, le=65535)
    smtp_use_tls: bool = Field(True)
    smtp_use_ssl: bool = Field(False)
    auth_type: str = Field("password", description="password, app_password, oauth2")
    username: Optional[str] = Field(None)
    password: Optional[str] = Field(None, description="Contraseña o App Password")
    access_token: Optional[str] = Field(None)
    refresh_token: Optional[str] = Field(None)
    token_expires_at: Optional[str] = Field(None)
    oauth_scopes: Optional[List[str]] = Field(None)
    is_default: bool = Field(False)
    sync_enabled: bool = Field(True)
    sync_interval_minutes: int = Field(15, ge=1)


class EmailAccountUpdateRequest(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_use_ssl: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_use_tls: Optional[bool] = None
    smtp_use_ssl: Optional[bool] = None
    auth_type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[str] = None
    oauth_scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None


class SendEmailRequest(BaseModel):
    email_account_id: str = Field(..., description="ID de la cuenta desde la cual enviar")
    to_addresses: List[EmailStr] = Field(..., description="Lista de destinatarios")
    subject: str = Field(..., description="Asunto del correo")
    body_text: str = Field(..., description="Cuerpo en texto plano")
    body_html: Optional[str] = Field(None, description="Cuerpo en HTML (opcional)")
    cc_addresses: Optional[List[EmailStr]] = Field(None)
    bcc_addresses: Optional[List[EmailStr]] = Field(None)
    attachments: Optional[List[str]] = Field(None, description="Rutas locales de archivos adjuntos")
    reply_to_message_id: Optional[str] = Field(None)


class EmailFlagsRequest(BaseModel):
    is_read: Optional[bool] = None
    is_flagged: Optional[bool] = None
    is_deleted: Optional[bool] = None
    is_spam: Optional[bool] = None
    folder_id: Optional[str] = None


# ------------------------------------------------------------------
# Dependencias
# ------------------------------------------------------------------
def get_email_manager(db: AsyncSession = Depends(get_db_session)) -> EmailManager:
    return EmailManager(db)


# ------------------------------------------------------------------
# Cuentas
# ------------------------------------------------------------------
@router.post("/email/accounts")
async def create_email_account(
    request: EmailAccountCreateRequest,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        result = await manager.add_email_account(
            account_id=account_id,
            name=request.name,
            email_address=request.email_address,
            provider=request.provider,
            imap_host=request.imap_host,
            imap_port=request.imap_port,
            imap_use_ssl=request.imap_use_ssl,
            smtp_host=request.smtp_host,
            smtp_port=request.smtp_port,
            smtp_use_tls=request.smtp_use_tls,
            smtp_use_ssl=request.smtp_use_ssl,
            auth_type=request.auth_type,
            username=request.username,
            password=request.password,
            access_token=request.access_token,
            refresh_token=request.refresh_token,
            token_expires_at=request.token_expires_at,
            oauth_scopes=request.oauth_scopes,
            is_default=request.is_default,
            sync_enabled=request.sync_enabled,
            sync_interval_minutes=request.sync_interval_minutes,
        )
        return result
    except Exception as exc:
        logger.error("Error creando cuenta de correo: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/email/accounts")
async def list_email_accounts(
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.list_email_accounts(account_id)
    except Exception as exc:
        logger.error("Error listando cuentas de correo: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error al listar cuentas de correo.")


@router.get("/email/accounts/{email_account_id}")
async def get_email_account(
    email_account_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.get_email_account(account_id, email_account_id)
    except Exception as exc:
        logger.error("Error obteniendo cuenta de correo: %s", exc, exc_info=True)
        raise HTTPException(status_code=404, detail="Cuenta de correo no encontrada.")


@router.put("/email/accounts/{email_account_id}")
async def update_email_account(
    email_account_id: str,
    request: EmailAccountUpdateRequest,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        current = await manager.get_email_account(account_id, email_account_id)
        update_data = request.dict(exclude_unset=True)

        # Si se actualiza la contraseña, hay que reencriptar
        password = update_data.pop("password", None)
        if password is not None:
            update_data["encrypted_password"] = manager.security.encrypt(password)

        access_token = update_data.pop("access_token", None)
        if access_token is not None:
            update_data["encrypted_access_token"] = manager.security.encrypt(access_token)

        refresh_token = update_data.pop("refresh_token", None)
        if refresh_token is not None:
            update_data["encrypted_refresh_token"] = manager.security.encrypt(refresh_token)

        token_expires_at = update_data.pop("token_expires_at", None)
        if token_expires_at is not None:
            update_data["token_expires_at"] = datetime.fromisoformat(token_expires_at)

        if update_data.get("is_default"):
            await manager.db.execute(
                update(EmailAccount)
                .where(EmailAccount.account_id == _to_uuid(account_id))
                .values(is_default=False)
            )

        await manager.db.execute(
            update(EmailAccount)
            .where(EmailAccount.id == _to_uuid(email_account_id))
            .values(**update_data)
        )
        await manager.db.commit()
        return {"updated": True, "email_account_id": email_account_id}
    except Exception as exc:
        logger.error("Error actualizando cuenta de correo: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/email/accounts/{email_account_id}")
async def delete_email_account(
    email_account_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        await manager.delete_email_account(account_id, email_account_id)
        return {"deleted": True, "email_account_id": email_account_id}
    except Exception as exc:
        logger.error("Error eliminando cuenta de correo: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/email/accounts/{email_account_id}/test-imap")
async def test_imap(
    email_account_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.test_imap_connection(account_id, email_account_id)
    except Exception as exc:
        logger.error("Error test IMAP: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/email/accounts/{email_account_id}/test-smtp")
async def test_smtp(
    email_account_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.test_smtp_connection(account_id, email_account_id)
    except Exception as exc:
        logger.error("Error test SMTP: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------
# Carpetas
# ------------------------------------------------------------------
@router.post("/email/accounts/{email_account_id}/folders/sync")
async def sync_folders(
    email_account_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        folders = await manager.sync_folders(account_id, email_account_id)
        return {"folders": folders}
    except Exception as exc:
        logger.error("Error sincronizando carpetas: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/email/accounts/{email_account_id}/folders")
async def list_folders(
    email_account_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.list_folders(account_id, email_account_id)
    except Exception as exc:
        logger.error("Error listando carpetas: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error al listar carpetas.")


# ------------------------------------------------------------------
# Emails
# ------------------------------------------------------------------
@router.get("/email/accounts/{email_account_id}/emails")
async def list_emails(
    email_account_id: str,
    folder_id: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    is_flagged: Optional[bool] = Query(None),
    is_spam: Optional[bool] = Query(None),
    is_deleted: Optional[bool] = Query(None),
    is_draft: Optional[bool] = Query(None),
    search_term: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        total, items = await manager.list_emails(
            account_id=account_id,
            email_account_id=email_account_id,
            folder_id=folder_id,
            is_read=is_read,
            is_flagged=is_flagged,
            is_spam=is_spam,
            is_deleted=is_deleted,
            is_draft=is_draft,
            search_term=search_term,
            skip=skip,
            limit=limit,
        )
        return {"total": total, "emails": items}
    except Exception as exc:
        logger.error("Error listando emails: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error al listar correos.")


@router.get("/email/accounts/{email_account_id}/emails/{email_id}")
async def get_email(
    email_account_id: str,
    email_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.get_email(account_id, email_id)
    except Exception as exc:
        logger.error("Error obteniendo email: %s", exc, exc_info=True)
        raise HTTPException(status_code=404, detail="Correo no encontrado.")


@router.patch("/email/accounts/{email_account_id}/emails/{email_id}/flags")
async def update_email_flags(
    email_account_id: str,
    email_id: str,
    request: EmailFlagsRequest,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.update_email_flags(
            account_id=account_id,
            email_id=email_id,
            is_read=request.is_read,
            is_flagged=request.is_flagged,
            is_deleted=request.is_deleted,
            is_spam=request.is_spam,
            folder_id=request.folder_id,
        )
    except Exception as exc:
        logger.error("Error actualizando flags: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/email/accounts/{email_account_id}/emails/{email_id}")
async def delete_email(
    email_account_id: str,
    email_id: str,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        await manager.delete_email(account_id, email_id)
        return {"deleted": True, "email_id": email_id}
    except Exception as exc:
        logger.error("Error eliminando email: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/email/send")
async def send_email(
    request: SendEmailRequest,
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.send_email(
            account_id=account_id,
            email_account_id=request.email_account_id,
            to_addresses=request.to_addresses,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            cc_addresses=request.cc_addresses,
            bcc_addresses=request.bcc_addresses,
            attachments=request.attachments,
            reply_to_message_id=request.reply_to_message_id,
        )
    except Exception as exc:
        logger.error("Error enviando email: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/email/accounts/{email_account_id}/folders/{folder_id}/sync")
async def sync_emails_for_folder(
    email_account_id: str,
    folder_id: str,
    limit: int = Query(100, ge=1, le=500),
    account_id: str = Depends(get_current_account_id),
    manager: EmailManager = Depends(get_email_manager),
):
    try:
        return await manager.sync_emails_for_folder(
            account_id=account_id,
            email_account_id=email_account_id,
            folder_id=folder_id,
            limit=limit,
        )
    except Exception as exc:
        logger.error("Error sincronizando emails: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc))
