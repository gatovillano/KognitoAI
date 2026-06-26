from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Literal
from pydantic import BaseModel
import uuid
import logging

from core.dependencies import get_db_session
from core.memory_manager import _run_semantic_search, _run_fts_search
from utils.embeddings import get_cached_embedding
from core.reranker import Reranker

router = APIRouter()
logger = logging.getLogger(__name__)

class NoteSearchResult(BaseModel):
    note_id: str
    title: Optional[str]
    content: str
    score: Optional[float] = None
    rank_score: Optional[float] = None
    rerank_score: Optional[float] = None
    created_at: Optional[str] = None
    workspace_id: Optional[str] = None

class NoteSearchResponse(BaseModel):
    results: List[NoteSearchResult]
    total_results: int
    search_type: str

@router.get("/notes/search", response_model=NoteSearchResponse)
async def search_notes(
    query: str = Query(..., min_length=1, description="Texto de búsqueda"),
    account_id: str = Query(..., description="ID del usuario"),
    workspace_id: Optional[str] = Query(None, description="ID del workspace (opcional)"),
    search_type: Literal["vector", "text", "hybrid"] = Query("hybrid", description="Tipo de búsqueda"),
    k: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    apply_rerank: bool = Query(False, description="Aplicar reranking a los resultados"),
    db: AsyncSession = Depends(get_db_session)
) -> NoteSearchResponse:
    """
    Realiza una búsqueda en las notas del usuario usando búsqueda vectorial, textual o híbrida.
    """
    all_results = []
    semantic_results = []
    fts_results = []

    try:
        # 1. Búsqueda Semántica (Vectorial)
        if search_type in ["vector", "hybrid"]:
            query_embedding = await get_cached_embedding(query)
            if query_embedding:
                semantic_raw = await _run_semantic_search(
                    query_embedding=query_embedding,
                    account_id=account_id,
                    k=k,
                    similarity_threshold=0.3, # Umbral más bajo para notas
                    workspace_id=workspace_id,
                    content_types=["user_notes"],
                    db_session=db
                )
                for doc, score in semantic_raw:
                    semantic_results.append(NoteSearchResult(
                        note_id=doc.metadata.get("note_id"),
                        title=doc.metadata.get("title"),
                        content=doc.page_content,
                        score=score,
                        created_at=doc.metadata.get("created_at"),
                        workspace_id=doc.metadata.get("workspace_id")
                    ))

        # 2. Búsqueda de Texto (FTS)
        if search_type in ["text", "hybrid"]:
            fts_raw = await _run_fts_search(
                query=query,
                account_id=account_id,
                k=k,
                workspace_id=workspace_id,
                content_types=["user_notes"],
                db_session=db
            )
            for doc in fts_raw:
                fts_results.append(NoteSearchResult(
                    note_id=doc.metadata.get("note_id"),
                    title=doc.metadata.get("title"),
                    content=doc.page_content,
                    rank_score=doc.metadata.get("rank_score"),
                    created_at=doc.metadata.get("created_at"),
                    workspace_id=doc.metadata.get("workspace_id")
                ))

        # 3. Combinar resultados
        if search_type == "hybrid":
            # Combinar y eliminar duplicados por note_id
            combined_dict = {}
            for res in semantic_results:
                combined_dict[res.note_id] = res
            
            for res in fts_results:
                if res.note_id in combined_dict:
                    # Si ya existe, mantenemos el score semántico y añadimos el rank_score
                    combined_dict[res.note_id].rank_score = res.rank_score
                else:
                    combined_dict[res.note_id] = res
            
            all_results = list(combined_dict.values())
            # Ordenar por una combinación de scores (simple suma por ahora)
            all_results.sort(key=lambda x: (x.score or 0) + (x.rank_score or 0), reverse=True)
        elif search_type == "vector":
            all_results = semantic_results
        else:
            all_results = fts_results

        # 4. Reranking (opcional)
        if apply_rerank and all_results:
            from langchain_core.documents import Document as LCDocument
            docs_to_rerank = [
                LCDocument(page_content=res.content, metadata={"note_id": res.note_id}) 
                for res in all_results
            ]
            reranker = Reranker()
            reranked_docs = await reranker.rerank(query, docs_to_rerank, account_id=account_id)
            
            # Mapear scores de rerank de vuelta
            rerank_map = {doc.metadata["note_id"]: doc.metadata["rerank_score"] for doc in reranked_docs}
            for res in all_results:
                res.rerank_score = rerank_map.get(res.note_id)
            
            all_results.sort(key=lambda x: x.rerank_score or 0, reverse=True)

        return NoteSearchResponse(
            results=all_results[:k],
            total_results=len(all_results),
            search_type=search_type
        )

    except Exception as e:
        logger.error(f"Error en búsqueda de notas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
