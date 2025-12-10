# core/dependencies.py

"""
Dependencias centralizadas para FastAPI.

Este módulo proporciona dependencias comunes que pueden ser utilizadas
en todos los endpoints de la API, garantizando consistencia y reutilización.
"""

import logging
from typing import AsyncGenerator, List
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import SessionLocal, WorkspacePermission, Workspace, Account # Importar WorkspacePermission, Workspace, Account
from utils.db_session import DBSession
from fastapi import HTTPException, status # Importar HTTPException y status
from sqlalchemy import select # Importar select
import uuid # Importar uuid

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

async def check_workspace_permission(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    account_id: uuid.UUID,
    required_roles: List[str]
):
    """
    Verifica si un usuario tiene el permiso requerido en un workspace.
    Lanza HTTPException 403 si el permiso es denegado.
    """
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