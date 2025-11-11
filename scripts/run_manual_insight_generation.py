import asyncio
import argparse
import datetime
import logging
import sys
import os

# Añadir el directorio raíz del proyecto al path para las importaciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.proactive_knowledge_linker import run_batch_analysis_job
from core.database import SessionLocal, create_tables
from core.config import settings

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Lanza manualmente la generación de insights proactivos.")
    parser.add_argument("--account_id", type=str, required=True,
                        help="El ID de la cuenta para la que se generarán los insights.")
    parser.add_argument("--since_days_ago", type=int, default=None,
                        help="Número de días hacia atrás desde hoy para analizar solo el conocimiento reciente.")
    parser.add_argument("--topic_keywords", type=str, nargs='*', default=None,
                        help="Lista de palabras clave para enfocar el análisis en ítems que contengan estas palabras.")
    parser.add_argument("--thread_id", type=str, default=None,
                        help="ID del hilo para enviar notificaciones de finalización (opcional).")

    args = parser.parse_args()

    # Inicializar la base de datos si es necesario
    await create_tables()

    since_timestamp = None
    if args.since_days_ago is not None:
        since_timestamp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=args.since_days_ago)
        logger.info(f"Analizando conocimiento desde: {since_timestamp}")

    logger.info(f"Iniciando generación manual de insights para account_id: {args.account_id}")
    logger.info(f"Parámetros: since_days_ago={args.since_days_ago}, topic_keywords={args.topic_keywords}, thread_id={args.thread_id}")

    try:
        await run_batch_analysis_job(
            account_id_filter=args.account_id,
            since_timestamp=since_timestamp,
            topic_keywords=args.topic_keywords,
            thread_id=args.thread_id
        )
        logger.info("Generación manual de insights completada exitosamente.")
    except Exception as e:
        logger.error(f"Error durante la generación manual de insights: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())