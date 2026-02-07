# api/users.py

import logging
import uuid
from typing import List, Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, status, Query, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update

from core.database import SessionLocal, Account, PlatformIdentity, delete_accounts_by_ids
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_db_session # Importar dependencia centralizada
from api.schemas import UserSettingsResponse, UserSettingsUpdateRequest, UserPasswordUpdateRequest, UserSecretRequest, UserSecretResponse
from utils.security import get_password_hash, verify_password
from core.repositories.secret_repository import SecretRepository

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# get_db eliminado en favor de core.dependencies.get_db_session

# Dependencia para verificar si el usuario es administrador
async def get_current_admin_account(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)) -> Account:
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account or not bool(account.is_admin):  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador.")
    return account

# --- Modelos de Respuesta para el Perfil de Usuario ---
class UserProfileResponse(BaseModel):
    """Define la estructura de datos para la respuesta del perfil de usuario."""
    id: str
    account_id: str # Añadido account_id
    name: Optional[str]
    email: Optional[EmailStr]
    username: Optional[str]
    telegram_id: Optional[int] = None  # Añadimos para el frontend
    is_admin: bool = False  # Añadimos el campo is_admin
    has_password: bool = False # Indica si el usuario tiene contraseña establecida

    class Config:
        from_attributes = True  # Habilita compatibilidad con ORM de SQLAlchemy

@router.get("/users/me", response_model=UserProfileResponse, summary="Obtener perfil del usuario actual (protegido)")
async def read_users_me(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    """
    Devuelve los datos públicos del usuario actualmente autenticado a través del token JWT.
    """
    account = await db.get(Account, uuid.UUID(current_account_id))  # Asegúrate de que el ID sea un UUID
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Intentar obtener el telegram_id si existe
    telegram_identity = await db.execute(
        select(PlatformIdentity).where(
            PlatformIdentity.account_id == uuid.UUID(current_account_id),
            PlatformIdentity.platform == 'telegram'
        )
    )
    telegram_id = None
    identity_obj = telegram_identity.scalars().first()
    if identity_obj is not None and getattr(identity_obj, 'platform_user_id', None):
        try:
            telegram_id = int(getattr(identity_obj, 'platform_user_id', ''))
        except ValueError:
            logger.warning(f"platform_user_id '{identity_obj.platform_user_id}' no es un entero para telegram_id.")

    return UserProfileResponse(
        id=str(account.id),
        account_id=str(account.id), # Asignamos el account_id
        name=account.name,  # type: ignore
        email=account.email,  # type: ignore
        username=account.username,  # type: ignore
        telegram_id=telegram_id,
        is_admin=bool(account.is_admin),  # type: ignore
        has_password=bool(account.hashed_password)
    )


# --- Endpoints de Configuración de Usuario ---
@router.get("/users/me/settings", response_model=UserSettingsResponse, summary="Obtener configuración del usuario actual")
async def get_user_settings(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    """
    Obtiene la configuración detallada del usuario actualmente autenticado.
    """
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    return UserSettingsResponse(
        name=account.name,
        email=account.email,
        phone=account.phone,
        bio=account.bio,
        profiles_enabled=account.profiles_enabled,
        galleries_enabled=account.galleries_enabled,
        forms_enabled=account.forms_enabled,
        theme=account.theme,
        notifications_email=account.notifications_email,
        notifications_push=account.notifications_push,
        language=account.language,
        privacy_data_sharing=account.privacy_data_sharing,
        llm_provider=account.llm_provider,
        llm_model=account.llm_model,
        llm_temperature=account.llm_temperature,
        llm_api_base=account.llm_api_base,
        fast_llm_model=account.fast_llm_model,
        vision_llm_model=account.vision_llm_model,
        use_prompt_tooling=account.use_prompt_tooling
    )

@router.put("/users/me/settings", response_model=UserSettingsResponse, summary="Actualizar configuración del usuario actual")
async def update_user_settings(
    settings_update: UserSettingsUpdateRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza la configuración del usuario actualmente autenticado.
    """
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Aplicar actualizaciones
    for field, value in settings_update.dict(exclude_unset=True).items():
        setattr(account, field, value)
    
    await db.commit()
    await db.refresh(account)

    return UserSettingsResponse(
        name=account.name,
        email=account.email,
        phone=account.phone,
        bio=account.bio,
        profiles_enabled=account.profiles_enabled,
        galleries_enabled=account.galleries_enabled,
        forms_enabled=account.forms_enabled,
        theme=account.theme,
        notifications_email=account.notifications_email,
        notifications_push=account.notifications_push,
        language=account.language,
        privacy_data_sharing=account.privacy_data_sharing,
        llm_provider=account.llm_provider,
        llm_model=account.llm_model,
        llm_temperature=account.llm_temperature,
        llm_api_base=account.llm_api_base,
        fast_llm_model=account.fast_llm_model,
        vision_llm_model=account.vision_llm_model,
        use_prompt_tooling=account.use_prompt_tooling
    )

@router.put("/users/me/password", summary="Actualizar contraseña del usuario")
async def update_user_password(
    password_update: UserPasswordUpdateRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Permite al usuario establecer o cambiar su contraseña.
    Si el usuario ya tiene contraseña, debe proporcionar la actual.
    """
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Si el usuario ya tiene contraseña, verificar la actual
    if account.hashed_password:
        if not password_update.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes proporcionar tu contraseña actual.")
        if not verify_password(password_update.current_password, account.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual es incorrecta.")
    
    # Establecer la nueva contraseña
    account.hashed_password = get_password_hash(password_update.new_password)
    
    await db.commit()
    
    return {"message": "Contraseña actualizada correctamente."}
    
# --- Endpoints para la Gestión de Secretos (API Keys) ---

@router.get("/users/me/secrets", response_model=List[UserSecretResponse], summary="Listar secretos del usuario actual")
async def list_user_secrets(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista los nombres de los secretos (API Keys) que el usuario ha guardado.
    No devuelve los valores reales por seguridad.
    """
    from core.database import UserSecret
    stmt = select(UserSecret).where(UserSecret.account_id == uuid.UUID(current_account_id))
    result = await db.execute(stmt)
    secrets = result.scalars().all()
    
    # Necesitamos desencriptar para mostrar un fragmento (máscara)
    repo = SecretRepository(db)
    response = []
    for s in secrets:
        decrypted = await repo.get_decrypted_secret(uuid.UUID(current_account_id), s.key_name)
        masked = f"{decrypted[:8]}...{decrypted[-4:]}" if decrypted and len(decrypted) > 12 else "****"
        response.append(UserSecretResponse(
            key_name=s.key_name,
            description=s.description,
            masked_value=masked,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        ))
    return response

@router.post("/users/me/secrets", response_model=UserSecretResponse, summary="Crear o actualizar un secreto")
async def set_user_secret(
    secret_req: UserSecretRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Guarda o actualiza un secreto (API Key) cifrado para el usuario.
    """
    repo = SecretRepository(db)
    secret_obj = await repo.set_secret(
        account_id=uuid.UUID(current_account_id),
        key_name=secret_req.key_name,
        value=secret_req.value,
        description=secret_req.description
    )
    
    masked = f"{secret_req.value[:8]}...{secret_req.value[-4:]}" if len(secret_req.value) > 12 else "****"
    
    return UserSecretResponse(
        key_name=secret_obj.key_name,
        description=secret_obj.description,
        masked_value=masked,
        created_at=secret_obj.created_at.isoformat(),
        updated_at=secret_obj.updated_at.isoformat()
    )

@router.delete("/users/me/secrets/{key_name}", summary="Eliminar un secreto")
async def delete_user_secret(
    key_name: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina un secreto guardado.
    """
    repo = SecretRepository(db)
    deleted = await repo.delete_secret(uuid.UUID(current_account_id), key_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Secreto no encontrado.")
    return {"message": f"Secreto '{key_name}' eliminado correctamente."}


# --- Endpoints de Administración de Usuarios (Solo para Admins) ---
@router.get("/admin/users", response_model=List[UserProfileResponse], summary="Listar todos los usuarios (solo admin)")
async def list_all_users(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todos los usuarios registrados en el sistema. Requiere privilegios de administrador.
    """
    logger.info(f"Admin {admin_account.id} listando todos los usuarios.")
    stmt = select(Account).order_by(Account.created_at.desc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    
    users_data = []
    for account in accounts:
        telegram_identity = await db.execute(
            select(PlatformIdentity).where(
                PlatformIdentity.account_id == account.id,
                PlatformIdentity.platform == 'telegram'
            )
        )
        telegram_id = None
        identity_obj = telegram_identity.scalars().first()
        if identity_obj is not None and getattr(identity_obj, 'platform_user_id', None):
            try:
                telegram_id = int(getattr(identity_obj, 'platform_user_id', ''))
            except ValueError:
                pass  # No es un ID numérico válido

        users_data.append(UserProfileResponse(
            id=str(account.id),
            account_id=str(account.id),
            name=account.name,  # type: ignore
            email=account.email,  # type: ignore
            username=account.username,  # type: ignore
            telegram_id=telegram_id,
            is_admin=bool(account.is_admin)  # type: ignore
        ))
    return users_data

@router.get("/users", response_model=List[UserProfileResponse], summary="Listar todos los usuarios (público)")
async def list_all_users_public(db: AsyncSession = Depends(get_db_session)):
    """
    Lista todos los usuarios registrados en el sistema.
    """
    logger.info("Listando todos los usuarios para acceso público.")
    stmt = select(Account).order_by(Account.created_at.desc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    
    users_data = []
    for account in accounts:
        telegram_identity = await db.execute(
            select(PlatformIdentity).where(
                PlatformIdentity.account_id == account.id,
                PlatformIdentity.platform == 'telegram'
            )
        )
        telegram_id = None
        identity_obj = telegram_identity.scalars().first()
        if identity_obj is not None and getattr(identity_obj, 'platform_user_id', None):
            try:
                telegram_id = int(getattr(identity_obj, 'platform_user_id', ''))
            except ValueError:
                pass  # No es un ID numérico válido

        users_data.append(UserProfileResponse(
            id=str(account.id),
            account_id=str(account.id),
            name=account.name,  # type: ignore
            email=account.email,  # type: ignore
            username=account.username,  # type: ignore
            telegram_id=telegram_id,
            is_admin=bool(account.is_admin)  # type: ignore
        ))
    return users_data

class DeleteUsersRequest(BaseModel):
    """Define la estructura de datos para eliminar usuarios."""
    account_ids: List[str]  # Lista de UUIDs de cuentas a eliminar

@router.post("/admin/users/delete", summary="Eliminar usuarios por ID (solo admin)")
async def delete_users_by_ids_endpoint(
    request: DeleteUsersRequest,
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina una o varias cuentas de usuario por sus IDs. Requiere privilegios de administrador.
    IMPORTANTE: Esta acción es irreversible.
    """
    logger.warning(f"Admin {admin_account.id} solicitando eliminación de cuentas: {request.account_ids}")
    
    # Convertir los IDs de string a UUID
    uuids_to_delete = [uuid.UUID(aid) for aid in request.account_ids]

    # Prevenir la eliminación de la propia cuenta del administrador si está en la lista
    if admin_account.id in uuids_to_delete:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes eliminar tu propia cuenta de administrador.")
    
    # Llamar a la función de la base de datos para eliminar las cuentas
    try:
        deleted_count = await delete_accounts_by_ids(db, uuids_to_delete)
        return {"message": f"Se eliminaron {deleted_count} cuentas correctamente."}
    except Exception as e:
        logger.error(f"Error al intentar eliminar cuentas por admin {admin_account.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al eliminar cuentas.")

@router.get("/users/search", summary="Buscar usuario por email o nombre de usuario")
async def search_user(identifier: str = Query(...), current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    """
    Busca un usuario por email o nombre de usuario de Telegram. Devuelve el account_id si se encuentra.
    Solo accesible para usuarios autenticados.
    """
    logger.info(f"Buscando usuario con identificador: {identifier} por la cuenta: {current_account_id}")
    
    # Buscar por email
    account_by_email = await db.scalar(select(Account).where(Account.email == identifier))
    if account_by_email:
        return {"account_id": str(account_by_email.id)}
    
    # Buscar por username
    account_by_username = await db.scalar(select(Account).where(Account.username == identifier))
    if account_by_username:
        return {"account_id": str(account_by_username.id)}
    
    # Buscar por platform_user_id en PlatformIdentity si es un ID de Telegram
    try:
        telegram_id = int(identifier)
        identity = await db.scalar(select(PlatformIdentity).where(
            PlatformIdentity.platform == 'telegram',
            PlatformIdentity.platform_user_id == str(telegram_id)
        ))
        if identity:
            return {"account_id": str(identity.account_id)}
    except ValueError:
        pass  # No es un ID numérico, ignorar esta búsqueda
    
    raise HTTPException(status_code=404, detail="Usuario no encontrado con el identificador proporcionado.")
