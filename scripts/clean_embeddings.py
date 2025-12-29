import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Obtener la URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL no está configurada en las variables de entorno.")
    exit(1)

# Convertir a URL síncrona para create_engine si es asyncpg
sync_database_url = DATABASE_URL.replace("+asyncpg", "")

# Configuración de SQLAlchemy
engine = create_engine(sync_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def clean_incorrect_dimension_embeddings(expected_dimension: int = 768):
    """
    Identifica y elimina embeddings con dimensiones incorrectas de la tabla langchain_pg_embedding.
    """
    logger.info(f"Iniciando limpieza de embeddings con dimensión diferente a {expected_dimension}...")
    
    deleted_count = 0
    try:
        with SessionLocal() as session:
            # Consulta para obtener todos los embeddings y sus dimensiones
            # Nota: pgvector almacena los embeddings como arrays de float.
            # La dimensión se puede obtener con array_length(embedding, 1)
            
            # Primero, identificar los IDs de los embeddings con dimensión incorrecta
            # Usamos text() para ejecutar SQL directamente ya que SQLAlchemy ORM no tiene
            # una forma directa de obtener la dimensión de un vector pgvector.
            
            # Asegúrate de que la tabla 'langchain_pg_embedding' y la columna 'embedding' existen.
            # Si tu tabla tiene un nombre diferente o la columna de embedding se llama distinto,
            # ajusta la consulta SQL.
            
            # Contar cuántos embeddings tienen la dimensión incorrecta
            count_query = text(f"""
                SELECT COUNT(*)
                FROM langchain_pg_embedding
                WHERE array_length(embedding, 1) != :expected_dimension;
            """)
            incorrect_count = session.execute(count_query, {"expected_dimension": expected_dimension}).scalar_one()

            if incorrect_count == 0:
                logger.info("No se encontraron embeddings con dimensiones incorrectas. ¡Todo limpio! ✨")
                return

            logger.warning(f"Se encontraron {incorrect_count} embeddings con dimensiones diferentes a {expected_dimension}.")
            
            confirmation = input(f"¿Estás seguro de que quieres ELIMINAR estos {incorrect_count} embeddings? (s/N): ")
            if confirmation.lower() != 's':
                logger.info("Operación cancelada por el usuario. 🛑")
                return

            # Eliminar los embeddings con dimensión incorrecta
            delete_query = text(f"""
                DELETE FROM langchain_pg_embedding
                WHERE array_length(embedding, 1) != :expected_dimension
                RETURNING id;
            """)
            
            result = session.execute(delete_query, {"expected_dimension": expected_dimension})
            deleted_ids = [row[0] for row in result]
            deleted_count = len(deleted_ids)
            
            session.commit()
            
            logger.info(f"✅ Se eliminaron {deleted_count} embeddings con dimensiones incorrectas. IDs eliminados: {deleted_ids}")
            logger.info("¡Limpieza completada! 🎉")

    except Exception as e:
        logger.error(f"❌ Ocurrió un error durante la limpieza de embeddings: {e}", exc_info=True)
        session.rollback() # Asegurarse de hacer rollback en caso de error

if __name__ == "__main__":
    # Ejecutar la función de limpieza
    asyncio.run(clean_incorrect_dimension_embeddings())
