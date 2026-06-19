# api/admin_llm.py

import logging
import uuid
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import Account, SystemSettings
from core.dependencies import get_db_session
from utils.security import get_current_account_id
from core.repositories.secret_repository import SecretRepository
from core.llm_manager import (
    initialize_llms,
    SYSTEM_ACCOUNT_ID,
    ensure_system_account
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to verify admin
async def get_current_admin_account(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
) -> Account:
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account or not bool(account.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador."
        )
    return account

# Schemas
class GlobalLLMSettingsResponse(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = 0.7
    llm_api_base: Optional[str] = None
    fast_llm_model: Optional[str] = None
    fast_llm_provider: Optional[str] = None
    vision_llm_model: Optional[str] = None
    vision_llm_provider: Optional[str] = None
    use_prompt_tooling: bool = False

class GlobalLLMSettingsUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_api_base: Optional[str] = None
    fast_llm_model: Optional[str] = None
    fast_llm_provider: Optional[str] = None
    vision_llm_model: Optional[str] = None
    vision_llm_provider: Optional[str] = None
    use_prompt_tooling: Optional[bool] = None

class GlobalSecretRequest(BaseModel):
    key_name: str = Field(..., pattern=r"^[A-Z0-9_]+$")
    value: str
    description: Optional[str] = None

class GlobalSecretResponse(BaseModel):
    key_name: str
    description: Optional[str]
    masked_value: str
    created_at: str
    updated_at: str

# Endpoints
@router.get("/admin/llm-settings", response_model=GlobalLLMSettingsResponse, summary="Obtener configuración global de LLM")
async def get_global_llm_settings_endpoint(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == "global_llm_settings"))
    row = result.scalar_one_or_none()
    if row and row.value:
        try:
            data = json.loads(row.value)
            return GlobalLLMSettingsResponse(**data)
        except Exception as e:
            logger.error(f"Error parsing global_llm_settings: {e}")
            
    return GlobalLLMSettingsResponse()

@router.put("/admin/llm-settings", response_model=GlobalLLMSettingsResponse, summary="Actualizar configuración global de LLM")
async def update_global_llm_settings_endpoint(
    request: GlobalLLMSettingsUpdateRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    # 1. Obtener configuración existente
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == "global_llm_settings"))
    row = result.scalar_one_or_none()
    
    current_data = {}
    if row and row.value:
        try:
            current_data = json.loads(row.value)
        except Exception:
            pass
            
    # 2. Mezclar actualizaciones
    update_data = request.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        current_data[k] = v
        
    # 3. Guardar en DB
    serialized = json.dumps(current_data)
    if not row:
        row = SystemSettings(key="global_llm_settings", value=serialized)
        db.add(row)
    else:
        row.value = serialized
        
    await db.commit()
    
    # 4. Reinicializar LLMs globales
    try:
        await initialize_llms()
        logger.info("LLMs globales reinicializados tras actualizar configuración.")
    except Exception as e:
        logger.error(f"Error al reinicializar LLMs globales: {e}")
        
    return GlobalLLMSettingsResponse(**current_data)

@router.get("/admin/llm-settings/secrets", response_model=List[GlobalSecretResponse], summary="Listar secretos globales")
async def list_global_secrets_endpoint(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    from core.database import UserSecret
    await ensure_system_account(db)
    
    stmt = select(UserSecret).where(UserSecret.account_id == SYSTEM_ACCOUNT_ID)
    result = await db.execute(stmt)
    secrets = result.scalars().all()
    
    repo = SecretRepository(db)
    response = []
    for s in secrets:
        decrypted = await repo.get_decrypted_secret(SYSTEM_ACCOUNT_ID, s.key_name)
        masked = f"{decrypted[:8]}...{decrypted[-4:]}" if decrypted and len(decrypted) > 12 else "****"
        response.append(GlobalSecretResponse(
            key_name=s.key_name,
            description=s.description,
            masked_value=masked,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        ))
    return response

@router.post("/admin/llm-settings/secrets", response_model=GlobalSecretResponse, summary="Crear o actualizar un secreto global")
async def set_global_secret_endpoint(
    secret_req: GlobalSecretRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    await ensure_system_account(db)
    repo = SecretRepository(db)
    
    secret_obj = await repo.set_secret(
        account_id=SYSTEM_ACCOUNT_ID,
        key_name=secret_req.key_name,
        value=secret_req.value,
        description=secret_req.description
    )
    
    masked = f"{secret_req.value[:8]}...{secret_req.value[-4:]}" if len(secret_req.value) > 12 else "****"
    
    # Reinicializar LLMs globales para usar la nueva clave
    try:
        await initialize_llms()
        logger.info("LLMs globales reinicializados tras actualizar secreto.")
    except Exception as e:
        logger.error(f"Error al reinicializar LLMs globales: {e}")
        
    return GlobalSecretResponse(
        key_name=secret_obj.key_name,
        description=secret_obj.description,
        masked_value=masked,
        created_at=secret_obj.created_at.isoformat(),
        updated_at=secret_obj.updated_at.isoformat()
    )

@router.delete("/admin/llm-settings/secrets/{key_name}", summary="Eliminar un secreto global")
async def delete_global_secret_endpoint(
    key_name: str,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    await ensure_system_account(db)
    repo = SecretRepository(db)
    
    deleted = await repo.delete_secret(SYSTEM_ACCOUNT_ID, key_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Secreto no encontrado.")
        
    # Reinicializar LLMs globales
    try:
        await initialize_llms()
        logger.info("LLMs globales reinicializados tras eliminar secreto.")
    except Exception as e:
        logger.error(f"Error al reinicializar LLMs globales: {e}")
        
    return {"message": f"Secreto global '{key_name}' eliminado correctamente."}
