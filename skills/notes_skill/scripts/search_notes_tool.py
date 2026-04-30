# tools/search_notes_tool.py

import logging
import asyncio
from typing import Type, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import text, select

from core.database import SessionLocal, Nota
from utils.embeddings import get_embedding_model
from utils.db_session import DBSession
from core.citation_models import ToolOutputWithSources, create_document_source, create_note_source, SourceType

logger = logging.getLogger(__name__) 

class SearchNotesInput(BaseModel):
    query: str = Field(description="La consulta de búsqueda para encontrar notas relevantes.")
    account_id: str = Field(description="ID de la cuenta del usuario.")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo para filtrar notas.")
    team_id: Optional[str] = Field(None, description="ID del equipo para filtrar notas.")
    k: int = Field(default=5, description="Número de notas a recuperar.")

class SearchNotesTool(BaseTool):
    name: str = "search_notes_tool"
    description: str = (
        "Útil para buscar notas existentes por contenido o título. "
        "Requiere una consulta de búsqueda y el ID de la cuenta. "
        "Puede filtrar por ID de espacio de trabajo o ID de equipo."
    )
    args_schema: Type[BaseModel] = SearchNotesInput
    account_id: Optional[str] = Field(None, description="ID de la cuenta a la que pertenece la nota.")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo al que pertenece la nota.")
    team_id: Optional[str] = Field(None, description="ID del equipo al que pertenece la nota.")
    telegram_id: Optional[str] = Field(None, description="ID de Telegram del usuario.")

    async def _arun(
        self,
        query: str,
        account_id: str,
        workspace_id: Optional[str] = None,
        team_id: Optional[str] = None,
        k: int = 5,
        **kwargs: Any,
    ) -> ToolOutputWithSources:
        logger.info(f"🔍 Buscando notas para la cuenta {account_id} con la consulta: '{query}'")
        try:
            embedding_model = get_embedding_model()
            if not embedding_model:
                logger.error("Los Embeddings no están inicializados. No se puede buscar notas.")
                return ToolOutputWithSources(context_for_llm="Error: Modelo de embeddings no inicializado.", sources=[])

            query_embedding = await embedding_model.aembed_query(query)

            async with DBSession(SessionLocal) as session:
                # Construir la consulta SQL para búsqueda semántica en la tabla 'notas'
                # Asegúrate de que la columna 'embedding' en la tabla 'notas' sea de tipo Vector
                sql_query = text(f"""
                    SELECT
                        id,
                        title,
                        content,
                        category,
                        (embedding <-> CAST(:query_embedding AS vector)) AS similarity_score
                    FROM notas
                    WHERE account_id = :account_id
                """)
                
                params = {
                    "query_embedding": query_embedding,
                    "account_id": account_id,
                }

                filter_clauses = []
                if workspace_id:
                    filter_clauses.append("workspace_id = :workspace_id")
                    params["workspace_id"] = workspace_id
                if team_id:
                    filter_clauses.append("team_id = :team_id")
                    params["team_id"] = team_id
                
                if filter_clauses:
                    sql_query = text(f"""
                        SELECT
                            id,
                            title,
                            content,
                            category,
                            (embedding <-> CAST(:query_embedding AS vector)) AS similarity_score
                        FROM notas
                        WHERE account_id = :account_id
                        AND {" AND ".join(filter_clauses)}
                    """)

                sql_query = text(f"""
                    {sql_query.text}
                    ORDER BY similarity_score
                    LIMIT :k
                """)
                params["k"] = k

                results = await session.execute(sql_query, params)
                notes = results.fetchall()

            if not notes:
                logger.info(f"No se encontraron notas para la consulta '{query}'.")
                return ToolOutputWithSources(context_for_llm="No se encontraron notas relevantes.", sources=[])

            formatted_notes = []
            sources = []
            for i, note in enumerate(notes):
                note_id, title, content, category, similarity_score = note
                # Incluir la cita numérica en el contexto para el LLM
                formatted_notes.append(
                    f"[{i + 1}] Título: {title if title else 'Sin título'} (Categoría: {category}, ID: {note_id})"
                )
                sources.append(create_note_source(
                    source_id=i + 1,
                    title=title if title else f"Nota {note_id}",
                    note_id=str(note_id), # Pasar el ID de la nota
                    snippet=content,
                    metadata={
                        "category": category,
                        "similarity_score": similarity_score
                    }
                ))
            
            context_for_llm = "Notas relevantes encontradas:\n" + "\n---\n".join(formatted_notes)
            logger.info(f"✅ Notas encontradas para la consulta '{query}'.")
            return ToolOutputWithSources(context_for_llm=context_for_llm, sources=sources)

        except Exception as e:
            logger.info(f"❌ Error en SearchNotesTool para la cuenta {account_id}: {e}", exc_info=True)
            return ToolOutputWithSources(context_for_llm=f"Ocurrió un error al buscar notas: {e}", sources=[])

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("search_notes_tool no soporta ejecución síncrona.")
