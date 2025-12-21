# tools/add_note_tool.py

import logging
import asyncio
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool


from core.database import SessionLocal
from core.notes_manager import NotesManager

from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class AddNoteInput(BaseModel):
    content: str = Field(..., description="El contenido principal de la nota.")
    title: str = Field(default="", description="Título opcional para la nota.")
    category: str = Field(default="General", description="Categoría para organizar la nota.")

class AddNoteTool(BaseTool):
    name: str = "add_note"
    description: str = "Guarda una nota de texto en la memoria del usuario. Útil para recordar información importante, ideas o tareas."
    args_schema: Type[BaseModel] = AddNoteInput
    account_id: str
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario.")
    telegram_id: Optional[int] = Field(None, description="El ID de usuario de Telegram.")



    async def _arun(
        self,
        content: str,
        title: str = "",
        category: str = "General",
        **kwargs: Any,
    ) -> str:
        if not self.account_id or not content:
            return "Error: Se requiere el ID de la cuenta y el contenido para guardar una nota."
        
        try:
            async with DBSession(SessionLocal) as session:
                notes_manager = NotesManager(session)
                result_dict = await notes_manager.add_note(
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                    content=content,
                    title=title if title else None,
                    category=category if category else None
                )
            
            logger.info(f"Nota añadida exitosamente para la cuenta {self.account_id}.")
            note_title = result_dict.get('title', 'Sin título')
            note_id = result_dict.get('id')
            return f"✅ Nota guardada exitosamente con ID {note_id}: '{note_title}'"
        except Exception as e:
            logger.error(f"Error en AddNoteTool para la cuenta {self.account_id}: {e}", exc_info=True)
            return f"Ocurrió un error al intentar guardar la nota: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("add_note_tool no soporta ejecución síncrona.")
