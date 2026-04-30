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
    Lee un secreto de Docker Secrets (archivo en /run/secrets/) con fallback a variable de entorno.

    Args:
        secret_name: Nombre del archivo de secreto (ej. 'jwt_secret_key').
        env_var_name: Nombre de la variable de entorno como fallback.
                      Si es None, se usa secret_name.upper() (ej. 'JWT_SECRET_KEY').
        default: Valor por defecto si no se encuentra ni el archivo ni la variable de entorno.

    Returns:
        El valor del secreto, o default si no se encuentra.
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

    # 2. Fallback a variable de entorno
    if env_var_name is None:
        env_var_name = secret_name.upper()

    env_value = os.getenv(env_var_name, default)
    if env_value and env_value != default:
        logger.debug(f"Secreto '{secret_name}' cargado desde variable de entorno '{env_var_name}'.")
    return env_value
