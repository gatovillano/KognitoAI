# tools/delete_note_tool.py

import logging
from typing import Type, Any, Optional

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal
from core.notes_manager import NotesManager

logger = logging.getLogger(__name__)

class DeleteNoteInput(BaseModel):
    note_id: int = Field(
        ...,
        description="El ID numérico único de la nota que se va a eliminar."
    )

class DeleteNoteTool(BaseTool):
    name: str = "delete_note_tool"
    description: str = (
        "Útil para borrar o eliminar permanentemente una nota existente. "
        "Requiere el ID de la nota. Si el usuario no lo proporciona, sugiere usar `get_notes_tool`."
    )
    args_schema: Type[BaseModel] = DeleteNoteInput
    account_id: str
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario.")
    telegram_id: Optional[str] = Field(None, description="El ID de usuario de Telegram.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación de Telegram.")

    async def _arun(self, note_id: int, **kwargs: Any) -> str:
        logger.info(f"Ejecutando DeleteNoteTool para cuenta '{self.account_id}' y nota ID '{note_id}'.")
        try:
            async with SessionLocal() as session:
                notes_manager = NotesManager(session)
                success = await notes_manager.delete_note(account_id=self.account_id, note_id=note_id)
            
            if success:
                logger.info(f"Herramienta de eliminación completada para cuenta '{self.account_id}'.")
                return f"¡Nota con ID {note_id} eliminada!"
            else:
                return f"No encontré ninguna nota con el ID {note_id} que te pertenezca."

        except Exception as e:
            logger.error(f"Error en DeleteNoteTool para cuenta '{self.account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar eliminar la nota: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("delete_note_tool no soporta ejecución síncrona.")
