import logging
from typing import Any, Optional


def get_postgres_history_connection_url(database_url: Optional[str]) -> Optional[str]:
    """Normaliza DATABASE_URL para el cliente síncrono usado por PostgresChatMessageHistory."""
    if not database_url:
        return None

    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql://", 1)

    return database_url.replace("+psycopg", "")


def close_postgres_chat_message_history(history: Any, logger: Optional[logging.Logger] = None) -> None:
    """Cierra de forma segura los recursos internos del historial de LangChain."""
    if history is None:
        return

    cursor = getattr(history, "cursor", None)
    if cursor is not None:
        try:
            cursor.close()
        except Exception as exc:
            if logger:
                logger.debug("No se pudo cerrar el cursor del historial: %s", exc)

    connection = getattr(history, "connection", None)
    if connection is not None:
        try:
            connection.close()
        except Exception as exc:
            if logger:
                logger.debug("No se pudo cerrar la conexion del historial: %s", exc)
