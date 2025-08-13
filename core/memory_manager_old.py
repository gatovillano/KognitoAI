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
from typing import Optional, List, Union, Dict, Any
from pydantic.fields import FieldInfo # Importar FieldInfo
import datetime
# Importación movida dentro de las funciones para evitar circularidad

import uuid
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import Table, MetaData, update

from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.database import (
    Perfil,
    SessionLocal,
    Account,
    engine,
    LangchainPgCollection,
    UserDocumentTopic
)
from utils.db_session import DBSession
from utils.embeddings import get_embedding_model
from core.config import settings
from core.citation_models import ToolOutputWithSources, Source, create_document_source, format_context_with_sources

logger = logging.getLogger(__name__)

CHUNK_SIZE = settings.chunk_size


async def search_vector_db_optimized(
    account_id: str,
    query: str,
    content_types: Optional[List[str]] = None, # CAMBIO: Renombrado a plural y tipo lista
    topics: Optional[List[str]] = None,
    category: str | None = None,
    workspace_id: str | None = None,
    team_id: str | None = None,
    visibility_teams: List[str] | None = None,
    k: int | None = 5,
    document_ids: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Búsqueda vectorial optimizada que puede filtrar por múltiples topics y document_ids.
    """
    logger.info(f"🔍 Buscando en DB vectorial (optimizada) para cuenta {account_id} con consulta: '{query[:50]}...'")
    logger.info(f"    content_types: {content_types}, topics: {topics}, doc_ids: {document_ids}, workspace: {workspace_id}")

    try:
        # 1. Construir la consulta SQL base
        sql_query = """
            SELECT
                document,
                cmetadata,
                topic,
                category,
                workspace_id,
                team_id,
                visibility_teams,
                cmetadata->>'document_id' AS document_id, -- Nuevo: seleccionar document_id para desduplicación
                (embedding <-> CAST(:query_embedding AS vector)) AS similarity_score
            FROM langchain_pg_embedding
            WHERE account_id = :account_id
        """
        query_params = {"account_id": account_id, "k": k}

        # 2. Construir cláusulas de filtro dinámicas
        filter_clauses = []

        if content_types: # CAMBIO: Usar el nombre plural
            filter_clauses.append("content_type = ANY(:content_types)") # CAMBIO: Usar ANY para lista
            query_params["content_types"] = content_types # CAMBIO: El parámetro es plural

        if category:
            filter_clauses.append("category = :category")
            query_params["category"] = category

        if workspace_id:
            filter_clauses.append("workspace_id = :workspace_id")
            query_params["workspace_id"] = workspace_id
        else:
            filter_clauses.append("workspace_id IS NULL")

        if team_id:
            filter_clauses.append("team_id = :team_id")
            query_params["team_id"] = team_id

        # --- Lógica de filtrado para RAG Context ---
        context_filters = []
        if document_ids:
            context_filters.append("cmetadata->>'document_id' = ANY(:document_ids)")
            query_params["document_ids"] = document_ids
            logger.info(f"📄 Filtro por document_ids: {document_ids}")

        if topics:
            context_filters.append("topic = ANY(:topics)")
            params_topics = []
            for tpc in topics:
                params_topics.append(tpc.description if isinstance(tpc, FieldInfo) else tpc)
            query_params["topics"] = params_topics
            logger.info(f"🏷️ Filtro por topics: {topics}")
        
        if context_filters:
            filter_clauses.append(f"( {' OR '.join(context_filters)} )")
        # --- Fin de la lógica de RAG Context ---

        if visibility_teams:
            filter_clauses.append("(visibility_teams ?| :visibility_teams OR team_id = ANY(:visibility_teams))")
            query_params["visibility_teams"] = visibility_teams

        if filter_clauses:
            sql_query += " AND " + " AND ".join(filter_clauses)

        # 3. Ordenar y limitar
        sql_query += " ORDER BY similarity_score LIMIT :k"

        logger.info(f"🔧 Query SQL optimizada: {sql_query}")

        # 4. Obtener embedding y ejecutar
        embeddings = get_embedding_model()
        if not embeddings:
            logger.error("❌ No se pudo obtener el modelo de embeddings")
            return []

        query_embedding = await embeddings.aembed_query(query)
        query_params["query_embedding"] = query_embedding

        async with DBSession(SessionLocal) as session:
            results = await session.execute(text(sql_query), query_params)
            rows = results.fetchall()

        processed_results = []
        for row in rows:
            # Asumiendo el orden de las columnas en el SELECT: document, cmetadata, topic, category, workspace_id, team_id, visibility_teams, document_id, similarity_score
            processed_results.append({
                "document": row[0],
                "cmetadata": json.loads(row[1]) if isinstance(row[1], str) else row[1], # Parse cmetadata if it's a JSON string
                "topic": row[2],
                "category": row[3],
                "workspace_id": str(row[4]) if row[4] else None, # Convert UUID to string
                "team_id": str(row[5]) if row[5] else None, # Convert UUID to string
                "visibility_teams": row[6],
                "document_id": str(row[7]) if row[7] else None, # Convert UUID to string
                "similarity_score": row[8]
            })
        return processed_results

    except Exception as e:
        logger.error(f"❌ Error en búsqueda vectorial optimizada: {e}", exc_info=True)
        return []


class MemoryContext:
    """
    Context Manager para aislamiento automático de memoria por workspace y teams.

    Proporciona una interfaz simplificada para búsquedas con aislamiento automático
    basado en el contexto del usuario (workspace, teams, permisos).
    """

    def __init__(
        self,
        account_id: str,
        workspace_id: str | None = None,
        team_id: str | None = None,
        user_teams: List[str] | None = None
    ):
        self.account_id = account_id
        self.workspace_id = workspace_id
        self.team_id = team_id
        self.user_teams = user_teams or []

        logger.info(f"🔒 MemoryContext creado para account_id: {account_id}")
        logger.info(f"🏢 Workspace: {workspace_id or 'General'}")
        logger.info(f"👥 Team: {team_id or 'Personal'}")
        logger.info(f"👁️ User teams: {self.user_teams}")

    async def search_memories(
        self,
        query: str,
        topic: str | None = None,
        category: str | None = None,
        k: int = 5,
        include_shared: bool = True
    ) -> List[Dict]:
        """
        Busca en memorias del usuario con aislamiento automático.

        Args:
            query: Consulta de búsqueda.
            topic: Topic organizacional específico.
            category: Categoría automática específica.
            k: Número máximo de resultados.
            include_shared: Si incluir contenido compartido con teams.

        Returns:
            Lista de resultados de búsqueda.
        """
        logger.info(f"🔍 Búsqueda de memorias en contexto: workspace={self.workspace_id}")

        visibility_teams = self.user_teams if include_shared else None

        return await search_vector_db_optimized(
            account_id=self.account_id,
            query=query,
            content_types=["user_memories"], # CAMBIO: Pasar como lista
            topics=[topic] if topic else None,
            category=category,
            workspace_id=self.workspace_id,
            team_id=self.team_id,
            visibility_teams=visibility_teams,
            k=k
        )

    async def search_documents(
        self,
        query: str,
        topic: str | None = None,
        category: str | None = None,
        k: int = 5,
        include_shared: bool = True
    ) -> List[Dict]:
        """
        Busca en documentos del usuario con aislamiento automático.
        """
        logger.info(f"📄 Búsqueda de documentos en contexto: workspace={self.workspace_id}")

        visibility_teams = self.user_teams if include_shared else None

        return await search_vector_db_optimized(
            account_id=self.account_id,
            query=query,
            content_types=["user_documents"], # CAMBIO: Pasar como lista
            topics=[topic] if topic else None,
            category=category,
            workspace_id=self.workspace_id,
            team_id=self.team_id,
            visibility_teams=visibility_teams,
            k=k
        )

    async def search_all(
        self,
        query: str,
        topic: str | None = None,
        category: str | None = None,
        k: int = 10,
        include_shared: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Busca en todas las fuentes (memorias y documentos) con aislamiento automático.

        Returns:
            Diccionario con 'memories' y 'documents' como claves.
        """
        logger.info(f"🔍📄 Búsqueda completa en contexto: workspace={self.workspace_id}")

        # Buscar en paralelo para mejor rendimiento
        memories_task = self.search_memories(query, topic, category, k//2, include_shared)
        documents_task = self.search_documents(query, topic, category, k//2, include_shared)

        memories, documents = await asyncio.gather(memories_task, documents_task)

        return {
            "memories": memories,
            "documents": documents
        }

    async def get_available_topics(self) -> List[Dict[str, str]]:
        """
        Obtiene los topics disponibles para el usuario en el contexto actual.

        Returns:
            Lista de diccionarios con 'name' y 'description' de cada topic.
        """
        logger.info(f"🏷️ Obteniendo topics disponibles para workspace: {self.workspace_id}")

        try:
            async with DBSession(SessionLocal) as session:
                # Obtener topics del usuario en el workspace actual
                query = """
                    SELECT name, description, is_global
                    FROM user_document_topics
                    WHERE account_id = :account_id
                    AND (workspace_id = :workspace_id OR (workspace_id IS NULL AND is_global = TRUE))
                    ORDER BY is_global DESC, name ASC
                """

                result = await session.execute(text(query), {
                    "account_id": self.account_id,
                    "workspace_id": self.workspace_id
                })

                topics = []
                for row in result.fetchall():
                    topics.append({
                        "name": row[0],
                        "description": row[1] or "",
                        "is_global": row[2]
                    })

                logger.info(f"📋 Topics encontrados: {len(topics)}")
                return topics

        except Exception as e:
            logger.error(f"❌ Error obteniendo topics: {e}", exc_info=True)
            return []
CHUNK_OVERLAP = settings.chunk_overlap
GLOBAL_COLLECTION_NAME = "global_knowledge_base"
USER_MEMORIES_PREFIX = "user_memories_"
USER_DOCUMENTS_PREFIX = "user_documents_"

PGVECTOR_SYNC_ENGINE = create_engine(settings.database_url or "postgresql://postgres:postgres@localhost:5432/postgres")


async def create_memory_context(
    account_id: str,
    workspace_id: str | None = None,
    team_id: str | None = None
) -> MemoryContext:
    """
    Crea un MemoryContext con información completa del usuario.

    Obtiene automáticamente los teams del usuario y otra información necesaria
    para el aislamiento correcto.

    Args:
        account_id: ID de la cuenta del usuario.
        workspace_id: ID del workspace actual (None = General).
        team_id: ID del team actual (None = Personal).

    Returns:
        MemoryContext configurado para el usuario.
    """
    logger.info(f"🔧 Creando MemoryContext para account_id: {account_id}")

    try:
        # TODO: Aquí se podría obtener los teams del usuario desde la base de datos
        # Por ahora, usamos una lista vacía
        user_teams = []

        # En el futuro, esto sería algo como:
        # async with DBSession(SessionLocal) as session:
        #     teams_query = """
        #         SELECT team_id FROM user_teams
        #         WHERE account_id = :account_id
        #     """
        #     result = await session.execute(text(teams_query), {"account_id": account_id})
        #     user_teams = [row[0] for row in result.fetchall()]

        context = MemoryContext(
            account_id=account_id,
            workspace_id=workspace_id,
            team_id=team_id,
            user_teams=user_teams
        )

        logger.info(f"✅ MemoryContext creado exitosamente")
        return context

    except Exception as e:
        logger.error(f"❌ Error creando MemoryContext: {e}", exc_info=True)
        # Retornar un contexto básico en caso de error
        return MemoryContext(account_id=account_id, workspace_id=workspace_id, team_id=team_id)


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

        params = {
            "account_id": account_id,
            "content_type": content_type,
            "topic": topic,
            "category": category,
            "workspace_id": workspace_id,
            "team_id": team_id,
            "visibility_teams": visibility_teams,
            "telegram_id": telegram_id,
            "thread_id": thread_id,
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
) -> int: # Changed return type to int
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
            return 0 # Return 0 on error

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
            documents=[Document(page_content=content, metadata=metadata)]
        )

        chunks_added = 0 # Initialize chunks_added
        # NUEVO: Actualizar las nuevas columnas optimizadas
        async with DBSession(SessionLocal) as db:
            collection_obj = await db.scalar(
                select(LangchainPgCollection).where(LangchainPgCollection.name == collection_name)
            )
            if collection_obj:
                chunks_added = await _update_embedding_columns_after_insert( # Capture return value
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
        return chunks_added # Return chunks_added
    except Exception as e:
        logger.error(
            f"❌ Error al añadir memoria a la DB vectorial para la cuenta {account_id}: {e}",
            exc_info=True,
        )
        return 0 # Return 0 on error


async def get_relevant_memories(
    account_id: str,
    query: str,
    k: int = 10,
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    filter_topics: Optional[List[str]] = None,
    filter_document_ids: Optional[List[str]] = None,
    content_types: Optional[List[str]] = None # CAMBIO: Nuevo parámetro para control granular
) -> ToolOutputWithSources:
    """
    Recupera memorias y/o documentos relevantes, los formatea para citación
    y devuelve un objeto ToolOutputWithSources.
    """
    logger.info(
        f"🔍 Buscando memorias/documentos relevantes para la cuenta {account_id} con la consulta: '{query[:50]}...'"
    )
    """
    Recupera memorias y/o documentos relevantes, los formatea para citación
    y devuelve un objeto ToolOutputWithSources.
    """
    logger.info(
        f"🔍 Buscando memorias/documentos relevantes para la cuenta {account_id} con la consulta: '{query[:50]}...'"
    )
    try:
        # CAMBIO: La lógica de content_type aquí se reemplaza por el nuevo parámetro content_types
        content_types_to_search = content_types
        if not content_types_to_search:
            # Si no se proporcionó, busca en todos los tipos relevantes por defecto
            content_types_to_search = ["user_memories", "user_documents", "team_memories", "team_documents"]
        
        results = await search_vector_db_optimized(
            account_id=account_id,
            query=query,
            content_types=content_types_to_search,
            workspace_id=workspace_id,
            topics=filter_topics,
            document_ids=filter_document_ids,
            k=k
        )

        # Formatear los resultados y crear el objeto ToolOutputWithSources
        context_for_llm, sources = format_context_with_sources(results)
        
        return ToolOutputWithSources(context_for_llm=context_for_llm, sources=sources)

    except Exception as e:
        logger.error(f"❌ Error al obtener memorias relevantes: {e}", exc_info=True)
        # Asegurarse de retornar un ToolOutputWithSources incluso en caso de error
        return ToolOutputWithSources(context_for_llm="No se pudieron recuperar memorias relevantes debido a un error interno.", sources=[])