"""
Seguridad para el módulo de correo.

Responsabilidades:
- Cifrar y descifrar credenciales/tokens de cuentas IMAP/SMTP/OAuth2.
- Proveer helpers de acceso: validar ownership por cuenta y enmascarar secretos en logs.
"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EmailSecurityError(Exception):
    """Error genérico de seguridad para el módulo de correo."""


class EmailSecurity:
    """
    Wrapper de cifrado para credenciales de email.

    Usa una clave simétrica Fernet tomada de DB_ENCRYPTION_KEY.
    """

    def __init__(self, encryption_key: Optional[str] = None) -> None:
        raw_key = encryption_key or os.getenv("DB_ENCRYPTION_KEY", "")
        if not raw_key:
            raise EmailSecurityError(
                "DB_ENCRYPTION_KEY no está configurada. "
                "Configurela en el entorno para habilitar cifrado de credenciales de email."
            )
        try:
            self.fernet = Fernet(raw_key.encode("utf-8"))
        except Exception as exc:  # pragma: no cover - configuración inválida
            raise EmailSecurityError(f"DB_ENCRYPTION_KEY inválida: {exc}") from exc

    def encrypt(self, plaintext: str) -> str:
        """
        Cifra un texto plano y devuelve el token como string UTF-8.
        """
        if plaintext is None:
            return ""
        return self.fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Descifra un token y devuelve el texto plano original.
        Lanza EmailSecurityError si el token es inválido.
        """
        if not ciphertext:
            return ""
        try:
            return self.fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise EmailSecurityError("Token de email inválido o corrupto.") from exc
        except Exception as exc:
            raise EmailSecurityError(f"Error al descifrar credencial de email: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers de acceso
# ---------------------------------------------------------------------------


def mask_secret(value: Optional[str]) -> str:
    """
    Enmascara un secreto para logs.
    """
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def assert_account_access(account_id: str, owner_account_id: str) -> None:
    """
    Validación simple de ownership por cuenta.

    Aquí se puede ampliar luego con roles/workspaces si hace falta.
    """
    if account_id != owner_account_id:
        raise EmailSecurityError("No tiene acceso a esta cuenta de correo.")
