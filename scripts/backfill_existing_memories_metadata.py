#!/usr/bin/env python3
"""
Backfill de metadatos para memorias preexistentes en langchain_pg_embedding.

Objetivo:
- Normalizar columnas optimizadas en filas de memorias antiguas.
- Asegurar que cmetadata tenga claves coherentes: account_id, type, topic, category.

Uso:
- Dry-run (por defecto):
    python scripts/backfill_existing_memories_metadata.py

- Aplicar cambios:
    python scripts/backfill_existing_memories_metadata.py --apply

- Aplicar cambios para una sola cuenta:
    python scripts/backfill_existing_memories_metadata.py --apply --account-id <uuid>
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

from sqlalchemy import create_engine, text


MEMORY_TYPES = (
    "user_memory",
    "user_memory_proactive_llm",
    "general_memory",
    "chat_summary",
    "thread_summary",
    "enhanced_episodic",
    "user_memories",
)


@dataclass
class Summary:
    total_memory_rows: int
    missing_account_id: int
    missing_content_type: int
    missing_topic: int
    missing_category: int


def normalize_db_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return url


def get_engine() -> object:
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_URL no está definido en el entorno")
    return create_engine(normalize_db_url(raw_url), future=True)


def build_where_sql(account_id: str | None) -> tuple[str, dict]:
    where = """
        EXISTS (
            SELECT 1
            FROM langchain_pg_collection c
            WHERE c.uuid = e.collection_id
              AND c.name LIKE 'user_memories_%'
        )
    """
    params: dict = {}
    if account_id:
        where += " AND (e.account_id = CAST(:account_id AS uuid) OR e.cmetadata->>'account_id' = :account_id)"
        params["account_id"] = account_id
    return where, params


def fetch_summary(conn, where_sql: str, params: dict) -> Summary:
    query = text(
        f"""
        SELECT
            COUNT(*) AS total_memory_rows,
            COUNT(*) FILTER (WHERE e.account_id IS NULL) AS missing_account_id,
            COUNT(*) FILTER (WHERE e.content_type IS NULL OR e.content_type = '') AS missing_content_type,
            COUNT(*) FILTER (WHERE e.topic IS NULL OR e.topic = '') AS missing_topic,
            COUNT(*) FILTER (WHERE e.category IS NULL OR e.category = '') AS missing_category
        FROM langchain_pg_embedding e
        WHERE {where_sql}
        """
    )
    row = conn.execute(query, params).mappings().first()
    if not row:
        return Summary(0, 0, 0, 0, 0)
    return Summary(
        total_memory_rows=row["total_memory_rows"] or 0,
        missing_account_id=row["missing_account_id"] or 0,
        missing_content_type=row["missing_content_type"] or 0,
        missing_topic=row["missing_topic"] or 0,
        missing_category=row["missing_category"] or 0,
    )


def print_summary(label: str, summary: Summary) -> None:
    print(f"\n[{label}]")
    print(f"- total_memory_rows: {summary.total_memory_rows}")
    print(f"- missing_account_id: {summary.missing_account_id}")
    print(f"- missing_content_type: {summary.missing_content_type}")
    print(f"- missing_topic: {summary.missing_topic}")
    print(f"- missing_category: {summary.missing_category}")


def run_backfill(conn, where_sql: str, params: dict) -> tuple[int, int]:
    type_list = list(MEMORY_TYPES)

    # Paso 1: backfill de columnas optimizadas desde cmetadata y defaults seguros.
    update_columns = text(
        f"""
        UPDATE langchain_pg_embedding e
        SET
            account_id = COALESCE(
                e.account_id,
                CASE
                    WHEN (e.cmetadata->>'account_id') ~* '^[0-9a-fA-F-]{{36}}$'
                    THEN CAST(e.cmetadata->>'account_id' AS uuid)
                    ELSE NULL
                END
            ),
            content_type = COALESCE(
                NULLIF(e.content_type, ''),
                NULLIF(e.cmetadata->>'type', ''),
                'general_memory'
            ),
            topic = COALESCE(
                NULLIF(e.topic, ''),
                NULLIF(e.cmetadata->>'topic', ''),
                NULLIF(e.cmetadata->>'category', ''),
                'general'
            ),
            category = COALESCE(
                NULLIF(e.category, ''),
                NULLIF(e.cmetadata->>'category', ''),
                NULLIF(e.cmetadata->>'topic', ''),
                'general'
            ),
            workspace_id = COALESCE(
                e.workspace_id,
                CASE
                    WHEN (e.cmetadata->>'workspace_id') ~* '^[0-9a-fA-F-]{{36}}$'
                    THEN CAST(e.cmetadata->>'workspace_id' AS uuid)
                    ELSE NULL
                END
            ),
            telegram_id = COALESCE(NULLIF(e.telegram_id, ''), NULLIF(e.cmetadata->>'telegram_id', '')),
            thread_id = COALESCE(NULLIF(e.thread_id, ''), NULLIF(e.cmetadata->>'thread_id', ''))
        WHERE {where_sql}
          AND (
              e.account_id IS NULL
              OR e.content_type IS NULL
              OR e.content_type = ''
              OR e.topic IS NULL
              OR e.topic = ''
              OR e.category IS NULL
              OR e.category = ''
              OR e.workspace_id IS NULL
              OR e.telegram_id IS NULL
              OR e.telegram_id = ''
              OR e.thread_id IS NULL
              OR e.thread_id = ''
          )
        """
    )
    res1 = conn.execute(update_columns, params)

    # Paso 2: sincronizar cmetadata para claves faltantes/inconsistentes.
    update_cmetadata = text(
        f"""
        UPDATE langchain_pg_embedding e
        SET cmetadata = e.cmetadata || jsonb_strip_nulls(
            jsonb_build_object(
                'account_id', COALESCE(NULLIF(e.cmetadata->>'account_id', ''), e.account_id::text),
                'type', COALESCE(NULLIF(e.cmetadata->>'type', ''), e.content_type),
                'topic', COALESCE(NULLIF(e.cmetadata->>'topic', ''), e.topic),
                'category', COALESCE(NULLIF(e.cmetadata->>'category', ''), e.category),
                'workspace_id', COALESCE(NULLIF(e.cmetadata->>'workspace_id', ''), e.workspace_id::text),
                'telegram_id', COALESCE(NULLIF(e.cmetadata->>'telegram_id', ''), e.telegram_id),
                'thread_id', COALESCE(NULLIF(e.cmetadata->>'thread_id', ''), e.thread_id)
            )
        )
        WHERE {where_sql}
          AND (
              (e.cmetadata->>'account_id') IS NULL
              OR (e.cmetadata->>'account_id') = ''
              OR (e.cmetadata->>'type') IS NULL
              OR (e.cmetadata->>'type') = ''
              OR (e.cmetadata->>'topic') IS NULL
              OR (e.cmetadata->>'topic') = ''
              OR (e.cmetadata->>'category') IS NULL
              OR (e.cmetadata->>'category') = ''
          )
          AND (
              e.content_type = ANY(:memory_types)
              OR (e.cmetadata->>'type') = ANY(:memory_types)
          )
        """
    )
    res2 = conn.execute(update_cmetadata, {**params, "memory_types": type_list})

    return res1.rowcount or 0, res2.rowcount or 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill de metadatos de memorias preexistentes")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios en DB. Sin esta bandera es dry-run")
    parser.add_argument("--account-id", type=str, default=None, help="Filtra a una cuenta específica (UUID)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine()

    where_sql, params = build_where_sql(args.account_id)

    with engine.begin() as conn:
        before = fetch_summary(conn, where_sql, params)
        print_summary("ANTES", before)

        if not args.apply:
            print("\nDRY-RUN: no se aplicaron cambios. Usa --apply para ejecutar el backfill.")
            return 0

        updated_cols, updated_meta = run_backfill(conn, where_sql, params)
        after = fetch_summary(conn, where_sql, params)

        print("\n[RESULTADO]")
        print(f"- filas actualizadas (columnas optimizadas): {updated_cols}")
        print(f"- filas actualizadas (cmetadata): {updated_meta}")
        print_summary("DESPUÉS", after)

    print("\nBackfill completado.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise
