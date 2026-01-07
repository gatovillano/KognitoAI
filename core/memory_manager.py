
# telegram_bot/memory/memory_manager.py

"""
Gestor de Memoria a Largo Plazo y Perfil del Usuario.

Este módulo es responsable de todas las interacciones con la memoria persistente
del usuario, que se divide en dos tipos principales:
1.  **Perfil Estructurado:** Datos clave-valor sobre el usuario (nombre, gustos, etc.),
    almacenados en la tabla `profiles`.
2.  **Memoria Vectorial (RAG):** Fragmentos de texto no estructurado (de documentos,
    conversaciones, etc.) que se convierten en embeddings y se almacenan en una
    base de datos vectorial (pgvector) para su posterior recuperación semántica.

En la nueva arquitectura universal, todas las funciones aquí operan con el
`account_id` (UUID) como identificador principal del usuario, garantizando la
independencia de la plataforma. El motor de embeddings ha sido migrado a
OllamaEmbeddings para usar modelos locales.
"""

import logging
import asyncio
import json
from sqlalchemy import select, text, create_engine, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Union, Dict, Any, Tuple
from pydantic.fields import FieldInfo
import datetime

import uuid
from langchain_core.documents import Document as LCDocument # Renombrado para evitar conflicto
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import Table, MetaData, update
from sqlalchemy.orm import selectinload, joinedload
from langchain_core.retrievers import BaseRetriever # Nueva importación

from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken # Importar tiktoken

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

from core.database import (
    Perfil,
    SessionLocal,
    Account,
    engine,
    LangchainPgCollection,
    UserDocumentTopic,
    GitHubDocument,
    ContactProfile, # <--- NUEVA IMPORTACIÓN
    Nota # <--- AÑADIDO PARA LA BÚSQUEDA DE NOTAS
)
from utils.db_session import DBSession
from utils.embeddings import get_embedding_model
from core.config import settings
from urllib.parse import unquote
from core.citation_models import ToolOutputWithSources, Source, SourceType, create_document_source, format_context_with_sources
from core.reranker import Reranker # Importación aquí para evitar circularidad

logger = logging.getLogger(__name__)

CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap
GLOBAL_COLLECTION_NAME = settings.global_collection_name
USER_MEMORIES_PREFIX = "user_memories_"
USER_DOCUMENTS_PREFIX = "user_documents_"

PGVECTOR_SYNC_ENGINE = create_engine(settings.database_url or "postgresql://postgres:postgres@localhost:5432/postgres")


async def _run_semantic_search(
    query_embedding: List[float],
    account_id: str,
    k: int,
    similarity_threshold: float,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
    content_types: Optional[List[str]] = None,
    category: Optional[str] = None,
    explicit_document_ids: Optional[List[str]] = None,
    db_session: Optional[AsyncSession] = None, # Optimization: Reuse session
) -> List[Tuple[LCDocument, float]]:
    """
    Realiza una búsqueda semántica en la base de datos vectorial, filtrando por account_id y content_types.
    """
    processed_results: List[Tuple[LCDocument, float]] = []
    
    try:
        # Búsqueda en langchain_pg_embedding
        if content_types and any(ct in ["user_memories", "user_documents"] for ct in content_types):
            sql_query = """
                SELECT
                    document,
                    cmetadata,
                    topic,
                    category,
                    workspace_id,
                    (embedding <-> CAST(:query_embedding AS vector)) AS similarity_score
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
            """
            query_params: Dict[str, Any] = {
                "account_id": account_id,
                "query_embedding": query_embedding,
            }

            filter_clauses = []
            # Lógica para workspace_id:
            # - Si workspace_id es un UUID válido (string no vacío), filtrar por ese workspace_id.
            # - Si workspace_id es explícitamente None, filtrar por workspace_id IS NULL (memorias personales).
            # - Si workspace_id no se proporciona (o es una cadena vacía), NO filtrar por workspace_id,
            #   lo que significa que se buscarán memorias tanto con como sin workspace_id.
            if workspace_id is not None and workspace_id != "":
                filter_clauses.append("workspace_id = :workspace_id")
                query_params["workspace_id"] = workspace_id
            elif workspace_id == "": # Caso en que se pasa explícitamente una cadena vacía para buscar NULLs
                filter_clauses.append("workspace_id IS NULL")
            # Si workspace_id es None (el valor por defecto), no se añade ninguna cláusula de filtro para workspace_id.
            
            if filter_topics:
                filter_clauses.append("topic = ANY(:filter_topics)")
                query_params["filter_topics"] = filter_topics

            if explicit_document_ids:
                filter_clauses.append("cmetadata->>'document_id' = ANY(:explicit_document_ids)")
                query_params["explicit_document_ids"] = explicit_document_ids

            if content_types:
                searchable_content_types = [ct for ct in content_types if ct in ["user_memories", "user_documents"]]
                if searchable_content_types:
                    filter_clauses.append("content_type = ANY(:content_types)")
                    query_params["content_types"] = searchable_content_types

            if category:
                filter_clauses.append("category = :category")
                query_params["category"] = category

            if filter_clauses:
                sql_query += " AND " + " AND ".join(filter_clauses)

            sql_query += " ORDER BY similarity_score LIMIT :k"
            query_params["k"] = k

            if db_session:
                logger.info(f"DEBUG SQL (Semantic Search): Query: {sql_query}") # Nuevo log
                logger.info(f"DEBUG SQL (Semantic Search): Params: {query_params}") # Nuevo log
                results = await db_session.execute(text(sql_query), query_params)
                rows = results.fetchall()
            else:
                async with DBSession(SessionLocal) as session:
                    logger.info(f"DEBUG SQL (Semantic Search): Query: {sql_query}") # Nuevo log
                    logger.info(f"DEBUG SQL (Semantic Search): Params: {query_params}") # Nuevo log
                    results = await session.execute(text(sql_query), query_params)
                    rows = results.fetchall()

            for row in rows:
                doc_content, doc_metadata, topic, cat, ws_id, similarity_score = row
                
                if isinstance(doc_metadata, str):
                    try:
                        doc_metadata = json.loads(doc_metadata)
                    except json.JSONDecodeError:
                        doc_metadata = {}
                elif not isinstance(doc_metadata, dict):
                    doc_metadata = {}

                if topic is not None: doc_metadata['topic'] = topic
                if cat is not None: doc_metadata['category'] = cat
                if ws_id is not None: doc_metadata['workspace_id'] = str(ws_id)
                
                processed_results.append((LCDocument(page_content=doc_content, metadata=doc_metadata), similarity_score))

        # Búsqueda en la tabla de Notas si se especifica
        if content_types and "user_notes" in content_types:
            note_clauses = [Nota.account_id == uuid.UUID(account_id)]
            
            # Filtrar por workspace_id si se proporciona
            if workspace_id is not None and workspace_id != "":
                note_clauses.append(Nota.workspace_id == uuid.UUID(workspace_id))
            elif workspace_id == "":
                note_clauses.append(Nota.workspace_id.is_(None))

            note_query = select(Nota, (Nota.embedding.l2_distance(query_embedding)).label("similarity_score")).where(
                *note_clauses
            ).order_by("similarity_score").limit(k)
            
            if db_session:
                logger.info(f"DEBUG SQL (Notes Semantic Search): Query: {note_query}") # Nuevo log
                logger.info(f"DEBUG SQL (Notes Semantic Search): Params: {note_query.compile().params}") # Nuevo log
                note_results = await db_session.execute(note_query)
                note_rows = note_results.all()
            else:
                async with DBSession(SessionLocal) as session:
                    logger.info(f"DEBUG SQL (Notes Semantic Search): Query: {note_query}") # Nuevo log
                    logger.info(f"DEBUG SQL (Notes Semantic Search): Params: {note_query.compile().params}") # Nuevo log
                    note_results = await session.execute(note_query)
                    note_rows = note_results.all()

                for nota, score in note_rows:
                    # El score de l2_distance es menor cuanto más similar, lo convertimos a similitud
                    similarity = 1 - score
                    if similarity >= similarity_threshold:
                        doc = LCDocument(
                            page_content=nota.content,
                            metadata={
                                "type": "user_notes",
                                "note_id": str(nota.id),
                                "title": nota.title,
                                "created_at": nota.created_at.isoformat(),
                                "document_id": f"note_{nota.id}",
                                "file_name": f"Nota: {nota.title}"
                            }
                        )
                        processed_results.append((doc, similarity))

        # Ordenar todos los resultados combinados por score
        processed_results.sort(key=lambda x: x[1], reverse=True)
        
        return processed_results[:k]

    except Exception as e:
        logger.error(f"❌ Error en búsqueda semántica: {e}", exc_info=True)
        return []

async def _run_fts_search(
    query: str,
    account_id: str,
    k: int,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
    content_types: Optional[List[str]] = None,
    category: Optional[str] = None,
    explicit_document_ids: Optional[List[str]] = None,
    db_session: Optional[AsyncSession] = None, # Optimization: Reuse session
) -> List[LCDocument]:
    """
    Realiza una búsqueda de texto completo (FTS) en la base de datos, filtrando por account_id y content_types.
    """
    processed_results: List[LCDocument] = []
    
    try:
        # Búsqueda en langchain_pg_embedding
        if content_types and any(ct in ["user_memories", "user_documents"] for ct in content_types):
            sql_query = f"""
                SELECT
                    document,
                    cmetadata,
                    topic,
                    category,
                    workspace_id,
                    ts_rank(text_search_vector, plainto_tsquery('spanish', :query_fts)) AS rank_score
                FROM langchain_pg_embedding
                WHERE account_id = :account_id AND text_search_vector @@ plainto_tsquery('spanish', :query_fts)
            """
            query_params: Dict[str, Any] = {
                "account_id": account_id,
                "query_fts": query.replace('\x00', '')[:2000], # Limpiar NUL bytes y truncar a 2000 caracteres
            }

            filter_clauses = []
            if workspace_id:
                filter_clauses.append("workspace_id = :workspace_id")
                query_params["workspace_id"] = workspace_id
            else:
                filter_clauses.append("workspace_id IS NULL")
            
            if filter_topics:
                filter_clauses.append("topic = ANY(:filter_topics)")
                query_params["filter_topics"] = filter_topics

            if explicit_document_ids:
                filter_clauses.append("cmetadata->>'document_id' = ANY(:explicit_document_ids)")
                query_params["explicit_document_ids"] = explicit_document_ids

            if content_types:
                searchable_content_types = [ct for ct in content_types if ct in ["user_memories", "user_documents"]]
                if searchable_content_types:
                    filter_clauses.append("content_type = ANY(:content_types)")
                    query_params["content_types"] = searchable_content_types

            if category:
                filter_clauses.append("category = :category")
                query_params["category"] = category

            if filter_clauses:
                sql_query += " AND " + " AND ".join(filter_clauses)

            sql_query += " ORDER BY rank_score DESC LIMIT :k"
            query_params["k"] = k

            if db_session:
                logger.info(f"DEBUG SQL (FTS Search): Query: {sql_query}") # Nuevo log
                logger.info(f"DEBUG SQL (FTS Search): Params: {query_params}") # Nuevo log
                results = await db_session.execute(text(sql_query), query_params)
                rows = results.fetchall()
            else:
                async with DBSession(SessionLocal) as session:
                    logger.info(f"DEBUG SQL (FTS Search): Query: {sql_query}") # Nuevo log
                    logger.info(f"DEBUG SQL (FTS Search): Params: {query_params}") # Nuevo log
                    results = await session.execute(text(sql_query), query_params)
                    rows = results.fetchall()

            for row in rows:
                doc_content, doc_metadata, topic, cat, ws_id, rank_score = row
                
                if isinstance(doc_metadata, str):
                    try:
                        doc_metadata = json.loads(doc_metadata)
                    except json.JSONDecodeError:
                        doc_metadata = {}
                elif not isinstance(doc_metadata, dict):
                    doc_metadata = {}

                if topic is not None: doc_metadata['topic'] = topic
                if cat is not None: doc_metadata['category'] = cat
                if ws_id is not None: doc_metadata['workspace_id'] = str(ws_id)
                doc_metadata['rank_score'] = rank_score

                processed_results.append(LCDocument(page_content=doc_content, metadata=doc_metadata))

        # Búsqueda en la tabla de Notas si se especifica
        if content_types and "user_notes" in content_types:
            note_clauses = [
                Nota.account_id == uuid.UUID(account_id),
                Nota.text_search_vector.op('@@')(func.plainto_tsquery('spanish', query))
            ]

            # Filtrar por workspace_id si se proporciona
            if workspace_id is not None and workspace_id != "":
                note_clauses.append(Nota.workspace_id == uuid.UUID(workspace_id))
            elif workspace_id == "":
                note_clauses.append(Nota.workspace_id.is_(None))

            note_query = select(
                Nota,
                func.ts_rank(Nota.text_search_vector, func.plainto_tsquery('spanish', query)).label("rank_score")
            ).where(
                *note_clauses
            ).order_by(text("rank_score DESC")).limit(k)

            if db_session:
                logger.info(f"DEBUG SQL (Notes FTS Search): Query: {note_query}") # Nuevo log
                logger.info(f"DEBUG SQL (Notes FTS Search): Params: {note_query.compile().params}") # Nuevo log
                note_results = await db_session.execute(note_query)
                note_rows = note_results.all()
            else:
                async with DBSession(SessionLocal) as session:
                    logger.info(f"DEBUG SQL (Notes FTS Search): Query: {note_query}") # Nuevo log
                    logger.info(f"DEBUG SQL (Notes FTS Search): Params: {note_query.compile().params}") # Nuevo log
                    note_results = await session.execute(note_query)
                    note_rows = note_results.all()

                for nota, score in note_rows:
                    doc = LCDocument(
                        page_content=nota.content,
                        metadata={
                            "type": "user_notes",
                            "note_id": str(nota.id),
                            "title": nota.title,
                            "created_at": nota.created_at.isoformat(),
                            "rank_score": score,
                            "document_id": f"note_{nota.id}",
                            "file_name": f"Nota: {nota.title}"
                        }
                    )
                    processed_results.append(doc)

        # Ordenar todos los resultados combinados por rank_score
        processed_results.sort(key=lambda doc: doc.metadata.get('rank_score', 0), reverse=True)

        return processed_results[:k]

    except Exception as e:
        logger.error(f"❌ Error en búsqueda FTS: {e}", exc_info=True)
        return []


async def get_relevant_memories(
    account_id: str,
    query: str,
    k: int = 20,
    workspace_id: Optional[str] = None,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    hybrid_search: bool = True,
    bm25_weight: float = settings.hybrid_search_bm25_weight,
    reranking: bool = True,
    content_types: Optional[List[str]] = None, # Cambiado a lista
    category: Optional[str] = None,
    similarity_threshold: float = 0.7,
    explicit_document_ids: Optional[List[str]] = None,
) -> ToolOutputWithSources:
    """
    Recupera memorias, documentos y/o notas relevantes, los formatea para citación
    y devuelve un objeto ToolOutputWithSources.
    """
    logger.info(
        f"🔍 Buscando memorias/documentos relevantes para la cuenta {account_id} con la consulta: '{query[:50]}...'"
    )
    try:
        # Definir los content_types que se buscarán.
        if content_types is None:
            content_types = ["user_memories", "user_documents", "user_notes"]
        
        # Asegurar que explicit_document_ids sean strings para evitar errores de validación de Pydantic
        if explicit_document_ids:
            explicit_document_ids = [str(doc_id) for doc_id in explicit_document_ids]
        
        class KognitoPGVectorRetriever(BaseRetriever):
            
            # collection_id: uuid.UUID # Eliminado
            k: int
            similarity_threshold: float
            filter_topics: Optional[List[str]]
            filter_document_ids: Optional[List[str]]
            account_id: str
            workspace_id: Optional[str]
            content_types: Optional[List[str]] # Nuevo
            category: Optional[str]
            explicit_document_ids: Optional[List[str]]
            db_session: Optional[AsyncSession] # Optimization

            def _get_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                return []

            async def _aget_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                from utils.embeddings import get_cached_embedding
                query_embedding = await get_cached_embedding(query_str)

                if query_embedding is None:
                    return []
                
                semantic_results_with_scores = await _run_semantic_search(
                    query_embedding=query_embedding,
                    account_id=self.account_id,
                    k=self.k,
                    similarity_threshold=self.similarity_threshold,
                    # collection_id=self.collection_id, # Eliminado
                    filter_topics=self.filter_topics,
                    filter_document_ids=self.filter_document_ids,
                    workspace_id=self.workspace_id,
                    content_types=self.content_types, # Pasado
                    category=self.category,
                    explicit_document_ids=self.explicit_document_ids,
                    db_session=self.db_session, # Optimization
                )
                return [doc for doc, score in semantic_results_with_scores]

        class KognitoFTSRetriever(BaseRetriever):
            
            # collection_id: uuid.UUID # Eliminado
            k: int
            filter_topics: Optional[List[str]]
            filter_document_ids: Optional[List[str]]
            account_id: str
            workspace_id: Optional[str]
            content_types: Optional[List[str]] # Nuevo
            category: Optional[str]
            explicit_document_ids: Optional[List[str]]
            db_session: Optional[AsyncSession] # Optimization

            def _get_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                return []
            
            async def _aget_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                return await _run_fts_search(
                    query=query_str,
                    account_id=self.account_id,
                    k=self.k,
                    # collection_id=self.collection_id, # Eliminado
                    filter_topics=self.filter_topics,
                    filter_document_ids=self.filter_document_ids,
                    workspace_id=self.workspace_id,
                    content_types=self.content_types, # Pasado
                    category=self.category,
                    explicit_document_ids=self.explicit_document_ids,
                )
        
        # Eliminar la lógica de obtener collection_obj y collection_id específica
        # Ya no necesitamos una colección de LangchainPgCollection específica
        # porque filtraremos directamente por account_id y content_type en las búsquedas SQL.

        # Create sessions for retrievers
        # We use two separate sessions to allow safe parallel execution if EnsembleRetriever runs them concurrently
        async with DBSession(SessionLocal) as session_semantic, DBSession(SessionLocal) as session_fts:
            semantic_retriever = KognitoPGVectorRetriever(
                k=k,
                similarity_threshold=similarity_threshold,
                filter_topics=filter_topics,
                filter_document_ids=filter_document_ids,
                account_id=account_id,
                workspace_id=workspace_id,
                content_types=content_types, # Pasado
                category=category,
                explicit_document_ids=explicit_document_ids,
                db_session=session_semantic
            )

            fts_retriever = KognitoFTSRetriever(
                k=k,
                filter_topics=filter_topics,
                filter_document_ids=filter_document_ids,
                account_id=account_id,
                workspace_id=workspace_id,
                content_types=content_types, # Pasado
                category=category,
                explicit_document_ids=explicit_document_ids,
                db_session=session_fts
            )

            from langchain.retrievers import EnsembleRetriever

            final_retrieved_docs: List[LCDocument] = []
            if hybrid_search:
                ensemble_retriever = EnsembleRetriever(
                    retrievers=[semantic_retriever, fts_retriever],
                    weights=[1 - bm25_weight, bm25_weight]
                )
                final_retrieved_docs = await ensemble_retriever.ainvoke(query)
            else:
                final_retrieved_docs = await semantic_retriever.ainvoke(query)

        # Reranking
        if reranking:
            logger.info(f"✨ Iniciando reranking de {len(final_retrieved_docs)} documentos para la consulta: '{query[:50]}...'")
            reranker = Reranker() # Asegúrate de que se instancia correctamente
            logger.info("Reranker instanciado. Ejecutando rerank...")
            final_retrieved_docs = await reranker.rerank(query, final_retrieved_docs) # Removed top_n
            logger.info(f"✅ Reranking completado. Documentos finales después de rerank: {len(final_retrieved_docs)}")
        
        # Convertir a ToolOutputWithSources (ya implementado)
        final_content_list = []
        final_sources = []
        for i, doc in enumerate(final_retrieved_docs):
            final_content_list.append(doc.page_content)
            
            # Determinar el tipo de fuente basado en los metadatos
            doc_type = doc.metadata.get("type", "user_documents")
            source_type = SourceType.DOCUMENT
            
            if doc_type == "user_memories":
                source_type = SourceType.MEMORY
            elif doc_type == "user_notes":
                source_type = SourceType.NOTE
            elif doc_type == "user_documents":
                source_type = SourceType.DOCUMENT
            
            # Corrected create_document_source call
            final_sources.append(Source(
                id=i + 1, # Pass a unique integer ID
                title=doc.metadata.get("title", doc.metadata.get("file_name", "Documento")),
                url=doc.metadata.get("document_id", doc.metadata.get("note_id", f"doc_{i}")), # Use document_id or note_id
                snippet=doc.page_content,
                type=source_type,
                metadata={
                    "document_id": doc.metadata.get("document_id"),
                    "note_id": doc.metadata.get("note_id"),
                    "file_name": doc.metadata.get("file_name"),
                    "chunk_index": doc.metadata.get("chunk_index"),
                    "topic": doc.metadata.get("topic"),
                    "rerank_score": doc.metadata.get("rerank_score"), # Nueva puntuación del reranker
                }
            ))
        
        return ToolOutputWithSources(context_for_llm="\n".join(final_content_list), sources=final_sources)

    except Exception as e:
        logger.error(f"❌ Error al recuperar memorias/documentos relevantes: {e}", exc_info=True)
        return ToolOutputWithSources(context_for_llm="Error al obtener información relevante.", sources=[])


async def _update_embedding_columns_after_insert(
    db: AsyncSession,
    collection_uuid: str,
    file_name: str,
    account_id: Optional[str],
    content_type: str,
    topic: str | None = None,
    category: str | None = None,
    workspace_id: str | None = None,
    telegram_id: Optional[str] = None,
    thread_id: Optional[str] = None
) -> int:
    """
    Actualiza las nuevas columnas optimizadas después de insertar embeddings.

    Esta función se ejecuta después de que LangChain inserta los embeddings
    para poblar las nuevas columnas que permiten búsquedas sin JOINs.

    Returns:
        Número de filas actualizadas.
    """
    try:
        logger.info(f"🔄 Actualizando columnas optimizadas para {file_name}")

        # Construir la consulta de actualización
        update_query = """
            UPDATE langchain_pg_embedding
            SET
                account_id = :account_id,
                content_type = :content_type,
                topic = :topic,
                category = :category,
                workspace_id = :workspace_id,
                telegram_id = :telegram_id,
                thread_id = :thread_id
            WHERE
                collection_id = :collection_uuid
                AND (
                    (cmetadata->>'file_name' = :file_name AND cmetadata->>'type' = 'document_chunk') OR
                    (cmetadata->>'type' = 'user_memory_proactive_llm' OR cmetadata->>'type' = 'thread_summary' OR cmetadata->>'type' = 'enhanced_episodic' OR cmetadata->>'type' = 'general_memory')
                )
        """

        # Procesar FieldInfo para workspace_id, telegram_id, thread_id
        processed_workspace_id = str(workspace_id) if isinstance(workspace_id, FieldInfo) else workspace_id
        processed_telegram_id = str(telegram_id) if isinstance(telegram_id, FieldInfo) else telegram_id
        processed_thread_id = str(thread_id) if isinstance(thread_id, FieldInfo) else thread_id

        params = {
            "account_id": account_id,
            "content_type": content_type,
            "topic": topic,
            "category": category,
            "workspace_id": processed_workspace_id,
            "telegram_id": processed_telegram_id,
            "thread_id": processed_thread_id,
            "collection_uuid": collection_uuid,
            "file_name": file_name
        }

        result = await db.execute(text(update_query), params)
        updated_count = getattr(result, 'rowcount', 0)
        await db.commit()

        logger.info(f"✅ Actualizadas {updated_count} filas con columnas optimizadas")
        return updated_count

    except Exception as e:
        logger.error(f"❌ Error actualizando columnas optimizadas: {e}", exc_info=True)
        await db.rollback()
        return 0



async def get_user_profile(account_id: str) -> Optional[Perfil]:
    """
    Obtiene el perfil de un usuario a partir de su account_id universal.
    """
    logger.info(f"Obteniendo perfil para la cuenta ID: {account_id}")
    async with DBSession(SessionLocal) as db:
        try:
            stmt = select(Perfil).filter_by(account_id=account_id)
            result = await db.execute(stmt)
            perfil = result.scalars().first()
            if not perfil:
                logger.warning(
                    f"No se encontró perfil para la cuenta ID: {account_id}. Creando uno nuevo."
                )
                account = await db.get(
                    Account, uuid.UUID(account_id)
                )
                if account:
                    perfil = Perfil(
                        account_id=uuid.UUID(account_id)
                    )
                    db.add(perfil)
                    await db.commit()
                    await db.refresh(perfil)
                    logger.info(
                        f"✅ Perfil vacío creado para la cuenta ID: {account_id}."
                    )
                else:
                    logger.error(
                        f"❌ No se puede crear perfil porque la cuenta ID {account_id} no existe."
                    )
                    return None
            return perfil
        except Exception as e:
            logger.error(
                f"❌ Error al obtener/crear perfil para la cuenta ID {account_id}: {e}",
                exc_info=True,
            )
            await db.rollback()
            return None


async def update_user_profile(
    account_id: str,
    nombre: Optional[str] = None,
    gustos: Optional[str] = None,
    intereses: Optional[str] = None,
    otros_datos: Optional[str] = None,
):
    """
    Actualiza los campos del perfil de un usuario.
    """
    logger.info(f"Actualizando perfil para la cuenta ID: {account_id}.")
    async with DBSession(SessionLocal) as db:
        try:
            perfil = await get_user_profile(account_id)
            if not perfil:
                logger.error(
                    f"❌ No se pudo obtener o crear un perfil para la cuenta {account_id}. No se puede actualizar."
                )
                return

            updates = {}
            if nombre is not None:
                updates['nombre'] = nombre
            if gustos is not None:
                updates['gustos'] = gustos
            if intereses is not None:
                updates['intereses'] = intereses
            if otros_datos is not None:
                updates['otros_datos'] = otros_datos

            if updates:
                await db.execute(update(Perfil).where(Perfil.account_id == account_id).values(**updates))
                await db.commit()
            logger.info(
                f"✅ Perfil de la cuenta ID {account_id} actualizado exitosamente."
            )
        except Exception as e:
            logger.error(
                f"❌ Error al actualizar el perfil de la cuenta ID {account_id}: {e}",
                exc_info=True,
            )
            await db.rollback()


async def add_memory_to_vector_db(
    account_id: str,
    content: str,
    type: str = "general_memory",
    workspace_id: Optional[str] = None,
    topic: Optional[str] = None,
    category: Optional[str] = None,
    telegram_id: Optional[str] = None, # Nuevo parámetro
    thread_id: Optional[str] = None, # Nuevo parámetro
) -> None:
    """
    Genera embeddings para el contenido y lo guarda en la DB vectorial del usuario o workspace.

    ACTUALIZADO: Ahora actualiza las nuevas columnas optimizadas después de la inserción
    para permitir búsquedas 10-50x más rápidas sin JOINs.
    """
    logger.info(
        f"🔄 Añadiendo memoria (OPTIMIZADO) a la DB vectorial para la cuenta {account_id}: '{content[:50]}...'"
    )
    try:
        embeddings = get_embedding_model()
        if not embeddings:
            logger.error(
                "Los Embeddings no están inicializados. No se puede añadir memoria."
            )
            return

        collection_name = f"user_memories_{account_id}"

        # Usar el motor asíncrono preconfigurado desde core/database.py
        from core.database import engine
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=engine,
            use_jsonb=True
        )

        metadata = {
            "account_id": str(account_id),
            "type": type,
            "scope": "personal",
            "topic": topic if topic else "general",
            "category": category if category else "general"
        }
        if workspace_id:
            metadata["workspace_id"] = str(workspace_id)
            metadata["scope"] = "workspace"
        if telegram_id: # Nuevo
            metadata["telegram_id"] = str(telegram_id) # Nuevo
        if thread_id: # Nuevo
            metadata["thread_id"] = str(thread_id) # Nuevo
        await vectorstore.aadd_documents(
            documents=[LCDocument(page_content=content, metadata=metadata)]
        )

        # NUEVO: Actualizar las nuevas columnas optimizadas
        async with DBSession(SessionLocal) as db:
            collection_obj = await db.scalar(
                select(LangchainPgCollection).where(LangchainPgCollection.name == collection_name)
            )
            if collection_obj:
                await _update_embedding_columns_after_insert(
                    db=db,
                    collection_uuid=str(collection_obj.uuid),
                    file_name="memory",  # Identificador para memorias
                    account_id=account_id,
                    content_type=type,
                    topic=topic,
                    category=category,
                    workspace_id=workspace_id,
                    telegram_id=telegram_id, # Nuevo
                    thread_id=thread_id # Nuevo
                )
                logger.info("✅ Columnas optimizadas actualizadas para la memoria")

        logger.info(
            f"✅ Memoria añadida a la base de datos vectorial de la cuenta {account_id}."
        )
    except Exception as e:
        logger.error(
            f"❌ Error al añadir memoria a la DB vectorial para la cuenta {account_id}: {e}",
            exc_info=True,
        )


async def process_document_for_rag(
    file_name: str,
    extracted_text: str,
    topic: str = "general_documents",
    account_id: Optional[str] = None,
    is_global: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[str] = None,
) -> int:
    """
    Divide, embebe y almacena el texto de un documento en la DB vectorial.
    
    CAMBIO: Ahora usa solo langchain_pg_embedding para todos los documentos,
    agregando workspace_id como metadato y columna cuando corresponde.
    """
    decoded_topic = unquote(topic)
    task_id = metadata.get("task_id") if metadata else None
    try:
        from core.websocket_manager import send_personal_message
        if account_id and task_id:
            await send_personal_message(account_id, {
                "type": "document_processing_started",
                "file_name": file_name,
                "task_id": task_id,
            })
    except ImportError:
        logger.warning("Could not import send_personal_message, WebSocket notifications will be disabled.")
    except Exception as e:
        logger.error(f"Error sending WebSocket notification: {e}")
    logger.info(f"DEBUG: process_document_for_rag llamado con file_name={file_name}, topic={topic} (decoded: {decoded_topic}), account_id={account_id}, workspace_id={workspace_id}")
    if not extracted_text:
        return 0
        
    # Asegurarse de que la colección exista en UserDocumentTopic
    # Esto es crucial para que el frontend pueda listar los detalles de la colección
    # incluso si el primer documento se sube sin crear la colección explícitamente.
    await create_empty_collection(
        account_id=account_id,
        topic_name=decoded_topic, # Usar el nombre decodificado
        workspace_id=workspace_id
    )

    # Limpiar el texto de caracteres no válidos como NUL bytes
    cleaned_text = extracted_text.replace('\x00', '')
    if len(cleaned_text) != len(extracted_text):
        logger.info(f"Se eliminaron caracteres no válidos del documento '{file_name}'.")
    extracted_text = cleaned_text

    try:
        logger.info("Intentando obtener el modelo de embeddings...")
        embeddings = get_embedding_model()
        if not embeddings:
            logger.error("Los Embeddings no están inicializados. No se puede procesar el documento.")
            return 0

        logger.info(f"Tamaño del texto extraído para '{file_name}': {len(extracted_text)} caracteres.")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=num_tokens_from_string # Usar la función de conteo de tokens
        )
        texts = text_splitter.split_text(extracted_text)
        logger.info(f"Documento '{file_name}' dividido en {len(texts)} chunks.")
        
        # Determinar la colección de LangChain (topic)
        # Si se proporciona workspace_id, la colección será específica de ese workspace.
        # Si no, será una colección de usuario/global.
        scope = "personal"
        if is_global:
            langchain_collection_name = GLOBAL_COLLECTION_NAME
            scope = "global"
        elif account_id:
            # Para documentos personales o de workspace, el nombre de la colección es el topic.
            langchain_collection_name = decoded_topic
            if workspace_id:
                scope = "workspace"
        else:
            logger.error("❌ process_document_for_rag llamado sin account_id, workspace_id o is_global=True.")
            return 0
 
        logger.info(f"📊 Iniciando procesamiento RAG para '{file_name}' en la colección LangChain '{langchain_collection_name}'.")
        
        # Preparar metadatos base
        base_metadata = metadata if metadata else {}
        base_metadata.update({
            "file_name": file_name,
            "topic": decoded_topic, # Usar el nombre decodificado
            "type": "document_chunk",
            "scope": scope,
        })
        
        # Agregar IDs según corresponda
        if account_id:
            base_metadata["account_id"] = str(account_id)
        if workspace_id:
            base_metadata["workspace_id"] = str(workspace_id) # Añadir workspace_id a los metadatos

        # Generar documento único ID para agrupar chunks
        document_id = str(uuid.uuid4())
        base_metadata["document_id"] = document_id

        ids, lc_documents = [], []
        for i, text_content in enumerate(texts):
            if not text_content.strip():
                continue
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            
            # Convertir fechas a string para JSON
            for k, v in chunk_metadata.items():
                if isinstance(v, (datetime.datetime, datetime.date)):
                    chunk_metadata[k] = v.isoformat()
                    
            lc_documents.append(LCDocument(page_content=text_content, metadata=chunk_metadata))
            ids.append(str(uuid.uuid4()))
        
        # Crear/obtener vectorstore y agregar documentos
        # Usar el motor asíncrono preconfigurado desde core/database.py
        from core.database import engine
        
        # Verificar si la colección ya existe en nuestra tabla LangchainPgCollection
        async with DBSession(SessionLocal) as db:
            existing_collection_obj = await db.scalar(
                select(LangchainPgCollection).where(LangchainPgCollection.name == langchain_collection_name)
            )
            
            if existing_collection_obj:
                logger.info(f"Colección '{langchain_collection_name}' ya existe. Reutilizando.")
                langchain_collection_uuid = existing_collection_obj.uuid
            else:
                logger.info(f"Colección '{langchain_collection_name}' no existe. Permitir que LangChain la cree.")
                langchain_collection_uuid = None # Se obtendrá después de aadd_documents
 
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name=langchain_collection_name,
            connection=engine,
            use_jsonb=True
        )

        # --- OPTIMIZATION: Batch embedding and insertion ---
        logger.info(f"Optimizando la subida de {len(lc_documents)} chunks.")
        
        # 1. Extraer textos, metadatos e IDs
        all_texts = [doc.page_content for doc in lc_documents]
        all_metadatas = [doc.metadata for doc in lc_documents]
        
        # 2. Generar embeddings en un solo batch
        logger.info(f"Iniciando aembed_documents para {len(all_texts)} chunks.")
        all_embeddings = await embeddings.aembed_documents(all_texts)
        logger.info(f"Finalizado aembed_documents.")

        if len(all_embeddings) != len(all_texts):
            raise ValueError("La cantidad de embeddings generados no coincide con la cantidad de textos.")

        # 3. Añadir embeddings y documentos a la base de datos en un solo batch
        logger.info(f"Iniciando aadd_embeddings para {len(all_texts)} chunks en colección '{langchain_collection_name}'.")
        await vectorstore.aadd_embeddings(
            texts=all_texts,
            embeddings=all_embeddings,
            metadatas=all_metadatas,
            ids=ids
        )
        logger.info(f"Finalizado aadd_embeddings para {len(all_texts)} chunks en colección '{langchain_collection_name}'.")
        # --- END OPTIMIZATION ---

        # Obtener el UUID de la colección de LangChain recién creada/existente
        async with DBSession(SessionLocal) as db:
            # Si no se obtuvo antes (porque no existía), obtenerla ahora
            if langchain_collection_uuid is None:
                collection_obj = await db.scalar(
                    select(LangchainPgCollection).where(LangchainPgCollection.name == langchain_collection_name)
                )
                if not collection_obj:
                    logger.error(f"No se pudo encontrar la colección LangChain '{langchain_collection_name}' después de from_documents.")
                    return 0
                langchain_collection_uuid = collection_obj.uuid

            # NUEVO: Actualizar las nuevas columnas directamente para optimización
            await _update_embedding_columns_after_insert(
                db=db,
                collection_uuid=langchain_collection_uuid,
                file_name=file_name,
                account_id=account_id,
                content_type="user_documents",
                topic=decoded_topic, # Usar el nombre decodificado
                workspace_id=workspace_id
            )

            # Los documentos de workspace se identifican por sus metadatos
            if workspace_id:
                logger.info(f"Documento añadido al workspace {workspace_id} en colección LangChain {langchain_collection_name}.")

        logger.info(f"✅ Procesado y añadido {len(lc_documents)} chunks a la colección '{langchain_collection_name}'.")
        
        try:
            from core.websocket_manager import send_personal_message
            if account_id and task_id:
                await send_personal_message(account_id, {
                    "type": "document_processing_completed",
                    "file_name": file_name,
                    "task_id": task_id,
                    "document_id": document_id,
                    "topic": decoded_topic, # Usar el nombre decodificado
                    "workspace_id": workspace_id,
                })
        except ImportError:
            logger.warning("Could not import send_personal_message, WebSocket notifications will be disabled.")
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")

        # Trigger proactivo deshabilitado para documentos (se analizará en un job nocturno)
        if account_id:
            logger.info("[Memory Manager] Análisis proactivo no programado para documentos. Se analizará en el job nocturno.")
            # TODO: Implementar job nocturno para análisis de documentos una vez al día.
            
        return len(lc_documents)

    except Exception as e:
        logger.error(f"❌ Error durante el procesamiento RAG para '{file_name}': {e}", exc_info=True)
        try:
            from core.websocket_manager import send_personal_message
            if account_id and task_id:
                await send_personal_message(account_id, {
                    "type": "document_processing_failed",
                    "file_name": file_name,
                    "task_id": task_id,
                    "error": str(e),
                })
        except ImportError:
            logger.warning("Could not import send_personal_message, WebSocket notifications will be disabled.")
        return 0

# Semáforo para limitar la concurrencia en el procesamiento de documentos
# Ajusta este valor según la capacidad del servidor y la carga esperada.
DOCUMENT_PROCESSING_SEMAPHORE = asyncio.Semaphore(5) # Limita a 5 documentos procesándose a la vez

async def process_multiple_documents_for_rag(
    documents_data: List[Dict[str, Any]]
) -> List[int]:
    """
    Procesa una lista de documentos de forma simultánea para RAG, controlando la concurrencia.

    Args:
        documents_data: Una lista de diccionarios, donde cada diccionario
                        contiene los datos necesarios para un documento
                        (file_name, extracted_text, topic, account_id, is_global, metadata, workspace_id).
    Returns:
        Una lista con el número de chunks procesados para cada documento.
    """
    logger.info(f"📊 Iniciando procesamiento simultáneo para {len(documents_data)} documentos.")
    
    async def _process_single_document_with_semaphore(doc_data: Dict[str, Any]) -> int:
        async with DOCUMENT_PROCESSING_SEMAPHORE:
            try:
                return await process_document_for_rag(
                    file_name=doc_data["file_name"],
                    extracted_text=doc_data["extracted_text"],
                    topic=doc_data.get("topic", "general_documents"),
                    account_id=doc_data["account_id"],
                    is_global=doc_data.get("is_global", False),
                    metadata=doc_data.get("metadata", {}),
                    workspace_id=doc_data.get("workspace_id")
                )
            except Exception as e:
                logger.error(f"❌ Error procesando documento '{doc_data.get('file_name', 'N/A')}' en batch: {e}", exc_info=True)
                return 0 # Retorna 0 chunks procesados en caso de error

    tasks = [_process_single_document_with_semaphore(doc_data) for doc_data in documents_data]
    results = await asyncio.gather(*tasks, return_exceptions=False) # return_exceptions=False para que falle si alguna tarea falla
    
    logger.info(f"✅ Finalizado procesamiento simultáneo de documentos. Resultados: {results}")
    return results

async def remove_document_from_rag(
    account_id: str,
    file_name: str,
    topic: str = "repositorio",
    workspace_id: Optional[str] = None
) -> int:
    """
    Elimina los embeddings de un documento específico de la base de datos vectorial.
    Utiliza la metadata para encontrar los chunks específicos del archivo.
    """
    try:
        # Determinar el nombre de la colección
        if workspace_id:
            langchain_collection_name = topic
        else:
            langchain_collection_name = f"user_documents_{account_id}"
        
        # Usar la función existente delete_document_chunks
        deleted_count = await delete_document_chunks(
            account_id=account_id,
            file_name=file_name,
            topic=topic,
            workspace_id=workspace_id
        )
        
        logger.info(f"🗑️ Eliminados {deleted_count} chunks del archivo '{file_name}' de la colección '{langchain_collection_name}'")
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Error eliminando documento '{file_name}' de RAG: {e}", exc_info=True)
        return 0


async def delete_document_chunks(
    account_id: str,
    file_name: Optional[str] = None,
    file_name_prefix: Optional[str] = None, # Nuevo parámetro
    topic: Optional[str] = None,
    workspace_id: Optional[str] = None,
    repo_url: Optional[str] = None # Nuevo parámetro para filtrar por repo
) -> int:
    """
    Elimina los chunks de documentos usando las columnas optimizadas (sin JOINs).

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin necesidad de JOINs.
    """
    if not file_name and not topic and not file_name_prefix: # Actualizado para incluir file_name_prefix
        logger.warning("Se llamó a delete_document_chunks sin file_name, topic ni file_name_prefix.")
        return 0

    logger.info(f"🗑️ Eliminando chunks optimizado para account_id: {account_id}")
    logger.info(f"📄 File name: {file_name}")
    logger.info(f"📁 File name prefix: {file_name_prefix}") # Log del nuevo parámetro
    logger.info(f"🏷️ Topic: {topic}")
    logger.info(f"🏢 Workspace ID: {workspace_id}")

    try:
        async with DBSession(SessionLocal) as db:
            # Construir consulta optimizada usando las nuevas columnas directamente
            clauses = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"account_id": account_id}

            if file_name:
                clauses.append("cmetadata->>'file_name' = :fname")
                params["fname"] = file_name
            elif file_name_prefix: # Nueva lógica para el prefijo
                clauses.append("cmetadata->>'file_name' LIKE :fname_prefix")
                params["fname_prefix"] = f"{file_name_prefix}%"

            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic.description if isinstance(topic, FieldInfo) else topic

            if workspace_id:
                clauses.append("workspace_id = :workspace_id")
                params["workspace_id"] = workspace_id

            delete_sql = text("DELETE FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))

            logger.info(f"🔧 Query SQL optimizada: {delete_sql}")
            logger.info(f"📋 Parámetros: {params}")

            result = await db.execute(delete_sql, params)
            deleted_count = result.rowcount or 0
            await db.commit()

            # --- NUEVA LÓGICA: Eliminar de GitHubDocument ---
            github_delete_clauses = [
                GitHubDocument.account_id == uuid.UUID(account_id)
            ]
            if repo_url: # Filtrar por repo_url si se proporciona
                github_delete_clauses.append(GitHubDocument.repo_url == repo_url)

            if file_name:
                github_delete_clauses.append(GitHubDocument.file_path == file_name)
            elif file_name_prefix:
                github_delete_clauses.append(GitHubDocument.file_path.like(f"{file_name_prefix}%"))
            
            # Si se proporciona workspace_id, también filtrar por él
            if workspace_id:
                github_delete_clauses.append(GitHubDocument.workspace_id == uuid.UUID(workspace_id))

            github_delete_stmt = delete(GitHubDocument).where(*github_delete_clauses)
            
            logger.info(f"🔧 Query SQL para GitHubDocument: {github_delete_stmt}")
            github_result = await db.execute(github_delete_stmt)
            github_deleted_count = github_result.rowcount or 0
            await db.commit()
            logger.info(f"🗑️ Total borrados {github_deleted_count} registros de GitHubDocument.")
            # --- FIN NUEVA LÓGICA ---
            logger.info(f"🗑️ Total borrados {deleted_count} chunks usando consulta optimizada.")
            return github_deleted_count if github_deleted_count > 0 else deleted_count
    except Exception as e:
        logger.error(f"❌ Error eliminando chunks optimizado: {e}", exc_info=True)
        await db.rollback()
        return 0


async def get_full_document_content(
    account_id: str,
    file_name: Optional[str] = None,
    document_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    topic: Optional[str] = None,
) -> Optional[str]:
    """
    Reconstruye y devuelve el contenido completo de un documento desde sus chunks.

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin JOINs.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a reconstruir.
        document_id: El ID único del documento a reconstruir.
        workspace_id: El ID del workspace (UUID en formato string) para buscar en la colección del workspace, si aplica.
        topic: El topic específico para filtrar los documentos (opcional).
    Returns:
        El contenido completo del documento como una cadena, o None si no se encuentra.
    """
    if not file_name and not document_id:
        raise ValueError("Se debe proporcionar file_name o document_id.")

    log_identifier = f"'{file_name}'" if file_name else f"documento ID '{document_id}'"
    logger.info(
        f"📄 Recuperando contenido completo (OPTIMIZADO) de {log_identifier} para la cuenta {account_id}"
        f" (Workspace: {workspace_id if workspace_id else 'N/A'})"
        f" (Topic: {topic if topic else 'ALL'})"
    )

    try:
        async with DBSession(SessionLocal) as db:
            # Construir consulta optimizada usando las nuevas columnas directamente
            clauses = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {
                "account_id": account_id,
            }

            if file_name:
                clauses.append("cmetadata->>'file_name' = :file_name")
                params["file_name"] = file_name
            elif document_id:
                clauses.append("cmetadata->>'document_id' = :document_id")
                params["document_id"] = str(document_id)
            
            # Filtro por topic si se especifica
            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic

            # Manejo de workspace_id: Asegurarse de que sea un string UUID válido
            processed_workspace_id = None
            if isinstance(workspace_id, FieldInfo):
                # Si es un FieldInfo, intentar extraer el UUID de la descripción
                # Asumimos que la descripción contiene el UUID o es el UUID directamente
                # Si la descripción es el UUID, se usará directamente.
                # Si la descripción es el texto largo, se intentará extraer el UUID.
                # Si no se puede extraer un UUID válido, se usará None.
                try:
                    # Intentar extraer el UUID de la descripción si es un string largo
                    # Ejemplo: "description='El ID del workspace (UUID en formato string) ...' extra={}"
                    # Buscar un patrón de UUID en la descripción
                    import re
                    uuid_match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', workspace_id.description)
                    if uuid_match:
                        processed_workspace_id = uuid_match.group(1)
                    else:
                        # Si no se encuentra un UUID en la descripción, intentar usar la descripción directamente
                        # si es un UUID válido.
                        uuid.UUID(workspace_id.description) # Validar si es un UUID
                        processed_workspace_id = workspace_id.description
                except (AttributeError, ValueError):
                    # Si no tiene atributo description o no es un UUID válido, se mantiene como None
                    processed_workspace_id = None
            elif isinstance(workspace_id, str) and workspace_id:
                # Si ya es un string y no está vacío, intentar validarlo como UUID
                try:
                    uuid.UUID(workspace_id)
                    processed_workspace_id = workspace_id
                except ValueError:
                    processed_workspace_id = None # No es un UUID válido

            # Manejo de workspace_id:
            # - Si processed_workspace_id es un UUID válido (string no vacío), filtrar por ese workspace_id.
            # - Si processed_workspace_id es explícitamente None, filtrar por workspace_id IS NULL.
            # - Si processed_workspace_id no se proporciona (o es una cadena vacía), NO filtrar por workspace_id,
            #   lo que significa que se buscarán chunks tanto con como sin workspace_id.
            if processed_workspace_id is not None and processed_workspace_id != "":
                clauses.append("workspace_id = :workspace_id")
                params["workspace_id"] = processed_workspace_id
            elif processed_workspace_id == "": # Caso en que se pasa explícitamente una cadena vacía para buscar NULLs
                clauses.append("workspace_id IS NULL")
            # Si processed_workspace_id es None (el valor por defecto), no se añade ninguna cláusula de filtro para workspace_id.

            # Consulta para obtener todos los chunks del documento
            select_sql = text(f"""
                SELECT document, cmetadata
                FROM langchain_pg_embedding
                WHERE {" AND ".join(clauses)}
                ORDER BY (cmetadata->>'chunk_index')::int
            """)

            logger.info(f"🔧 Query SQL optimizada: {select_sql}")
            logger.info(f"📋 Parámetros: {params}")

            result = await db.execute(select_sql, params)
            chunks = result.fetchall()

        if not chunks:
            logger.warning(f"No se encontraron chunks para el documento '{file_name}' en el contexto especificado.")
            return None

        logger.info(f"📊 Encontrados {len(chunks)} chunks para el documento '{file_name}'")

        # Reconstruir el contenido completo
        full_content = "".join([chunk[0] for chunk in chunks])  # chunk[0] es el document

        logger.info(f"✅ Reconstruido documento '{file_name}'. Longitud: {len(full_content)} chars.")
        return full_content

    except Exception as e:
        logger.error(
            f"❌ Error recuperando contenido optimizado de '{file_name}' (workspace {workspace_id}, topic {topic}): {e}", exc_info=True
        )
        return None


async def list_user_documents(
    account_id: str,
    workspace_id: Optional[str] = None,
    topic: Optional[str] = None, # Mantener para compatibilidad
    document_ids: Optional[List[str]] = None, # Nuevo
    topics: Optional[List[str]] = None # Nuevo
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todos los documentos únicos.

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin JOINs.

    - Si se proporciona `document_ids` o `topics`, filtra específicamente por ellos.
    - Si se proporciona `workspace_id`, lista los documentos de ese workspace Y del contexto general.
    - Si no, lista los documentos de la colección general del usuario.
    """
    logger.info(f"📋 list_user_documents - account_id: {account_id}, workspace_id: {workspace_id}, topic: {topic}, topics: {topics}, doc_ids: {document_ids}")
    async with DBSession(SessionLocal) as db:
        try:
            base_clauses = [
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {}

            # --- Lógica de Filtro de Contexto Explícito ---
            if document_ids or topics:
                context_filters = []
                if document_ids:
                    context_filters.append("cmetadata->>'document_id' = ANY(:document_ids)")
                    params["document_ids"] = document_ids
                if topics: # Nuevo parámetro topics (lista)
                    context_filters.append("topic = ANY(:topics)")
                    params["topics"] = topics
                
                base_clauses.append(f"({' OR '.join(context_filters)})")
            # --- Fin Lógica de Filtro de Contexto ---
            else:
                # --- Lógica de Filtro General (si no hay contexto explícito) ---
                # Siempre filtrar por account_id por seguridad
                base_clauses.append("account_id = :account_id")
                params["account_id"] = account_id
                
                # Si el topic es 'all_documents', no aplicar filtro de topic
                if topic == "all_documents":
                    logger.info("📎 Topic es 'all_documents', no se aplicará filtro de topic.")
                else:
                    # NUEVO: Solo filtrar por workspace_id si se proporciona explícitamente
                    # Si no se proporciona, buscar en TODOS los workspaces del usuario
                    if isinstance(workspace_id, str) and workspace_id:
                        # Si se especifica workspace, mostrar documentos del workspace
                        base_clauses.append("workspace_id = :workspace_id")
                        params["workspace_id"] = workspace_id

                    if topic: # Filtro de compatibilidad
                        base_clauses.append("topic = :topic")
                        params["topic"] = str(topic.description) if isinstance(topic, FieldInfo) else str(topic)


            query_str = f"""
                SELECT DISTINCT ON (cmetadata->>'document_id')
                       cmetadata->>'file_name' AS file_name,
                       topic AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author,
                       cmetadata->>'document_id' AS document_id,
                       workspace_id::text AS workspace_id
                FROM langchain_pg_embedding
                WHERE {" AND ".join(base_clauses)}
                ORDER BY cmetadata->>'document_id', id;
            """
 
            logger.info(f"DEBUG: Final SQL query for list_user_documents: {query_str}")
            logger.info(f"DEBUG: Parameters for list_user_documents: {params}")
 
            document_list_query = text(query_str)
            document_list_result = await db.execute(document_list_query, params)
            documents = [dict(row) for row in document_list_result.mappings()]
 
            logger.info(f"✅ Listados {len(documents)} documentos usando consulta optimizada.")
            return documents
 
        except Exception as e:
            logger.error(f"❌ Error listando documentos optimizado para la cuenta {account_id}: {e}", exc_info=True)
            return []


async def list_user_documents_all_teams(
    account_id: str,
    workspace_id: Optional[str] = None,
    topic: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de TODOS los documentos únicos del usuario,
    independientemente de si están compartidos con equipos o no.

    Esta función es para la vista personal del usuario donde debe ver
    todos sus documentos sin filtrar por team_id.
    """
    logger.info(f"📋 Listando TODOS los documentos del usuario {account_id} (Workspace: {workspace_id if workspace_id else 'N/A'}) - Querying langchain_pg_embedding")

    async with DBSession(SessionLocal) as db:
        try:
            # Construir consulta optimizada usando las nuevas columnas directamente
            # NO filtrar por team_id para obtener todos los documentos del usuario
            clauses = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"account_id": account_id}

            if workspace_id:
                clauses.append("workspace_id = :workspace_id")
                params["workspace_id"] = workspace_id

            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic.description if isinstance(topic, FieldInfo) else topic

            # Consulta optimizada para obtener documentos únicos por document_id
            # CORREGIDO: Usar document_id en lugar de file_name para evitar pérdida de documentos
            query_str = f"""
                SELECT DISTINCT ON (cmetadata->>'document_id')
                       cmetadata->>'file_name' AS file_name,
                       topic AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author,
                       cmetadata->>'document_id' AS document_id,
                       workspace_id::text AS workspace_id
                FROM langchain_pg_embedding
                WHERE {" AND ".join(clauses)}
                ORDER BY cmetadata->>'document_id', id;
            """
 
            logger.info(f" Query SQL para todos los documentos: {query_str}")
            logger.info(f"📋 Parámetros: {params}")
 
            document_list_query = text(query_str)
            document_list_result = await db.execute(document_list_query, params)
            documents = [dict(row) for row in document_list_result.mappings()]
 
            logger.info(f"✅ Listados {len(documents)} documentos totales del usuario.")
            return documents
 
        except Exception as e:
            logger.error(f"❌ Error listando todos los documentos del usuario {account_id}: {e}", exc_info=True)
            return []


async def update_document_metadata(
    account_id: str,
    file_name: str,
    new_title: Optional[str],
    new_topic: Optional[str],
    workspace_id: Optional[str] = None,
) -> bool:
    """
    Actualiza el título y/o la categoría (topic) de todos los chunks de un documento.

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin JOINs.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a actualizar.
        new_title: El nuevo título (si se proporciona).
        new_topic: La nueva categoría/base de conocimiento (si se proporciona).
        workspace_id: El ID del workspace (UUID en formato string) para actualizar el documento de un workspace específico, si aplica.

    Returns:
        True si la operación fue exitosa, False en caso contrario.
    """
    # Decodificar new_topic al principio
    decoded_new_topic = unquote(new_topic) if new_topic else None

    if not new_title and not decoded_new_topic: # Usar decoded_new_topic aquí
        logger.warning(f"Se llamó a update_document_metadata para '{file_name}' sin nuevos datos para actualizar.")
        return False

    logger.info(
        f"📝 Actualizando metadatos (OPTIMIZADO) para '{file_name}' (cuenta {account_id}). "
        f"Nuevo título: {new_title}, Nuevo tema: {decoded_new_topic}. Workspace ID: {workspace_id if workspace_id else 'N/A'}."
    )

    async with DBSession(SessionLocal) as db:
        try:
            # Construir filtros usando las nuevas columnas directamente
            clauses = [
                "account_id = CAST(:account_id AS UUID)",
                "cmetadata->>'file_name' = :file_name",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {
                "account_id": account_id,
                "file_name": file_name
            }

            if workspace_id:
                clauses.append("workspace_id = CAST(:workspace_id AS UUID)")
                params["workspace_id"] = workspace_id

            # Primero, obtener el cmetadata actual de un chunk para no sobrescribir otros metadatos
            select_sql = text(f"""
                SELECT cmetadata
                FROM langchain_pg_embedding
                WHERE {" AND ".join(clauses)}
                LIMIT 1
            """)

            cmetadata_result = await db.execute(select_sql, params)
            current_cmetadata = cmetadata_result.scalar_one_or_none()

            if not current_cmetadata:
                logger.warning(f"No se encontraron chunks para el archivo '{file_name}' para actualizar.")
                return False

            # Preparar los valores actualizados
            values_to_update = current_cmetadata.copy()
            if new_title is not None:
                values_to_update['title'] = new_title
            if decoded_new_topic is not None: # Usar decoded_new_topic aquí
                values_to_update['topic'] = decoded_new_topic # Usar decoded_new_topic aquí
            if workspace_id:
                values_to_update['workspace_id'] = str(workspace_id)

            # Actualizar tanto cmetadata como las columnas optimizadas
            update_sql = text(f"""
                UPDATE langchain_pg_embedding
                SET
                    cmetadata = :new_cmetadata,
                    topic = :topic_column
                WHERE {" AND ".join(clauses)}
            """)

            update_params = params.copy()
            update_params.update({
                "new_cmetadata": json.dumps(values_to_update),  # Serializar a JSON string para PostgreSQL
                "topic_column": decoded_new_topic if decoded_new_topic is not None else current_cmetadata.get('topic') # Usar decoded_new_topic aquí
            })

            logger.info(f"🔧 Query SQL optimizada: {update_sql}")
            logger.info(f"📋 Parámetros: {update_params}")

            result = await db.execute(update_sql, update_params)
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Se actualizaron {result.rowcount} chunks para el archivo '{file_name}' usando consulta optimizada.")

                # ACTUALIZACIÓN DEL GRAFO DE CONOCIMIENTO (Neo4j)
                if decoded_new_topic is not None:
                    old_topic = current_cmetadata.get('topic')
                    if old_topic and old_topic != decoded_new_topic:
                        try:
                            from utils.knowledge_graph_service import KnowledgeGraphService
                            kg_service = KnowledgeGraphService()
                            await kg_service.update_dataset_name_flow(
                                old_dataset_name=old_topic,
                                new_dataset_name=decoded_new_topic,
                                account_id=account_id,
                                file_name=file_name
                            )
                            logger.info(f"🧠 Grafo de conocimiento actualizado: '{old_topic}' -> '{decoded_new_topic}' para '{file_name}'")
                        except Exception as e:
                            logger.error(f"❌ Error al actualizar el grafo de conocimiento: {e}")

                # Enviar notificación WebSocket en tiempo real
                try:
                    from core.websocket_manager import send_personal_message
                    await send_personal_message(account_id, {
                        "type": "document_title_updated",
                        "file_name": file_name,
                        "new_title": new_title,
                        "new_topic": decoded_new_topic, # Usar decoded_new_topic aquí
                        "workspace_id": workspace_id,
                        "message": f"Título actualizado para '{file_name}'"
                    })
                    logger.info(f"📡 Notificación WebSocket enviada para actualización de título de '{file_name}'")
                except Exception as e:
                    logger.error(f"❌ Error al enviar notificación WebSocket: {e}")

                return True
            else:
                logger.warning(f"⚠️ No se actualizó ninguna fila para el archivo '{file_name}'.")
                return False

        except Exception as e:
            logger.error(f"❌ Error al actualizar metadatos del documento '{file_name}': {e}", exc_info=True)
            await db.rollback()
            return False



async def list_user_collections(account_id: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todas las colecciones (temas) únicas de documentos de un usuario.

    Solo busca en UserDocumentTopic, no en langchain_pg_embedding para evitar duplicados.

    NUEVO COMPORTAMIENTO:
    - Si se especifica `workspace_id`, se devuelven SOLO las colecciones de ese workspace.
    - Si `workspace_id` es `None`, se devuelven TODAS las colecciones del usuario a través de todos sus workspaces,
      incluyendo las que no tienen workspace asignado.

    Args:
        account_id: ID de la cuenta del usuario. Obligatorio.
        workspace_id: ID del workspace (opcional). Usado para filtrar por un workspace específico.
    """
    logger.info(f"Listando colecciones para cuenta {account_id}, workspace: {workspace_id if workspace_id else 'TODOS'}")

    async with DBSession(SessionLocal) as db:
        try:
            collections_list = []

            # 1. Obtener colecciones definidas por el usuario en UserDocumentTopic
            user_topics_query = select(UserDocumentTopic).options(
                joinedload(UserDocumentTopic.workspace),
                joinedload(UserDocumentTopic.account)
            )

            # Si se especifica un workspace, mostrar TODAS las colecciones de ese workspace
            # (no solo las del usuario actual)
            if workspace_id:
                user_topics_query = user_topics_query.where(
                    UserDocumentTopic.workspace_id == uuid.UUID(workspace_id)
                )
            else:
                # Si no se especifica workspace, mostrar solo las colecciones del usuario
                user_topics_query = user_topics_query.where(
                    UserDocumentTopic.account_id == uuid.UUID(account_id)
                )

            result = await db.execute(user_topics_query)
            user_topics = result.scalars().all()

            # 2. Para cada colección, contar documentos desde langchain_pg_embedding
            for topic in user_topics:
                # Contar documentos en langchain_pg_embedding para esta colección
                # NUEVO: Contar por topic y account_id, permitiendo cualquier workspace_id
                count_clauses = [
                    "cmetadata->>'type' = 'document_chunk'",
                    "topic = :topic_name",
                    "account_id = :account_id"
                ]
                count_params: Dict[str, Any] = {
                    "topic_name": topic.name,
                    "account_id": str(topic.account_id)
                }
                
                # Si la colección tiene workspace_id, filtrar por ese workspace
                # Si no tiene workspace_id, contar documentos de CUALQUIER workspace del usuario
                if topic.workspace_id:
                    count_clauses.append("workspace_id = :workspace_id")
                    count_params["workspace_id"] = str(topic.workspace_id)

                count_query = text(f"""
                    SELECT COUNT(DISTINCT cmetadata->>'document_id')
                    FROM langchain_pg_embedding
                    WHERE {" AND ".join(count_clauses)}
                """)
                document_count = await db.scalar(count_query, count_params) or 0

                collections_list.append({
                    "topic": topic.name,
                    "document_count": document_count,
                    "description": topic.description,
                    "workspace_id": str(topic.workspace_id) if topic.workspace_id else None,
                    "workspace_name": topic.workspace.name if topic.workspace else None,
                    "workspace_color": topic.workspace.color if topic.workspace else None,
                    "created_by_account_id": str(topic.account_id),
                    "created_by_email": topic.account.email if topic.account else None,
                    "has_knowledge_graph": False
                })

            logger.info(f"✅ Devolviendo {len(collections_list)} colecciones para la cuenta {account_id} (workspace: {workspace_id if workspace_id else 'TODOS'})")
            return collections_list

        except Exception as e:
            logger.error(f"❌ Error listando colecciones para la cuenta {account_id}: {e}", exc_info=True)
            return []


async def create_empty_collection(
    account_id: str, 
    topic_name: str, 
    description: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> bool:
    """
    Crea una colección vacía en la tabla UserDocumentTopic.
    
    Args:
        account_id: ID de la cuenta del usuario.
        topic_name: Nombre de la nueva colección.
        description: Descripción opcional de la colección.
        workspace_id: ID del workspace (opcional).
        
    Returns:
        True si la colección se creó exitosamente, False si ya existe o hay error.
    """
    # Decodificar el nombre del topic al principio
    decoded_topic_name = unquote(topic_name)
    logger.info(f"DEBUG: create_empty_collection llamado con account_id={account_id}, topic_name={topic_name} (decoded: {decoded_topic_name}), workspace_id={workspace_id}")
    logger.info(f"Creando colección vacía '{decoded_topic_name}' para cuenta {account_id}")
    
    async with DBSession(SessionLocal) as db:
        try:
            # Verificar si la colección ya existe
            existing_query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id)
            )
            if workspace_id:
                existing_query = existing_query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            else:
                existing_query = existing_query.where(UserDocumentTopic.workspace_id.is_(None))
            
            existing_query = existing_query.where(UserDocumentTopic.name == decoded_topic_name) # Usar el nombre decodificado
            
            existing_collection = await db.scalar(existing_query)
            if existing_collection:
                logger.warning(f"ADVERTENCIA: Colección '{decoded_topic_name}' ya existe para la cuenta {account_id} en workspace {workspace_id}. No se creará de nuevo.")
                return True
            
            new_topic = UserDocumentTopic(
                account_id=uuid.UUID(account_id),
                name=decoded_topic_name, # Usar el nombre decodificado
                description=description,
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None
            )
            db.add(new_topic)
            await db.commit()
            await db.refresh(new_topic)
            logger.info(f"✅ Colección vacía '{decoded_topic_name}' creada exitosamente.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al crear colección vacía '{decoded_topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False


async def update_collection(
    account_id: str,
    old_topic_name: str,
    new_topic_name: Optional[str] = None,
    new_description: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> bool:
    """
    Actualiza una colección existente (nombre, descripción, workspace_id o team_id).
    
    Args:
        account_id: ID de la cuenta del usuario.
        old_topic_name: Nombre actual de la colección a actualizar.
        new_topic_name: Nuevo nombre de la colección (opcional).
        new_description: Nueva descripción de la colección (opcional).
        workspace_id: ID del workspace (opcional).
        
    Returns:
        True si la colección se actualizó exitosamente, False en caso contrario.
    """
    # Decodificar nombres de topic al principio
    decoded_old_topic_name = unquote(old_topic_name)
    decoded_new_topic_name = unquote(new_topic_name) if new_topic_name else None
    
    logger.info(f"Actualizando colección '{decoded_old_topic_name}' para cuenta {account_id}. Nuevos datos: topic={decoded_new_topic_name}, description={new_description}, workspace_id={workspace_id}")

    async with DBSession(SessionLocal) as db:
        try:
            # Buscar la colección SOLO por account_id y nombre
            # No filtrar por workspace_id aquí para permitir actualizar colecciones
            # que originalmente no tienen workspace asignado
            collection_query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == decoded_old_topic_name
            )
            
            collection = (await db.execute(collection_query)).scalars().first()

            if not collection:
                logger.warning(f"Colección '{decoded_old_topic_name}' no encontrada para la cuenta {account_id}.")
                return False

            # Verificar si el nuevo nombre ya existe (si se proporciona)
            if decoded_new_topic_name and decoded_new_topic_name != decoded_old_topic_name:
                existing_query = select(UserDocumentTopic).where(
                    UserDocumentTopic.account_id == uuid.UUID(account_id),
                    UserDocumentTopic.name == decoded_new_topic_name
                )
                if workspace_id:
                    existing_query = existing_query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
                else:
                    existing_query = existing_query.where(UserDocumentTopic.workspace_id.is_(None))
                
                existing_collection = (await db.execute(existing_query)).scalars().first()
                if existing_collection:
                    logger.warning(f"Ya existe una colección con el nombre '{decoded_new_topic_name}' para la cuenta {account_id}.")
                    return False


            # Actualizar los campos proporcionados
            old_workspace_id = collection.workspace_id
            if decoded_new_topic_name:
                collection.name = decoded_new_topic_name
            if new_description is not None:
                collection.description = new_description
            if workspace_id:
                collection.workspace_id = uuid.UUID(workspace_id)
            
            await db.commit()
            await db.refresh(collection)

            # Actualizar los documentos asociados en langchain_pg_embedding
            # si cambió el nombre de la colección o el workspace_id
            if decoded_new_topic_name or workspace_id:
                try:
                    update_clauses = []
                    update_params: Dict[str, Any] = {}
                    
                    if decoded_new_topic_name:
                        update_clauses.append("topic = :new_topic")
                        update_params["new_topic"] = decoded_new_topic_name
                    
                    if workspace_id:
                        update_clauses.append("workspace_id = :new_workspace_id")
                        update_params["new_workspace_id"] = workspace_id
                    
                    # Construir las condiciones WHERE para encontrar los documentos de la colección
                    where_clauses = [
                        "account_id = :account_id",
                        "topic = :old_topic"
                    ]
                    where_params: Dict[str, Any] = {
                        "account_id": account_id,
                        "old_topic": decoded_old_topic_name
                    }
                    
                    # Filtrar por el workspace_id original de la colección
                    if old_workspace_id:
                        where_clauses.append("workspace_id = :old_workspace_id")
                        where_params["old_workspace_id"] = str(old_workspace_id)
                    else:
                        where_clauses.append("workspace_id IS NULL")
                    
                    # Combinar parámetros
                    all_params = {**update_params, **where_params}
                    
                    # Ejecutar la actualización
                    update_query = text(f"""
                        UPDATE langchain_pg_embedding
                        SET {", ".join(update_clauses)}
                        WHERE {" AND ".join(where_clauses)}
                    """)
                    
                    result = await db.execute(update_query, all_params)
                    await db.commit()
                    
                    logger.info(f"✅ Actualizados {result.rowcount} chunks de documentos en langchain_pg_embedding.")
                except Exception as e:
                    logger.warning(f"⚠️ Error al actualizar documentos en langchain_pg_embedding: {e}")
                    # No fallar toda la operación si los documentos no se actualizan

            logger.info(f"✅ Colección '{decoded_old_topic_name}' actualizada exitosamente.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar la colección '{decoded_old_topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False

async def update_collection_workspace(account_id: str, topic_name: str, workspace_id: str) -> bool:
    """
    Actualiza el workspace_id de una colección existente en la tabla UserDocumentTopic.
    """
    logger.info(f"Actualizando workspace_id para la colección '{topic_name}' de la cuenta {account_id} a {workspace_id}")

    async with DBSession(SessionLocal) as db:
        try:
            # Buscar la colección
            collection_query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )
            collection = (await db.execute(collection_query)).scalars().first()

            if not collection:
                logger.warning(f"Colección '{topic_name}' no encontrada para la cuenta {account_id}.")
                return False

            # Actualizar el workspace_id
            collection.workspace_id = uuid.UUID(workspace_id)
            await db.commit()
            await db.refresh(collection)

            logger.info(f"✅ Workspace_id de la colección '{topic_name}' actualizado exitosamente a {workspace_id}.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar workspace_id para la colección '{topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False


async def link_profile_to_collection(account_id: str, topic_name: str, profile_id: str, workspace_id: Optional[str] = None) -> bool:
    """
    Vincula un perfil de contacto a una colección de documentos (UserDocumentTopic).
    """
    logger.info(f"Intentando vincular perfil {profile_id} a la colección '{topic_name}' para la cuenta {account_id} (workspace: {workspace_id})")
    async with DBSession(SessionLocal) as db:
        try:
            # 1. Obtener la colección
            topic_query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )
            if workspace_id:
                topic_query = topic_query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            else:
                topic_query = topic_query.where(UserDocumentTopic.workspace_id.is_(None))

            collection = (await db.execute(topic_query)).scalars().first()
            if not collection:
                logger.warning(f"Colección '{topic_name}' no encontrada para la cuenta {account_id} en workspace {workspace_id}.")
                return False

            # 2. Obtener el perfil de contacto
            profile = await db.get(ContactProfile, uuid.UUID(profile_id))
            if not profile or profile.account_id != uuid.UUID(account_id):
                logger.warning(f"Perfil {profile_id} no encontrado o no pertenece a la cuenta {account_id}.")
                return False

            # 3. Verificar si ya está vinculado
            if profile in collection.contact_profiles:
                logger.info(f"El perfil {profile_id} ya está vinculado a la colección '{topic_name}'.")
                return True

            # 4. Vincular
            collection.contact_profiles.append(profile)
            await db.commit()
            await db.refresh(collection)
            logger.info(f"✅ Perfil {profile_id} vinculado exitosamente a la colección '{topic_name}'.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al vincular perfil {profile_id} a la colección '{topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False


async def unlink_profile_from_collection(account_id: str, topic_name: str, profile_id: str, workspace_id: Optional[str] = None) -> bool:
    """
    Desvincula un perfil de contacto de una colección de documentos (UserDocumentTopic).
    """
    logger.info(f"Intentando desvincular perfil {profile_id} de la colección '{topic_name}' para la cuenta {account_id} (workspace: {workspace_id})")
    async with DBSession(SessionLocal) as db:
        try:
            # 1. Obtener la colección
            topic_query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )
            if workspace_id:
                topic_query = topic_query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            else:
                topic_query = topic_query.where(UserDocumentTopic.workspace_id.is_(None))

            collection = (await db.execute(topic_query)).scalars().first()
            if not collection:
                logger.warning(f"Colección '{topic_name}' no encontrada para la cuenta {account_id} en workspace {workspace_id}.")
                return False

            # 2. Obtener el perfil de contacto
            profile = await db.get(ContactProfile, uuid.UUID(profile_id))
            if not profile or profile.account_id != uuid.UUID(account_id):
                logger.warning(f"Perfil {profile_id} no encontrado o no pertenece a la cuenta {account_id}.")
                return False

            # 3. Verificar si está vinculado
            if profile not in collection.contact_profiles:
                logger.info(f"El perfil {profile_id} no está vinculado a la colección '{topic_name}'.")
                return True # Already unlinked or never linked

            # 4. Desvincular
            collection.contact_profiles.remove(profile)
            await db.commit()
            await db.refresh(collection)
            logger.info(f"✅ Perfil {profile_id} desvinculado exitosamente de la colección '{topic_name}'.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al desvincular perfil {profile_id} de la colección '{topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False


async def delete_collection(account_id: str, topic_name: str, workspace_id: Optional[str] = None) -> bool:
    """
    Elimina una colección (UserDocumentTopic) y todos sus documentos asociados.
    """
    # Decodificar el nombre del topic al principio
    decoded_topic_name = unquote(topic_name)
    logger.info(f"Eliminando colección '{decoded_topic_name}' para cuenta {account_id} en workspace {workspace_id}")
    async with DBSession(SessionLocal) as db:
        try:
            # 1. Obtener la colección para determinar su workspace_id real
            collection = await get_user_document_topic_by_name(
                account_id=account_id,
                topic_name=decoded_topic_name,
                workspace_id=workspace_id
            )
            if not collection:
                logger.warning(f"Colección '{decoded_topic_name}' no encontrada para la cuenta {account_id} en workspace {workspace_id}.")
                return False

            # Usar el workspace_id de la colección encontrada para eliminar chunks
            collection_workspace_id = collection.get("workspace_id")

            # 2. Eliminar todos los chunks de documentos asociados a esta colección
            deleted_chunks_count = await delete_document_chunks(
                account_id=account_id,
                topic=decoded_topic_name, # Usar el nombre decodificado
                workspace_id=collection_workspace_id
            )
            logger.info(f"Eliminados {deleted_chunks_count} chunks de documentos para la colección '{decoded_topic_name}'.")

            # 3. Eliminar la entrada de la colección de la tabla UserDocumentTopic
            delete_query = delete(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == decoded_topic_name # Usar el nombre decodificado
            )
            if collection_workspace_id:
                delete_query = delete_query.where(UserDocumentTopic.workspace_id == uuid.UUID(collection_workspace_id))

            result = await db.execute(delete_query)
            deleted_collection_entries = result.rowcount or 0
            await db.commit()

            if deleted_chunks_count > 0 or deleted_collection_entries > 0:
                logger.info(f"✅ Colección '{decoded_topic_name}' y sus documentos eliminados exitosamente.")
                return True
            else:
                logger.warning(f"No se encontraron documentos ni entradas de colección para eliminar para '{decoded_topic_name}'.")
                return False
        except Exception as e:
            logger.error(f"❌ Error al eliminar colección '{decoded_topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False


async def get_user_document_topic_by_name(account_id: str, topic_name: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Obtiene los detalles de una colección (UserDocumentTopic) por su nombre.
    """
    decoded_topic_name = unquote(topic_name)
    logger.info(f"Obteniendo detalles de colección '{decoded_topic_name}' para cuenta {account_id} (workspace: {workspace_id})")
    async with DBSession(SessionLocal) as db:
        try:
            logger.info(f"DEBUG: get_user_document_topic_by_name - account_id: {account_id}, topic_name: {topic_name} (decoded: {decoded_topic_name}), workspace_id: {workspace_id})")

            conditions = [
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == decoded_topic_name # Usar el nombre decodificado
            ]

            # Modificación aquí: Solo añadir la condición de workspace_id si se proporciona
            if workspace_id:
                conditions.append(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            # Si workspace_id es None, no añadimos ninguna condición de workspace_id,
            # lo que significa que buscará la colección en todos los workspaces del usuario.

            topic_query = select(UserDocumentTopic).options(
                selectinload(UserDocumentTopic.contact_profiles),
                selectinload(UserDocumentTopic.account)
            ).where(*conditions)

            # Log the SQL query before execution
            from sqlalchemy.dialects import postgresql # Import for compiling query
            compiled_query = topic_query.compile(dialect=postgresql.dialect())
            logger.info(f"DEBUG: get_user_document_topic_by_name - Compiled SQL Query: {compiled_query.string}")
            logger.info(f"DEBUG: get_user_document_topic_by_name - Query Parameters: {compiled_query.params}")

            collection = (await db.execute(topic_query)).scalars().first()
            if not collection:
                logger.warning(f"Colección '{decoded_topic_name}' no encontrada para la cuenta {account_id} en workspace {workspace_id}.")
                return None

            # Contar documentos en langchain_pg_embedding
            count_clauses = [
                "cmetadata->>'type' = 'document_chunk'",
                "topic = :topic_name"
            ]
            count_params: Dict[str, Any] = {
                "topic_name": decoded_topic_name # Usar el nombre decodificado
            }
            if workspace_id:
                count_clauses.append("workspace_id = :workspace_id")
                count_params["workspace_id"] = workspace_id
            else:
                count_clauses.append("workspace_id IS NULL")
            
            count_query = text(f"""
                SELECT COUNT(DISTINCT cmetadata->>'document_id')
                FROM langchain_pg_embedding
                WHERE {" AND ".join(count_clauses)}
            """)
            document_count = await db.scalar(count_query, count_params) or 0

            linked_profiles_data = []
            for cp in collection.contact_profiles:
                linked_profiles_data.append({
                    "id": str(cp.id),
                    "name": cp.name,
                    "email": cp.email,
                    "phone": cp.phone,
                })

            return {
                "id": str(collection.id),
                "topic": collection.name,
                "description": collection.description,
                "document_count": document_count,
                "workspace_id": str(collection.workspace_id) if collection.workspace_id else None,
                "created_by_account_id": str(collection.account_id),
                "created_by_email": collection.account.email if collection.account else None,
                "linked_profiles": linked_profiles_data,
                "has_knowledge_graph": False # Placeholder, se actualizará si se genera un KG
            }
        except Exception as e:
            logger.error(f"❌ Error al obtener detalles de colección '{decoded_topic_name}': {e}", exc_info=True)
            await db.rollback()
            return None