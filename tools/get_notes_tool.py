# tools/get_notes_tool.py

import logging
from typing import Type, Optional, Any

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal
from core.notes_manager import NotesManager

from utils.db_session import DBSession

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

from core.citation_models import ToolOutputWithSources, create_note_source

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
        limit: int = 10,
        offset: int = 0,
        **kwargs: Any,
    ) -> ToolOutputWithSources:
        if not self.account_id:
            return ToolOutputWithSources(context_for_llm="Error: Se requiere el ID de la cuenta para obtener las notas.", sources=[])

        logger.info(f"Buscando notas para cuenta {self.account_id} con filtros: Categoria='{category}', Query='{search_query}'")

        try:
            async with DBSession(SessionLocal) as session:
                notes_manager = NotesManager(session)
                notes_list = []
                total_notes = 0

                if self.workspace_id:
                    total_notes, notes_list = await notes_manager.get_notes_as_dicts(
                        account_id=self.account_id,
                        workspace_id=self.workspace_id,
                        search_query=search_query,
                        category=category
                    )
                else:
                    total_notes, notes_list = await notes_manager.list_all_notes(
                        account_id=self.account_id,
                        search_query=search_query,
                        category=category
                    )

            if not notes_list:
                return ToolOutputWithSources(context_for_llm="No tienes ninguna nota guardada o ninguna coincide con tu búsqueda.", sources=[])

            response_lines = [f"Encontré {total_notes} nota(s). Aquí están las primeras:"]
            sources = []
            
            for i, note in enumerate(notes_list):
                title = note.get('title') or "Nota sin título"
                content = note.get('content') or ""
                note_id = str(note.get('id'))
                category_val = note.get('category') or "Sin categoría"
                
                # Crear la representación de texto para el LLM
                team_info = f" (Equipo: {note['team_id']})" if note.get('team_shared') else ""
                workspace_info = f" (Workspace: {note.get('workspace_name')})" if note.get('workspace_id') else ""
                response_lines.append(f"\n- <b>ID: {note_id}</b> | {title} (Categoría: {category_val}){team_info}{workspace_info}\n  <i>{content}</i>")
                
                # Crear el objeto Source estructurado
                sources.append(create_note_source(
                    source_id=i + 1,
                    title=title,
                    note_id=note_id,
                    snippet=content,
                    metadata={
                        "category": category_val,
                        "team_id": note.get('team_id'),
                        "workspace_id": note.get('workspace_id')
                    }
                ))

            context_for_llm = "\n".join(response_lines)
            return ToolOutputWithSources(context_for_llm=context_for_llm, sources=sources)

        except Exception as e:
            logger.error(f"Error al ejecutar get_notes para cuenta {self.account_id}: {e}", exc_info=True)
            return ToolOutputWithSources(context_for_llm="Ocurrió un error inesperado al buscar tus notas.", sources=[])

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("get_notes_tool no soporta ejecución síncrona.")
