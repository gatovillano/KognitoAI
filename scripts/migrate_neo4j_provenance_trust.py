#!/usr/bin/env python3
"""
Script de migración Cypher para añadir atributos de Provenance & Trust Tracking
a los nodos (Entity, DocumentChunk) y relaciones existentes en Neo4j.

Mitiga el riesgo ASI06 (Memory Poisoning) asegurando que todos los elementos
tengan metadatos de trazabilidad y confiabilidad.
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


async def run_provenance_trust_migration():
    """Ejecuta la migración idempotente de Provenance & Trust en Neo4j."""
    logger.info("🚀 Iniciando migración de Provenance & Trust en Neo4j...")
    
    graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    graph_db.connect()

    try:
        # 1. Migrar Nodos Entity
        entity_query = """
        MATCH (n:Entity)
        WHERE n.trust_score IS NULL
        SET n.provenance_source = COALESCE(n.source, n.source_document, 'unknown'),
            n.provenance_method = COALESCE(n.extraction_method, 'slm_extractor'),
            n.trust_score = 0.8,
            n.extraction_model = COALESCE(n.extraction_model, 'Qwen2.5-3B-Instruct')
        RETURN count(n) AS updated_count
        """
        res_entity = await graph_db.execute_query(entity_query)
        updated_entities = res_entity[0]["updated_count"] if res_entity else 0
        logger.info(f"✅ Nodos 'Entity' actualizados: {updated_entities}")

        # 2. Migrar Nodos DocumentChunk
        chunk_query = """
        MATCH (n:DocumentChunk)
        WHERE n.trust_score IS NULL
        SET n.provenance_source = COALESCE(n.source_document, 'document'),
            n.provenance_method = COALESCE(n.extraction_method, 'parser'),
            n.trust_score = 1.0,
            n.extraction_model = 'system'
        RETURN count(n) AS updated_count
        """
        res_chunk = await graph_db.execute_query(chunk_query)
        updated_chunks = res_chunk[0]["updated_count"] if res_chunk else 0
        logger.info(f"✅ Nodos 'DocumentChunk' actualizados: {updated_chunks}")

        # 3. Migrar Relaciones
        rel_query = """
        MATCH ()-[r]->()
        WHERE r.trust_score IS NULL
        SET r.provenance_source = COALESCE(r.source, 'unknown'),
            r.provenance_method = COALESCE(r.extraction_method, 'slm_extractor'),
            r.trust_score = 0.8,
            r.extraction_model = COALESCE(r.extraction_model, 'Qwen2.5-3B-Instruct')
        RETURN count(r) AS updated_count
        """
        res_rel = await graph_db.execute_query(rel_query)
        updated_rels = res_rel[0]["updated_count"] if res_rel else 0
        logger.info(f"✅ Relaciones actualizadas: {updated_rels}")

        logger.info("🎉 Migración de Provenance & Trust completada con éxito.")
        return True

    except Exception as e:
        logger.error(f"❌ Error durante la migración Cypher: {e}")
        return False
    finally:
        graph_db.close()


if __name__ == "__main__":
    asyncio.run(run_provenance_trust_migration())
