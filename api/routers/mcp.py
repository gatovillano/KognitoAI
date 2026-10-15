import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.dependencies import get_db_session
from core.database import Account, MCPServer
from utils.security import get_current_active_account
from core.mcp_manager import mcp_manager

try:
    from langchain_mcp_adapters.tools import load_mcp_tools
except ImportError:
    load_mcp_tools = None

router = APIRouter(prefix="/api/mcp-servers", tags=["mcp"])
logger = logging.getLogger(__name__)

class MCPServerBase(BaseModel):
    name: str
    transport_type: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    env: Optional[dict] = None
    headers: Optional[dict] = None

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
    allowed = {"stdio", "sse", "http", "streamable", "streamable-http", "streamable_http"}
    if server_in.transport_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid transport_type. Must be stdio, sse or http/streamable-http.")

    new_server = MCPServer(
        account_id=current_user.id,
        name=server_in.name,
        transport_type=server_in.transport_type,
        command=server_in.command,
        args=server_in.args,
        url=server_in.url,
        env=server_in.env,
        headers=server_in.headers,
        status="disconnected"
    )
    
    db.add(new_server)
    await db.commit()
    await db.refresh(new_server)
    
    return new_server

async def _load_tools_from_session(session) -> list[dict]:
    """Carga herramientas desde una sesión MCP activa usando langchain_mcp_adapters."""
    if not load_mcp_tools:
        logger.error("langchain_mcp_adapters no está disponible")
        return []
    tools = await load_mcp_tools(session)
    result: list[dict] = []
    for tool in tools:
        try:
            desc = getattr(tool, "description", None) or getattr(tool, "desc", None) or tool.__doc__ or ""
            desc_str = str(desc)
        except Exception as e:
            logger.warning(f"Error leyendo descripción de herramienta {getattr(tool, 'name', '?')}: {e}")
            desc_str = ""
        result.append({
            "name": getattr(tool, "name", None) or "unknown",
            "description": desc_str,
        })
    return result


@router.get("/tools")
async def list_mcp_server_tools(
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    """Devuelve todas las herramientas disponibles en los servidores MCP conectados."""
    try:
        stmt = select(MCPServer).where(MCPServer.account_id == current_user.id, MCPServer.status == "connected")
        result = await db.execute(stmt)
        servers = result.scalars().all()

        all_tools: list[dict] = []
        for server in servers:
            server_id = str(server.id)
            if not mcp_manager.is_session_alive(server_id):
                logger.info(f"Reconectando servidor MCP {server.name} (sesión no viva)...")
                success = await mcp_manager.connect_server(server)
                if not success:
                    continue

            session = mcp_manager._active_sessions.get(server_id)
            if session is None:
                continue
            try:
                tools = await _load_tools_from_session(session)
                for tool in tools:
                    tool["server"] = server.name
                    tool["server_id"] = server_id
                    all_tools.append(tool)
            except Exception as e:
                logger.error(f"Error cargando tools de MCP {server.name}: {e}")

        return {"count": len(all_tools), "tools": all_tools}
    except Exception as e:
        logger.error(f"Error obteniendo herramientas MCP: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo herramientas MCP: {e}")


@router.get("/{server_id}/tools")
async def list_mcp_server_tools_by_id(
    server_id: uuid.UUID,
    current_user: Account = Depends(get_current_active_account),
    db: AsyncSession = Depends(get_db_session)
):
    """Devuelve las herramientas de un servidor MCP concreto, intentando conectar si es necesario."""
    server = await db.get(MCPServer, server_id)
    if not server or server.account_id != current_user.id:
        raise HTTPException(status_code=404, detail="Server not found")

    sid = str(server.id)
    try:
        if not mcp_manager.is_session_alive(sid):
            logger.info(f"Conectando servidor MCP {server.name} para listar herramientas...")
            success = await mcp_manager.connect_server(server)
            if not success:
                server.status = "error"
                await db.commit()
                return {
                    "count": 0,
                    "tools": [],
                    "server_id": sid,
                    "server": server.name,
                    "status": server.status,
                    "error": "No se pudo conectar al servidor MCP",
                }

        session = mcp_manager._active_sessions.get(sid)
        if session is None:
            return {
                "count": 0,
                "tools": [],
                "server_id": sid,
                "server": server.name,
                "status": server.status,
                "error": "Sesión MCP no disponible",
            }

        tools = await _load_tools_from_session(session)
        for tool in tools:
            tool["server"] = server.name
            tool["server_id"] = sid

        if server.status != "connected":
            server.status = "connected"
            await db.commit()

        return {
            "count": len(tools),
            "tools": tools,
            "server_id": sid,
            "server": server.name,
            "status": "connected",
        }
    except Exception as e:
        logger.error(f"Error obteniendo herramientas del servidor MCP {server.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo herramientas MCP: {e}")



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
    if server_in.env is not None:
        server.env = server_in.env
    if server_in.headers is not None:
        server.headers = server_in.headers
    
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
