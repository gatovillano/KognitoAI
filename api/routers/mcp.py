import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.dependencies import get_db_session
from core.database import Account
from utils.security import get_current_active_account
from core.mcp_manager import mcp_manager

router = APIRouter(prefix="/api/mcp-servers", tags=["mcp"])
logger = logging.getLogger(__name__)

class MCPServerBase(BaseModel):
    name: str
    transport_type: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None

class MCPServerCreate(MCPServerBase):
    pass

class MCPServerResponse(MCPServerBase):
    id: uuid.UUID
    status: str

    class Config:
        from_attributes = True

@router.get("", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MCPServer).where(MCPServer.account_id == current_user.id)
    result = await db.execute(stmt)
    servers = result.scalars().all()
    return servers

@router.post("", response_model=MCPServerResponse)
async def create_mcp_server(
    server_in: MCPServerCreate,
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    if server_in.transport_type not in ["stdio", "sse"]:
        raise HTTPException(status_code=400, detail="Invalid transport_type. Must be stdio or sse.")

    new_server = MCPServer(
        account_id=current_user.id,
        name=server_in.name,
        transport_type=server_in.transport_type,
        command=server_in.command,
        args=server_in.args,
        url=server_in.url,
        status="disconnected"
    )
    
    db.add(new_server)
    await db.commit()
    await db.refresh(new_server)
    
    return new_server

@router.put("/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: uuid.UUID,
    server_in: MCPServerCreate,
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    server = await db.get(MCPServer, server_id)
    if not server or server.account_id != current_user.id:
        raise HTTPException(status_code=404, detail="Server not found")

    server.name = server_in.name
    server.transport_type = server_in.transport_type
    server.command = server_in.command
    server.args = server_in.args
    server.url = server_in.url
    
    await db.commit()
    await db.refresh(server)
    
    # Si estaba conectado, desconectar para forzar reconexión con nuevos parámetros
    await mcp_manager.disconnect_server(str(server_id))
    
    return server

@router.delete("/{server_id}")
async def delete_mcp_server(
    server_id: uuid.UUID,
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    server = await db.get(MCPServer, server_id)
    if not server or server.account_id != current_user.id:
        raise HTTPException(status_code=404, detail="Server not found")

    await mcp_manager.disconnect_server(str(server_id))
    
    await db.delete(server)
    await db.commit()
    
    return {"status": "ok"}

@router.post("/{server_id}/connect")
async def connect_mcp_server(
    server_id: uuid.UUID,
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    server = await db.get(MCPServer, server_id)
    if not server or server.account_id != current_user.id:
        raise HTTPException(status_code=404, detail="Server not found")

    success = await mcp_manager.connect_server(server)
    if success:
        server.status = "connected"
    else:
        server.status = "error"
        
    await db.commit()
    return {"status": server.status}

@router.post("/{server_id}/disconnect")
async def disconnect_mcp_server(
    server_id: uuid.UUID,
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    server = await db.get(MCPServer, server_id)
    if not server or server.account_id != current_user.id:
        raise HTTPException(status_code=404, detail="Server not found")

    await mcp_manager.disconnect_server(str(server_id))
    server.status = "disconnected"
    await db.commit()
    return {"status": server.status}
