"""
cli/core/auth.py
Gestión segura de autenticación: validación JWT, refresco de token,
y protección de archivos de configuración.
"""
from __future__ import annotations

import os
import stat
import time
from typing import Optional, Dict, Any

# PyJWT ya está en requirements.txt
try:
    import jwt as _jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


class TokenValidator:
    """Valida y decodifica JWT sin verificar firma (para inspección de claims)."""

    @staticmethod
    def decode_claims(token: str) -> Dict[str, Any]:
        """
        Decodifica el payload del JWT sin verificar la firma.
        Solo para inspeccionar exp, sub, etc.
        """
        if not token:
            return {}
        try:
            if JWT_AVAILABLE:
                return _jwt.decode(token, options={"verify_signature": False})
            # Fallback manual sin dependencia
            import base64, json
            parts = token.split(".")
            if len(parts) < 2:
                return {}
            payload = parts[1]
            # Añadir padding
            payload += "=" * (-len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(payload))
        except Exception:
            return {}

    @staticmethod
    def is_expired(token: str, margin_seconds: int = 60) -> bool:
        """
        Retorna True si el token está vencido o vence en los próximos
        `margin_seconds` segundos.
        """
        claims = TokenValidator.decode_claims(token)
        exp = claims.get("exp")
        if exp is None:
            return False  # Sin exp → asumir válido (servidor decide)
        return time.time() >= (exp - margin_seconds)

    @staticmethod
    def get_subject(token: str) -> Optional[str]:
        return TokenValidator.decode_claims(token).get("sub")

    @staticmethod
    def get_expiry_str(token: str) -> str:
        claims = TokenValidator.decode_claims(token)
        exp = claims.get("exp")
        if not exp:
            return "sin expiración"
        import datetime
        dt = datetime.datetime.fromtimestamp(exp)
        return dt.strftime("%Y-%m-%d %H:%M")


def secure_config_file(path: str) -> None:
    """
    Aplica permisos 600 (solo lectura/escritura del propietario)
    al archivo de configuración para proteger el token.
    """
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass  # Windows no soporta chmod estándar, se ignora


def require_auth(config: "CLIConfig") -> None:  # type: ignore[name-defined]
    """
    Verifica que la sesión esté autenticada y que el token no haya vencido.
    Lanza RuntimeError con mensaje descriptivo si falla.
    """
    if not config.is_authenticated:
        raise RuntimeError(
            "❌ No autenticado. Ejecuta:\n"
            "    python -m cli login\n"
            "  o abre el TUI con:\n"
            "    python -m cli tui"
        )
    if config.token and TokenValidator.is_expired(config.token):
        raise RuntimeError(
            "⏰ Tu sesión ha expirado. Vuelve a iniciar sesión:\n"
            "    python -m cli login"
        )
