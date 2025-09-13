# tools/get_notes_tool.py

import logging
from typing import Type, Optional, Any

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal
from core.notes_manager import NotesManager

logger = logging.getLogger(__name__)

class GetNotesInput(BaseModel):
    category: Optional[str] = Field(
        None,
        description="Filtra las notas por una categoría específica. Ejemplo: 'Trabajo', 'Ideas'."
    )
    search_query: Optional[str] = Field(
        None,
        description="Busca un texto específico en el título o contenido de las notas."
    )

class GetNotesTool(BaseTool):
    name: str = "get_notes_tool"
    description: str = ("Útil para cuando un usuario quiere ver, listar o buscar sus notas. "
                      "Permite filtrar las notas por una categoría o buscar por palabras clave.")
    args_schema: Type[BaseModel] = GetNotesInput
    account_id: str
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario.")
    telegram_id: Optional[int] = Field(None, description="El ID de usuario de Telegram.")

    async def _arun(
        self,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        if not self.account_id:
            return "Error: No se pudo identificar la cuenta del usuario."

        logger.info(f"Buscando notas para cuenta {self.account_id} con filtros: Categoria='{category}', Query='{search_query}'")

        try:
            async with SessionLocal() as session:
                notes_manager = NotesManager(session)
                if self.workspace_id:
                    notes = await notes_manager.get_notes_as_dicts(
                        account_id=self.account_id,
                        workspace_id=self.workspace_id,
                        search_query=search_query,
                        category=category
                    )
                else:
                    notes = await notes_manager.list_all_notes(
                        account_id=self.account_id,
                        search_query=search_query,
                        category=category
                    )

            if not notes:
                return "No tienes ninguna nota guardada o ninguna coincide con tu búsqueda."

            response_lines = ["Aquí están tus notas:"]
            for note in notes:
                title = f"<b>{note['title']}</b>" if note['title'] else "Nota sin título"
                team_info = f" (Equipo: {note['team_id']})" if note.get('team_shared') else ""
                response_lines.append(f"\n- <b>ID: {note['id']}</b> | {title} (Categoría: {note['category']}){team_info}\n  <i>{note['content']}</i>")

            return "\n".join(response_lines)

        except Exception as e:
            logger.error(f"Error al ejecutar get_notes para cuenta {self.account_id}: {e}", exc_info=True)
            return "Ocurrió un error inesperado al buscar tus notas."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("get_notes_tool no soporta ejecución síncrona.")
