# api/chat.py

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, Form
from fastapi import BackgroundTasks
from pydantic import BaseModel

from core.agent import create_and_run_agent
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncSession:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# --- Modelos para el Chat ---
class ChatRequest(BaseModel):
    """Define la estructura de datos para una solicitud de mensaje de chat al agente."""
    thread_id: str
    account_id: str
    telegram_id: Optional[int] = None  # Hacemos telegram_id opcional
    user_message: str
    image_base64: Optional[str] = None
    mode: Optional[str] = None

class ChatResponse(BaseModel):
    """Define la estructura de datos para la respuesta del agente de chat."""
    response_text: str

@router.post("/chat", response_model=ChatResponse, summary="Procesar Mensaje de Chat")
async def handle_chat(request: ChatRequest, background_tasks: BackgroundTasks, current_account_id: str = Depends(get_current_account_id)) -> ChatResponse:
    """
    Endpoint principal para procesar mensajes de chat con el agente de IA.
    Requiere autenticación JWT.
    """
    try:
        account_id_uuid = uuid.UUID(request.account_id)
        if str(account_id_uuid) != current_account_id:  # Validar que el account_id coincida con el del token
            logger.error(f"El account_id proporcionado ({request.account_id}) no coincide con el token de autenticación ({current_account_id})")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El account_id proporcionado no coincide con el token de autenticación.")
    except ValueError:
        logger.error(f"El account_id proporcionado no es un UUID válido: {request.account_id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El account_id proporcionado no tiene un formato válido.")

    logger.info(f"Petición de chat recibida de la cuenta: {request.account_id} con modo: {request.mode}")
    try:
        final_response_text = await create_and_run_agent(
            account_id=request.account_id,
            thread_id=request.thread_id,
            telegram_id=request.telegram_id,  # telegram_id ahora es Optional[int]
            user_message=request.user_message,
            image_base64=request.image_base64,
            mode=request.mode,
            background_tasks=background_tasks
        )
        return ChatResponse(response_text=final_response_text)
    except Exception as e:
        logger.error(f"Error al procesar petición de la cuenta {request.account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error interno al procesar tu solicitud.")
