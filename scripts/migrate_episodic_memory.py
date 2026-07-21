#!/usr/bin/env python3
"""
Script de migración para la tabla `episodic_memory` en PostgreSQL (Fase 3).
Crea la tabla e índices necesarios para búsqueda episódica con pgvector (768 dimensiones).
"""

import asyncio
import sys
import os
import logging
from sqlalchemy import text

# Agregar directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def run_episodic_memory_migration():
    """Ejecuta la migración DDL para la tabla episodic_memory en PostgreSQL."""
    logger.info("🚀 Iniciando migración DDL de Memoria Episódica en PostgreSQL...")
    
    ddl_statements = [
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "DROP TABLE IF EXISTS episodic_memory CASCADE;",
        """
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
            workspace_id UUID,
            event_text TEXT NOT NULL,
            embedding vector(768),
            occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            episode_type VARCHAR(50) DEFAULT 'chat',
            extra_metadata JSONB
        );
        """,
        "CREATE INDEX IF NOT EXISTS ix_episodic_memory_account_id ON episodic_memory(account_id);",
        "CREATE INDEX IF NOT EXISTS ix_episodic_memory_workspace_id ON episodic_memory(workspace_id);",
        "CREATE INDEX IF NOT EXISTS ix_episodic_memory_occurred_at ON episodic_memory(occurred_at DESC);",
        "CREATE INDEX IF NOT EXISTS ix_episodic_memory_episode_type ON episodic_memory(episode_type);",
        "CREATE INDEX IF NOT EXISTS ix_episodic_memory_recency ON episodic_memory(account_id, occurred_at DESC);"
    ]

    try:
        async with engine.begin() as conn:
            for stmt in ddl_statements:
                await conn.execute(text(stmt))
        logger.info("🎉 Migración de Memoria Episódica en PostgreSQL completada con éxito.")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando la tabla episodic_memory: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(run_episodic_memory_migration())
