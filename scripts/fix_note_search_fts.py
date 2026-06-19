import asyncio
import sys
import os
import logging
from sqlalchemy import text

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_note_search_fts():
    """
    Popula la columna text_search_vector en la tabla 'notas' 
    y añade un trigger para mantenerla actualizada.
    """
    logger.info("🚀 Iniciando reparación de búsqueda FTS en notas...")
    
    queries = [
        # 1. Asegurar que la columna existe (ya debería existir por la migración, pero por seguridad)
        "ALTER TABLE notas ADD COLUMN IF NOT EXISTS text_search_vector TSVECTOR",
        
        # 2. Crear el índice GIN para búsquedas rápidas si no existe
        "CREATE INDEX IF NOT EXISTS idx_notas_fts ON notas USING GIN(text_search_vector)",
        
        # 3. Función para el trigger (usamos coalesce para manejar NULLs)
        """
        CREATE OR REPLACE FUNCTION notas_fts_trigger_func() RETURNS trigger AS $$
        begin
          new.text_search_vector :=
            setweight(to_tsvector('spanish', coalesce(new.title,'')), 'A') ||
            setweight(to_tsvector('spanish', coalesce(new.content,'')), 'B');
          return new;
        end
        $$ LANGUAGE plpgsql;
        """,
        
        # 4. El trigger propiamente dicho (eliminar si existe para recrear)
        "DROP TRIGGER IF EXISTS tsvectorupdate ON notas",
        "CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON notas FOR EACH ROW EXECUTE FUNCTION notas_fts_trigger_func()",
        
        # 5. Popular la columna para todas las notas existentes
        """
        UPDATE notas SET text_search_vector = 
            setweight(to_tsvector('spanish', coalesce(title,'')), 'A') ||
            setweight(to_tsvector('spanish', coalesce(content,'')), 'B')
        """
    ]
    
    async with engine.begin() as conn:
        for query in queries:
            try:
                logger.info(f"Ejecutando: {query[:100]}...")
                await conn.execute(text(query))
                logger.info("✅ Éxito")
            except Exception as e:
                logger.error(f"❌ Error ejecutando query: {e}")
                # No lanzamos excepción aquí para intentar continuar con las demás si es posible
    
    logger.info("🏁 Reparación completada!")

if __name__ == "__main__":
    asyncio.run(fix_note_search_fts())
