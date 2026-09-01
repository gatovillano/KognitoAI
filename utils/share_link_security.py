"""Utilidades de seguridad para enlaces compartidos públicos."""

import hashlib
import secrets

_PBKDF2_ITERATIONS = 100_000


def hash_share_link_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest}"


def verify_share_link_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False

    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False
        _, iterations_str, salt, expected = parts
        try:
            iterations = int(iterations_str)
        except ValueError:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return secrets.compare_digest(candidate, expected)

    # Compatibilidad con hashes legados SHA-256 sin salt (64 hex)
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash
