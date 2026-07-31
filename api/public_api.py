# api/public_api.py

"""
API Pública KAI - Compatible con OpenAI

Endpoints para uso de API keys y chat completions compatibles con OpenAI.
"""

import logging
import time
import uuid
import json
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db_session, Account
from core.api_key_model import ApiKey
from core.llm_manager import get_main_llm, get_llm_for_user, get_fast_llm, get_fallback_llm
from core.prompts import KAI_SYSTEM_PROMPT
from utils.security import oauth2_scheme_optional

logger = logging.getLogger(__name__)
router = APIRouter()

# --- API Key Pydantic Models ---

class ApiKeyCreate(BaseModel):
    """Modelo para crear una nueva API Key"""
    name: str = Field(..., min_length=1, max_length=255, description='Nombre descriptivo para la API Key')
    description: Optional[str] = Field(None, max_length=1000, description='Descripción opcional')
    expires_in_days: Optional[int] = Field(None, description='Días hasta expiración (opcional)')
    rate_limit_per_minute: int = Field(60, ge=1, le=1000, description='Límite de requests por minuto')
    rate_limit_per_hour: int = Field(1000, ge=1, le=10000, description='Límite de requests por hora')

class ApiKeyResponse(BaseModel):
    """Modelo de respuesta para una API Key"""
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    is_revoked: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    key: Optional[str] = None

class ApiKeyListResponse(BaseModel):
    """Modelo de respuesta para lista de API Keys"""
    data: List[ApiKeyResponse]
    total: int

# --- OpenAI Compatibility Models ---

class ChatCompletionMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    user: Optional[str] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatCompletionMessage
    finish_reason: Optional[str] = "stop"

class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4()}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None

# --- Helper Functions ---

def generate_api_key() -> str:
    """
    Genera una API key compatible con OpenAI.
    Formato: sk-kaito-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    """
    random_part = secrets.token_hex(24)
    return f"sk-kaito-{random_part}"

def hash_api_key(api_key: str) -> str:
    """Hash de una API key para almacenamiento seguro"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verifica una API key contra su hash"""
    return hashlib.sha256(plain_key.encode()).hexdigest() == hashed_key

# --- Endpoints for API Key management ---

@router.get("/api-keys", response_model=ApiKeyListResponse, summary="Listar API Keys")
async def list_api_keys(
    account_id: str = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db_session)
):
    """Lista todas las API Keys del usuario autenticado"""
    if not account_id:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.account_id == uuid.UUID(account_id),
            ApiKey.is_revoked == False
        )
    )
    keys = result.scalars().all()
    
    data = [
        ApiKeyResponse(
            id=str(k.id),
            name=k.name,
            description=k.description,
            created_at=k.created_at,
            expires_at=k.expires_at,
            is_active=k.is_active,
            is_revoked=k.is_revoked,
            rate_limit_per_minute=k.rate_limit_per_minute,
            rate_limit_per_hour=k.rate_limit_per_hour
        )
        for k in keys
    ]
    return ApiKeyListResponse(data=data, total=len(keys))

@router.post("/api-keys", response_model=ApiKeyResponse, summary="Crear API Key")
async def create_api_key(
    key_data: ApiKeyCreate,
    account_id: str = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db_session)
):
    """Crea una nueva API Key"""
    if not account_id:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    
    plain_key = generate_api_key()
    hashed_key = hash_api_key(plain_key)
    
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=key_data.expires_in_days)
        
    db_key = ApiKey(
        name=key_data.name,
        hashed_key=hashed_key,
        account_id=uuid.UUID(account_id),
        description=key_data.description,
        expires_at=expires_at,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        rate_limit_per_hour=key_data.rate_limit_per_hour
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    
    return ApiKeyResponse(
        id=str(db_key.id),
        name=db_key.name,
        description=db_key.description,
        created_at=db_key.created_at,
        expires_at=db_key.expires_at,
        is_active=db_key.is_active,
        is_revoked=db_key.is_revoked,
        rate_limit_per_minute=db_key.rate_limit_per_minute,
        rate_limit_per_hour=db_key.rate_limit_per_hour,
        key=plain_key
    )

@router.delete("/api-keys/{key_id}", summary="Revocar API Key")
async def revoke_api_key(
    key_id: str,
    account_id: str = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db_session)
):
    """Revoca una API Key"""
    if not account_id:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
        
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == uuid.UUID(key_id),
            ApiKey.account_id == uuid.UUID(account_id)
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key no encontrada")
        
    api_key.is_revoked = True
    await db.commit()
    
    return {"message": "API Key revocada exitosamente"}

# --- Dependency to authenticate using API Key or JWT ---

async def get_account_id_from_api_key(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db_session)
) -> str:
    """
    Obtiene el account_id desde:
    1. JWT token (Bearer <jwt>)
    2. API Key (Bearer sk-kaito-...)
    3. Internal API Key
    """
    # 1. Try JWT (if token doesn't start with sk-)
    if token and not token.startswith("sk-"):
        from utils.security import decode_access_token
        payload = decode_access_token(token)
        if payload:
            account_id = payload.get("sub")
            if account_id:
                return account_id
                
    # 2. Try API Key (token or query/header X-API-Key)
    api_key = None
    if token and token.startswith("sk-"):
        api_key = token
    else:
        api_key = request.headers.get("X-API-Key")
        
    if api_key:
        hashed = hash_api_key(api_key)
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.hashed_key == hashed,
                ApiKey.is_revoked == False,
                ApiKey.is_active == True
            )
        )
        db_key = result.scalar_one_or_none()
        if db_key:
            if db_key.expires_at and db_key.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="API Key expirada")
                
            db_key.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            return str(db_key.account_id)
            
    # 3. Try Internal API Key
    internal_key = request.headers.get("X-Internal-API-Key")
    if internal_key == settings.internal_api_key_for_bot:
        result = await db.execute(
            select(Account).where(
                Account.is_admin == True,
                Account.is_active == True
            )
        )
        admin = result.scalars().first()
        if admin:
            return str(admin.id)
            
        result = await db.execute(
            select(Account).where(
                Account.is_active == True
            )
        )
        first_user = result.scalars().first()
        if first_user:
            return str(first_user.id)
            
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication. Use JWT token or API Key.",
        headers={"WWW-Authenticate": "Bearer"}
    )

# --- OpenAI Compatibility Endpoints ---

async def openai_streaming_generator(llm, messages, model_name):
    """Generador para streaming OpenAI-compatible"""
    id = f"chatcmpl-{uuid.uuid4()}"
    created = int(time.time())
    
    try:
        async for chunk in llm.astream(messages):
            content = ""
            if hasattr(chunk, "content"):
                content = chunk.content
            elif isinstance(chunk, str):
                content = chunk
                
            if not content:
                continue
                
            delta = {"content": content}
            chunk_resp = {
                "id": id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": delta,
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_resp)}\n\n"
            
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error in OpenAI streaming: {e}", exc_info=True)
        yield f'data: {{"error": {{"message": "{str(e)}", "type": "internal_error"}}}}\n\n'
        yield "data: [DONE]\n\n"

@router.post("/v1/chat/completions", summary="OpenAI-compatible Chat Completions")
async def chat_completions(
    request: ChatCompletionRequest,
    account_id: str = Depends(get_account_id_from_api_key)
):
    """OpenAI-compatible chat completion endpoint"""
    logger.info(f"OpenAI-compatible request from {account_id} for model {request.model}")
    
    llm = await get_llm_for_user(account_id)
    if not llm:
        raise HTTPException(status_code=500, detail="Could not initialize LLM for user")
        
    langchain_messages = []
    has_system = any(m.role == "system" for m in request.messages)
    if not has_system:
        langchain_messages.append(("system", KAI_SYSTEM_PROMPT))
        
    for msg in request.messages:
        role = msg.role
        if role == "assistant":
            role = "ai"
        elif role == "user":
            role = "human"
        langchain_messages.append((role, msg.content))
        
    if request.stream:
        return StreamingResponse(
            openai_streaming_generator(llm, langchain_messages, request.model),
            media_type="text/event-stream"
        )
        
    try:
        try:
            response = await llm.ainvoke(langchain_messages)
        except Exception as primary_err:
            logger.warning(f"Primary LLM for account {account_id} failed ({primary_err}). Attempting fallback to default system LLM...")
            try:
                from langchain_community.chat_models import ChatLiteLLM
                fallback_model = settings.llm_model if settings.llm_model and "poolside" not in settings.llm_model else "gemini/gemini-2.0-flash"
                fallback_llm = ChatLiteLLM(model=fallback_model)
                response = await fallback_llm.ainvoke(langchain_messages)
            except Exception as fallback_err:
                logger.error(f"Fallback LLM failed: {fallback_err}")
                raise primary_err

        content = response.content if hasattr(response, "content") else str(response)
        
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content=content)
                )
            ],
            usage=ChatCompletionUsage()
        )
    except Exception as e:
        logger.error(f"Error in OpenAI chat completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/models", summary="OpenAI-compatible Models List")
async def list_models(account_id: Optional[str] = Depends(oauth2_scheme_optional)):
    """Lista de modelos compatibles con OpenAI"""
    models = []
    seen_ids = set()
    
    def add_model(model_id: str, owned_by: str = "kognito"):
        if model_id and model_id not in seen_ids:
            models.append({
                "id": model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": owned_by
            })
            seen_ids.add(model_id)
            
    if account_id:
        try:
            async with SessionLocal() as db:
                result = await db.execute(select(Account).where(Account.id == uuid.UUID(account_id)))
                account = result.scalars().first()
                if account:
                    if account.llm_model:
                        add_model(account.llm_model, owned_by="user-preference")
                    if account.fast_llm_model:
                        add_model(account.fast_llm_model, owned_by="user-preference")
        except Exception as e:
            logger.error(f"Error fetching user models: {e}")
            
    add_model(settings.llm_model, owned_by="system-default")
    add_model(settings.fast_llm_model, owned_by="system-default")
    add_model("kognito-agent", owned_by="kognito")
    
    return {"object": "list", "data": models}
