"""
Configuraciones específicas por proveedor de correo electrónico.
 Cada proveedor tiene sus propios servidores, puertos y métodos de autenticación.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class AuthMethod(Enum):
    """Métodos de autenticación soportados."""
    PASSWORD = "password"           # Contraseña normal / App Password
    OAUTH2 = "oauth2"               # OAuth 2.0
    XOAUTH2 = "xoauth2"             # XOAUTH2 (variante de OAuth2 para IMAP)

@dataclass
class ProviderConfig:
    """Configuración completa de un proveedor de correo."""
    name: str
    imap_server: str
    imap_port: int
    imap_ssl: bool
    smtp_server: str
    smtp_port: int
    smtp_tls: bool
    auth_method: AuthMethod
    oauth2_required: bool
    app_password_supported: bool
    notes: Optional[str] = None

# Registro de proveedores soportados
PROVIDERS: Dict[str, ProviderConfig] = {
    "gmail": ProviderConfig(
        name="Gmail",
        imap_server="imap.gmail.com",
        imap_port=993,
        imap_ssl=True,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_tls=True,
        auth_method=AuthMethod.OAUTH2,
        oauth2_required=True,
        app_password_supported=True,
        notes="OAuth2 recomendado. App Password como fallback si 2FA está activado."
    ),
    "outlook": ProviderConfig(
        name="Outlook/Office 365",
        imap_server="outlook.office365.com",
        imap_port=993,
        imap_ssl=True,
        smtp_server="smtp.office365.com",
        smtp_port=587,
        smtp_tls=True,
        auth_method=AuthMethod.OAUTH2,
        oauth2_required=True,
        app_password_supported=True,
        notes="Usa Microsoft Graph API para OAuth2."
    ),
    "yahoo": ProviderConfig(
        name="Yahoo Mail",
        imap_server="imap.mail.yahoo.com",
        imap_port=993,
        imap_ssl=True,
        smtp_server="smtp.mail.yahoo.com",
        smtp_port=587,
        smtp_tls=True,
        auth_method=AuthMethod.OAUTH2,
        oauth2_required=True,
        app_password_supported=True,
        notes="Requiere App Password incluso con OAuth2."
    ),
    "disroot": ProviderConfig(
        name="Disroot",
        imap_server="disroot.org",
        imap_port=993,
        imap_ssl=True,
        smtp_server="disroot.org",
        smtp_port=587,
        smtp_tls=True,
        auth_method=AuthMethod.PASSWORD,
        oauth2_required=False,
        app_password_supported=False,
        notes="Ético y descentralizado. Autenticación por contraseña normal. "
              "Servidor IMAP: disroot.org (no imap.disroot.org). "
              "Soporta SSL/TLS en puerto 993."
    )
}

def get_provider_config(provider_name: str) -> ProviderConfig:
    """Obtiene la configuración de un proveedor por nombre.
    
    Args:
        provider_name: Nombre del proveedor (gmail, outlook, yahoo, disroot)
        
    Returns:
        ProviderConfig con la configuración del proveedor
        
    Raises:
        ValueError: Si el proveedor no existe
    """
    provider_name = provider_name.lower()
    if provider_name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Proveedor '{provider_name}' no soportado. "
            f"Disponibles: {available}"
        )
    return PROVIDERS[provider_name]

def list_supported_providers() -> list[str]:
    """Lista todos los proveedores soportados."""
    return list(PROVIDERS.keys())
