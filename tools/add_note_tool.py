# tools/add_note_tool.py

import logging
import asyncio
from typing import Type, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from core.database import SessionLocal
from core.notes_manager import NotesManager

logger = logging.getLogger(__name__)

class AddNoteInput(BaseModel):
    content: str = Field(description="El contenido principal de la nota a guardar.")
    title: str = Field(default="", description="Un título opcional para la nota.")
    category: str = Field(default="General", description="Una categoría opcional para la nota.")

class AddNoteTool(BaseTool):
    name: str = "add_note_tool"
    description: str = (
        "Útil para cuando un usuario quiere crear o guardar una nueva nota, apunte o idea. "
        "Debes proporcionar el contenido y, opcionalmente, un título y una categoría."
    )
    args_schema: Type[BaseModel] = AddNoteInput
    account_id: str

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
            async with SessionLocal() as session:
                notes_manager = NotesManager(session)
                result_dict = await notes_manager.add_note(
                    account_id=self.account_id,
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
