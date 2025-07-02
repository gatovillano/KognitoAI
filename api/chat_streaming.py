# api/chat_streaming.py

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.security import get_current_account_id
from core.agent import create_and_run_agent_streaming

logger = logging.getLogger(__name__)
router = APIRouter()

class StreamChatRequest(BaseModel):
    thread_id: str
    account_id: str
    user_message: str
    image_base64: Optional[str] = None
    document_url: Optional[str] = None
    mode: Optional[str] = None

async def generate_chat_stream(request: StreamChatRequest) -> AsyncGenerator[str, None]:
    """Genera stream de respuestas del agente."""
    try:
        async for chunk in create_and_run_agent_streaming(
            account_id=request.account_id,
            thread_id=request.thread_id,
            user_message=request.user_message,
            image_base64=request.image_base64,
            document_url=request.document_url,
            mode=request.mode
        ):
            # Formato SSE
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        # Señal de finalización
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    except Exception as e:
        logger.error(f"Error en streaming: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@router.post("/chat/stream")
async def stream_chat(
    request: StreamChatRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """Endpoint de chat con streaming SSE."""
    if request.account_id != current_account_id:
        raise HTTPException(status_code=403, detail="Account ID mismatch")
    
    return StreamingResponse(
        generate_chat_stream(request),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )
