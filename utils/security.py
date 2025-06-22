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

logger = logging.getLogger(__name__)

# 1. Contexto de Hasheo de Contraseña
# Usamos bcrypt, que es el estándar recomendado.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Esquema de Autenticación OAuth2
# Esto le dice a FastAPI cómo esperar el token (en el header "Authorization: Bearer <token>")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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

def decode_access_token(token: str) -> Optional[str]:
    """
    Decodifica un token JWT y devuelve el 'subject' (account_id).
    
    Returns:
        El account_id (str) si el token es válido, o None si ha expirado o es inválido.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        # 'sub' (subject) es el estándar para el ID del usuario en JWT.
        account_id: str = payload.get("sub")
        if account_id is None:
            return None
        return account_id
    except jwt.ExpiredSignatureError:
        logger.warning("Intento de uso de un token JWT expirado.")
        return None
    except jwt.PyJWTError as e:
        logger.error(f"Error de decodificación de JWT: {e}")
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
    
    account_id = decode_access_token(token)
    
    if account_id is None:
        raise credentials_exception
        
    return account_id