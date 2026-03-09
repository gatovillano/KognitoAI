import asyncio
from sqlalchemy import text
from core.database import engine, SessionLocal
from utils.db_session import DBSession
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_accounts_table():
    """
    Añade las columnas faltantes a la tabla 'accounts' para soportar multi-LLM.
    """
    columns_to_add = [
        ("fast_llm_model", "VARCHAR(255)"),
        ("fast_llm_provider", "VARCHAR(50)"),
        ("vision_llm_model", "VARCHAR(255)"),
        ("vision_llm_provider", "VARCHAR(50)"),
        ("use_prompt_tooling", "BOOLEAN DEFAULT FALSE NOT NULL")
    ]
    
    async with engine.begin() as conn:
        for col_name, col_type in columns_to_add:
            try:
                # Comprobar si la columna existe
                check_query = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='accounts' AND column_name='{col_name}';")
                result = await conn.execute(check_query)
                if not result.fetchone():
                    logger.info(f"Añadiendo columna {col_name} a la tabla accounts...")
                    await conn.execute(text(f"ALTER TABLE accounts ADD COLUMN {col_name} {col_type};"))
                    logger.info(f"✅ Columna {col_name} añadida exitosamente.")
                else:
                    logger.info(f"La columna {col_name} ya existe.")
            except Exception as e:
                logger.error(f"Error al procesar la columna {col_name}: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_accounts_table())
