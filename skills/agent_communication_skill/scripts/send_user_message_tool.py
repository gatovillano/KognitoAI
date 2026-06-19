# tools/send_user_message_tool.py

import logging
from typing import Type, Any, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.database import SessionLocal
from core.notes_manager import NotesManager
from utils.db_session import DBSession

logger = logging.getLogger(__name__)


class SendUserMessageInput(BaseModel):
    message: str = Field(
        ...,
        description="Mensaje que el agente quiere enviar al usuario para su Bandeja de entrada.",
    )
    title: str = Field(
        default="Mensaje del agente",
        description="Título breve del mensaje para la Bandeja de entrada.",
    )
    category: str = Field(
        default="Bandeja de entrada",
        description="Categoría visual para organizar mensajes en la Bandeja.",
    )


class SendUserMessageTool(BaseTool):
    name: str = "send_user_message"
    description: str = (
        "Envía un mensaje del agente al usuario en la Bandeja de entrada. "
        "No crea una nota personal del usuario."
    )
    args_schema: Type[BaseModel] = SendUserMessageInput
    account_id: str
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario.")
    telegram_id: Optional[int] = Field(None, description="El ID de usuario de Telegram.")

    async def _arun(
        self,
        message: str,
        title: str = "Mensaje del agente",
        category: str = "Bandeja de entrada",
        **kwargs: Any,
    ) -> str:
        if not self.account_id or not message:
            return "Error: Se requiere account_id y message para enviar un mensaje al usuario."

        try:
            async with DBSession(SessionLocal) as session:
                notes_manager = NotesManager(session)
                payload = await notes_manager.add_note(
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                    title=title if title else "Mensaje del agente",
                    content=message,
                    category=category if category else "Bandeja de entrada",
                    is_agent_message=True,
                )

            return f"✅ Mensaje enviado a la Bandeja de entrada con ID {payload.get('id')}."
        except Exception as exc:
            logger.error(
                "Error enviando mensaje del agente para cuenta %s: %s",
                self.account_id[:8],
                exc,
                exc_info=True,
            )
            return f"Ocurrió un error al enviar el mensaje al usuario: {exc}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("send_user_message no soporta ejecución síncrona.")
