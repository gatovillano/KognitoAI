"""
Utilidad para leer secretos desde Docker Secrets con fallback a variables de entorno.

Docker Secrets monta los secretos como archivos en /run/secrets/<nombre>.
Esta función intenta leerlos de ahí primero, y si no existen (ej. en desarrollo local),
hace fallback a os.getenv().
"""

import os
import logging

logger = logging.getLogger(__name__)

SECRETS_DIR = os.getenv("SECRETS_DIR", "/run/secrets")


def get_secret(secret_name: str, env_var_name: str | None = None, default: str | None = None) -> str | None:
    """
    Lee un secreto de Docker Secrets, directorio de usuario ~/.kognito/secrets, o repo local con fallback a env.
    """
    # 1. Intentar leer de Docker Secrets
    secret_path = os.path.join(SECRETS_DIR, secret_name)
    try:
        with open(secret_path, "r") as f:
            value = f.read().strip()
            if value:
                logger.debug(f"Secreto '{secret_name}' cargado desde Docker Secrets.")
                return value
    except (IOError, FileNotFoundError):
        pass

    # 2. Intentar leer desde ~/.kognito/secrets/<secret_name> o <secret_name>.txt
    user_secrets_dir = os.getenv("KOGNITO_SECRETS_DIR", os.path.expanduser("~/.kognito/secrets"))
    for candidate_name in [secret_name, f"{secret_name}.txt"]:
        candidate_path = os.path.join(user_secrets_dir, candidate_name)
        try:
            with open(candidate_path, "r") as f:
                value = f.read().strip()
                if value:
                    logger.debug(f"Secreto '{secret_name}' cargado desde user secrets.")
                    return value
        except (IOError, FileNotFoundError):
            pass

    # 3. Fallback a variable de entorno
    if env_var_name is None:
        env_var_name = secret_name.upper()

    env_value = os.getenv(env_var_name, default)
    if env_value and env_value != default:
        logger.debug(f"Secreto '{secret_name}' cargado desde variable de entorno '{env_var_name}'.")
    return env_value
