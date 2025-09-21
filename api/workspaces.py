# api/workspaces.py

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, AsyncGenerator, cast
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Depends, status, Query, Form, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func

from core.database import SessionLocal, Workspace, ChatThread
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
    
    # Consulta para el total de workspaces
    total_stmt = select(func.count()).where(Workspace.account_id == account_uuid)
    total_result = await db.execute(total_stmt)
    total_workspaces = total_result.scalar_one()

    # Consulta para los workspaces paginados
    stmt = select(Workspace).where(Workspace.account_id == account_uuid).order_by(Workspace.created_at.asc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    workspaces = result.scalars().all()
    
    return PaginatedWorkspacesResponse(
        total=total_workspaces,
        workspaces=[WorkspaceResponse(id=str(w.id), name=w.name, system_prompt=w.system_prompt, color=w.color, created_at=w.created_at) for w in workspaces]
    )

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Obtener detalles de un workspace")
async def get_workspace(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado o no pertenece al usuario.")
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, color=workspace.color, created_at=workspace.created_at)  # type: ignore

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
    await db.refresh(new_workspace)
    return WorkspaceResponse(id=str(new_workspace.id), name=new_workspace.name, system_prompt=new_workspace.system_prompt, color=new_workspace.color, created_at=new_workspace.created_at)  # type: ignore

@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse, summary="Actualizar un workspace")
async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    
    if request.name is not None:
        setattr(workspace, 'name', request.name)
    if request.system_prompt is not None:
        setattr(workspace, 'system_prompt', request.system_prompt)
    if request.color is not None: # NEW
        setattr(workspace, 'color', request.color) # NEW
        
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, system_prompt=workspace.system_prompt, color=workspace.color, created_at=workspace.created_at)  # type: ignore

@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un workspace")
async def delete_workspace(workspace_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == uuid.UUID(workspace_id), Workspace.account_id == uuid.UUID(current_account_id)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado.")
    
    await db.delete(workspace)
    await db.commit()
    return






