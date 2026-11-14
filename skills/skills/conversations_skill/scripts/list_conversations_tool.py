# skills/conversations_skill/scripts/list_conversations_tool.py

import logging
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import SessionLocal, ChatThread
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class ListConversationsInput(BaseModel):
    limit: Optional[int] = Field(10, description="El número máximo de conversaciones a listar.")
    search_query: Optional[str] = Field(None, description="Consulta opcional para buscar conversaciones por título.")

class ListConversationsTool(BaseTool):
    name: str = "list_conversations_tool"
    description: str = (
        "Lista los hilos de conversación recientes del usuario actual en KAI. "
        "Permite buscar por título e inyecta automáticamente el ID de la cuenta."
    )
    args_schema: Type[BaseModel] = ListConversationsInput
    account_id: Optional[str] = Field(None, description="ID de la cuenta a la que pertenecen las conversaciones, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace, inyectado automáticamente.")

    async def _arun(
        self,
        limit: Optional[int] = 10,
        search_query: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        logger.info(f"Listando conversaciones para la cuenta: {self.account_id}")
        if not self.account_id:
            return "Error: No se inyectó el ID de cuenta de usuario."

        import uuid
        try:
            acc_uuid = uuid.UUID(self.account_id)
        except Exception:
            return f"Error: ID de cuenta inválido: {self.account_id}"

        try:
            async with DBSession(SessionLocal) as session:
                stmt = select(ChatThread).where(ChatThread.account_id == acc_uuid)
                
                if search_query:
                    stmt = stmt.where(ChatThread.title.ilike(f"%{search_query}%"))
                    
                stmt = stmt.order_by(ChatThread.created_at.desc()).limit(limit)
                
                result = await session.execute(stmt)
                threads = result.scalars().all()
                
                if not threads:
                    return "No se encontraron hilos de conversación."
                
                output = "Conversaciones recientes en KAI:\n\n"
                for t in threads:
                    created_str = t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "Fecha de creación no disponible"
                    output += f"- 💬 Título: '{t.title}' | ID: {t.id} | Creado: {created_str} | Plataforma: {t.platform}\n"
                return output
        except Exception as e:
            logger.error(f"Error en ListConversationsTool: {e}", exc_info=True)
            return f"Error al listar conversaciones: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
