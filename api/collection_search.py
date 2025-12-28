"""
API endpoint para búsqueda híbrida (vectorial + textual) en documentos de colecciones.
"""

import logging
from typing import Optional, List, Literal, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from core.memory_manager import _run_semantic_search, _run_fts_search
from utils.embeddings import get_cached_embedding
from core.reranker import reranker, Reranker # Importar el reranker

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchResult(BaseModel):
    """Resultado individual de búsqueda"""
    document_id: str
    file_name: str
    title: Optional[str] = None
    content: str
    topic: Optional[str] = None
    chunk_index: Optional[int] = None
    score: Optional[float] = None
    rank_score: Optional[float] = None
    rerank_score: Optional[float] = None


class CollectionSearchResponse(BaseModel):
    """Respuesta de búsqueda en colección"""
    results: List[SearchResult]
    total_results: int
    search_type: str


@router.get("/collections/search", response_model=CollectionSearchResponse)
async def search_in_collection(
    query: str = Query(..., min_length=1, description="Texto de búsqueda"),
    topic: str = Query(..., description="Nombre de la colección (topic)"),
    account_id: str = Query(..., description="ID del usuario"),
    workspace_id: Optional[str] = Query(None, description="ID del workspace (opcional)"),
    search_type: Literal["vector", "text", "hybrid"] = Query("hybrid", description="Tipo de búsqueda"),
    k: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    apply_rerank: bool = Query(False, description="Aplicar reranking a los resultados"), # Nuevo parámetro
    db: AsyncSession = Depends(get_db_session)
) -> CollectionSearchResponse:
    """
    Busca documentos dentro de una colección específica usando búsqueda vectorial, textual o híbrida.
    
    Args:
        query: Texto de búsqueda
        topic: Nombre de la colección
        account_id: ID del usuario
        workspace_id: ID del workspace (opcional)
        search_type: Tipo de búsqueda (vector, text, hybrid)
        k: Número máximo de resultados
        db: Sesión de base de datos
        
    Returns:
        CollectionSearchResponse con los resultados de la búsqueda
    """
    try:
        logger.info(f"🔍 Búsqueda en colección '{topic}' - Query: '{query[:50]}...' - Tipo: {search_type}")
        
        all_results = []
        
        # Búsqueda vectorial
        if search_type in ["vector", "hybrid"]:
            try:
                query_embedding = await get_cached_embedding(query)
                
                if query_embedding:
                    semantic_results = await _run_semantic_search(
                        query_embedding=query_embedding,
                        account_id=account_id,
                        k=k,
                        similarity_threshold=0.5,  # Umbral más bajo para más resultados
                        filter_topics=[topic],
                        workspace_id=workspace_id,
                        content_types=["user_documents"],
                        db_session=db
                    )
                    
                    for doc, score in semantic_results:
                        all_results.append(SearchResult(
                            document_id=doc.metadata.get("document_id", "unknown"),
                            file_name=doc.metadata.get("file_name", "Sin nombre"),
                            title=doc.metadata.get("title"),
                            content=doc.page_content,
                            topic=doc.metadata.get("topic"),
                            chunk_index=doc.metadata.get("chunk_index"),
                            score=float(score) if score else None
                        ))
                    
                    logger.info(f"✅ Búsqueda vectorial: {len(semantic_results)} resultados")
                else:
                    logger.warning("⚠️ No se pudo generar embedding para la consulta")
                    
            except Exception as e:
                logger.error(f"❌ Error en búsqueda vectorial: {e}", exc_info=True)
        
        # Búsqueda textual (FTS)
        if search_type in ["text", "hybrid"]:
            try:
                fts_results = await _run_fts_search(
                    query=query,
                    account_id=account_id,
                    k=k,
                    filter_topics=[topic],
                    workspace_id=workspace_id,
                    content_types=["user_documents"],
                    db_session=db
                )
                
                for doc in fts_results:
                    # Evitar duplicados si es búsqueda híbrida
                    doc_id = doc.metadata.get("document_id", "unknown")
                    if search_type == "hybrid" and any(r.document_id == doc_id for r in all_results):
                        continue
                    
                    all_results.append(SearchResult(
                        document_id=doc_id,
                        file_name=doc.metadata.get("file_name", "Sin nombre"),
                        title=doc.metadata.get("title"),
                        content=doc.page_content,
                        topic=doc.metadata.get("topic"),
                        chunk_index=doc.metadata.get("chunk_index"),
                        rank_score=doc.metadata.get("rank_score")
                    ))
                
                logger.info(f"✅ Búsqueda textual: {len(fts_results)} resultados")
                
            except Exception as e:
                logger.error(f"❌ Error en búsqueda textual: {e}", exc_info=True)
        
        # Ordenar resultados por score/rank_score
        if search_type == "vector":
            all_results.sort(key=lambda x: x.score or 0, reverse=True)
        elif search_type == "text":
            all_results.sort(key=lambda x: x.rank_score or 0, reverse=True)
        else:  # hybrid
            # Combinar scores normalizados
            all_results.sort(key=lambda x: (x.score or 0) + (x.rank_score or 0), reverse=True)
        
        # Antes de limitar, aplicar reranking si se solicita
        if apply_rerank and reranker._model is not None:
            logger.info("✨ Aplicando reranking a los resultados...")
            # Convertir SearchResult a un formato compatible con el reranker si es necesario
            # Por ahora, asumimos que el reranker puede trabajar con una lista de objetos con 'content'
            # y que el reranker modifica los objetos in-place o devuelve nuevos objetos.
            # Aquí necesitamos un wrapper para que el reranker pueda manejar los SearchResult
            
            # Crear una lista de objetos que el reranker pueda procesar
            # El reranker espera una lista de documentos con un atributo page_content
            
            # Mapear SearchResult a un formato temporal para el reranker
            class RerankerDocument:
                def __init__(self, page_content: str, metadata: Dict[str, Any]):
                    self.page_content = page_content
                    self.metadata = metadata

            reranker_input_docs = []
            for res in all_results:
                reranker_input_docs.append(RerankerDocument(
                    page_content=res.content,
                    metadata={
                        "document_id": res.document_id,
                        "file_name": res.file_name,
                        "title": res.title,
                        "topic": res.topic,
                        "chunk_index": res.chunk_index,
                        "score": res.score,
                        "rank_score": res.rank_score,
                    }
                ))

            reranked_langchain_docs = await reranker.rerank(query, reranker_input_docs)
            
            # Mapear los documentos rerankeados de vuelta a SearchResult
            reranked_results = []
            for doc in reranked_langchain_docs:
                original_result = next((res for res in all_results if res.document_id == doc.metadata["document_id"] and res.chunk_index == doc.metadata["chunk_index"]), None)
                if original_result:
                    original_result.rerank_score = doc.metadata.get('rerank_score')
                    reranked_results.append(original_result)
                else:
                    # En caso de que no se encuentre el original (lo cual no debería pasar si la lógica es correcta)
                    reranked_results.append(SearchResult(
                        document_id=doc.metadata.get("document_id", "unknown"),
                        file_name=doc.metadata.get("file_name", "Sin nombre"),
                        title=doc.metadata.get("title"),
                        content=doc.page_content,
                        topic=doc.metadata.get("topic"),
                        chunk_index=doc.metadata.get("chunk_index"),
                        score=doc.metadata.get("score"),
                        rank_score=doc.metadata.get("rank_score"),
                        rerank_score=doc.metadata.get('rerank_score')
                    ))
            
            all_results = reranked_results
            all_results.sort(key=lambda x: x.rerank_score or 0, reverse=True) # Ordenar por rerank_score
            logger.info(f"✅ Reranking aplicado. Top rerank_score: {all_results[0].rerank_score:.4f}" if all_results else "No hay resultados para rerankear.")

        # Limitar resultados después de reranking
        all_results = all_results[:k]
        
        logger.info(f"✅ Búsqueda completada: {len(all_results)} resultados totales")
        
        return CollectionSearchResponse(
            results=all_results,
            total_results=len(all_results),
            search_type=search_type
        )
        
    except Exception as e:
        logger.error(f"❌ Error en búsqueda de colección: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al realizar la búsqueda: {str(e)}"
        )
