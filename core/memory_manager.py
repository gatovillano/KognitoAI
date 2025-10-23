
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
from sqlalchemy.orm import selectinload, joinedload
from langchain_core.retrievers import BaseRetriever # Nueva importación

from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.database import (
    Perfil,
    SessionLocal,
    Account,
    engine,
    LangchainPgCollection,
    UserDocumentTopic,
    GitHubDocument,
    ContactProfile # <--- NUEVA IMPORTACIÓN
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
        
        if filter_topics:
            filter_clauses.append("topic = ANY(:filter_topics)")
            query_params["filter_topics"] = filter_topics

        if filter_document_ids:
            filter_clauses.append("cmetadata->>'document_id' = ANY(:filter_document_ids)")
            query_params["filter_document_ids"] = filter_document_ids

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
            similarity_score = row[5]
            
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
        
        if filter_topics:
            filter_clauses.append("topic = ANY(:filter_topics)")
            query_params["filter_topics"] = filter_topics

        if filter_document_ids:
            filter_clauses.append("cmetadata->>'document_id' = ANY(:filter_document_ids)")
            query_params["filter_document_ids"] = filter_document_ids

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

            processed_results.append(LCDocument(page_content=doc_content, metadata=doc_metadata))
        
        return processed_results

    except Exception as e:
        logger.error(f"❌ Error en búsqueda FTS: {e}", exc_info=True)
        return []


async def get_relevant_memories(
    account_id: str,
    query: str,
    k: int = 10,
    workspace_id: Optional[str] = None,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    hybrid_search: bool = True,
    bm25_weight: float = settings.hybrid_search_bm25_weight,
    reranking: bool = True,
    content_type: Optional[str] = None, # NUEVO
    category: Optional[str] = None, # NUEVO
    similarity_threshold: float = 0.7, # NUEVO
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
                    content_type="user_memories",
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
        # Si no, será una colección de usuario/global.
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
        else:
            logger.error("❌ process_document_for_rag llamado sin account_id, workspace_id o is_global=True.")
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
                topic=topic,
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
                    "topic": topic,
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
        except Exception as ws_e:
            logger.error(f"Error sending WebSocket notification on failure: {ws_e}")
        return 0


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
) -> Optional[str]:
    """
    Reconstruye y devuelve el contenido completo de un documento desde sus chunks.

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin JOINs.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a reconstruir.
        document_id: El ID único del documento a reconstruir.
        workspace_id: El ID del workspace (UUID en formato string) para buscar en la colección del workspace, si aplica.
    Returns:
        El contenido completo del documento como una cadena, o None si no se encuentra.
    """
    if not file_name and not document_id:
        raise ValueError("Se debe proporcionar file_name o document_id.")

    log_identifier = f"'{file_name}'" if file_name else f"documento ID '{document_id}'"
    logger.info(
        f"📄 Recuperando contenido completo (OPTIMIZADO) de {log_identifier} para la cuenta {account_id}"
        f" (Workspace: {workspace_id if workspace_id else 'N/A'})"
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
                    if isinstance(workspace_id, str) and workspace_id:
                        base_clauses.append("workspace_id = :workspace_id")
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



async def list_user_collections(account_id: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todas las colecciones (temas) únicas de documentos de un usuario.

    Combina:
    1. Colecciones definidas por el usuario en UserDocumentTopic (incluye vacías).
    2. Colecciones que tienen documentos en langchain_pg_embedding (con conteo).

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
            collections_map = {}

            # 1. Obtener colecciones definidas por el usuario en UserDocumentTopic
            user_topics_query = select(UserDocumentTopic).options(
                joinedload(UserDocumentTopic.workspace)
            ).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id)
            )

            # Si se especifica un workspace, filtramos. Si no, traemos todas.
            if workspace_id:
                user_topics_query = user_topics_query.where(
                    UserDocumentTopic.workspace_id == uuid.UUID(workspace_id)
                )
            
            result = await db.execute(user_topics_query)
            user_topics = result.scalars().all()
            
            # Añadir todas las colecciones definidas por el usuario (con 0 documentos por defecto)
            for topic in user_topics:
                # Usar una clave compuesta para evitar colisiones de nombres entre workspaces
                map_key = f"{topic.name}-{topic.workspace_id}"
                collections_map[map_key] = {
                    "topic": topic.name,
                    "document_count": 0,
                    "description": topic.description,
                    "workspace_id": str(topic.workspace_id) if topic.workspace_id else None,
                    "workspace_name": topic.workspace.name if topic.workspace else None, # Añadir nombre del workspace
                    "workspace_color": topic.workspace.color if topic.workspace else None, # Añadir color del workspace
                    "has_knowledge_graph": False 
                }
            
            # 2. Obtener conteos reales de documentos desde langchain_pg_embedding
            where_clause_parts = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'",
                "topic IS NOT NULL"
            ]
            params = {"account_id": account_id}

            # Si se especifica un workspace, filtramos. Si no, traemos de todos.
            if workspace_id:
                where_clause_parts.append("workspace_id = :workspace_id")
                params["workspace_id"] = workspace_id

            final_where_clause = " AND ".join(where_clause_parts)

            collections_query = text(
                f"""
                SELECT
                    topic AS topic,
                    COUNT(DISTINCT cmetadata->>'document_id') as document_count,
                    workspace_id::text as workspace_id
                FROM langchain_pg_embedding
                WHERE {final_where_clause}
                GROUP BY topic, workspace_id
                ORDER BY topic;
                """
            )
            
            result = await db.execute(collections_query, params)
            embedding_collections = [dict(row) for row in result.mappings()]
            
            # 3. Actualizar conteos y agregar colecciones que solo existen en embeddings
            for collection in embedding_collections:
                topic_name = collection["topic"]
                current_workspace_id = collection["workspace_id"]
                map_key = f"{topic_name}-{current_workspace_id}"

                if map_key in collections_map:
                    collections_map[map_key]["document_count"] = collection["document_count"]
                else:
                    # Si no existe, es una colección creada implícitamente al subir un doc.
                    workspace_name = None
                    workspace_color = None # Add this
                    if current_workspace_id:
                        from core.database import Workspace
                        ws = await db.get(Workspace, uuid.UUID(current_workspace_id))
                        if ws:
                            workspace_name = ws.name
                            workspace_color = ws.color # Add this

                    collections_map[map_key] = {
                        "topic": topic_name,
                        "document_count": collection["document_count"],
                        "description": None,
                        "workspace_id": current_workspace_id,
                        "workspace_name": workspace_name,
                        "workspace_color": workspace_color, # Add this
                        "has_knowledge_graph": False
                    }
            
            final_list = list(collections_map.values())
            logger.info(f"✅ Devolviendo {len(final_list)} colecciones para la cuenta {account_id} (workspace: {workspace_id if workspace_id else 'TODOS'})")
            return final_list
            
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
    logger.info(f"Creando colección vacía '{topic_name}' para cuenta {account_id}")
    
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
            
            existing_query = existing_query.where(UserDocumentTopic.name == topic_name)
            
            existing_collection = await db.scalar(existing_query)
            if existing_collection:
                logger.warning(f"Colección '{topic_name}' ya existe para la cuenta {account_id} en workspace {workspace_id}.")
                return False
            
            new_topic = UserDocumentTopic(
                account_id=uuid.UUID(account_id),
                name=topic_name,
                description=description,
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None
            )
            db.add(new_topic)
            await db.commit()
            await db.refresh(new_topic)
            logger.info(f"✅ Colección vacía '{topic_name}' creada exitosamente.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al crear colección vacía '{topic_name}': {e}", exc_info=True)
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
    logger.info(f"Eliminando colección '{topic_name}' para cuenta {account_id} en workspace {workspace_id}")
    async with DBSession(SessionLocal) as db:
        try:
            # 1. Eliminar todos los chunks de documentos asociados a esta colección
            deleted_chunks_count = await delete_document_chunks(
                account_id=account_id,
                topic=topic_name,
                workspace_id=workspace_id
            )
            logger.info(f"Eliminados {deleted_chunks_count} chunks de documentos para la colección '{topic_name}'.")

            # 2. Eliminar la entrada de la colección de la tabla UserDocumentTopic
            delete_query = delete(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )
            if workspace_id:
                delete_query = delete_query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            else:
                delete_query = delete_query.where(UserDocumentTopic.workspace_id.is_(None))
            
            result = await db.execute(delete_query)
            deleted_collection_entries = result.rowcount or 0
            await db.commit()

            if deleted_chunks_count > 0 or deleted_collection_entries > 0:
                logger.info(f"✅ Colección '{topic_name}' y sus documentos eliminados exitosamente.")
                return True
            else:
                logger.warning(f"No se encontraron documentos ni entradas de colección para eliminar para '{topic_name}'.")
                return False
        except Exception as e:
            logger.error(f"❌ Error al eliminar colección '{topic_name}': {e}", exc_info=True)
            await db.rollback()
            return False


async def get_user_document_topic_by_name(account_id: str, topic_name: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Obtiene los detalles de una colección (UserDocumentTopic) por su nombre.
    """
    logger.info(f"Obteniendo detalles de colección '{topic_name}' para cuenta {account_id} (workspace: {workspace_id})")
    async with DBSession(SessionLocal) as db:
        try:
            topic_query = select(UserDocumentTopic).options(selectinload(UserDocumentTopic.contact_profiles)).where(
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
                return None

            # Contar documentos en langchain_pg_embedding
            count_clauses = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'",
                "topic = :topic_name"
            ]
            count_params: Dict[str, Any] = {
                "account_id": account_id,
                "topic_name": topic_name
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
                "linked_profiles": linked_profiles_data,
                "has_knowledge_graph": False # Placeholder, se actualizará si se genera un KG
            }
        except Exception as e:
            logger.error(f"❌ Error al obtener detalles de colección '{topic_name}': {e}", exc_info=True)
            return None