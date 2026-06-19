import logging
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client

from core.database import MCPServer
from core.utils.logging_utils import AgentLogger

logger = AgentLogger(__name__)

class MCPManager:
    """
    Gestor para conexiones a servidores MCP (Model Context Protocol).
    Permite inicializar sesiones, obtener herramientas y envolverlas para LangChain.
    """
    def __init__(self):
        self._active_sessions: Dict[str, ClientSession] = {}
        self._exit_stacks: Dict[str, Any] = {}

    async def connect_server(self, server: MCPServer) -> bool:
        """Establece conexión con un servidor MCP y la guarda en sesión."""
        server_id = str(server.id)
        if server_id in self._active_sessions:
            return True

        logger.info(f"Conectando a servidor MCP: {server.name} ({server.transport_type})")
        
        try:
            from contextlib import AsyncExitStack
            exit_stack = AsyncExitStack()
            
            if server.transport_type == "stdio":
                if not server.command:
                    logger.error("Transporte stdio requiere un comando.")
                    return False
                    
                args = server.args if server.args else []
                server_params = StdioServerParameters(
                    command=server.command,
                    args=args,
                    env=None # Puedes inyectar variables de entorno si lo necesitas
                )
                
                read, write = await exit_stack.enter_async_context(stdio_client(server_params))
            elif server.transport_type == "sse":
                if not server.url:
                    logger.error("Transporte sse requiere una URL.")
                    return False
                read, write = await exit_stack.enter_async_context(sse_client(server.url))
            else:
                logger.error(f"Tipo de transporte desconocido: {server.transport_type}")
                return False

            session = await exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self._active_sessions[server_id] = session
            self._exit_stacks[server_id] = exit_stack
            logger.info(f"Servidor MCP {server.name} conectado exitosamente.")
            return True
            
        except Exception as e:
            logger.error(f"Error conectando a MCP {server.name}: {e}", exc_info=True)
            return False

    async def disconnect_server(self, server_id: str):
        """Desconecta un servidor MCP activo."""
        if server_id in self._exit_stacks:
            try:
                await self._exit_stacks[server_id].aclose()
                del self._exit_stacks[server_id]
                if server_id in self._active_sessions:
                    del self._active_sessions[server_id]
                logger.info(f"Servidor MCP {server_id} desconectado.")
            except Exception as e:
                logger.error(f"Error desconectando servidor MCP {server_id}: {e}")

    async def get_tools_for_account(self, db: AsyncSession, account_id: str) -> List[BaseTool]:
        """Obtiene todas las herramientas de todos los servidores MCP activos para una cuenta."""
        stmt = select(MCPServer).where(MCPServer.account_id == account_id, MCPServer.status == "connected")
        result = await db.execute(stmt)
        servers = result.scalars().all()
        
        all_tools = []
        for server in servers:
            server_id = str(server.id)
            if server_id not in self._active_sessions:
                success = await self.connect_server(server)
                if not success:
                    continue
            
            session = self._active_sessions[server_id]
            try:
                # Usamos el adaptador oficial de langchain para cargar las tools
                tools = await load_mcp_tools(session)
                
                # Opcional: prefijar los nombres de las tools para evitar colisiones
                for tool in tools:
                    # tool.name = f"{server.name.replace(' ', '_').lower()}_{tool.name}"
                    all_tools.append(tool)
                    
            except Exception as e:
                logger.error(f"Error cargando tools de MCP {server.name}: {e}")
                
        return all_tools

# Instancia global del gestor MCP
mcp_manager = MCPManager()
