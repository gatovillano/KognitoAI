import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.dependencies import get_db_session
from core.repositories.secret_repository import SecretRepository
from utils.security import get_current_account_id

logger = logging.getLogger(__name__)

router = APIRouter()

class NotionCredentialsRequest(BaseModel):
    api_key: str
    description: Optional[str] = "Clave de API de Notion"

@router.post("/credentials")
async def save_notion_credentials(
    request: NotionCredentialsRequest,
    db: AsyncSession = Depends(get_db_session),
    account_id: str = Depends(get_current_account_id)
):
    """
    Guarda la API Key de Notion del usuario de forma cifrada.
    """
    try:
        secret_repo = SecretRepository(db)
        await secret_repo.set_secret(
            account_id=uuid.UUID(account_id),
            key_name="NOTION_API_KEY",
            value=request.api_key,
            description=request.description
        )
        return {"message": "Credenciales de Notion guardadas correctamente."}
    except Exception as e:
        logger.error(f"Error al guardar credenciales de Notion para {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar las credenciales: {str(e)}"
        )

@router.get("/status")
async def get_notion_status(
    db: AsyncSession = Depends(get_db_session),
    account_id: str = Depends(get_current_account_id)
):
    """
    Verifica si el usuario tiene configurado Notion.
    """
    secret_repo = SecretRepository(db)
    secret = await secret_repo.get_secret_entry(uuid.UUID(account_id), "NOTION_API_KEY")
    return {
        "is_configured": secret is not None,
        "updated_at": secret.updated_at if secret else None
    }

@router.delete("/credentials")
async def delete_notion_credentials(
    db: AsyncSession = Depends(get_db_session),
    account_id: str = Depends(get_current_account_id)
):
    """
    Elimina las credenciales de Notion del usuario.
    """
    secret_repo = SecretRepository(db)
    deleted = await secret_repo.delete_secret(uuid.UUID(account_id), "NOTION_API_KEY")
    if not deleted:
        raise HTTPException(status_code=404, detail="No se encontraron credenciales de Notion para eliminar.")
    return {"message": "Credenciales de Notion eliminadas."}
