from types import SimpleNamespace

from utils.postgres_chat_history import (
    close_postgres_chat_message_history,
    get_postgres_history_connection_url,
)


class _Closable:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_get_postgres_history_connection_url_normalizes_psycopg_urls():
    assert (
        get_postgres_history_connection_url("postgresql+psycopg://user:pass@db:5432/app")
        == "postgresql://user:pass@db:5432/app"
    )
    assert (
        get_postgres_history_connection_url("postgresql+psycopg2://user:pass@db:5432/app")
        == "postgresql://user:pass@db:5432/app"
    )


def test_close_postgres_chat_message_history_closes_cursor_and_connection():
    cursor = _Closable()
    connection = _Closable()
    history = SimpleNamespace(cursor=cursor, connection=connection)

    close_postgres_chat_message_history(history)

    assert cursor.closed is True
    assert connection.closed is True


def test_close_postgres_chat_message_history_tolerates_partial_objects():
    history = SimpleNamespace(connection=_Closable())

    close_postgres_chat_message_history(history)

    assert history.connection.closed is True
