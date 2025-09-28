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
from pydantic.fields import FieldInfo # Importar FieldInfo
import datetime

import uuid
from langchain_core.documents import Document as LCDocument # Renombrado para evitar conflicto
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import Table, MetaData, update
from langchain_core.retrievers import BaseRetriever # Nueva importación

from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.database import (
    Perfil,
    SessionLocal,
    Account,
    engine,
    LangchainPgCollection,
    UserDocumentTopic,
    GitHubDocument # <--- NUEVA IMPORTACIÓN
)
from utils.db_session import DBSession
from utils.embeddings import get_embedding_model
from core.config import settings
from core.citation_models import ToolOutputWithSources, Source, create_document_source, format_context_with_sources
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
    k: int,
    similarity_threshold: float,
    collection_id: uuid.UUID,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    account_id: str = None,
    workspace_id: str = None,
    team_id: str = None,
    visibility_teams: List[str] = None,
    content_type: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Tuple[LCDocument, float]]:
    """
    Realiza una búsqueda semántica en la base de datos vectorial.
    """
    try:
        sql_query = """
            SELECT
                document,
                cmetadata,
                topic,
                category,
                workspace_id,
                team_id,
                visibility_teams,
                (embedding <-> CAST(:query_embedding AS vector)) AS similarity_score
            FROM langchain_pg_embedding
            WHERE collection_id = :collection_id
        """
        query_params = {
            "collection_id": collection_id,
            "query_embedding": query_embedding,
        }

        filter_clauses = []

        if account_id:
            filter_clauses.append("account_id = :account_id")
            query_params["account_id"] = account_id

        if workspace_id:
            filter_clauses.append("workspace_id = :workspace_id")
            query_params["workspace_id"] = workspace_id
        else:
            filter_clauses.append("workspace_id IS NULL")

        if team_id:
            filter_clauses.append("team_id = :team_id")
            query_params["team_id"] = team_id
        
        if filter_topics:
            filter_clauses.append("topic = ANY(:filter_topics)")
            query_params["filter_topics"] = filter_topics

        if filter_document_ids:
            filter_clauses.append("cmetadata->>'document_id' = ANY(:filter_document_ids)")
            query_params["filter_document_ids"] = filter_document_ids

        if visibility_teams:
            filter_clauses.append("(visibility_teams ?| :visibility_teams OR team_id = ANY(:visibility_teams))")
            query_params["visibility_teams"] = visibility_teams

        if content_type: # NUEVO
            filter_clauses.append("content_type = :content_type")
            query_params["content_type"] = content_type

        if category: # NUEVO
            filter_clauses.append("category = :category")
            query_params["category"] = category

        if filter_clauses:
            sql_query += " AND " + " AND ".join(filter_clauses)

        sql_query += " ORDER BY similarity_score LIMIT :k"
        query_params["k"] = k

        async with DBSession(SessionLocal) as session:
            results = await session.execute(text(sql_query), query_params)
            rows = results.fetchall()

        processed_results = []
        for row in rows:
            doc_content = row[0]
            doc_metadata = row[1]
            similarity_score = row[7]
            
            if isinstance(doc_metadata, str):
                try:
                    doc_metadata = json.loads(doc_metadata)
                except json.JSONDecodeError:
                    doc_metadata = {}
            elif not isinstance(doc_metadata, dict):
                doc_metadata = {}

            if row[2] is not None: doc_metadata['topic'] = row[2]
            if row[3] is not None: doc_metadata['category'] = row[3]
            if row[4] is not None: doc_metadata['workspace_id'] = str(row[4])
            if row[5] is not None: doc_metadata['team_id'] = str(row[5])
            if row[6] is not None: doc_metadata['visibility_teams'] = row[6]

            processed_results.append((LCDocument(page_content=doc_content, metadata=doc_metadata), similarity_score))

        return processed_results

    except Exception as e:
        logger.error(f"❌ Error en búsqueda semántica: {e}", exc_info=True)
        return []

async def _run_fts_search(
    query: str,
    k: int,
    collection_id: uuid.UUID,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    account_id: str = None,
    workspace_id: str = None,
    team_id: str = None,
    visibility_teams: List[str] = None,
    content_type: Optional[str] = None, # NUEVO
    category: Optional[str] = None, # NUEVO
) -> List[LCDocument]:
    """
    Realiza una búsqueda de texto completo (FTS) en la base de datos.
    """
    try:
        sql_query = f"""
            SELECT
                document,
                cmetadata,
                topic,
                category,
                workspace_id,
                team_id,
                visibility_teams,
                ts_rank(text_search_vector, plainto_tsquery('spanish', :query_fts)) AS rank_score
            FROM langchain_pg_embedding
            WHERE collection_id = :collection_id AND text_search_vector @@ plainto_tsquery('spanish', :query_fts)
        """
        query_params = {
            "collection_id": collection_id,
            "query_fts": query,
        }

        filter_clauses = []

        if account_id:
            filter_clauses.append("account_id = :account_id")
            query_params["account_id"] = account_id

        if workspace_id:
            filter_clauses.append("workspace_id = :workspace_id")
            query_params["workspace_id"] = workspace_id
        else:
            filter_clauses.append("workspace_id IS NULL")

        if team_id:
            filter_clauses.append("team_id = :team_id")
            query_params["team_id"] = team_id
        
        if filter_topics:
            filter_clauses.append("topic = ANY(:filter_topics)")
            query_params["filter_topics"] = filter_topics

        if filter_document_ids:
            filter_clauses.append("cmetadata->>'document_id' = ANY(:filter_document_ids)")
            query_params["filter_document_ids"] = filter_document_ids

        if visibility_teams:
            filter_clauses.append("(visibility_teams ?| :visibility_teams OR team_id = ANY(:visibility_teams))")
            query_params["visibility_teams"] = visibility_teams

        if content_type: # NUEVO
            filter_clauses.append("content_type = :content_type")
            query_params["content_type"] = content_type

        if category: # NUEVO
            filter_clauses.append("category = :category")
            query_params["category"] = category

        if filter_clauses:
            sql_query += " AND " + " AND ".join(filter_clauses)

        sql_query += " ORDER BY rank_score DESC LIMIT :k"
        query_params["k"] = k

        async with DBSession(SessionLocal) as session:
            results = await session.execute(text(sql_query), query_params)
            rows = results.fetchall()

        processed_results = []
        for row in rows:
            doc_content = row[0]
            doc_metadata = row[1]
            
            if isinstance(doc_metadata, str):
                try:
                    doc_metadata = json.loads(doc_metadata)
                except json.JSONDecodeError:
                    doc_metadata = {}
            elif not isinstance(doc_metadata, dict):
                doc_metadata = {}

            if row[2] is not None: doc_metadata['topic'] = row[2]
            if row[3] is not None: doc_metadata['category'] = row[3]
            if row[4] is not None: doc_metadata['workspace_id'] = str(row[4])
            if row[5] is not None: doc_metadata['team_id'] = str(row[5])
            if row[6] is not None: doc_metadata['visibility_teams'] = row[6]

            processed_results.append(LCDocument(page_content=doc_content, metadata=doc_metadata))
        
        return processed_results

    except Exception as e:
        logger.error(f"❌ Error en búsqueda FTS: {e}", exc_info=True)
        return []


async def get_relevant_memories(
    account_id: str,
    query: str,
    k: int = 10,
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    hybrid_search: bool = True,
    bm25_weight: float = settings.hybrid_search_bm25_weight,
    reranking: bool = True,
    content_type: Optional[str] = None, # NUEVO
    category: Optional[str] = None, # NUEVO
    similarity_threshold: float = 0.7, # NUEVO
    visibility_teams: Optional[List[str]] = None, # AÑADIDO
) -> ToolOutputWithSources:
    """
    Recupera memorias y/o documentos relevantes, los formatea para citación
    y devuelve un objeto ToolOutputWithSources.
    """
    logger.info(
        f"🔍 Buscando memorias/documentos relevantes para la cuenta {account_id} con la consulta: '{query[:50]}...'"
    )
    try:
        # Instancia tu cliente de vector store (PGVector)
        # Necesitas un cliente que pueda ejecutar tanto vector search como FTS
        # Podrías crear una clase Wrapper para tu PGVector
        class KognitoPGVectorRetriever(BaseRetriever):
            # Implementar _get_relevant_documents y _aget_relevant_documents
            # que llamen a _run_semantic_search y _run_fts_search de MemoryManager
            
            collection_id: uuid.UUID
            k: int
            similarity_threshold: float
            filter_topics: Optional[List[str]]
            filter_document_ids: Optional[List[str]]
            account_id: str
            workspace_id: Optional[str]
            team_id: Optional[str]
            visibility_teams: Optional[List[str]]
            content_type: Optional[str]
            category: Optional[str]

            def _get_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                return []

            async def _aget_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                from utils.embeddings import get_cached_embedding
                query_embedding = await get_cached_embedding(query_str)
                
                semantic_results_with_scores = await _run_semantic_search(
                    query_embedding=query_embedding,
                    k=self.k,
                    similarity_threshold=self.similarity_threshold,
                    collection_id=self.collection_id,
                    filter_topics=self.filter_topics,
                    filter_document_ids=self.filter_document_ids,
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                    team_id=self.team_id,
                    visibility_teams=self.visibility_teams,
                    content_type=self.content_type, # NUEVO
                    category=self.category, # NUEVO
                )
                return [doc for doc, score in semantic_results_with_scores]

        # Para el retriever FTS, lo construiremos directamente con la lógica de MemoryManager
        class KognitoFTSRetriever(BaseRetriever):
            
            collection_id: uuid.UUID
            k: int
            filter_topics: Optional[List[str]]
            filter_document_ids: Optional[List[str]]
            account_id: str
            workspace_id: Optional[str]
            team_id: Optional[str]
            visibility_teams: Optional[List[str]]
            content_type: Optional[str]
            category: Optional[str]

            def _get_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                return []
            
            async def _aget_relevant_documents(self, query_str: str, **kwargs) -> List[LCDocument]:
                return await _run_fts_search(
                    query=query_str,
                    k=self.k,
                    collection_id=self.collection_id,
                    filter_topics=self.filter_topics,
                    filter_document_ids=self.filter_document_ids,
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                    team_id=self.team_id,
                    visibility_teams=self.visibility_teams,
                    content_type=self.content_type, # NUEVO
                    category=self.category, # NUEVO
                )
        
        # Obtener la colección de LangchainPgCollection
        async with DBSession(SessionLocal) as db:
            collection_obj = await db.scalar(
                select(LangchainPgCollection).where(LangchainPgCollection.name == f"user_documents_{account_id}")
            )
            if not collection_obj:
                logger.warning(f"No se encontró la colección de documentos para account_id: {account_id}. Creando una nueva.")
                # Crear una colección dummy si no existe para evitar errores.
                # En un escenario real, esto se manejaría mejor al crear el usuario/workspace.
                collection_obj = LangchainPgCollection(name=f"user_documents_{account_id}")
                db.add(collection_obj)
                await db.commit()
                await db.refresh(collection_obj)
            collection_id = collection_obj.uuid

        semantic_retriever = KognitoPGVectorRetriever(
            memory_manager=None, # No se necesita la instancia de MemoryManager aquí
            collection_id=collection_id,
            k=k,
            similarity_threshold=similarity_threshold, # Ahora configurable
            filter_topics=filter_topics,
            filter_document_ids=filter_document_ids,
            account_id=account_id,
            workspace_id=workspace_id,
            team_id=team_id,
            visibility_teams=visibility_teams, # Pasado
            content_type=content_type, # Pasado
            category=category, # Pasado
        )

        fts_retriever = KognitoFTSRetriever(
            memory_manager=None, # No se necesita la instancia de MemoryManager aquí
            collection_id=collection_id,
            k=k,
            filter_topics=filter_topics,
            filter_document_ids=filter_document_ids,
            account_id=account_id,
            workspace_id=workspace_id,
            team_id=team_id,
            visibility_teams=visibility_teams,
            content_type=content_type, # Pasado
            category=category, # Pasado
        )

        from langchain.retrievers import EnsembleRetriever # Importación aquí para evitar circularidad
        # from core.reranker import Reranker # Importación aquí para evitar circularidad

        final_retrieved_docs: List[LCDocument] = []
        if hybrid_search:
            ensemble_retriever = EnsembleRetriever(
                retrievers=[semantic_retriever, fts_retriever],
                weights=[1 - bm25_weight, bm25_weight]
            )
            final_retrieved_docs = await ensemble_retriever.ainvoke(query)
        else:
            final_retrieved_docs = await semantic_retriever.ainvoke(query) # Solo semántico

        # Reranking
        if reranking:
            reranker = Reranker() # Asegúrate de que se instancia correctamente
            final_retrieved_docs = await reranker.rerank(query, final_retrieved_docs) # Removed top_n
        
        # Convertir a ToolOutputWithSources (ya implementado)
        final_content_list = []
        final_sources = []
        for i, doc in enumerate(final_retrieved_docs):
            final_content_list.append(doc.page_content)
            # Corrected create_document_source call
            final_sources.append(create_document_source(
                source_id=i + 1, # Pass a unique integer ID
                title=doc.metadata.get("title", doc.metadata.get("file_name", "Documento")),
                file_path=doc.metadata.get("document_id", f"doc_{i}"), # Use document_id as unique URL/path
                snippet=doc.page_content,
                metadata={
                    "document_id": doc.metadata.get("document_id"),
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
    team_id: str | None = None,
    visibility_teams: List[str] | None = None,
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
                team_id = :team_id,
                visibility_teams = :visibility_teams,
                telegram_id = :telegram_id,
                thread_id = :thread_id
            WHERE
                collection_id = :collection_uuid
                AND cmetadata->>'file_name' = :file_name
                AND cmetadata->>'type' = 'document_chunk'
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
            "team_id": team_id,
            "visibility_teams": visibility_teams,
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
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    topic: Optional[str] = None,
    category: Optional[str] = None,
    telegram_id: Optional[str] = None, # Nuevo parámetro
    thread_id: Optional[str] = None, # Nuevo parámetro
) -> None:
    """
    Genera embeddings para el contenido y lo guarda en la DB vectorial del usuario o equipo.

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

        collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"

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
            "scope": "personal" if not team_id else "team",
            "topic": topic if topic else "general",
            "category": category if category else "general"
        }
        if team_id:
            metadata["team_id"] = str(team_id)
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
                    content_type="user_memories" if not team_id else "team_memories",
                    topic=topic,
                    category=category,
                    workspace_id=workspace_id,
                    team_id=team_id,
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
    team_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[str] = None,
) -> int:
    """
    Divide, embebe y almacena el texto de un documento en la DB vectorial.
    
    CAMBIO: Ahora usa solo langchain_pg_embedding para todos los documentos,
    agregando workspace_id como metadato y columna cuando corresponde.
    """
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
    """
    Divide, embebe y almacena el texto de un documento en la DB vectorial.
    
    CAMBIO: Ahora usa solo langchain_pg_embedding para todos los documentos,
    agregando workspace_id como metadato y columna cuando corresponde.
    """
    if not extracted_text:
        return 0
        
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
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        texts = text_splitter.split_text(extracted_text)
        logger.info(f"Documento '{file_name}' dividido en {len(texts)} chunks.")
        
        # Determinar la colección de LangChain (topic)
        # Si se proporciona workspace_id, la colección será específica de ese workspace.
        # Si no, será una colección de usuario/equipo/global.
        if workspace_id:
            # Para colecciones de workspace, el nombre de la colección en PGVector será el topic
            # El topic es el nombre de la colección dentro del workspace.
            langchain_collection_name = topic # El topic es el nombre de la colección
            scope = "workspace"
        elif is_global:
            langchain_collection_name = GLOBAL_COLLECTION_NAME
            scope = "global"
        elif account_id:
            langchain_collection_name = f"user_documents_{account_id}"
            scope = "personal"
        elif team_id:
            langchain_collection_name = f"team_documents_{team_id}"
            scope = "team"
        else:
            logger.error("❌ process_document_for_rag llamado sin account_id, team_id, workspace_id o is_global=True.")
            return 0
 
        logger.info(f"📊 Iniciando procesamiento RAG para '{file_name}' en la colección LangChain '{langchain_collection_name}'.")
        
        # Preparar metadatos base
        base_metadata = metadata if metadata else {}
        base_metadata.update({
            "file_name": file_name, 
            "topic": topic, # El topic sigue siendo el tema del documento
            "type": "document_chunk",
            "scope": scope,
        })
        
        # Agregar IDs según corresponda
        if account_id: 
            base_metadata["account_id"] = str(account_id)
        if team_id: 
            base_metadata["team_id"] = str(team_id)
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
        logger.info(f"Iniciando aadd_documents para {len(lc_documents)} chunks en colección '{langchain_collection_name}'.")
        await vectorstore.aadd_documents(lc_documents)
        logger.info(f"Finalizado aadd_documents para {len(lc_documents)} chunks en colección '{langchain_collection_name}'.")

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
                topic=topic,
                workspace_id=workspace_id,
                team_id=team_id
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
                    "topic": topic,
                    "workspace_id": workspace_id,
                })
        except ImportError:
            logger.warning("Could not import send_personal_message, WebSocket notifications will be disabled.")
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")

        # Trigger proactivo deshabilitado para documentos (se analizará en un job nocturno)
        if account_id or team_id:
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
        except Exception as ws_e:
            logger.error(f"Error sending WebSocket notification on failure: {ws_e}")
        return 0


async def remove_document_from_rag(
    account_id: str,
    file_name: str,
    topic: str = "repositorio",
    team_id: Optional[str] = None,
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
        elif team_id:
            langchain_collection_name = f"team_documents_{team_id}"
        else:
            langchain_collection_name = f"user_documents_{account_id}"
        
        # Usar la función existente delete_document_chunks
        deleted_count = await delete_document_chunks(
            account_id=account_id,
            file_name=file_name,
            topic=topic,
            team_id=team_id,
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
    team_id: Optional[str] = None,
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
    logger.info(f"👥 Team ID: {team_id}")
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

            if team_id:
                clauses.append("team_id = :team_id")
                params["team_id"] = team_id

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
    file_name: str,
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> Optional[str]:
    """
    Reconstruye y devuelve el contenido completo de un documento desde sus chunks.

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin JOINs.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a reconstruir.
        team_id: El ID del equipo (UUID en formato string) para buscar en la colección del equipo, si aplica.
        workspace_id: El ID del workspace (UUID en formato string) para buscar en la colección del workspace, si aplica.
    Returns:
        El contenido completo del documento como una cadena, o None si no se encuentra.
    """
    logger.info(
        f"📄 Recuperando contenido completo (OPTIMIZADO) de '{file_name}' para la cuenta {account_id}"
        f" (Workspace: {workspace_id if workspace_id else 'N/A'})"
    )

    try:
        async with DBSession(SessionLocal) as db:
            # Construir consulta optimizada usando las nuevas columnas directamente
            clauses = [
                "account_id = :account_id",
                "cmetadata->>'file_name' = :file_name",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {
                "account_id": account_id,
                "file_name": file_name
            }

            if team_id:
                clauses.append("team_id = :team_id")
                params["team_id"] = team_id

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

            if processed_workspace_id:
                clauses.append("workspace_id = :workspace_id")
                params["workspace_id"] = processed_workspace_id

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
            f"❌ Error recuperando contenido optimizado de '{file_name}' (workspace {workspace_id}): {e}", exc_info=True
        )
        return None


async def list_user_documents(
    account_id: str,
    team_id: Optional[str] = None,
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
    - Si no, lista los documentos de la colección general del usuario o equipo.
    """
    logger.info(f"📋 list_user_documents - account_id: {account_id}, workspace_id: {workspace_id}, topic: {topic}, topics: {topics}, doc_ids: {document_ids}")
    async with DBSession(SessionLocal) as db:
        try:
            base_clauses = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"account_id": account_id}

            # --- Lógica de Filtro de Contexto Explícito ---
            if document_ids or topics:
                context_filters = []
                if document_ids:
                    context_filters.append("cmetadata->>'document_id' = ANY(:document_ids)")
                    params["document_ids"] = document_ids
                if topics: # Nuevo parámetro topics (lista)
                    # Si se especifican topics, filtrar por ellos
                    context_filters.append("topic = ANY(:topics)")
                    params["topics"] = topics
                
                base_clauses.append(f"({' OR '.join(context_filters)})")
            # --- Fin Lógica de Filtro de Contexto ---
            else:
                # --- Lógica de Filtro General (si no hay contexto explícito) ---
                # Si el topic es 'all_documents', no aplicar filtro de topic
                if topic == "all_documents":
                    logger.info("📎 Topic es 'all_documents', no se aplicará filtro de topic.")
                else:
                    if team_id:
                        base_clauses.append("team_id = :team_id")
                        params["team_id"] = team_id

                    if isinstance(workspace_id, str) and workspace_id:
                        base_clauses.append("(workspace_id = :workspace_id OR workspace_id IS NULL)")
                        params["workspace_id"] = workspace_id
                    else:
                        base_clauses.append("workspace_id IS NULL")

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
                       workspace_id::text AS workspace_id,
                       team_id::text AS team_id,
                       CASE WHEN team_id IS NOT NULL THEN true ELSE false END AS team_shared
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
                       workspace_id::text AS workspace_id,
                       team_id::text AS team_id,
                       CASE WHEN team_id IS NOT NULL THEN true ELSE false END AS team_shared
                FROM langchain_pg_embedding
                WHERE {" AND ".join(clauses)}
                ORDER BY cmetadata->>'document_id', id;
            """

            logger.info(f"� Query SQL para todos los documentos: {query_str}")
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
    team_id: Optional[str] = None,
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
        team_id: El ID del equipo (UUID en formato string) para actualizar en la colección del equipo, si aplica.
        workspace_id: El ID del workspace (UUID en formato string) para actualizar el documento de un workspace específico, si aplica.

    Returns:
        True si la operación fue exitosa, False en caso contrario.
    """
    if not new_title and not new_topic:
        logger.warning(f"Se llamó a update_document_metadata para '{file_name}' sin nuevos datos para actualizar.")
        return False

    logger.info(
        f"📝 Actualizando metadatos (OPTIMIZADO) para '{file_name}' (cuenta {account_id}). "
        f"Nuevo título: {new_title}, Nuevo tema: {new_topic}. Workspace ID: {workspace_id if workspace_id else 'N/A'}."
    )

    async with DBSession(SessionLocal) as db:
        try:
            # Construir filtros usando las nuevas columnas directamente
            clauses = [
                "account_id = :account_id",
                "cmetadata->>'file_name' = :file_name",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {
                "account_id": account_id,
                "file_name": file_name
            }

            if team_id:
                clauses.append("team_id = :team_id")
                params["team_id"] = team_id

            if workspace_id:
                clauses.append("workspace_id = :workspace_id")
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
            if new_topic is not None:
                values_to_update['topic'] = new_topic
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
                "topic_column": new_topic if new_topic is not None else current_cmetadata.get('topic')
            })

            logger.info(f"🔧 Query SQL optimizada: {update_sql}")
            logger.info(f"📋 Parámetros: {update_params}")

            result = await db.execute(update_sql, update_params)
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Se actualizaron {result.rowcount} chunks para el archivo '{file_name}' usando consulta optimizada.")

                # Enviar notificación WebSocket en tiempo real
                try:
                    from core.websocket_manager import send_personal_message
                    await send_personal_message(account_id, {
                        "type": "document_title_updated",
                        "file_name": file_name,
                        "new_title": new_title,
                        "new_topic": new_topic,
                        "workspace_id": workspace_id,
                        "team_id": team_id,
                        "message": f"Título actualizado para '{file_name}'"
                    })
                    logger.info(f"📡 Notificación WebSocket enviada para actualización de título de '{file_name}'")
                except Exception as e:
                    logger.warning(f"No se pudo enviar notificación WebSocket para '{file_name}': {e}")

                return True
            else:
                logger.warning(f"La consulta de actualización optimizada para '{file_name}' no afectó ninguna fila.")
                return False

        except Exception as e:
            logger.error(f"❌ Error actualizando metadatos optimizado de '{file_name}' (workspace {workspace_id}): {e}", exc_info=True)
            await db.rollback()
            return False



async def list_user_collections(account_id: str, team_id: Optional[str] = None, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todas las colecciones (temas) únicas de documentos de un usuario o equipo.

    Combina:
    1. Colecciones definidas por el usuario en UserDocumentTopic (incluye vacías)
    2. Colecciones que tienen documentos en langchain_pg_embedding (con conteo)

    IMPORTANTE: Cuando se especifica workspace_id, se incluyen SOLO las colecciones específicas de ese workspace.
    Para acceder a colecciones del contexto general, no se debe especificar workspace_id.

    Args:
        account_id: ID de la cuenta del usuario. Obligatorio para listar colecciones de usuario.
        team_id: ID del equipo (opcional). Usado para filtrar documentos de equipo.
        workspace_id: ID del workspace (opcional). Usado para filtrar documentos de un workspace específico.
    """
    logger.info(f"Listando colecciones (temas) de documentos para la cuenta {account_id}, workspace: {workspace_id}")

    async with DBSession(SessionLocal) as db:
        try:
            collections_map = {}

            # 1. Obtener colecciones definidas por el usuario en UserDocumentTopic
            user_topics_query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id)
            )

            if workspace_id:
                # Para workspaces, incluir SOLO las colecciones específicas del workspace
                user_topics_query = user_topics_query.where(
                    UserDocumentTopic.workspace_id == uuid.UUID(workspace_id)
                )
            elif team_id:
                user_topics_query = user_topics_query.where(
                    UserDocumentTopic.team_id == uuid.UUID(team_id)
                )
            else:
                # Colecciones personales (sin workspace ni team)
                user_topics_query = user_topics_query.where(
                    UserDocumentTopic.workspace_id.is_(None),
                    UserDocumentTopic.team_id.is_(None)
                )
            
            result = await db.execute(user_topics_query)
            user_topics = result.scalars().all()
            logger.info(f"DEBUG: user_topics obtenidos de UserDocumentTopic: {[t.name + ' (workspace_id: ' + (str(t.workspace_id) if t.workspace_id else 'None') + ')' for t in user_topics]}")
            
            # Añadir todas las colecciones definidas por el usuario (con 0 documentos por defecto)
            for topic in user_topics:
                collections_map[topic.name] = {
                    "topic": topic.name,
                    "document_count": 0,
                    "description": topic.description,
                    "workspace_id": str(topic.workspace_id) if topic.workspace_id else None # Añadir workspace_id
                }
            logger.info(f"DEBUG: collections_map después de UserDocumentTopic: {collections_map}")
            
            # 2. Obtener conteos reales de documentos desde langchain_pg_embedding (OPTIMIZADO)
            where_clause_parts = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'",
                "topic IS NOT NULL"
            ]
            params = {"account_id": account_id}

            if team_id:
                where_clause_parts.append("team_id = :team_id")
                params["team_id"] = team_id

            if workspace_id:
                # Para workspaces, incluir SOLO las colecciones específicas del workspace
                where_clause_parts.append("workspace_id = :workspace_id")
                params["workspace_id"] = workspace_id
            else:
                # Para contexto general, incluir solo documentos sin workspace_id
                where_clause_parts.append("workspace_id IS NULL")

            final_where_clause = " AND ".join(where_clause_parts)

            collections_query = text(
                f"""
                SELECT
                    topic AS topic,
                    COUNT(DISTINCT cmetadata->>'document_id') as document_count, -- Contar documentos únicos
                    workspace_id::text as workspace_id -- Obtener el workspace_id de los documentos
                FROM langchain_pg_embedding
                WHERE {final_where_clause}
                GROUP BY topic, workspace_id -- Agrupar también por workspace_id
                ORDER BY topic;
                """
            )
            
            logger.info(f"DEBUG: list_user_collections - Querying langchain_pg_embedding with SQL: {collections_query} and params: {params}")
            result = await db.execute(collections_query, params)
            embedding_collections = [dict(row) for row in result.mappings()]
            logger.info(f"DEBUG: embedding_collections (conteos) obtenidos: {embedding_collections}")
            
            # 3. Actualizar conteos y agregar colecciones que solo existen en embeddings
            for collection in embedding_collections:
                topic_name = collection["topic"]
                current_workspace_id = collection["workspace_id"] # Obtener workspace_id del embedding
                
                # Usar una clave compuesta para manejar colecciones con el mismo nombre en diferentes workspaces
                # Si la colección ya existe en collections_map con el mismo nombre y workspace_id, actualizar
                # Si la colección existe con el mismo nombre pero diferente workspace_id (o None), añadirla como nueva entrada
                
                # Buscar si ya existe una entrada para esta combinación de topic y workspace_id
                found_match = False
                for k, v in collections_map.items():
                    if v["topic"] == topic_name and v["workspace_id"] == current_workspace_id:
                        v["document_count"] = collection["document_count"]
                        found_match = True
                        break
                
                if not found_match:
                    # Si no se encontró una combinación existente, añadir como nueva
                    collections_map[f"{topic_name}-{current_workspace_id}"] = { # Usar clave compuesta para evitar sobrescribir
                        "topic": topic_name,
                        "document_count": collection["document_count"],
                        "description": None,
                        "workspace_id": current_workspace_id
                    }
            
            return_list = list(collections_map.values())
            logger.info(f"DEBUG: collections_map final antes de retornar: {return_list}")
            return return_list
            
        except Exception as e:
            logger.error(f"❌ Error listando colecciones (temas) de documentos para la cuenta {account_id}: {e}", exc_info=True)
            return []


async def create_empty_collection(
    account_id: str, 
    topic_name: str, 
    description: Optional[str] = None,
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None
) -> bool:
    """
    Crea una colección vacía en la tabla UserDocumentTopic.
    
    Args:
        account_id: ID de la cuenta del usuario.
        topic_name: Nombre de la nueva colección.
        description: Descripción opcional de la colección.
        workspace_id: ID del workspace (opcional).
        team_id: ID del equipo (opcional).
        
    Returns:
        True si la colección se creó exitosamente, False si ya existe o hay error.
    """
    logger.info(f"Creando colección vacía '{topic_name}' para cuenta {account_id}")
    
    async with DBSession(SessionLocal) as db:
        try:
            # Verificar si la colección ya existe
            existing_query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )
            
            if workspace_id:
                existing_query = existing_query.where(
                    UserDocumentTopic.workspace_id == uuid.UUID(workspace_id)
                )
            elif team_id:
                existing_query = existing_query.where(
                    UserDocumentTopic.team_id == uuid.UUID(team_id)
                )
            else:
                existing_query = existing_query.where(
                    UserDocumentTopic.workspace_id.is_(None),
                    UserDocumentTopic.team_id.is_(None)
                )
            
            existing_collection = await db.scalar(existing_query)
            if existing_collection:
                logger.warning(f"La colección '{topic_name}' ya existe para la cuenta {account_id}")
                return False
            
            # Crear la nueva colección
            new_collection = UserDocumentTopic(
                account_id=uuid.UUID(account_id),
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                team_id=uuid.UUID(team_id) if team_id else None,
                name=topic_name,
                description=description
            )
            
            db.add(new_collection)
            await db.commit()
            
            logger.info(f"✅ Colección '{topic_name}' creada exitosamente para cuenta {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando colección '{topic_name}' para cuenta {account_id}: {e}", exc_info=True)
            await db.rollback()
            return False

async def update_collection_metadata(
    account_id: str,
    old_topic_name: str,
    new_topic_name: Optional[str] = None,
    new_description: Optional[str] = None,
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None
) -> bool:
    """
    Actualiza los metadatos de una colección (nombre y/o descripción).

    Args:
        account_id: ID de la cuenta del usuario.
        old_topic_name: Nombre actual de la colección.
        new_topic_name: Nuevo nombre de la colección (opcional).
        new_description: Nueva descripción de la colección (opcional).
        workspace_id: ID del workspace (opcional).
        team_id: ID del equipo (opcional).

    Returns:
        True si la colección fue actualizada exitosamente, False si hay error.
    """
    logger.info(f"🔄 Actualizando metadatos de colección '{old_topic_name}' para cuenta {account_id}")

    async with DBSession(SessionLocal) as db:
        try:
            # Iniciar transacción
            async with db.begin():
                # 1. Actualizar la definición de la colección en UserDocumentTopic
                update_topic_stmt = update(UserDocumentTopic).where(
                    UserDocumentTopic.account_id == uuid.UUID(account_id),
                    UserDocumentTopic.name == old_topic_name
                )
                
                if workspace_id:
                    update_topic_stmt = update_topic_stmt.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
                elif team_id:
                    update_topic_stmt = update_topic_stmt.where(UserDocumentTopic.team_id == uuid.UUID(team_id))
                else:
                    update_topic_stmt = update_topic_stmt.where(UserDocumentTopic.workspace_id.is_(None), UserDocumentTopic.team_id.is_(None))

                values_to_update = {}
                if new_topic_name is not None:
                    values_to_update['name'] = new_topic_name
                if new_description is not None:
                    values_to_update['description'] = new_description

                if values_to_update:
                    result_topic = await db.execute(update_topic_stmt.values(**values_to_update))
                    if result_topic.rowcount == 0:
                        logger.warning(f"No se encontró la colección '{old_topic_name}' en UserDocumentTopic para actualizar.")
                        # No retornamos False todavía, puede que solo existan en embeddings

                # 2. Si se cambió el nombre, actualizar todos los chunks en langchain_pg_embedding
                if new_topic_name is not None and new_topic_name != old_topic_name:
                    clauses = [
                        "account_id = :account_id",
                        "topic = :old_topic_name",
                        "cmetadata->>'type' = 'document_chunk'"
                    ]
                    params: Dict[str, Any] = {
                        "account_id": account_id,
                        "old_topic_name": old_topic_name,
                        "new_topic_name": new_topic_name,
                        "new_cmetadata_topic": json.dumps(new_topic_name)
                    }

                    if workspace_id:
                        clauses.append("workspace_id = :workspace_id")
                        params["workspace_id"] = workspace_id
                    elif team_id:
                        clauses.append("team_id = :team_id")
                        params["team_id"] = team_id
                    else:
                        clauses.append("workspace_id IS NULL")

                    # Usamos jsonb_set para actualizar solo el campo 'topic' en cmetadata
                    update_embeddings_sql = text(f"""
                        UPDATE langchain_pg_embedding
                        SET
                            cmetadata = :new_cmetadata,
                            topic = :new_topic_name
                        WHERE {" AND ".join(clauses)}
                    """)

                    result_embeddings = await db.execute(update_embeddings_sql, params)
                    logger.info(f"✅ Se actualizaron {result_embeddings.rowcount} chunks en langchain_pg_embedding con el nuevo nombre de colección.")

            logger.info(f"✅ Colección '{old_topic_name}' actualizada exitosamente.")
            return True

        except Exception as e:
            logger.error(f"❌ Error actualizando colección '{old_topic_name}': {e}", exc_info=True)
            return False

async def update_collection_workspace(
    account_id: str,
    topic_name: str,
    workspace_id: str
) -> bool:
    """
    Actualiza el workspace_id en los metadatos de todos los documentos de una colección.
    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin JOINs.
    Args:
        account_id: El ID de la cuenta del usuario.
        topic_name: Nombre de la colección a actualizar.
        workspace_id: ID del workspace al que se asociará la colección.
    Returns:
        True si la colección fue actualizada exitosamente, False si hay error.
    """
    logger.info(f"🔄 Asociando colección (OPTIMIZADO) '{topic_name}' al workspace {workspace_id} para cuenta {account_id}")
    async with DBSession(SessionLocal) as db:
        try:
            # Construir filtros usando las nuevas columnas directamente
            clauses = [
                "account_id = :account_id",
                "topic = :topic_name",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {
                "account_id": account_id,
                "topic_name": topic_name
            }

            # Primero, obtener el cmetadata actual para no sobrescribir otros metadatos
            select_sql = text(f"""
                SELECT cmetadata
                FROM langchain_pg_embedding
                WHERE {" AND ".join(clauses)}
                LIMIT 1
            """)

            cmetadata_result = await db.execute(select_sql, params)
            current_cmetadata = cmetadata_result.scalar_one_or_none()

            if not current_cmetadata:
                logger.warning(f"No se encontraron documentos para la colección '{topic_name}'.")
                return False

            # Actualizar metadatos con el nuevo workspace_id
            values_to_update = current_cmetadata.copy()
            values_to_update['workspace_id'] = workspace_id

            # Actualizar tanto cmetadata como la columna optimizada workspace_id
            update_sql = text(f"""
                UPDATE langchain_pg_embedding
                SET
                    cmetadata = :new_cmetadata,
                    workspace_id = :workspace_id_column
                WHERE {" AND ".join(clauses)}
            """)

            update_params = params.copy()
            update_params.update({
                "new_cmetadata": json.dumps(values_to_update),  # Serializar a JSON string para PostgreSQL
                "workspace_id_column": workspace_id
            })

            logger.info(f"🔧 Query SQL optimizada: {update_sql}")
            logger.info(f"📋 Parámetros: {update_params}")

            result = await db.execute(update_sql, update_params)
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Se actualizaron {result.rowcount} documentos para la colección '{topic_name}' con workspace_id {workspace_id} usando consulta optimizada.")
                return True
            else:
                logger.warning(f"No se encontraron documentos para actualizar en la colección '{topic_name}'.")
                return False

        except Exception as e:
            logger.error(f"❌ Error asociando colección optimizado '{topic_name}' al workspace {workspace_id}: {e}", exc_info=True)
            await db.rollback()
            return False

async def delete_collection(
    account_id: str, 
    topic_name: str, 
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None
) -> bool:
    """
    Elimina una colección y todos los documentos asociados de la base de datos.
    
    Args:
        account_id: ID de la cuenta del usuario.
        topic_name: Nombre de la colección a eliminar.
        workspace_id: ID del workspace (opcional).
        team_id: ID del equipo (opcional).
        
    Returns:
        True si la colección y sus documentos fueron eliminados exitosamente, False si hay error.
    """
    logger.info(f"Eliminando colección '{topic_name}' para cuenta {account_id}")
    
    async with DBSession(SessionLocal) as db:
        try:
            # Eliminar los documentos asociados a la colección
            deleted_chunks = await delete_document_chunks(
                account_id=account_id,
                topic=topic_name,
                team_id=team_id,
                workspace_id=workspace_id
            )
            logger.info(f"Se eliminaron {deleted_chunks} fragmentos de documentos de la colección '{topic_name}'")
            
            # Construir la consulta de eliminación para UserDocumentTopic de forma más robusta
            delete_query = delete(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )
            
            if workspace_id:
                # Si se proporcionó un workspace_id, buscar la colección asociada a ese workspace
                delete_query = delete_query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            else:
                # Si no se proporcionó workspace_id, buscar colecciones sin workspace (generales/personales)
                delete_query = delete_query.where(UserDocumentTopic.workspace_id.is_(None))
            
            if team_id:
                # Si se proporcionó un team_id, buscar la colección asociada a ese team
                delete_query = delete_query.where(UserDocumentTopic.team_id == uuid.UUID(team_id))
            else:
                # Si no se proporcionó team_id, buscar colecciones sin team (personales/generales)
                delete_query = delete_query.where(UserDocumentTopic.team_id.is_(None))
            
            result = await db.execute(delete_query)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Colección '{topic_name}' eliminada exitosamente de UserDocumentTopic para cuenta {account_id}")
                return True
            else:
                logger.warning(f"La colección '{topic_name}' no se encontró en UserDocumentTopic para la cuenta {account_id} con los criterios especificados.")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error eliminando colección '{topic_name}' para cuenta {account_id}: {e}", exc_info=True)
            await db.rollback()
            return False
async def extract_titles_and_update_metadata(account_id: str, topic: Optional[str] = None, workspace_id: Optional[str] = None, team_id: Optional[str] = None) -> int:
    """
    Extrae títulos de los documentos y actualiza sus metadatos en la base de conocimiento del usuario.
    
    Args:
        account_id: El ID universal de la cuenta del usuario.
        topic: Tema de los documentos a procesar (opcional).
        workspace_id: El ID del workspace (UUID en formato string) para procesar documentos de un workspace específico, si aplica.
        team_id: El ID del equipo (opcional).
    
    Returns:
        Número de documentos actualizados.
    """
    logger.info(
        f"Iniciando extracción y actualización de títulos para cuenta {account_id}. "
        f"Tema: {topic}, Workspace ID: {workspace_id if workspace_id else 'N/A'}."
    )
    
    updated_count = 0
    async with DBSession(SessionLocal) as db:
        try:
            # Construir consulta optimizada usando las nuevas columnas directamente
            logger.info(f"📊 Procesando documentos (OPTIMIZADO) para cuenta {account_id}.")

            clauses = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"account_id": account_id}

            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic.description if isinstance(topic, FieldInfo) else topic.description if isinstance(topic, FieldInfo) else topic
            if workspace_id:
                clauses.append("workspace_id = :workspace_id")
                params["workspace_id"] = workspace_id
            if team_id:
                clauses.append("team_id = :team_id")
                params["team_id"] = team_id

            select_sql = text("SELECT * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
            logger.info(f"🔧 Ejecutando consulta SQL optimizada: {select_sql} con parámetros: {params}")
            result = await db.execute(select_sql, params)
            chunks = result.mappings().all()
            logger.info(f"📊 Se encontraron {len(chunks)} fragmentos de documentos para procesar usando consulta optimizada.")

            if not chunks:
                logger.info("No se encontraron fragmentos de documentos para procesar.")
                return 0

            documents = {}
            for chunk in chunks:
                file_name = chunk['cmetadata'].get('file_name')
                if file_name:
                    if file_name not in documents:
                        documents[file_name] = []
                    documents[file_name].append(chunk)
                else:
                    logger.warning(f"Fragmento sin 'file_name' en cmetadata: {chunk['cmetadata']}")

            for file_name, doc_chunks in documents.items():
                logger.info(f"Procesando documento: {file_name} con {len(doc_chunks)} fragmentos.")
                
                full_content = "".join([c['document'] for c in sorted(doc_chunks, key=lambda x: x['cmetadata'].get('chunk_index', 0))])

                new_title = None
                if full_content:
                    lines = [line.strip() for line in full_content.split('\n') if line.strip()]
                    if lines:
                        first_line = lines[0]
                        if 5 < len(first_line) < 100:
                            new_title = first_line
                        else:
                            for line in lines[:5]:
                                if len(line) > 10 and len(line) < 150 and line.isupper() and line.count(' ') < len(line)/3:
                                    new_title = line.title()
                                    break
                        if not new_title and len(lines) > 1:
                            combined_lines = " ".join(lines[:2])
                            if 10 < len(combined_lines) < 150:
                                new_title = combined_lines

                if new_title and new_title != doc_chunks[0]['cmetadata'].get('title'):
                    logger.info(f"Título extraído para {file_name}: '{new_title}'")
                    success = await update_document_metadata(account_id, file_name, new_title=new_title, new_topic=None, team_id=team_id, workspace_id=workspace_id)
                    if success:
                        updated_count += 1
                        logger.info(f"Actualizado título para el documento {file_name}.")
                    else:
                        logger.warning(f"No se pudo actualizar el título para el documento {file_name}.")
                else:
                    logger.info(f"No se encontró un nuevo título válido o el título es el mismo para {file_name}. Primera línea: {new_title}")

            if updated_count > 0:
                logger.info(f"Se actualizaron los títulos de {updated_count} documentos para la cuenta {account_id}.")
            else:
                logger.info(f"No se encontraron títulos para actualizar en los documentos de la cuenta {account_id}.")
            
            return updated_count
        except Exception as e:
            logger.error(f"Error al extraer y actualizar títulos para la cuenta {account_id} (workspace {workspace_id}): {e}", exc_info=True)
            await db.rollback()
            return 0

async def get_user_document_topic_by_name(
    account_id: str,
    topic_name: str,
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None
) -> Optional[UserDocumentTopic]:
    """
    Obtiene un UserDocumentTopic por su nombre y contexto (account_id, workspace_id, team_id).

    Args:
        account_id: ID de la cuenta del usuario.
        topic_name: Nombre del topic/colección.
        workspace_id: ID del workspace (opcional).
        team_id: ID del equipo (opcional).

    Returns:
        El objeto UserDocumentTopic si se encuentra, de lo contrario None.
    """
    logger.info(f"Buscando UserDocumentTopic '{topic_name}' para cuenta {account_id}, workspace {workspace_id}, team {team_id}")
    async with DBSession(SessionLocal) as db:
        try:
            query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )

            if workspace_id:
                query = query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            else:
                query = query.where(UserDocumentTopic.workspace_id.is_(None))

            if team_id:
                query = query.where(UserDocumentTopic.team_id == uuid.UUID(team_id))
            else:
                query = query.where(UserDocumentTopic.team_id.is_(None))

            result = await db.execute(query)
            topic = result.scalars().first()
            if topic:
                logger.info(f"✅ UserDocumentTopic '{topic_name}' encontrado.")
            else:
                logger.warning(f"UserDocumentTopic '{topic_name}' no encontrado.")
            return topic
        except Exception as e:
            logger.error(f"❌ Error al buscar UserDocumentTopic '{topic_name}': {e}", exc_info=True)
            return None

async def link_profile_to_collection(
    account_id: str,
    topic_name: str,
    description: Optional[str] = None,
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None
) -> bool:
    """
    Vincula un perfil (account_id) a una colección (topic) en UserDocumentTopic.
    Si la colección no existe para el contexto dado, la crea.

    Args:
        account_id: ID de la cuenta del usuario.
        topic_name: Nombre del topic/colección a vincular.
        description: Descripción opcional para la nueva colección.
        workspace_id: ID del workspace (opcional).
        team_id: ID del equipo (opcional).

    Returns:
        True si la vinculación fue exitosa (ya existía o se creó), False en caso de error.
    """
    logger.info(f"Vinculando perfil {account_id} a colección '{topic_name}' (workspace: {workspace_id}, team: {team_id})")
    async with DBSession(SessionLocal) as db:
        try:
            existing_topic = await get_user_document_topic_by_name(account_id, topic_name, workspace_id, team_id)

            if existing_topic:
                logger.info(f"La colección '{topic_name}' ya está vinculada al perfil {account_id}.")
                return True
            else:
                new_topic = UserDocumentTopic(
                    account_id=uuid.UUID(account_id),
                    name=topic_name,
                    description=description,
                    workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                    team_id=uuid.UUID(team_id) if team_id else None
                )
                db.add(new_topic)
                await db.commit()
                logger.info(f"✅ Colección '{topic_name}' creada y vinculada al perfil {account_id}.")
                return True
        except Exception as e:
            logger.error(f"❌ Error al vincular perfil {account_id} a colección '{topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False

async def unlink_profile_from_collection(
    account_id: str,
    topic_name: str,
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None
) -> bool:
    """
    Desvincula un perfil (account_id) de una colección (topic) en UserDocumentTopic.
    Esto elimina la entrada de la tabla UserDocumentTopic.

    Args:
        account_id: ID de la cuenta del usuario.
        topic_name: Nombre del topic/colección a desvincular.
        workspace_id: ID del workspace (opcional).
        team_id: ID del equipo (opcional).

    Returns:
        True si la desvinculación fue exitosa, False si no se encontró o hubo un error.
    """
    logger.info(f"Desvinculando perfil {account_id} de colección '{topic_name}' (workspace: {workspace_id}, team: {team_id})")
    async with DBSession(SessionLocal) as db:
        try:
            query = delete(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )

            if workspace_id:
                query = query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            else:
                query = query.where(UserDocumentTopic.workspace_id.is_(None))

            if team_id:
                query = query.where(UserDocumentTopic.team_id == uuid.UUID(team_id))
            else:
                query = query.where(UserDocumentTopic.team_id.is_(None))

            result = await db.execute(query)
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Colección '{topic_name}' desvinculada exitosamente del perfil {account_id}.")
                return True
            else:
                logger.warning(f"La colección '{topic_name}' no se encontró para desvincular del perfil {account_id}.")
                return False
        except Exception as e:
            logger.error(f"❌ Error buscando UserDocumentTopic '{topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False