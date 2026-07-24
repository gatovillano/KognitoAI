import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.dependencies import get_db_session
from utils.security import get_current_account_id
from core.repositories.secret_repository import SecretRepository
from core.config import settings

from .models import UserEmailConfig
from .schemas import EmailConfigResponse, EmailConfigUpdate, EmailSendRequest, AIDraftRequest
from .client import EmailClient
from .oauth import get_google_auth_url, exchange_code_for_tokens, refresh_google_access_token
from .ai import summarize_email_body, draft_email_response

router = APIRouter(prefix="/api/email", tags=["email"])

async def get_or_create_config(account_id: uuid.UUID, db: AsyncSession) -> UserEmailConfig:
    stmt = select(UserEmailConfig).where(UserEmailConfig.account_id == account_id)
    res = await db.execute(stmt)
    config = res.scalars().first()
    if not config:
        config = UserEmailConfig(account_id=account_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config

async def get_oauth_tokens(account_id: uuid.UUID, config: UserEmailConfig, repo: SecretRepository) -> str:
    """Helper to get a fresh access token for Gmail OAuth."""
    refresh_token = await repo.get_decrypted_secret(account_id, "EMAIL_GOOGLE_REFRESH_TOKEN")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Google Account not connected")
    
    client_id = await repo.get_decrypted_secret(account_id, "EMAIL_GOOGLE_CLIENT_ID") or getattr(settings, "google_email_client_id", None)
    client_secret = await repo.get_decrypted_secret(account_id, "EMAIL_GOOGLE_CLIENT_SECRET") or getattr(settings, "google_email_client_secret", None)
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Google OAuth App Credentials missing")
    
    try:
        access_token = await refresh_google_access_token(client_id, client_secret, refresh_token)
        return access_token
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Failed to refresh access token: {str(e)}")

@router.get("/config", response_model=EmailConfigResponse)
async def get_config(account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)
    
    imap_pass = await repo.get_decrypted_secret(uid, "EMAIL_IMAP_PASSWORD")
    smtp_pass = await repo.get_decrypted_secret(uid, "EMAIL_SMTP_PASSWORD")
    refresh_t = await repo.get_decrypted_secret(uid, "EMAIL_GOOGLE_REFRESH_TOKEN")
    client_id = await repo.get_decrypted_secret(uid, "EMAIL_GOOGLE_CLIENT_ID")
    
    return EmailConfigResponse(
        provider=config.provider,
        imap_server=config.imap_server,
        imap_port=config.imap_port,
        imap_ssl=config.imap_ssl,
        imap_user=config.imap_user,
        smtp_server=config.smtp_server,
        smtp_port=config.smtp_port,
        smtp_ssl=config.smtp_ssl,
        smtp_user=config.smtp_user,
        has_imap_password=bool(imap_pass),
        has_smtp_password=bool(smtp_pass),
        has_google_oauth=bool(refresh_t),
        google_client_id=client_id
    )

@router.put("/config", response_model=EmailConfigResponse)
async def update_config(update_data: EmailConfigUpdate, account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)

    # Save standard attributes
    for field, val in update_data.dict(exclude_unset=True).items():
        if hasattr(config, field):
            setattr(config, field, val)
    await db.commit()
    await db.refresh(config)

    # Save secrets
    if update_data.imap_password:
        await repo.set_secret(uid, "EMAIL_IMAP_PASSWORD", update_data.imap_password, "Email IMAP Password")
    if update_data.smtp_password:
        await repo.set_secret(uid, "EMAIL_SMTP_PASSWORD", update_data.smtp_password, "Email SMTP Password")
    if update_data.google_client_id:
        await repo.set_secret(uid, "EMAIL_GOOGLE_CLIENT_ID", update_data.google_client_id, "Google Client ID for Email")
    if update_data.google_client_secret:
        await repo.set_secret(uid, "EMAIL_GOOGLE_CLIENT_SECRET", update_data.google_client_secret, "Google Client Secret for Email")

    return await get_config(account_id, db)

@router.get("/folders")
async def get_folders(account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)

    if config.provider == "google":
        access_token = await get_oauth_tokens(uid, config, repo)
        folders = await asyncio.to_thread(EmailClient.fetch_folders, config, None, access_token)
    else:
        password = await repo.get_decrypted_secret(uid, "EMAIL_IMAP_PASSWORD")
        if not password:
            raise HTTPException(status_code=400, detail="IMAP password not configured")
        folders = await asyncio.to_thread(EmailClient.fetch_folders, config, password)
    return {"folders": folders}

@router.get("/messages")
async def get_messages(folder: str = "INBOX", limit: int = 20, offset: int = 0, account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)

    try:
        if config.provider == "google":
            access_token = await get_oauth_tokens(uid, config, repo)
            messages = await asyncio.to_thread(EmailClient.fetch_messages, config, None, folder, limit, offset, access_token)
        else:
            password = await repo.get_decrypted_secret(uid, "EMAIL_IMAP_PASSWORD")
            if not password:
                raise HTTPException(status_code=400, detail="IMAP password not configured")
            messages = await asyncio.to_thread(EmailClient.fetch_messages, config, password, folder, limit, offset)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")

@router.get("/messages/{message_uid}")
async def get_message_detail(message_uid: str, folder: str = "INBOX", account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)

    try:
        if config.provider == "google":
            access_token = await get_oauth_tokens(uid, config, repo)
            detail = await asyncio.to_thread(EmailClient.fetch_message_detail, config, None, folder, message_uid, access_token)
        else:
            password = await repo.get_decrypted_secret(uid, "EMAIL_IMAP_PASSWORD")
            if not password:
                raise HTTPException(status_code=400, detail="IMAP password not configured")
            detail = await asyncio.to_thread(EmailClient.fetch_message_detail, config, password, folder, message_uid)
        return detail
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch email detail: {str(e)}")

@router.post("/send")
async def send_email(req: EmailSendRequest, account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)

    try:
        if config.provider == "google":
            access_token = await get_oauth_tokens(uid, config, repo)
            await asyncio.to_thread(EmailClient.send_email, config, None, req.to_email, req.cc_emails, req.subject, req.body, access_token)
        else:
            password = await repo.get_decrypted_secret(uid, "EMAIL_SMTP_PASSWORD")
            if not password:
                raise HTTPException(status_code=400, detail="SMTP password not configured")
            await asyncio.to_thread(EmailClient.send_email, config, password, req.to_email, req.cc_emails, req.subject, req.body)
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@router.get("/oauth/url")
async def get_oauth_url(account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    repo = SecretRepository(db)
    
    client_id = await repo.get_decrypted_secret(uid, "EMAIL_GOOGLE_CLIENT_ID") or getattr(settings, "google_email_client_id", None)
    if not client_id:
        raise HTTPException(status_code=400, detail="Google Client ID is missing. Configure it first.")
    
    redirect_uri = f"{settings.frontend_url.rstrip('/')}/email/oauth/callback"
    auth_url = get_google_auth_url(client_id, redirect_uri, account_id)
    return {"url": auth_url}

@router.post("/oauth/callback")
async def oauth_callback(code: str, account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)
    
    client_id = await repo.get_decrypted_secret(uid, "EMAIL_GOOGLE_CLIENT_ID") or getattr(settings, "google_email_client_id", None)
    client_secret = await repo.get_decrypted_secret(uid, "EMAIL_GOOGLE_CLIENT_SECRET") or getattr(settings, "google_email_client_secret", None)
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Google Client credentials missing")

    redirect_uri = f"{settings.frontend_url.rstrip('/')}/email/oauth/callback"
    
    try:
        tokens = await exchange_code_for_tokens(client_id, client_secret, code, redirect_uri)
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")
        
        if refresh_token:
            await repo.set_secret(uid, "EMAIL_GOOGLE_REFRESH_TOKEN", refresh_token, "Google email OAuth Refresh Token")
        if access_token:
            await repo.set_secret(uid, "EMAIL_GOOGLE_ACCESS_TOKEN", access_token, "Google email OAuth Access Token")
        
        # Force set provider to google
        config.provider = "google"
        await db.commit()
        
        return {"status": "success", "message": "Google Account linked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {str(e)}")

@router.post("/messages/{message_uid}/ai-summarize")
async def ai_summarize_email(message_uid: str, folder: str = "INBOX", account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    uid = uuid.UUID(account_id)
    config = await get_or_create_config(uid, db)
    repo = SecretRepository(db)
    
    try:
        if config.provider == "google":
            access_token = await get_oauth_tokens(uid, config, repo)
            detail = await asyncio.to_thread(EmailClient.fetch_message_detail, config, None, folder, message_uid, access_token)
        else:
            password = await repo.get_decrypted_secret(uid, "EMAIL_IMAP_PASSWORD")
            detail = await asyncio.to_thread(EmailClient.fetch_message_detail, config, password, folder, message_uid)
        
        body_text = detail.get("text", "")
        summary = await summarize_email_body(body_text, uid)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Summarization failed: {str(e)}")

@router.post("/ai-draft")
async def ai_draft_email(req: AIDraftRequest, account_id: str = Depends(get_current_account_id)):
    try:
        draft = await draft_email_response(req.instructions, req.original_body, req.original_subject, uuid.UUID(account_id))
        return {"draft": draft}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Drafting failed: {str(e)}")
