# tools/update_note_tool.py

import logging
from typing import Type, Optional, Any, Union

from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field

from core.database import SessionLocal
from core.notes_manager import NotesManager

logger = logging.getLogger(__name__)

class UpdateNoteInput(BaseModel):
    note_id: int = Field(..., description="El ID numérico de la nota a modificar.")
    new_content: Union[str, None] = Field(None, description="El nuevo contenido para la nota.")
    new_title: Union[str, None] = Field(None, description="El nuevo título para la nota.")
    new_category: Union[str, None] = Field(None, description="La nueva categoría para la nota.")

class UpdateNoteTool(BaseTool):
    name: str = "update_note_tool"
    description: str = (
        "Útil para modificar una nota existente. Requiere el ID numérico de la nota (`note_id`). "
        "Si el usuario no proporciona el ID, infórmale que es necesario."
    )
    args_schema: Type[BaseModel] = UpdateNoteInput
    account_id: str

    async def _arun(
        self,
        note_id: int,
        new_content: Optional[str] = None,
        new_title: Optional[str] = None,
        new_category: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        logger.info(f"Ejecutando UpdateNoteTool para nota {note_id} de cuenta {self.account_id[:8]}...")
        try:
            async with SessionLocal() as session:
                notes_manager = NotesManager(session)
                success = await notes_manager.update_note(
                    account_id=self.account_id,
                    note_id=note_id,
                    new_content=new_content,
                    new_title=new_title,
                    new_category=new_category
                )
            
            if success:
                return f"¡Nota con ID {note_id} actualizada correctamente!"
            else:
                return f"No encontré ninguna nota con el ID {note_id} que te pertenezca."

        except Exception as e:
            logger.error(f"Error en UpdateNoteTool para cuenta {self.account_id[:8]}: {e}", exc_info=True)
            return f"Ocurrió un error inesperado al actualizar la nota: {e}"

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("La herramienta 'update_note_tool' solo soporta ejecución asíncrona.")
