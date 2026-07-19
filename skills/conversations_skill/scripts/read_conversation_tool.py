# skills/conversations_skill/scripts/read_conversation_tool.py

import logging
import json
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import text
from core.database import SessionLocal, ChatThread
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class ReadConversationInput(BaseModel):
    thread_id: str = Field(..., description="ID de la conversación (UUID) que se desea leer.")
    limit: Optional[int] = Field(100, description="El número máximo de mensajes a recuperar.")

class ReadConversationTool(BaseTool):
    name: str = "read_conversation_tool"
    description: str = (
        "Recupera y formatea el historial completo de mensajes intercambiados "
        "en una conversación de KAI para que el agente pueda resumirlos o continuar."
    )
    args_schema: Type[BaseModel] = ReadConversationInput
    account_id: Optional[str] = Field(None, description="ID de la cuenta, inyectado automáticamente.")

    async def _arun(
        self,
        thread_id: str,
        limit: Optional[int] = 100,
        **kwargs: Any,
    ) -> str:
        logger.info(f"Leyendo conversación {thread_id} para la cuenta {self.account_id}")
        
        try:
            async with DBSession(SessionLocal) as session:
                # Comprobar si el thread existe y pertenece a la cuenta si account_id está disponible
                if self.account_id:
                    import uuid
                    try:
                        t_uuid = uuid.UUID(thread_id)
                        acc_uuid = uuid.UUID(self.account_id)
                        check_stmt = text("SELECT id FROM chat_threads WHERE id = :thread_id AND account_id = :account_id")
                        check_res = await session.execute(check_stmt, {"thread_id": t_uuid, "account_id": acc_uuid})
                        if not check_res.first():
                            return "Error: No se encontró la conversación especificada o no tienes permiso para verla."
                    except Exception as e:
                        return f"Error al validar el ID de la conversación: {str(e)}"

                # Consultar langchain_chat_history
                stmt = text("""
                    SELECT message 
                    FROM langchain_chat_history 
                    WHERE session_id = :session_id 
                    ORDER BY id ASC 
                    LIMIT :limit
                """)
                result = await session.execute(stmt, {"session_id": str(thread_id), "limit": limit})
                rows = result.all()
                
                if not rows:
                    return f"No se encontraron mensajes en la conversación {thread_id}."
                
                output = f"Historial de mensajes de la conversación {thread_id}:\n\n"
                
                for idx, row in enumerate(rows):
                    raw_msg = row[0]
                    if not raw_msg:
                        continue
                    
                    try:
                        msg_data = json.loads(raw_msg) if isinstance(raw_msg, str) else raw_msg
                    except Exception:
                        msg_data = raw_msg
                        
                    # Extraer el rol (human/ai/system/etc)
                    msg_type = msg_data.get("type", "unknown")
                    if msg_type == "human":
                        role = "Usuario"
                    elif msg_type == "ai":
                        role = "Agente/AI"
                    elif msg_type == "system":
                        role = "Sistema"
                    else:
                        role = msg_type.capitalize()
                        
                    # Extraer el contenido
                    content = ""
                    if isinstance(msg_data, dict):
                        if "data" in msg_data and isinstance(msg_data["data"], dict) and "content" in msg_data["data"]:
                            content = msg_data["data"]["content"]
                        elif "content" in msg_data:
                            content = msg_data["content"]
                        else:
                            content = str(msg_data)
                    else:
                        content = str(msg_data)
                        
                    output += f"[{idx+1}] {role}:\n{content.strip()}\n\n"
                    output += "-" * 30 + "\n\n"
                    
                return output
        except Exception as e:
            logger.error(f"Error en ReadConversationTool: {e}", exc_info=True)
            return f"Error al leer la conversación: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
