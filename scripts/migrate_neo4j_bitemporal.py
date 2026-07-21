#!/usr/bin/env python3
"""
Script de migración Cypher para añadir la Capa Bi-Temporal (is_current, valid_from, valid_to)
a las relaciones existentes en Neo4j.

Permite versionar el conocimiento y distinguir hechos vigentes de hechos pasados.
"""

import asyncio
import sys
import os
import logging

# Agregar directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.graph_database import GraphDB
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def run_bitemporal_migration():
    """Ejecuta la migración idempotente de la Capa Bi-Temporal en Neo4j."""
    logger.info("🚀 Iniciando migración de Capa Bi-Temporal en relaciones Neo4j...")
    
    graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    graph_db.connect()

    try:
        rel_query = """
        MATCH ()-[r]->()
        WHERE r.is_current IS NULL
        SET r.is_current = true,
            r.valid_from = COALESCE(r.created_at, toString(datetime())),
            r.valid_to = null
        RETURN count(r) AS updated_count
        """
        res_rel = await graph_db.execute_query(rel_query)
        updated_rels = res_rel[0]["updated_count"] if res_rel else 0
        logger.info(f"✅ Relaciones actualizadas con atributos bi-temporales: {updated_rels}")

        logger.info("🎉 Migración de Capa Bi-Temporal completada con éxito.")
        return True

    except Exception as e:
        logger.error(f"❌ Error durante la migración Cypher bi-temporal: {e}")
        return False
    finally:
        graph_db.close()


if __name__ == "__main__":
    asyncio.run(run_bitemporal_migration())
