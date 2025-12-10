# knowledge_graph/memory_graph_processor.py

"""
Módulo para procesar memorias del agente en un grafo de conocimiento conceptual.
"""

import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy import text, select, update
import uuid

from core.database import SessionLocal
from utils.db_session import DBSession
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from core.config import settings

# Configuración del logger
logger = logging.getLogger(__name__)

# Umbral de memorias para procesar en un lote
MEMORY_PROCESSING_THRESHOLD = 10

# Lock para evitar condiciones de carrera al procesar lotes
processing_lock = asyncio.Lock()


async def get_unprocessed_memories_count(account_id: str) -> int:
    """Cuenta las memorias no procesadas para un usuario."""
    async with DBSession(SessionLocal) as db:
        query = text("""
            SELECT COUNT(*) FROM langchain_pg_embedding
            WHERE account_id = :account_id AND is_graph_processed = false
        """)
        result = await db.execute(query, {"account_id": account_id})
        return result.scalar_one_or_none() or 0

async def get_unprocessed_memories(account_id: str, limit: int) -> List[Dict[str, Any]]:
    """Obtiene las memorias no procesadas de la base de datos."""
    async with DBSession(SessionLocal) as db:
        query = text("""
            SELECT uuid, document, cmetadata FROM langchain_pg_embedding
            WHERE account_id = :account_id AND is_graph_processed = false
            ORDER BY cmetadata->>'created_at' ASC
            LIMIT :limit
        """)
        result = await db.execute(query, {"account_id": account_id, "limit": limit})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

async def mark_memories_as_processed(memory_ids: List[uuid.UUID]):
    """Marca una lista de memorias como procesadas en la base de datos."""
    if not memory_ids:
        return
    async with DBSession(SessionLocal) as db:
        query = text("""
            UPDATE langchain_pg_embedding
            SET is_graph_processed = true
            WHERE uuid = ANY(:memory_ids)
        """)
        await db.execute(query, {"memory_ids": memory_ids})
        await db.commit()


async def schedule_memory_graph_processing(account_id: str):
    """
    Verifica si hay suficientes memorias pendientes y, de ser así,
    dispara la tarea de procesamiento en lotes.
    """
    try:
        logger.info(f"Verificando si se debe procesar el grafo de memorias para la cuenta {account_id}...")
        unprocessed_count = await get_unprocessed_memories_count(account_id)

        if unprocessed_count >= MEMORY_PROCESSING_THRESHOLD:
            logger.info(f"Umbral de {MEMORY_PROCESSING_THRESHOLD} memorias alcanzado. Programando procesamiento en lote.")
            asyncio.create_task(process_memory_batches(account_id=account_id))
        else:
            logger.info(f"Aún no se alcanza el umbral de procesamiento. Memorias pendientes: {unprocessed_count}")
    except Exception as e:
        logger.error(f"Error al programar el procesamiento del grafo de memoria: {e}", exc_info=True)


async def process_memory_batches(account_id: str):
    """
    Tarea principal que se ejecuta en segundo plano para procesar las memorias.
    """
    if await processing_lock.acquire():
        try:
            logger.info(f"Iniciando procesamiento de lote de memorias para la cuenta {account_id}.")
            
            memories_to_process = await get_unprocessed_memories(account_id, limit=100)
            
            if not memories_to_process:
                logger.info("No hay memorias nuevas para procesar en este lote.")
                return

            logger.info(f"Se procesarán {len(memories_to_process)} memorias en este lote.")
            
            documents = [
                {
                    "title": f"Memory_{mem.get('cmetadata', {}).get('type', 'general')}_{mem.get('cmetadata', {}).get('created_at', '')}",
                    "content": mem.get('document', ''),
                    "metadata": {
                        "type": "agent_memory",
                        "memory_type": mem.get('cmetadata', {}).get('type', 'general'),
                        "category": mem.get('cmetadata', {}).get('category'),
                        "created_at": mem.get('cmetadata', {}).get('created_at'),
                        "original_uuid": str(mem.get('uuid'))
                    }
                } for mem in memories_to_process
            ]
            
            graph_db = GraphDB(uri=str(settings.neo4j_uri), user=str(settings.neo4j_user), password=str(settings.neo4j_password))
            graph_db.connect()
            graph_integration = GraphIntegration(graph_db)
            
            await graph_integration.process_documents(
                documents=documents,
                dataset_name=f"agent_memories_{account_id.replace('-', '_')}",
                processing_mode="hybrid"
            )

            memory_ids = [mem['uuid'] for mem in memories_to_process]
            await mark_memories_as_processed(memory_ids)
            
            logger.info(f"Lote de {len(memories_to_process)} memorias procesado y añadido al grafo de conocimiento.")

        except Exception as e:
            logger.error(f"Error durante el procesamiento del lote de memorias para la cuenta {account_id}: {e}", exc_info=True)
        finally:
            processing_lock.release()
    else:
        logger.info(f"El procesamiento de lotes para la cuenta {account_id} ya está en curso.")
