
import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to Python path
sys.path.append(os.getcwd())

from core.database import SessionLocal
from utils.db_session import DBSession
from knowledge_graph.memory_graph_processor import process_memory_batches
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reprocess_memories():
    logger.info("🚀 Iniciando reprocesamiento de memorias...")
    
    async with DBSession(SessionLocal) as db:
        # 1. Obtener todos los account_ids distintos
        logger.info("🔍 Buscando cuentas con memorias...")
        result = await db.execute(text("SELECT DISTINCT account_id FROM langchain_pg_embedding"))
        account_ids = [row[0] for row in result.fetchall() if row[0]]
        
        logger.info(f"📋 Cuentas encontradas: {len(account_ids)}")

        for account_id in account_ids:
            str_account_id = str(account_id)
            logger.info(f"🔄 Procesando cuenta: {str_account_id}")
            
            # 2. Resetear el flag is_graph_processed para memorias
            # Filtramos por tipos comunes de memoria para no reprocesar documentos grandes innecesariamente si no son memorias
            reset_query = text("""
                UPDATE langchain_pg_embedding
                SET is_graph_processed = false
                WHERE account_id = :account_id 
                AND (
                    cmetadata->>'type' = 'user_memory' 
                    OR cmetadata->>'type' = 'user_memory_proactive_llm'
                    OR cmetadata->>'type' = 'agent_memory'
                    OR cmetadata->>'type' = 'chat_summary'
                )
            """)
            
            result = await db.execute(reset_query, {"account_id": str_account_id})
            logger.info(f"   ↪️  Memorias marcadas para reprocesar: {result.rowcount}")
            await db.commit()
            
            # 3. Ejecutar el procesamiento por lotes
            if result.rowcount > 0:
                logger.info(f"   ⚙️  Ejecutando process_memory_batches...")
                await process_memory_batches(str_account_id)
                logger.info(f"   ✅  Procesamiento finalizado para {str_account_id}")
            else:
                logger.info(f"   ℹ️  No se encontraron memorias para reprocesar en esta cuenta.")

    logger.info("✨ Reprocesamiento global completado.")

if __name__ == "__main__":
    asyncio.run(reprocess_memories())
