# api/auth.py

import logging
import uuid
import random
import json
import hmac
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status, Form, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, EmailStr
import httpx

from core.config import settings
from core.database import SessionLocal, Account, PlatformIdentity, VerificationCode
from core.repositories.account_repository import AccountRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.security import get_password_hash, verify_password, create_access_token, get_current_account_id, oauth2_scheme
from core.dependencies import get_db_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# get_db eliminado en favor de core.dependencies.get_db_session

api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False) # type: ignore

async def get_internal_api_key(
    x_internal_api_key: Optional[str] = Depends(api_key_header)
) -> str:
    """
    Dependencia para validar una clave API interna para comunicación entre servicios.
    Requiere que la clave 'X-Internal-API-Key' coincida con 'settings.internal_api_key_for_bot'.
    """
    if x_internal_api_key and x_internal_api_key == settings.internal_api_key_for_bot:
        return x_internal_api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Clave API Interna inválida o ausente."
    )

def _validate_telegram_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    """Valida los datos de inicialización de una Telegram WebApp."""
    if not settings.telegram_bot_token: return None
    try:
        decoded_data = unquote(init_data)
        parsed_data = parse_qs(decoded_data)
        if "hash" not in parsed_data: return None

        data_check_string_parts = []
        for key, value in sorted(parsed_data.items()):
            if key != "hash":
                data_check_string_parts.append(f"{key}={value[0]}")
        data_check_string = "\n".join(data_check_string_parts)

        secret_key = hmac.new("WebAppData".encode(), settings.telegram_bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calculated_hash, parsed_data["hash"][0]):
            user_str = parsed_data.get("user", [None])[0]
            if user_str:
                return json.loads(user_str)
        return None
    except Exception as e:
        logger.error(f"Error validando initData: {e}")
        return None

async def get_validated_user_id(initData: str = Form(...)) -> int:
    """Dependencia para obtener el ID de usuario de Telegram validado desde `initData`."""
    user_data = _validate_telegram_init_data(initData)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Datos de inicialización inválidos o ausentes.")
    return int(user_data["id"])

class RegisterRequest(BaseModel):
    """Define la estructura de datos para una solicitud de registro."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = None

class LoginRequest(BaseModel):
    """Define la estructura de datos para una solicitud de inicio de sesión."""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Define la estructura de datos para la respuesta del token de autenticación."""
    access_token: str
    token_type: str = "bearer"

class RegisterResponse(TokenResponse):
    """Define la estructura de datos para la respuesta de registro, incluyendo un mensaje."""
    message: str

class TelegramLoginRequest(BaseModel):
    """Define la estructura de datos para una solicitud de login de Telegram."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

# --- Endpoints de Email/Pass y Social Login ---
@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, summary="Registrar con email/pass")
async def register_user(request: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    """Registra una nueva cuenta de usuario con email y contraseña."""
    existing_account_result = await db.execute(select(Account).where(Account.email == request.email))
    if existing_account_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una cuenta con este correo electrónico.")

    new_account = Account(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        name=request.name or request.email.split('@')[0],
        username=request.name or request.email.split('@')[0] # Usar el nombre proporcionado o parte del email como username
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    access_token = create_access_token(data={"sub": str(new_account.id)})
    return RegisterResponse(access_token=access_token, message="¡Registro exitoso! Ya puedes iniciar sesión.")

@router.post("/auth/login", response_model=TokenResponse, summary="Iniciar sesión con email/pass")
async def login_for_access_token(request: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """Inicia sesión con email y contraseña y devuelve un token de acceso JWT."""
    account_result = await db.execute(select(Account).where(Account.email == request.email))
    account = account_result.scalars().first()
    if not account or not account.hashed_password or not verify_password(request.password, account.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos.")

    access_token = create_access_token(data={"sub": str(account.id)})
    return TokenResponse(access_token=access_token)

def verify_telegram_hash(data: TelegramLoginRequest, bot_token: str) -> bool:
    """Verifica el hash de los datos de login de Telegram (método Login Widget oficial)."""
    data_dict = data.dict(exclude={'hash'})
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()) if v is not None)
    # Para Telegram Login Widget oficial, la clave secreta es SHA256 del bot token
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_hash, data.hash)





@router.post("/auth/telegram/callback", response_model=TokenResponse, summary="Callback de Login Social de Telegram")
async def handle_telegram_login(login_data: TelegramLoginRequest, db: AsyncSession = Depends(get_db_session)):
    """Maneja el callback de autenticación social de Telegram, crea o vincula la cuenta y devuelve un token."""
    logger.warning("--- /api/auth/telegram/callback endpoint has been hit! ---")
    if not settings.telegram_bot_token: raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Autenticación de Telegram no configurada.")

    logger.warning(f"Incoming Telegram login data: {login_data}")
    data_dict = login_data.dict(exclude={'hash'})
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()) if v is not None)
    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    logger.warning(f"Calculated hash: {calculated_hash}, Provided hash: {login_data.hash}")

    if not verify_telegram_hash(login_data, settings.telegram_bot_token): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hash de Telegram inválido.")
    if time.time() - login_data.auth_date > 300: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Datos de autenticación expirados.")

    repo = AccountRepository(db)
    account, _ = await repo.get_or_create_account_from_platform_id(
        platform='telegram',
        platform_user_id=str(login_data.id),
        first_name=login_data.first_name,
        last_name=login_data.last_name,
        username=login_data.username
    )

    access_token = create_access_token(data={"sub": str(account.id)})
    return TokenResponse(access_token=access_token)

# --- Endpoints de Login con Código (Legado y Específico de Telegram) ---
class AuthRequestCode(BaseModel):
    """Define la estructura para solicitar un código de verificación."""
    identifier: str

class AuthVerifyCode(BaseModel):
    """Define la estructura para verificar un código y obtener un token."""
    identifier: str
    code: str

@router.options("/auth/request-code", summary=" Manejar preflight para solicitar código de verificación")
async def request_verification_code_options():
    """Responde a las solicitudes OPTIONS para el endpoint de solicitud de código."""
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.post("/auth/request-code", summary="Solicitar código de verificación")
async def request_verification_code(request_data: AuthRequestCode, db: AsyncSession = Depends(get_db_session)):
    """Busca al usuario, genera un código, lo guarda en la BD y lo envía a Telegram vía HTTP."""
    repo = AccountRepository(db)
    identity = await repo.find_telegram_identity(request_data.identifier)
    if not identity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se encontró usuario con identificador '{request_data.identifier}'.")
    
    telegram_id = int(identity.platform_user_id)
    account_id = identity.account_id

    # Genera el código y la fecha de expiración
    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Guarda el código en la base de datos primero
    new_code = VerificationCode(account_id=account_id, code=code, expires_at=expires_at)
    db.add(new_code)
    await db.commit()

    # Ahora, intenta enviar el mensaje haciendo una llamada HTTP al servicio del bot
    telegram_service_url = "http://kognito_telegram_client:9090/internal/send-message"
    message_payload = {
        "chat_id": telegram_id,
        "text": f"Tu código de acceso para Kognito es: <b>{code}</b>"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(telegram_service_url, json=message_payload, timeout=10)
            response.raise_for_status()  # Lanza un error para respuestas 4xx o 5xx
        
        logger.info(f"Petición de envío de código a {telegram_service_url} exitosa para chat_id {telegram_id}")
        return {"message": "Código de verificación enviado a tu chat de Telegram."}
    
    except httpx.RequestError as e:
        logger.error(f"Error de red al contactar el servicio de Telegram en '{telegram_service_url}': {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Servicio de mensajería no disponible.")
    except httpx.HTTPStatusError as e:
        logger.error(f"El servicio de Telegram devolvió un error {e.response.status_code}: {e.response.text}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fallo al enviar el mensaje a través del servicio interno.")

@router.post("/auth/verify-code", response_model=TokenResponse, summary="Verificar código")
async def verify_code_and_get_token(request_data: AuthVerifyCode, db: AsyncSession = Depends(get_db_session)):
    """Verifica un código contra la BD y devuelve un token si es válido."""
    repo = AccountRepository(db)
    identity = await repo.find_telegram_identity(request_data.identifier)
    if not identity:
        raise HTTPException(status_code=404, detail="No se pudo encontrar la cuenta asociada.")

    # Busca el código en la base de datos
    stmt = select(VerificationCode).where(
        VerificationCode.account_id == identity.account_id,
        VerificationCode.code == request_data.code,
        VerificationCode.expires_at > datetime.now(timezone.utc)
    ).order_by(VerificationCode.created_at.desc())
    
    result = await db.execute(stmt)
    valid_code = result.scalars().first()

    if not valid_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código incorrecto o expirado.")

    # Si el código es válido, lo eliminamos para que no se pueda reusar
    await db.delete(valid_code)
    await db.commit()

    # Creamos el token de acceso
    access_token = create_access_token(data={"sub": str(identity.account_id)})

    # DEBUG: Log token generation
    if settings.debug_mode:
        logger.warning(f"🔑 Token generado para account_id: {identity.account_id}")
        logger.warning(f"🔑 Token prefix: {access_token[:50]}...")

        # Verificar inmediatamente el token generado
        from utils.security import decode_access_token
        test_decode = decode_access_token(access_token)
        logger.warning(f"🔑 Verificación inmediata del token: {test_decode}")

    return TokenResponse(access_token=access_token)

@router.post("/auth/refresh-token", response_model=TokenResponse, summary="Refrescar token")
async def refresh_token(current_account_id: str = Depends(get_current_account_id)):
    """Genera un nuevo token para el usuario actual (útil cuando hay problemas de JWT)."""
    access_token = create_access_token(data={"sub": current_account_id})
    return TokenResponse(access_token=access_token)

@router.get("/auth/debug-token", summary="Debug token (solo en modo debug)")
async def debug_token(token: str = Depends(oauth2_scheme)):
    """Endpoint para debuggear problemas de JWT (solo disponible en modo debug)."""
    if not settings.debug_mode:
        raise HTTPException(status_code=404, detail="Endpoint no disponible")

    try:
        from utils.security import decode_access_token
        account_id = decode_access_token(token)
        return {
            "token_valid": account_id is not None,
            "account_id": account_id,
            "jwt_secret_key_prefix": settings.jwt_secret_key[:10] + "...",
            "debug_mode": settings.debug_mode
        }
    except Exception as e:
        return {
            "token_valid": False,
            "error": str(e),
            "jwt_secret_key_prefix": settings.jwt_secret_key[:10] + "...",
            "debug_mode": settings.debug_mode
        }

@router.post("/auth/emergency-token", response_model=TokenResponse, summary="Token de emergencia (solo debug)")
async def emergency_token(telegram_id: str, db: AsyncSession = Depends(get_db_session)):
    """Genera un token de emergencia para un usuario de Telegram (solo en modo debug)."""
    if not settings.debug_mode:
        raise HTTPException(status_code=404, detail="Endpoint no disponible")

    try:
        # Buscar la cuenta de Telegram
        repo = AccountRepository(db)
        account = await repo.get_account_by_telegram_id(int(telegram_id)) # Se necesita Account, no PlatformIdentity

        if not account:
            raise HTTPException(status_code=404, detail="Usuario de Telegram no encontrado")

        # Generar nuevo token
        access_token = create_access_token(data={"sub": str(account.id)})
        return TokenResponse(access_token=access_token)

    except Exception as e:
        logger.error(f"Error generando token de emergencia: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generando token")

@router.get("/auth/clear-tokens", summary="Limpiar tokens del frontend (solo debug)")
async def clear_frontend_tokens():
    """Endpoint para indicar al frontend que limpie sus tokens (solo en modo debug)."""
    if not settings.debug_mode:
        raise HTTPException(status_code=404, detail="Endpoint no disponible")

    return {
        "action": "clear_tokens",
        "message": "Limpia localStorage.removeItem('authToken') y localStorage.removeItem('access_token')",
        "jwt_secret_prefix": settings.jwt_secret_key[:10] + "...",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/get-system-prompt")
async def get_system_prompt(user_id: int = Depends(get_validated_user_id), db: AsyncSession = Depends(get_db_session)):
    """
    Obtiene el prompt de sistema personalizado para un usuario de Telegram.
    Protegido por `initData` de Telegram.
    """
    repo = AccountRepository(db)
    account = await repo.get_account_by_telegram_id(user_id)
    if not account:
        return {"prompt": settings.default_system_prompt, "is_custom": False}

    # Asumimos que profile está cargado o accedemos directamente al atributo.
    # El atributo custom_system_prompt ahora está directamente en el modelo Account
    prompt = account.custom_system_prompt if account.custom_system_prompt else settings.default_system_prompt
    is_custom = account.custom_system_prompt is not None

    return {"prompt": prompt, "is_custom": is_custom}

@router.post("/save-system-prompt")
async def save_system_prompt(user_id: int = Depends(get_validated_user_id), system_prompt: str = Form(""), db: AsyncSession = Depends(get_db_session)):
    """
    Guarda el prompt de sistema personalizado para un usuario de Telegram.
    Protegido por `initData` de Telegram.
    """
    repo = AccountRepository(db)
    account = await repo.get_account_by_telegram_id(user_id)
    if not account:
        raise HTTPException(status_code=404, detail="No se pudo encontrar la cuenta para guardar el prompt.")

    account.custom_system_prompt = system_prompt.strip() if system_prompt.strip() else None
    await db.commit()
    return {"message": "Prompt del sistema actualizado."}