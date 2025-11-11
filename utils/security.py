# utils/security.py

"""
Módulo de utilidades de seguridad para la autenticación.

Encapsula la lógica para:
- Hashear y verificar contraseñas de forma segura usando passlib.
- Crear y decodificar tokens de acceso JWT.
- Proporcionar una dependencia de FastAPI para proteger endpoints.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from core.config import settings
from core.database import get_db_session, Account, Workspace, WorkspacePermission # Importar WorkspacePermission
from sqlalchemy.ext.asyncio import AsyncSession # Importar AsyncSession
from sqlalchemy import select # Importar select
import uuid # Importar uuid
from typing import List # Importar List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # AÑADIR ESTA LÍNEA

# 1. Contexto de Hasheo de Contraseña
# Usamos bcrypt, que es el estándar recomendado.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Esquema de Autenticación OAuth2
# Esto le dice a FastAPI cómo esperar el token (en el header "Authorization: Bearer <token>")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
from fastapi import WebSocket, WebSocketException # Añadido
from starlette.websockets import WebSocketDisconnect # Añadido

# --- Funciones de Contraseña ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su versión hasheada."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)

# --- Funciones de Token JWT ---

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crea un nuevo token de acceso JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expiry_days)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica un token JWT y devuelve el payload.
    
    Returns:
        El payload (dict) si el token es válido, o None si ha expirado o es inválido.
    """
    logger.debug(f"🔑 DEBUG: Token recibido en decode_access_token: {token[:50]}...")
    logger.debug(f"🔑 DEBUG: Usando JWT_SECRET_KEY que empieza con: {settings.jwt_secret_key[:10]}...")
    logger.debug(f"🔑 DEBUG: Intentando decodificar token: {token[:50]}...")
    logger.debug(f"🔑 DEBUG: Usando JWT_SECRET_KEY que empieza con: {settings.jwt_secret_key[:10]}... (longitud: {len(settings.jwt_secret_key)})")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        logger.debug(f"✅ DEBUG: Token decodificado exitosamente. Payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("❌ Token JWT expirado.")
        return None
    except jwt.PyJWTError as e:
        logger.error(f"❌ Error de decodificación de JWT: {e}", exc_info=True)
        return None

# --- Dependencia de FastAPI ---

async def get_current_account_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependencia de FastAPI para proteger endpoints.
    
    Extrae el token del header, lo valida y devuelve el account_id.
    Si el token es inválido o no se proporciona, lanza una HTTPException 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    logger.info(f"🔑 DEBUG: Token recibido en get_current_account_id: {token[:50]}...")
    
    payload = decode_access_token(token)
    
    if payload is None:
        logger.warning("❌ Payload es None después de decodificar el token.")
        raise credentials_exception

    account_id: str = payload.get("sub")
    if account_id is None:
        logger.warning("❌ account_id es None en el payload del token.")
        raise credentials_exception
    
    logger.info(f"✅ account_id extraído del token: {account_id}")
    return account_id

def verify_token_ws(token: str) -> str:
    """
    Verifica un token JWT para WebSockets y devuelve el account_id.
    Lanza HTTPException 403 si el token es inválido o no autorizado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No se pudieron validar las credenciales WebSocket",
    )
    
    payload = decode_access_token(token)
    
    if payload is None:
        logger.warning("❌ Payload es None después de decodificar el token WebSocket.")
        raise credentials_exception

    account_id: str = payload.get("sub")
    if account_id is None:
        logger.warning("❌ account_id es None en el payload del token WebSocket.")
async def get_websocket_token(websocket: WebSocket) -> str:
    """
    Extrae y valida el token JWT de la conexión WebSocket.
    El token se espera en el encabezado 'Authorization' como 'Bearer <token>'.
    """
    try:
        token: str = websocket.headers.get("Authorization")
        if not token:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token de autenticación no proporcionado")
        
        scheme, credentials = token.split(" ")
        if scheme.lower() != "bearer":
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Esquema de autenticación no soportado")
        
        payload = decode_access_token(credentials)
        if payload is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido o expirado")
        
        account_id: str = payload.get("sub")
        if account_id is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="ID de cuenta no encontrado en el token")
        
        return account_id
    except WebSocketException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener token de WebSocket: {e}", exc_info=True)
        raise WebSocketException(code=status.WS_1011_INTERNAL_ERROR, reason="Error interno del servidor al procesar el token")
        raise credentials_exception
    
    logger.debug(f"✅ DEBUG: account_id extraído del token WebSocket: {account_id}")
    return account_id

async def _get_user_from_token_payload(payload: dict, session: AsyncSession) -> dict:
    """
    Función auxiliar para obtener la información del usuario a partir de un payload de token decodificado.
    """
    from core.database import Account # Necesitamos importar Account para el tipo

    account_id: str = payload.get("sub")
    if account_id is None:
        logger.warning("❌ account_id es None en el payload del token.")
        return None # O lanzar una excepción específica

    try:
        query = select(Account).where(
            Account.id == account_id,
            Account.is_active == True
        )
        result = await session.execute(query)
        user_account = result.scalars().first()

        if not user_account:
            return None # O lanzar una excepción específica
        
        return {
            "account_id": str(user_account.id), # Convertir UUID a str
            "email": user_account.email,
            "username": user_account.username,
            "is_active": user_account.is_active,
            "created_at": user_account.created_at.isoformat() # Convertir datetime a str
        }

    except Exception as e:
        logger.error(f"Error obteniendo información del usuario desde el payload: {e}", exc_info=True)
        return None # O lanzar una excepción específica

async def get_current_active_account(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> Account:
    """
    Dependencia de FastAPI para obtener el objeto Account completo del usuario actual.

    Extrae el token del header, lo valida y devuelve el objeto Account.
    Si el token es inválido, no se proporciona, o el usuario no está activo, lanza una HTTPException 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    account_id: str = payload.get("sub")
    if account_id is None:
        raise credentials_exception
    
    try:
        query = select(Account).where(
            Account.id == account_id,
            Account.is_active == True
        )
        result = await session.execute(query)
        user_account = result.scalars().first()

        if not user_account:
            raise credentials_exception
        
        return user_account

    except Exception as e:
        logger.error(f"Error obteniendo el objeto Account del usuario: {e}")
        raise credentials_exception


async def get_optional_current_active_account(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    session: AsyncSession = Depends(get_db_session)
) -> Optional[Account]:
    """
    Dependencia de FastAPI para obtener opcionalmente el objeto Account completo del usuario actual.

    Si se proporciona un token válido, devuelve el objeto Account.
    Si no se proporciona un token o es inválido, devuelve None sin lanzar un error.
    """
    if token is None:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    account_id: str = payload.get("sub")
    if account_id is None:
        return None
    
    try:
        query = select(Account).where(
            Account.id == account_id,
            Account.is_active == True
        )
        result = await session.execute(query)
        user_account = result.scalars().first()
        
        return user_account

    except Exception as e:
        logger.error(f"Error obteniendo el objeto Account opcional del usuario: {e}")
        return None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Dependencia de FastAPI para obtener información completa del usuario actual.

    Extrae el token del header, lo valida y devuelve información del usuario.
    Si el token es inválido o no se proporciona, lanza una HTTPException 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_info = await _get_user_from_token_payload(payload, session)
    if user_info is None:
        raise credentials_exception
    return user_info

async def get_current_user_from_websocket_query_param(
    websocket: WebSocket,
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Dependencia de FastAPI para obtener información completa del usuario actual desde un WebSocket,
    leyendo el token de los query_params.
    """
    credentials_exception = WebSocketException(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="No se pudieron validar las credenciales WebSocket",
    )

    token = websocket.url.query_params.get("token")
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_info = await _get_user_from_token_payload(payload, session)
    if user_info is None:
        raise credentials_exception
    return user_info

import uuid # Importar uuid

async def check_workspace_permission(
    account_id: str,
    workspace_id: str,
    db: AsyncSession,
    required_roles: List[str]
) -> bool:
    """
    Verifica si el account_id tiene los permisos requeridos para acceder al workspace_id.
    """
    if not workspace_id:
        return False # No se puede verificar el permiso sin un workspace_id

    stmt = select(WorkspacePermission).where(
        WorkspacePermission.account_id == uuid.UUID(account_id),
        WorkspacePermission.workspace_id == uuid.UUID(workspace_id)
    )
    result = await db.execute(stmt)
    permission = result.scalar_one_or_none()

    if not permission or permission.role not in required_roles:
        logger.warning(f"Permiso denegado para account {account_id} en workspace {workspace_id} con roles {required_roles}. Rol actual: {permission.role if permission else 'N/A'}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso denegado. No tienes acceso a este workspace o tu rol no es el adecuado."
        )
    logger.info(f"Permiso concedido para account {account_id} en workspace {workspace_id} con rol {permission.role}.")
    return True
