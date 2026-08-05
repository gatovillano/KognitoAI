# core/dependencies.py

"""
Dependencias centralizadas para FastAPI.

Este módulo proporciona dependencias comunes que pueden ser utilizadas
en todos los endpoints de la API, garantizando consistencia y reutilización.
"""

import logging
from typing import AsyncGenerator, List
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

logger = logging.getLogger(__name__)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI para obtener una sesión de base de datos asíncrona.
    Este es el patrón estándar para la inyección de dependencias de sesiones en FastAPI.
    
    YIELD:
        - AsyncSession: La sesión de base de datos
    """
    from core.database import SessionLocal, log_pool_status
    
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        logger.error(f"Error en la sesión de la base de datos: {e}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()
        await log_pool_status()


async def check_workspace_permission(
    db: AsyncSession = Depends(get_db_session),
    workspace_id: uuid.UUID = None,
    account_id: uuid.UUID = None,
    required_roles: List[str] = None
):
    """
    Verifica si un usuario tiene el permiso requerido en un workspace.
    Lanza HTTPException 403 si el permiso es denegado.
    """
    from core.database import WorkspacePermission
    
    stmt = select(WorkspacePermission).where(
        WorkspacePermission.workspace_id == workspace_id,
        WorkspacePermission.account_id == account_id
    )
    result = await db.execute(stmt)
    permission = result.scalar_one_or_none()

    if not permission or permission.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso denegado. No tienes acceso a este workspace o tu rol no es el adecuado."
        )
    return True