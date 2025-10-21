# api/workspaces.py

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, AsyncGenerator, cast
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Depends, status, Query, Form, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from core.database import Account

from core.database import SessionLocal, Workspace, ChatThread, WorkspacePermission
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.agent import create_thread_for_account, force_update_thread_title
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:  # type: ignore
        try:
            yield session
        finally:
            await session.close()


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


# --- Modelos Pydantic para Workspaces ---
class WorkspaceResponse(BaseModel):
    id: str
    name: str
    system_prompt: Optional[str]
    color: Optional[str] # NEW
    created_at: datetime

class WorkspaceCreateRequest(BaseModel):
    name: str
    system_prompt: Optional[str] = None
    color: Optional[str] = None # NEW

class WorkspaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    color: Optional[str] = None # NEW
 
# --- Modelos Pydantic para Compartir Workspaces ---
class ShareWorkspaceRequest(BaseModel):
    account_id: uuid.UUID
    role: str = Field(..., pattern="^(owner|editor|viewer)$") # Validar que el rol sea uno de los permitidos

class UpdateWorkspacePermissionRequest(BaseModel):
   new_role: str = Field(..., pattern="^(owner|editor|viewer)$")

class PermissionResponse(BaseModel):
   account_id: str
   email: str
   role: str

# --- Endpoints para Workspaces ---
class PaginatedWorkspacesResponse(BaseModel):
   total: int
   workspaces: List[WorkspaceResponse]

@router.get("/workspaces", response_model=PaginatedWorkspacesResponse, summary="Listar workspaces del usuario con paginación")
async def list_workspaces(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Número de elementos a omitir"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de elementos a devolver")
):
    account_uuid = uuid.UUID(current_account_id)
    
    # Subconsulta para obtener los IDs de los workspaces permitidos
    permission_stmt = select(WorkspacePermission.workspace_id).where(WorkspacePermission.account_id == account_uuid)
    
    # Consulta para el total de workspaces
    total_stmt = select(func.count(Workspace.id)).where(Workspace.id.in_(permission_stmt))
    total_result = await db.execute(total_stmt)
    total_workspaces = total_result.scalar_one()

    # Consulta para los workspaces paginados
    stmt = select(Workspace).where(Workspace.id.in_(permission_stmt)).order_by(Workspace.created_at.asc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    workspaces = result.scalars().all()
    
    return PaginatedWorkspacesResponse(
        total=total_workspaces,
        workspaces=[WorkspaceResponse(id=str(w.id), name=w.name, system_prompt=w.system_prompt, color=w.color, created_at=w.created_at) for w in workspaces]
    )

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Obtener detalles de un workspace")
async def get_workspace(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace_uuid = uuid.UUID(workspace_id)
    account_uuid = uuid.UUID(current_account_id)

    await check_workspace_permission(db, workspace_uuid, account_uuid, required_roles=['owner', 'editor', 'viewer'])

    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_uuid))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, color=workspace.color, created_at=workspace.created_at)

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo workspace")
async def create_workspace(request: WorkspaceCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    new_workspace = Workspace(
        account_id=uuid.UUID(current_account_id),
        name=request.name,
        system_prompt=request.system_prompt,
        color=request.color # NEW
    )
    db.add(new_workspace)
    await db.commit()

    new_permission = WorkspacePermission(
        workspace_id=new_workspace.id,
        account_id=uuid.UUID(current_account_id),
        role='owner'
    )
    db.add(new_permission)
    await db.commit()
    
    await db.refresh(new_workspace)
    return WorkspaceResponse(id=str(new_workspace.id), name=new_workspace.name, system_prompt=new_workspace.system_prompt, color=new_workspace.color, created_at=new_workspace.created_at)  # type: ignore

@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Actualizar un workspace")
async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace_uuid = uuid.UUID(workspace_id)
    account_uuid = uuid.UUID(current_account_id)

    await check_workspace_permission(db, workspace_uuid, account_uuid, required_roles=['owner', 'editor'])

    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_uuid))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(workspace, key, value)
        
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, color=workspace.color, created_at=workspace.created_at)

@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un workspace")
async def delete_workspace(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace_uuid = uuid.UUID(workspace_id)
    account_uuid = uuid.UUID(current_account_id)

    await check_workspace_permission(db, workspace_uuid, account_uuid, required_roles=['owner'])

    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_uuid))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    
    await db.delete(workspace)
    await db.commit()
    return


@router.post("/workspaces/{workspace_id}/share", status_code=status.HTTP_200_OK, summary="Compartir un workspace con otro usuario")
async def share_workspace(
    workspace_id: str,
    request: ShareWorkspaceRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    workspace_uuid = uuid.UUID(workspace_id)
    current_account_uuid = uuid.UUID(current_account_id)
    invited_account_uuid = request.account_id

    # 1. Verificar permisos del usuario actual (owner o editor)
    await check_workspace_permission(db, workspace_uuid, current_account_uuid, required_roles=['owner', 'editor'])

    # 2. Verificar que el account_id del invitado existe
    account_exists = await db.scalar(select(Account).where(Account.id == invited_account_uuid))
    if not account_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El usuario invitado no existe.")

    # 3. Verificar si ya existe una entrada en WorkspacePermission para este workspace_id y account_id
    existing_permission = await db.scalar(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace_uuid,
            WorkspacePermission.account_id == invited_account_uuid
        )
    )
    if existing_permission:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario ya tiene acceso a este workspace.")

    # 4. Crear una nueva entrada en WorkspacePermission
    new_permission = WorkspacePermission(
        workspace_id=workspace_uuid,
        account_id=invited_account_uuid,
        role=request.role
    )
    db.add(new_permission)

    try:
        await db.commit()
        await db.refresh(new_permission)
        return {"message": f"Workspace compartido con éxito con el usuario {invited_account_uuid} con el rol {request.role}."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al compartir workspace: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al compartir el workspace.")

@router.put("/workspaces/{workspace_id}/permissions/{account_id}", status_code=status.HTTP_200_OK, summary="Actualizar el rol de un usuario en un workspace")
async def update_workspace_permission(
    workspace_id: str,
    account_id: str,
    request: UpdateWorkspacePermissionRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    workspace_uuid = uuid.UUID(workspace_id)
    account_to_modify_uuid = uuid.UUID(account_id)
    current_account_uuid = uuid.UUID(current_account_id)

    # 1. Verificar permisos del usuario actual (owner o editor)
    await check_workspace_permission(db, workspace_uuid, current_account_uuid, required_roles=['owner', 'editor'])

    # 2. Verificar que el account_id del usuario a modificar existe
    account_exists = await db.scalar(select(Account).where(Account.id == account_to_modify_uuid))
    if not account_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El usuario a modificar no existe.")

    # 3. Buscar la entrada existente en WorkspacePermission
    permission_to_update = await db.scalar(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace_uuid,
            WorkspacePermission.account_id == account_to_modify_uuid
        )
    )
    if not permission_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El usuario no tiene permisos en este workspace.")

    # 4. Actualizar el rol
    permission_to_update.role = request.new_role

    try:
        await db.commit()
        await db.refresh(permission_to_update)
        return {"message": f"Rol del usuario {account_to_modify_uuid} actualizado a {request.new_role} en el workspace {workspace_uuid}."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar el permiso del workspace: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al actualizar el permiso del workspace.")







@router.get("/workspaces/{workspace_id}/permissions", response_model=List[PermissionResponse], summary="Obtener la lista de permisos de un workspace")
async def get_workspace_permissions(
    workspace_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    workspace_uuid = uuid.UUID(workspace_id)
    current_account_uuid = uuid.UUID(current_account_id)

    # 1. Verificar permisos del usuario actual (owner o editor)
    await check_workspace_permission(db, workspace_uuid, current_account_uuid, required_roles=['owner', 'editor'])

    # 2. Consultar todas las entradas de WorkspacePermission para el workspace
    stmt = select(WorkspacePermission, Account).join(
        Account, WorkspacePermission.account_id == Account.id
    ).where(
        WorkspacePermission.workspace_id == workspace_uuid
    )
    result = await db.execute(stmt)
    permissions_with_accounts = result.all()

    if not permissions_with_accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron permisos para este workspace.")

    # 3. Formatear la respuesta
    response_list = []
    for permission, account in permissions_with_accounts:
        response_list.append(PermissionResponse(
            account_id=str(permission.account_id),
            email=account.email,
            role=permission.role
        ))
    return response_list


@router.delete("/workspaces/{workspace_id}/permissions/{account_id}", status_code=status.HTTP_200_OK, summary="Revocar acceso de un usuario a un workspace")
async def delete_workspace_permission(
    workspace_id: str,
    account_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    workspace_uuid = uuid.UUID(workspace_id)
    account_to_remove_uuid = uuid.UUID(account_id)
    current_account_uuid = uuid.UUID(current_account_id)

    # 1. Verificar permisos del usuario actual (owner o editor)
    await check_workspace_permission(db, workspace_uuid, current_account_uuid, required_roles=['owner', 'editor'])

    # 2. Obtener el workspace para verificar el propietario original
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_uuid))
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace no encontrado.")

    # 3. Asegurarse de que el propietario original del workspace no pueda ser eliminado
    if workspace.account_id == account_to_remove_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede revocar el acceso del propietario original del workspace.")

    # 4. Buscar la entrada existente en WorkspacePermission para eliminar
    permission_to_delete = await db.scalar(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace_uuid,
            WorkspacePermission.account_id == account_to_remove_uuid
        )
    )
    if not permission_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El usuario no tiene permisos en este workspace o ya fueron revocados.")

    # 5. Eliminar la entrada de permiso
    await db.delete(permission_to_delete)

    try:
        await db.commit()
        return {"message": f"Acceso del usuario {account_to_remove_uuid} revocado del workspace {workspace_uuid}."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al revocar el acceso del workspace: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al revocar el acceso del workspace.")
