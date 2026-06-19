"""
Secure Email Recovery Skill
============================
Skill empresarial para recuperación segura de correos electrónicos.
Soporta múltiples proveedores, OAuth2, caché y manejo de errores avanzado.
"""

from .auth_manager import AuthManager, AuthCredentials
from .imap_client import IMAPClient, EmailMessage
from .email_parser import EmailParser
from .cache_manager import EmailCache, get_default_cache
from .error_handler import ErrorHandler, EmailRecoveryError, ErrorCategory, ErrorSeverity

# Importar desde scripts usando importlib para evitar problemas de ruta
import importlib.util
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

secure_email_recovery = importlib.import_module("secure_email_recovery")
EmailRecovery = secure_email_recovery.EmailRecovery
PROVIDERS = secure_email_recovery.PROVIDERS

__version__ = "1.0.0"
__all__ = [
    "EmailRecovery",
    "AuthManager",
    "AuthCredentials",
    "IMAPClient",
    "EmailMessage",
    "EmailParser",
    "EmailCache",
    "get_default_cache",
    "ErrorHandler",
    "EmailRecoveryError",
    "ErrorCategory",
    "ErrorSeverity",
    "PROVIDERS"
]
