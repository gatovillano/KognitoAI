# core/dependencies.py

"""
Dependencias centralizadas para FastAPI.

Este módulo proporciona dependencias comunes que pueden ser utilizadas
en todos los endpoints de la API, garantizando consistencia y reutilización.
"""

import logging
from typing import AsyncGenerator, List
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import SessionLocal, WorkspacePermission, Workspace, Account, get_db_session # Importar get_db_session
from utils.db_session import DBSession
from fastapi import HTTPException, status # Importar HTTPException y status
from sqlalchemy import select # Importar select
import uuid # Importar uuid

logger = logging.getLogger(__name__)

# get_db_session eliminada de aquí porque ahora se importa directamente de core.database
# para evitar el error de _AsyncGeneratorContextManager y mantener consistencia.

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