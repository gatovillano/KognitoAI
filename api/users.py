# api/users.py

import logging
import uuid
from typing import List, Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from core.database import SessionLocal, Account, PlatformIdentity, delete_accounts_by_ids
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:  # type: ignore
        try:
            yield session
        finally:
            await session.close()

# Dependencia para verificar si el usuario es administrador
async def get_current_admin_account(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)) -> Account:
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

    class Config:
        from_attributes = True  # Habilita compatibilidad con ORM de SQLAlchemy

@router.get("/users/me", response_model=UserProfileResponse, summary="Obtener perfil del usuario actual (protegido)")
async def read_users_me(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
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
        is_admin=bool(account.is_admin)  # type: ignore
    )

# --- Endpoints de Administración de Usuarios (Solo para Admins) ---
@router.get("/admin/users", response_model=List[UserProfileResponse], summary="Listar todos los usuarios (solo admin)")
async def list_all_users(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db)
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
async def list_all_users_public(db: AsyncSession = Depends(get_db)):
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
    db: AsyncSession = Depends(get_db)
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
async def search_user(identifier: str = Query(...), current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
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
