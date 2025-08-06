# core/dependencies.py

"""
Dependencias centralizadas para FastAPI.

Este módulo proporciona dependencias comunes que pueden ser utilizadas
en todos los endpoints de la API, garantizando consistencia y reutilización.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import SessionLocal
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI que proporciona una sesión de base de datos
    utilizando el patrón DBSession para manejo automático de transacciones.
    
    Esta dependencia debe ser utilizada en todos los endpoints de la API
    para garantizar un manejo consistente de las sesiones de base de datos.
    
    Yields:
        AsyncSession: Sesión de base de datos con manejo automático de commit/rollback
    """
    async with DBSession(SessionLocal) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Error en sesión de base de datos: {e}", exc_info=True)
            raise