# api/openai.py

import logging
import time
import uuid
import json
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.llm_manager import get_main_llm, get_llm_for_user
from core.prompts import KAI_SYSTEM_PROMPT
from utils.security import get_current_account_id, oauth2_scheme_optional

logger = logging.getLogger(__name__)

router = APIRouter()

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

# --- Helper for Streaming ---

async def openai_streaming_generator(llm, messages, model_name):
    id = f"chatcmpl-{uuid.uuid4()}"
    created = int(time.time())
    
    try:
        async for chunk in llm.astream(messages):
            # LiteLLM/LangChain chunk processing
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
        
        # End of stream
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error in OpenAI streaming: {e}", exc_info=True)
        yield f'data: {{"error": {{"message": "{str(e)}", "type": "internal_error"}}}}\n\n'
        yield "data: [DONE]\n\n"

from core.config import settings
from sqlalchemy import select
from core.database import SessionLocal, Account

async def get_openai_account_id(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> str:
    """
    Custom dependency for OpenAI API authentication.
    Supports:
    1. JWT (Bearer token)
    2. Internal API Key (X-Internal-API-Key or Bearer <internal_key>)
    """
    # 1. Try JWT first
    if token:
        from utils.security import decode_access_token
        payload = decode_access_token(token)
        if payload:
            account_id = payload.get("sub")
            if account_id:
                return account_id
        
    # 2. Try Header X-Internal-API-Key
    internal_key = request.headers.get("X-Internal-API-Key")
    if not internal_key and token == settings.internal_api_key_for_bot:
        internal_key = token

    if internal_key and internal_key == settings.internal_api_key_for_bot:
        async with SessionLocal() as db:
            # First try to find an admin
            res = await db.execute(select(Account).where(Account.is_admin == True, Account.is_active == True))
            admin = res.scalars().first()
            if admin:
                return str(admin.id)
            
            # Fallback to the first active account if no admin exists yet
            res = await db.execute(select(Account).where(Account.is_active == True))
            first_user = res.scalars().first()
            if first_user:
                logger.info(f"Internal Key used but no admin found. Falling back to user {first_user.id}")
                return str(first_user.id)

    # 3. If no auth found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication. Use your JWT token or Internal API Key.",
        headers={"WWW-Authenticate": "Bearer"},
    )

@router.post("/v1/chat/completions", summary="OpenAI-compatible Chat Completions")
async def chat_completions(
    request: ChatCompletionRequest,
    account_id: str = Depends(get_openai_account_id)
):
    """
    OpenAI-compatible chat completion endpoint.
    Uses the user's default model and the KAI system prompt if no system message is provided.
    """
    logger.info(f"OpenAI-compatible request from {account_id} for model {request.model}")

    # 1. Get LLM for user
    llm = await get_llm_for_user(account_id)
    if not llm:
        raise HTTPException(status_code=500, detail="Could not initialize LLM for user")

    # 2. Prepare messages
    langchain_messages = []
    
    # Check if a system message exists
    has_system = any(m.role == "system" for m in request.messages)
    
    if not has_system:
        # Inject KAI system prompt as default
        langchain_messages.append(("system", KAI_SYSTEM_PROMPT))
    
    for msg in request.messages:
        role = msg.role
        if role == "assistant":
            role = "ai"
        elif role == "user":
            role = "human"
        
        langchain_messages.append((role, msg.content))

    # 3. Handle Streaming
    if request.stream:
        return StreamingResponse(
            openai_streaming_generator(llm, langchain_messages, request.model),
            media_type="text/event-stream"
        )

    # 4. Handle Non-streaming
    try:
        response = await llm.ainvoke(langchain_messages)
        content = response.content if hasattr(response, "content") else str(response)

        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content=content)
                )
            ],
            usage=ChatCompletionUsage(
                # We don't have exact token counts easily from LiteLLM/LangChain without extra config
                # but we can return zeros or estimates. OpenAI clients often expect these fields.
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
        )
    except Exception as e:
        logger.error(f"Error in OpenAI chat completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def get_optional_openai_account_id(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[str]:
    """Optional version of get_openai_account_id"""
    try:
        return await get_openai_account_id(request, token)
    except HTTPException:
        return None

@router.get("/v1/models", summary="OpenAI-compatible Models List")
async def list_models(account_id: Optional[str] = Depends(get_optional_openai_account_id)):
    """
    OpenAI-compatible models list.
    Returns the models configured in Kognito, prioritizing the user's preference if authenticated.
    """
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

    # 1. Add User's specific model if authenticated
    if account_id:
        try:
            async with SessionLocal() as db:
                account = await db.get(Account, uuid.UUID(account_id))
                if account:
                    if account.llm_model:
                        add_model(account.llm_model, owned_by="user-preference")
                    if account.fast_llm_model:
                        add_model(account.fast_llm_model, owned_by="user-preference")
        except Exception as e:
            logger.error(f"Error fetching user models for list_models: {e}")

    # 2. Add System defaults from .env
    add_model(settings.llm_model, owned_by="system-default")
    add_model(settings.fast_llm_model, owned_by="system-default")
    
    # 3. Add Virtual Agent Model
    add_model("kognito-agent", owned_by="kognito")

    return {
        "object": "list",
        "data": models
    }
