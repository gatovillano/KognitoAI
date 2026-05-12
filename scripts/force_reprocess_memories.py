
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

        for i, account_id in enumerate(account_ids):
            str_account_id = str(account_id)
            logger.info(f"🔄 [{i+1}/{len(account_ids)}] Procesando cuenta: {str_account_id}")
            
            # 2. Resetear el flag is_graph_processed para memorias
            reset_query = text("""
                UPDATE langchain_pg_embedding
                SET is_graph_processed = false
                WHERE account_id = :account_id 
                AND (
                    cmetadata->>'type' IN ('user_memory', 'user_memory_proactive_llm', 'agent_memory', 'chat_summary')
                )
            """)
            
            result = await db.execute(reset_query, {"account_id": str_account_id})
            count = result.rowcount
            logger.info(f"   ↪️  Se marcaron {count} memorias para reprocesar en esta cuenta.")
            await db.commit()
            
            # 3. Ejecutar el procesamiento por lotes
            if count > 0:
                logger.info(f"   ⚙️  Iniciando process_memory_batches para account_id: {str_account_id}...")
                await process_memory_batches(str_account_id)
                logger.info(f"   ✅  Lote finalizado para la cuenta {str_account_id}")
            else:
                logger.info(f"   ℹ️  No hay memorias pendientes para la cuenta {str_account_id}.")

    logger.info("✨ Reprocesamiento global completado.")

if __name__ == "__main__":
    asyncio.run(reprocess_memories())
