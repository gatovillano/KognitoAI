# api/users.py

import os
import logging
import uuid
from typing import List, Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, status, Query, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update

from core.database import SessionLocal, Account, PlatformIdentity, delete_accounts_by_ids, EmailAccount
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_db_session # Importar dependencia centralizada
from api.schemas import UserSettingsResponse, UserSettingsUpdateRequest, UserPasswordUpdateRequest, UserSecretRequest, UserSecretResponse
from utils.security import get_password_hash, verify_password
from core.repositories.secret_repository import SecretRepository
from utils.sanitization import sanitize_text

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

# --- Modelos de Respuesta para el Perfil de IA (Memoria Estructurada) ---
class AIUserProfileResponse(BaseModel):
    nombre: Optional[str] = None
    gustos: Optional[str] = None
    intereses: Optional[str] = None
    otros_datos: Optional[str] = None
    system_prompt: Optional[str] = None

    class Config:
        from_attributes = True

class AIUserProfileUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    gustos: Optional[str] = None
    intereses: Optional[str] = None
    otros_datos: Optional[str] = None
    system_prompt: Optional[str] = None


@router.get("/users/me/profile", response_model=AIUserProfileResponse, summary="Obtener perfil estructurado de IA del usuario actual")
async def get_user_ai_profile(
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Obtiene el perfil estructurado de IA del usuario actualmente autenticado.
    Este perfil es gestionado autónomamente por el agente pero puede ser visualizado/editado aquí.
    """
    from core.memory_manager import get_user_profile
    perfil = await get_user_profile(current_account_id)
    if not perfil:
        return AIUserProfileResponse()
    return AIUserProfileResponse(
        nombre=perfil.nombre,
        gustos=perfil.gustos,
        intereses=perfil.intereses,
        otros_datos=perfil.otros_datos,
        system_prompt=perfil.system_prompt
    )


@router.put("/users/me/profile", response_model=AIUserProfileResponse, summary="Actualizar perfil estructurado de IA del usuario actual")
async def update_user_ai_profile(
    profile_update: AIUserProfileUpdateRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Actualiza el perfil estructurado de IA del usuario actualmente autenticado.
    """
    from core.memory_manager import update_user_profile, get_user_profile
    
    # Sanitizar las entradas si están provistas para evitar código malicioso
    nombre_sanitized = sanitize_text(profile_update.nombre) if profile_update.nombre is not None else None
    gustos_sanitized = sanitize_text(profile_update.gustos) if profile_update.gustos is not None else None
    intereses_sanitized = sanitize_text(profile_update.intereses) if profile_update.intereses is not None else None
    otros_datos_sanitized = sanitize_text(profile_update.otros_datos) if profile_update.otros_datos is not None else None
    system_prompt_sanitized = sanitize_text(profile_update.system_prompt) if profile_update.system_prompt is not None else None

    await update_user_profile(
        account_id=current_account_id,
        nombre=nombre_sanitized,
        gustos=gustos_sanitized,
        intereses=intereses_sanitized,
        otros_datos=otros_datos_sanitized,
        system_prompt=system_prompt_sanitized
    )
    
    # Recuperar el perfil actualizado para la respuesta
    perfil = await get_user_profile(current_account_id)
    if not perfil:
        raise HTTPException(status_code=500, detail="Error al recuperar el perfil actualizado.")
        
    return AIUserProfileResponse(
        nombre=perfil.nombre,
        gustos=perfil.gustos,
        intereses=perfil.intereses,
        otros_datos=perfil.otros_datos,
        system_prompt=perfil.system_prompt
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
    
    # Obtener cuenta de correo principal por defecto
    stmt = (
        select(EmailAccount)
        .where(EmailAccount.account_id == account.id)
        .order_by(EmailAccount.is_default.desc(), EmailAccount.created_at.asc())
    )
    result = await db.execute(stmt)
    email_account = result.scalars().first()
    
    # Obtener contraseña de correo desde SecretRepository
    email_password_secret = None
    try:
        repo = SecretRepository(db)
        secret = await repo.get_secret(
            account_id=uuid.UUID(current_account_id),
            key_name="email_password"
        )
        email_password_secret = secret.value if secret else None
    except Exception as e:
        logger.warning(f"No se pudo obtener el secreto email_password: {e}")

    installed_exts = list(account.installed_extensions or [])
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for ext_name in ["kognito_chat", "fediverso", "email_management", "jitsi_meet", "gallery_selection_panel"]:
        if ext_name not in installed_exts:
            ext_path = os.path.join(project_root, "extensions", ext_name)
            if os.path.exists(ext_path):
                installed_exts.append(ext_name)

    return UserSettingsResponse(
        name=account.name,
        email=account.email,
        phone=account.phone,
        bio=account.bio,
        profiles_enabled=account.profiles_enabled,
        galleries_enabled=account.galleries_enabled,
        forms_enabled=account.forms_enabled,
        skills_enabled=account.skills_enabled,
        heartbeat_enabled=account.heartbeat_enabled,
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
        fast_llm_provider=account.fast_llm_provider,
        vision_llm_model=account.vision_llm_model,
        vision_llm_provider=account.vision_llm_provider,
        use_prompt_tooling=account.use_prompt_tooling,
        tts_provider=account.tts_provider,
        tts_model=account.tts_model,
        tts_voice=account.tts_voice,
        tts_speed=account.tts_speed,
        tts_region=account.tts_region,
        tts_api_base=account.tts_api_base,
        embedding_provider=account.embedding_provider,
        embedding_model=account.embedding_model,
        embedding_api_key_name=account.embedding_api_key_name,
        embedding_api_base=account.embedding_api_base,
        reranker_provider=account.reranker_provider,
        reranker_model=account.reranker_model,
        reranker_api_base=account.reranker_api_base,
        disabled_skills=account.disabled_skills,
        installed_extensions=installed_exts,
        ssh_host=account.ssh_host,
        ssh_port=account.ssh_port,
        ssh_user=account.ssh_user,
        local_base_path=account.local_base_path,
        cloud_storage_path=account.cloud_storage_path,
        email_provider=email_account.provider if email_account else None,
        email_imap_host=email_account.imap_host if email_account else None,
        email_imap_port=str(email_account.imap_port) if email_account and email_account.imap_port is not None else "993",
        email_smtp_host=email_account.smtp_host if email_account else None,
        email_smtp_port=str(email_account.smtp_port) if email_account and email_account.smtp_port is not None else "465",
        email_use_ssl=email_account.imap_use_ssl if email_account else True,
        email_username=email_account.username if email_account else None,
        email_password_secret=email_password_secret,
        custom_heartbeat_instructions=account.custom_heartbeat_instructions,
        custom_heartbeat_interval_minutes=account.custom_heartbeat_interval_minutes,
        custom_heartbeat_allowed_tools=account.custom_heartbeat_allowed_tools
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

    update_data = settings_update.dict(exclude_unset=True)
    email_password_secret = update_data.pop("email_password_secret", None)

    # Extraer campos de correo electrónico para manejarlos por separado
    email_fields_map = {
        "email_provider": "provider",
        "email_imap_host": "imap_host",
        "email_imap_port": "imap_port",
        "email_smtp_host": "smtp_host",
        "email_smtp_port": "smtp_port",
        "email_use_ssl": "imap_use_ssl",
        "email_username": "username"
    }
    
    email_updates = {}
    for req_field, db_field in email_fields_map.items():
        if req_field in update_data:
            email_updates[db_field] = update_data.pop(req_field)

    # Aplicar actualizaciones a la cuenta de usuario
    for field, value in update_data.items():
        if field in ['name', 'bio'] and isinstance(value, str):
            value = sanitize_text(value)
        setattr(account, field, value)

    # Obtener o crear cuenta de correo si hay actualizaciones de correo
    stmt = (
        select(EmailAccount)
        .where(EmailAccount.account_id == account.id)
        .order_by(EmailAccount.is_default.desc(), EmailAccount.created_at.asc())
    )
    result = await db.execute(stmt)
    email_account = result.scalars().first()
    
    if email_updates or email_password_secret is not None:
        if not email_account:
            # Crear cuenta de correo principal por defecto
            email_address = email_updates.get("username") or account.email or "user@example.com"
            email_account = EmailAccount(
                account_id=account.id,
                name="Correo Principal",
                email_address=email_address,
                is_default=True,
                is_active=True
            )
            db.add(email_account)
            
        # Aplicar actualizaciones
        for db_field, val in email_updates.items():
            if db_field in ["imap_port", "smtp_port"] and val is not None:
                try:
                    val = int(val)
                except ValueError:
                    pass
            setattr(email_account, db_field, val)
            
        # Si se actualizó la contraseña de correo, cifrarla y guardarla en el modelo
        if email_password_secret is not None:
            from utils.email_security import EmailSecurity
            security = EmailSecurity()
            email_account.encrypted_password = security.encrypt(email_password_secret)

    # Si se actualizó la contraseña de correo, guardarla también en SecretRepository por compatibilidad
    if email_password_secret is not None:
        repo = SecretRepository(db)
        await repo.set_secret(
            account_id=uuid.UUID(current_account_id),
            key_name="email_password",
            value=email_password_secret,
            description="Contraseña de correo IMAP/SMTP"
        )
        logger.info(f"Contraseña de correo actualizada para la cuenta {current_account_id}")
    
    await db.commit()
    await db.refresh(account)
    if email_account:
        await db.refresh(email_account)

    # Si se actualizaron campos de LLM, limpiar el cache de LLM del usuario
    llm_fields = {
        'llm_provider', 'llm_model', 'llm_temperature', 'llm_api_base',
        'fast_llm_model', 'fast_llm_provider',
        'vision_llm_model', 'vision_llm_provider'
    }
    if any(field in update_data for field in llm_fields):
        try:
            from core.llm_manager import clear_user_llm_cache
            clear_user_llm_cache(current_account_id)
        except Exception as e:
            logger.error(f"Error al limpiar cache de LLM tras actualización de configuración: {e}")

    # Si se actualizaron campos de heartbeat, reprogramar el job
    heartbeat_fields = ['custom_heartbeat_instructions', 'custom_heartbeat_interval_minutes', 'custom_heartbeat_allowed_tools']
    if any(field in update_data for field in heartbeat_fields):
        try:
            from utils.scheduled_tools_manager import schedule_custom_user_heartbeat
            await schedule_custom_user_heartbeat(
                account_id=str(account.id),
                interval_minutes=account.custom_heartbeat_interval_minutes or 60,
                allowed_tools=account.custom_heartbeat_allowed_tools
            )
            logger.info(f"Heartbeat personalizado reprogramado para la cuenta {current_account_id} tras actualización de configuración.")
        except Exception as e:
            logger.error(f"Error al reprogramar heartbeat tras actualización de configuración: {e}")

    installed_exts = list(account.installed_extensions or [])
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for ext_name in ["kognito_chat", "kognichat", "fediverso", "email_management", "jitsi_meet", "gallery_selection_panel"]:
        if ext_name not in installed_exts:
            ext_path = os.path.join(project_root, "extensions", ext_name)
            if os.path.exists(ext_path):
                installed_exts.append(ext_name)

    return UserSettingsResponse(
        name=account.name,
        email=account.email,
        phone=account.phone,
        bio=account.bio,
        profiles_enabled=account.profiles_enabled,
        galleries_enabled=account.galleries_enabled,
        forms_enabled=account.forms_enabled,
        skills_enabled=account.skills_enabled,
        heartbeat_enabled=account.heartbeat_enabled,
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
        fast_llm_provider=account.fast_llm_provider,
        vision_llm_model=account.vision_llm_model,
        vision_llm_provider=account.vision_llm_provider,
        use_prompt_tooling=account.use_prompt_tooling,
        tts_provider=account.tts_provider,
        tts_model=account.tts_model,
        tts_voice=account.tts_voice,
        tts_speed=account.tts_speed,
        tts_region=account.tts_region,
        tts_api_base=account.tts_api_base,
        embedding_provider=account.embedding_provider,
        embedding_model=account.embedding_model,
        embedding_api_key_name=account.embedding_api_key_name,
        embedding_api_base=account.embedding_api_base,
        reranker_provider=account.reranker_provider,
        reranker_model=account.reranker_model,
        reranker_api_base=account.reranker_api_base,
        disabled_skills=account.disabled_skills,
        installed_extensions=installed_exts,
        ssh_host=account.ssh_host,
        ssh_port=account.ssh_port,
        ssh_user=account.ssh_user,
        local_base_path=account.local_base_path,
        cloud_storage_path=account.cloud_storage_path,
        email_provider=email_account.provider if email_account else None,
        email_imap_host=email_account.imap_host if email_account else None,
        email_imap_port=str(email_account.imap_port) if email_account and email_account.imap_port is not None else "993",
        email_smtp_host=email_account.smtp_host if email_account else None,
        email_smtp_port=str(email_account.smtp_port) if email_account and email_account.smtp_port is not None else "465",
        email_use_ssl=email_account.imap_use_ssl if email_account else True,
        email_username=email_account.username if email_account else None,
        email_password_secret=email_password_secret,
        custom_heartbeat_instructions=account.custom_heartbeat_instructions,
        custom_heartbeat_interval_minutes=account.custom_heartbeat_interval_minutes,
        custom_heartbeat_allowed_tools=account.custom_heartbeat_allowed_tools
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
    logger.info(f"Guardando secreto '{secret_req.key_name}' para la cuenta {current_account_id}")
    repo = SecretRepository(db)
    secret_obj = await repo.set_secret(
        account_id=uuid.UUID(current_account_id),
        key_name=secret_req.key_name,
        value=secret_req.value,
        description=secret_req.description
    )
    
    masked = f"{secret_req.value[:8]}...{secret_req.value[-4:]}" if len(secret_req.value) > 12 else "****"
    
    # Limpiar caché de LLM ya que una API key asociada pudo cambiar
    try:
        from core.llm_manager import clear_user_llm_cache
        clear_user_llm_cache(current_account_id)
    except Exception as e:
        logger.error(f"Error al limpiar cache de LLM tras actualizar secreto: {e}")

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

    # Limpiar caché de LLM ya que una API key asociada fue eliminada
    try:
        from core.llm_manager import clear_user_llm_cache
        clear_user_llm_cache(current_account_id)
    except Exception as e:
        logger.error(f"Error al limpiar cache de LLM tras eliminar secreto: {e}")

    return {"message": f"Secreto '{key_name}' eliminado correctamente."}


# --- Endpoints de Administración de Usuarios (Solo para Admins) ---
@router.put("/admin/users/{user_id}", summary="Actualizar privilegios de administrador (solo admin)")
async def update_user_admin_status(
    user_id: str,
    is_admin: bool = Body(..., embed=True),
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Sube o baja la categoría de un usuario a administrador. Requiere privilegios de administrador.
    """
    logger.info(f"Admin {admin_account.id} cambiando is_admin a {is_admin} para el usuario {user_id}")
    
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de usuario inválido.")

    # Prevenir que el admin se quite a sí mismo el permiso si es el único o por seguridad
    # (Opcional: podrías lanzar un error si intenta quitarse el admin a sí mismo)
    
    user = await db.get(Account, target_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    user.is_admin = is_admin
    await db.commit()
    await db.refresh(user)
    
    return {"message": f"Estado de administrador actualizado para {user.name or user_id}."}

@router.get("/admin/users", response_model=List[UserProfileResponse], summary="Listar todos los usuarios (solo admin)")
async def list_all_users(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todos los usuarios registrados en el sistema. Requiere privilegios de administrador.
    """
    result = await db.execute(select(Account))
    accounts = result.scalars().all()
    
    response = []
    for account in accounts:
        response.append(UserProfileResponse(
            id=str(account.id),
            account_id=str(account.id),
            name=account.name,
            email=account.email,
            username=account.username,
            is_admin=bool(account.is_admin),
            has_password=bool(account.hashed_password)
        ))
    return response
