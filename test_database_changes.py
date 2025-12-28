#!/usr/bin/env python3
"""
Script de pruebas para verificar los cambios en la configuración de la base de datos.
Este script prueba la sintaxis y la funcionalidad de las modificaciones realizadas.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from core.database import get_db_session, log_pool_status, engine

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_db_session():
    """
    Prueba la creación y cierre de una sesión de base de datos.
    """
    logger.info("Iniciando prueba de sesión de base de datos...")
    try:
        async for session in get_db_session():
            logger.info("Sesión de base de datos creada correctamente.")
            # Realizar una consulta simple para verificar la conexión
            result = await session.execute("SELECT 1")
            logger.info(f"Consulta ejecutada correctamente: {result.scalar()}")
            break
        logger.info("Sesión de base de datos cerrada correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error durante la prueba de sesión: {e}", exc_info=True)
        return False


async def test_pool_status():
    """
    Prueba la función de monitoreo del pool de conexiones.
    """
    logger.info("Iniciando prueba de monitoreo del pool de conexiones...")
    try:
        await log_pool_status()
        logger.info("Monitoreo del pool de conexiones ejecutado correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error durante la prueba del pool: {e}", exc_info=True)
        return False


async def test_concurrent_sessions():
    """
    Prueba la creación de múltiples sesiones concurrentes para verificar el manejo del pool.
    """
    logger.info("Iniciando prueba de sesiones concurrentes...")
    try:
        tasks = []
        for i in range(5):
            task = asyncio.create_task(test_db_session())
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        if all(results):
            logger.info("Todas las sesiones concurrentes se manejaron correctamente.")
            return True
        else:
            logger.error("Algunas sesiones concurrentes fallaron.")
            return False
    except Exception as e:
        logger.error(f"Error durante la prueba de sesiones concurrentes: {e}", exc_info=True)
        return False


async def main():
    """
    Función principal para ejecutar todas las pruebas.
    """
    logger.info("Iniciando pruebas de cambios en la base de datos...")
    
    # Prueba 1: Sesión individual
    session_test_passed = await test_db_session()
    
    # Prueba 2: Monitoreo del pool
    pool_test_passed = await test_pool_status()
    
    # Prueba 3: Sesiones concurrentes
    concurrent_test_passed = await test_concurrent_sessions()
    
    # Resumen de resultados
    logger.info("\n" + "="*50)
    logger.info("RESUMEN DE PRUEBAS")
    logger.info("="*50)
    logger.info(f"Prueba de sesión individual: {'PASADA' if session_test_passed else 'FALLIDA'}")
    logger.info(f"Prueba de monitoreo del pool: {'PASADA' if pool_test_passed else 'FALLIDA'}")
    logger.info(f"Prueba de sesiones concurrentes: {'PASADA' if concurrent_test_passed else 'FALLIDA'}")
    
    if all([session_test_passed, pool_test_passed, concurrent_test_passed]):
        logger.info("\n✅ Todas las pruebas pasaron exitosamente.")
        return True
    else:
        logger.error("\n❌ Algunas pruebas fallaron. Revisa los logs para más detalles.")
        return False


if __name__ == "__main__":
    # Ejecutar las pruebas
    success = asyncio.run(main())
    exit(0 if success else 1)