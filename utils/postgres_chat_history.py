import logging
from typing import Any, Optional


from sqlalchemy.engine import make_url

def get_postgres_history_connection_url(database_url: Optional[str]) -> Optional[str]:
    """Normaliza DATABASE_URL para el cliente síncrono usado por PostgresChatMessageHistory."""
    if not database_url:
        return None

    try:
        url = make_url(database_url).set(drivername="postgresql")
        return url.render_as_string(hide_password=False)
    except Exception:
        if "://" in database_url and (database_url.startswith("postgresql+") or database_url.startswith("postgres+")):
            _, rest = database_url.split("://", 1)
            return f"postgresql://{rest}"
        return database_url


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
