"""
Gestor de autenticación para correo electrónico.
 Soporta contraseña normal y OAuth2 (Gmail, Outlook, Yahoo).
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)

@dataclass
class AuthCredentials:
    """Credenciales de autenticación."""
    provider: str
    email: str
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    token_expiry: Optional[datetime] = None

class AuthManager:
    """Gestor centralizado de autenticación para correo."""
    
    def __init__(self, provider: str, email: str):
        self.provider = provider.lower()
        self.email = email
        self._credentials: Optional[AuthCredentials] = None
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Carga credenciales desde variables de entorno."""
        provider_upper = self.provider.upper()
        
        # Credenciales comunes
        password = os.getenv(f"{provider_upper}_PASSWORD") or os.getenv(f"{provider_upper}_EMAIL_PASSWORD")
        client_id = os.getenv(f"{provider_upper}_CLIENT_ID")
        client_secret = os.getenv(f"{provider_upper}_CLIENT_SECRET")
        refresh_token = os.getenv(f"{provider_upper}_REFRESH_TOKEN")
        access_token = os.getenv(f"{provider_upper}_ACCESS_TOKEN")
        
        # Parsear expiración de token
        token_expiry = None
        expiry_str = os.getenv(f"{provider_upper}_TOKEN_EXPIRY")
        if expiry_str:
            try:
                token_expiry = datetime.fromisoformat(expiry_str)
            except ValueError:
                logger.warning(f"Formato de TOKEN_EXPIRY inválido: {expiry_str}")
        
        self._credentials = AuthCredentials(
            provider=self.provider,
            email=self.email,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            access_token=access_token,
            token_expiry=token_expiry
        )
    
    def get_auth_method(self) -> str:
        """Determina el método de autenticación disponible."""
        if self._credentials.password:
            return "password"
        elif self._credentials.access_token or self._credentials.refresh_token:
            return "oauth2"
        else:
            raise ValueError(
                f"No hay credenciales configuradas para {self.provider}. "
                f"Configura variables de entorno."
            )
    
    def get_password(self) -> str:
        """Obtiene la contraseña (para IMAP SMTP directo)."""
        if not self._credentials.password:
            raise ValueError(
                f"Contraseña no configurada para {self.provider}. "
                f"Configura {self.provider.upper()}_PASSWORD"
            )
        return self._credentials.password
    
    async def get_valid_access_token(self) -> str:
        """Obtiene un access token válido, renovándolo si es necesario."""
        if self.get_auth_method() != "oauth2":
            raise ValueError("Este método requiere OAuth2 configurado")
        
        # Si tenemos token y no ha expirado, usarlo
        if (self._credentials.access_token and 
            self._credentials.token_expiry and
            datetime.now() < self._credentials.token_expiry - timedelta(minutes=5)):
            return self._credentials.access_token
        
        # Renovar token
        return await self._refresh_access_token()
    
    async def _refresh_access_token(self) -> str:
        """Renueva el access token usando el refresh token."""
        if not self._credentials.refresh_token:
            raise ValueError("Refresh token no configurado")
        
        logger.info(f"Renovando access token para {self.provider}")
        
        # Endpoints de renovación por proveedor
        token_urls = {
            "gmail": "https://oauth2.googleapis.com/token",
            "outlook": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "yahoo": "https://api.login.yahoo.com/oauth2/get_token"
        }
        
        token_url = token_urls.get(self.provider)
        if not token_url:
            raise ValueError(f"Proveedor {self.provider} no tiene endpoint OAuth2")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._credentials.refresh_token,
            "client_id": self._credentials.client_id,
            "client_secret": self._credentials.client_secret,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
        
        # Actualizar credenciales
        self._credentials.access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        self._credentials.token_expiry = datetime.now() + timedelta(seconds=expires_in)
        
        # Guardar en variables de entorno para persistencia (opcional)
        os.environ[f"{self.provider.upper()}_ACCESS_TOKEN"] = token_data["access_token"]
        os.environ[f"{self.provider.upper()}_TOKEN_EXPIRY"] = self._credentials.token_expiry.isoformat()
        
        logger.info(f"Token renovado exitosamente, expira en {expires_in}s")
        return self._credentials.access_token
    
    def get_oauth2_string(self) -> str:
        """Genera string XOAUTH2 para autenticación IMAP."""
        import base64
        token = self._credentials.access_token
        if not token:
            raise ValueError("Access token no disponible")
        
        auth_string = f"user={self.email}\1auth=Bearer {token}\1\1"
        return base64.b64encode(auth_string.encode()).decode()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Valida que las credenciales estén correctamente configuradas."""
        issues = []
        
        if not self.email or "@" not in self.email:
            issues.append("Email inválido o no configurado")
        
        auth_method = self.get_auth_method()
        
        if auth_method == "password":
            if not self._credentials.password:
                issues.append(f"Contraseña no configurada ({self.provider.upper()}_PASSWORD)")
        elif auth_method == "oauth2":
            if not self._credentials.client_id:
                issues.append(f"Client ID no configurado ({self.provider.upper()}_CLIENT_ID)")
            if not self._credentials.client_secret:
                issues.append(f"Client Secret no configurado ({self.provider.upper()}_CLIENT_SECRET)")
            if not self._credentials.refresh_token:
                issues.append(f"Refresh token no configurado ({self.provider.upper()}_REFRESH_TOKEN)")
        
        return {
            "valid": len(issues) == 0,
            "auth_method": auth_method,
            "issues": issues,
            "provider": self.provider,
            "email": self.email
        }
