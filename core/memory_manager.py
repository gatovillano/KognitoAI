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
import uuid
import json
from sqlalchemy import select, text, create_engine, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Union, Dict, Any
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

logger = logging.getLogger(__name__)

CHUNK_SIZE = settings.chunk_size


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
            content_type="user_memories",
            topic=topic,
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
            content_type="user_documents",
            topic=topic,
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

metadata = MetaData()
langchain_pg_collection = Table('langchain_pg_collection', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)
langchain_pg_embedding = Table('langchain_pg_embedding', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)


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
    visibility_teams: List[str] | None = None
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
                visibility_teams = :visibility_teams
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
    account_id: str, content: str, type: str = "general_memory", team_id: Optional[str] = None, workspace_id: Optional[str] = None, topic: Optional[str] = None, category: Optional[str] = None
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
        await vectorstore.aadd_documents(
            documents=[Document(page_content=content, metadata=metadata)]
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
                    team_id=team_id
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


async def get_relevant_memories(
    account_id: str,
    query: str,
    k: int = 10,
    metadata_filters: Optional[Dict[str, Any]] = None,
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    topic: Optional[str] = None
) -> str:
    """
    Recupera memorias relevantes de la base de datos vectorial.

    OPTIMIZADO: Usa exclusivamente la función optimizada search_vector_db_optimized
    para búsquedas 10-50x más rápidas sin JOINs.
    """
    logger.info(
        f"🔍 Buscando memorias relevantes (OPTIMIZADO) para la cuenta {account_id} con la consulta: '{query[:50]}...'"
    )
    try:
        logger.info("🚀 Usando búsqueda optimizada para memorias")

        # Usar la función optimizada para búsquedas de memorias
        optimized_results = await search_vector_db_optimized(
            account_id=account_id,
            query=query,
            content_type="user_memories",
            topic=topic,
            workspace_id=workspace_id,
            team_id=team_id,
            k=k
        )

        if not optimized_results:
            logger.info("No se encontraron memorias relevantes.")
            return "No se encontraron memorias relevantes."

        logger.info(f"✅ Búsqueda optimizada exitosa: {len(optimized_results)} memorias encontradas")

        # Convertir resultados optimizados al formato esperado
        memories_list = []
        for result in optimized_results:
            scope = result.get("metadata", {}).get("scope", "N/A")
            topic_info = result.get("topic", "N/A")
            content = result.get("content", "")
            memories_list.append(f"- [Fuente: {scope}] (Tema: {topic_info}): {content}")

        return "\n".join(memories_list)

    except Exception as e:
        logger.error(f"❌ Error al recuperar memorias relevantes: {e}", exc_info=True)
        return "Error al obtener memorias relevantes."



async def search_vector_db_optimized(
    account_id: str,
    query: str,
    content_type: str | None = None,
    topic: str | None = None,
    category: str | None = None,
    workspace_id: str | None = None,
    team_id: str | None = None,
    visibility_teams: List[str] | None = None,
    k: int | None = 5,
) -> List[Dict]:
    """
    Búsqueda vectorial optimizada usando las nuevas columnas directamente (sin JOINs).

    Args:
        account_id: El ID de la cuenta del usuario.
        query: La consulta de búsqueda.
        content_type: Tipo de contenido (user_memories, user_documents, team_memories, team_documents).
        topic: Topic organizacional del usuario.
        category: Categoría automática del LLM.
        workspace_id: ID del workspace (NULL = General).
        team_id: ID del team propietario.
        visibility_teams: Lista de teams con acceso.
        k: Número máximo de resultados.

    Returns:
        Lista de diccionarios con los resultados de la búsqueda.
    """
    logger.info(f"🚀 Búsqueda vectorial optimizada para account_id: {account_id}")
    logger.info(f"📝 Query: '{query}'")
    logger.info(f"📂 Content type: {content_type}")
    logger.info(f"🏷️ Topic: {topic}")
    logger.info(f"🔖 Category: {category}")
    logger.info(f"🏢 Workspace ID: {workspace_id}")
    logger.info(f"👥 Team ID: {team_id}")
    logger.info(f"👁️ Visibility teams: {visibility_teams}")
    logger.info(f"📊 K (límite): {k}")

    try:
        # 1. Construir la consulta SQL optimizada (sin JOINs)
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
            WHERE account_id = :account_id
        """

        query_params = {
            "account_id": account_id,
            "k": k
        }

        # 2. Agregar filtros opcionales
        if content_type:
            sql_query += " AND content_type = :content_type"
            query_params["content_type"] = content_type
            logger.info(f"📂 Filtro content_type: {content_type}")

        if topic:
            sql_query += " AND topic = :topic"
            query_params["topic"] = topic
            logger.info(f"🏷️ Filtro topic: {topic}")

        if category:
            sql_query += " AND category = :category"
            query_params["category"] = category
            logger.info(f"🔖 Filtro category: {category}")

        if workspace_id:
            sql_query += " AND workspace_id = :workspace_id"
            query_params["workspace_id"] = workspace_id
            logger.info(f"🏢 Filtro workspace_id: {workspace_id}")
        elif workspace_id is None:
            # Buscar solo en General (workspace_id IS NULL)
            sql_query += " AND workspace_id IS NULL"
            logger.info("🏢 Filtro: Solo workspace General")

        if team_id:
            sql_query += " AND team_id = :team_id"
            query_params["team_id"] = team_id
            logger.info(f"👥 Filtro team_id: {team_id}")

        # 3. Filtro de visibilidad para teams
        if visibility_teams:
            # El usuario puede ver contenido si:
            # - Es el propietario (account_id match)
            # - Su team está en visibility_teams
            # - El contenido es de su team
            teams_condition = " OR ".join([f"visibility_teams ? '{team}'" for team in visibility_teams])
            teams_condition += f" OR team_id = ANY(ARRAY{visibility_teams})"
            sql_query += f" AND ({teams_condition})"
            logger.info(f"👁️ Filtro visibilidad teams: {visibility_teams}")

        # 4. Ordenar por similarity score y limitar
        sql_query += " ORDER BY similarity_score LIMIT :k"

        logger.info(f"🔧 Query SQL optimizada: {sql_query}")

        # 5. Obtener embedding de la consulta
        embeddings = get_embedding_model()
        if not embeddings:
            logger.error("❌ No se pudo obtener el modelo de embeddings")
            return []

        logger.info("🧠 Generando embedding para la consulta...")
        query_embedding = await embeddings.aembed_query(query)
        query_params["query_embedding"] = query_embedding
        logger.info(f"✅ Embedding generado. Dimensiones: {len(query_embedding) if query_embedding else 'None'}")

        # 6. Ejecutar consulta
        logger.info("🚀 Ejecutando consulta SQL optimizada...")
        async with DBSession(SessionLocal) as session:
            results = await session.execute(text(sql_query), query_params)
            rows = results.fetchall()

        logger.info(f"📊 Resultados obtenidos: {len(rows)}")

        # 7. Procesar resultados
        processed_results = []
        for i, row in enumerate(rows):
            document, cmetadata, topic_col, category_col, workspace_id_col, team_id_col, visibility_teams_col, similarity_score = row

            # Convertir UUIDs a string para evitar errores de serialización JSON
            workspace_id_str = str(workspace_id_col) if workspace_id_col else None
            team_id_str = str(team_id_col) if team_id_col else None

            result_item = {
                "content": document,
                "metadata": cmetadata,
                "topic": topic_col,
                "category": category_col,
                "workspace_id": workspace_id_str,
                "team_id": team_id_str,
                "visibility_teams": visibility_teams_col,
                "similarity_score": similarity_score,
            }
            processed_results.append(result_item)
            logger.info(f"📄 Resultado {i+1}: score={similarity_score:.4f}, topic={topic_col}, category={category_col}")

        logger.info(f"✅ Búsqueda optimizada completada. Resultados: {len(processed_results)}")
        return processed_results

    except Exception as e:
        logger.error(f"❌ Error en search_vector_db_optimized: {e}", exc_info=True)
        return []


async def search_vector_db(
    account_id: str,
    query: str,
    collection_name: str | None = None,
    topic: str | None = None,
    workspace_id: str | None = None,
    k: int | None = 5,
) -> List[Dict]:
    """
    Realiza una búsqueda en la base de datos vectorial.

    OPTIMIZADO: Usa exclusivamente la función optimizada search_vector_db_optimized
    para búsquedas 10-50x más rápidas sin JOINs.

    Args:
        account_id: El ID de la cuenta del usuario.
        query: La consulta de búsqueda.
        collection_name: El nombre de la colección en la que buscar (user_memories o user_documents).
        topic: El tema por el que filtrar los resultados.
        workspace_id: El ID del workspace por el que filtrar los resultados.
        k: El número máximo de resultados a devolver.

    Returns:
        Una lista de diccionarios con los resultados de la búsqueda.
    """
    logger.info(f"🔍 Búsqueda vectorial (OPTIMIZADA) para account_id: {account_id}")
    logger.info(f"📝 Query: '{query}'")
    logger.info(f"📚 Collection: {collection_name}")
    logger.info(f"🏷️ Topic: {topic}")
    logger.info(f"🏢 Workspace ID: {workspace_id}")

    try:
        # Mapear collection_name a content_type
        content_type = None
        if collection_name:
            if "user_memories" in collection_name:
                content_type = "user_memories"
            elif "user_documents" in collection_name:
                content_type = "user_documents"
            elif "team_memories" in collection_name:
                content_type = "team_memories"
            elif "team_documents" in collection_name:
                content_type = "team_documents"
            elif collection_name in ["user_memories", "user_documents", "team_memories", "team_documents"]:
                content_type = collection_name

        logger.info(f"🚀 Usando búsqueda optimizada con content_type: {content_type}")

        # Usar la función optimizada
        optimized_results = await search_vector_db_optimized(
            account_id=account_id,
            query=query,
            content_type=content_type,
            topic=topic,
            workspace_id=workspace_id,
            k=k
        )

        logger.info(f"✅ Búsqueda optimizada completada: {len(optimized_results)} resultados")
        return optimized_results

    except Exception as e:
        logger.error(f"❌ Error en search_vector_db optimizada: {e}", exc_info=True)
        return []




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
    if not extracted_text:
        return 0
        
    # Limpiar el texto de caracteres no válidos como NUL bytes
    cleaned_text = extracted_text.replace('\x00', '')
    if len(cleaned_text) != len(extracted_text):
        logger.info(f"Se eliminaron caracteres no válidos del documento '{file_name}'.")
    extracted_text = cleaned_text

    try:
        embeddings = get_embedding_model()
        if not embeddings:
            logger.error("Los Embeddings no están inicializados. No se puede procesar el documento.")
            return 0

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        texts = text_splitter.split_text(extracted_text)
        
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
                    
            lc_documents.append(Document(page_content=text_content, metadata=chunk_metadata))
            ids.append(str(uuid.uuid4()))
        
        # Crear/obtener vectorstore y agregar documentos
        # Usar el motor asíncrono preconfigurado desde core/database.py
        from core.database import engine
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name=langchain_collection_name,
            connection=engine,
            use_jsonb=True
        )
        await vectorstore.aadd_documents(lc_documents)

        # Obtener el UUID de la colección de LangChain recién creada/existente
        async with DBSession(SessionLocal) as db:
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
        
        # Trigger proactivo deshabilitado para documentos (se analizará en un job nocturno)
        if account_id or team_id:
            logger.info("[Memory Manager] Análisis proactivo no programado para documentos. Se analizará en el job nocturno.")
            # TODO: Implementar job nocturno para análisis de documentos una vez al día.
            
        return len(lc_documents)

    except Exception as e:
        logger.error(f"❌ Error durante el procesamiento RAG para '{file_name}': {e}", exc_info=True)
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
    topic: Optional[str] = None,
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> int:
    """
    Elimina los chunks de documentos usando las columnas optimizadas (sin JOINs).

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin necesidad de JOINs.
    """
    if not file_name and not topic:
        logger.warning("Se llamó a delete_document_chunks sin file_name ni topic.")
        return 0

    logger.info(f"🗑️ Eliminando chunks optimizado para account_id: {account_id}")
    logger.info(f"📄 File name: {file_name}")
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

            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic

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

            logger.info(f"🗑️ Total borrados {deleted_count} chunks usando consulta optimizada.")
            return deleted_count

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

            if workspace_id:
                clauses.append("workspace_id = :workspace_id")
                params["workspace_id"] = workspace_id

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
    topic: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todos los documentos únicos.

    OPTIMIZADO: Usa filtros directos en langchain_pg_embedding sin JOINs.

    - Si se proporciona workspace_id, lista los documentos de ese workspace Y del contexto general.
    - Si no, lista los documentos de la colección general del usuario o equipo.

    IMPORTANTE: Cuando se especifica workspace_id, también se incluyen los documentos del contexto general
    (workspace_id = NULL) para permitir el acceso a documentos importados del contexto general.
    """
    logger.info(f"📋 Listando documentos (OPTIMIZADO) para la cuenta {account_id} (Workspace: {workspace_id if workspace_id else 'N/A'})")

    async with DBSession(SessionLocal) as db:
        try:
            # Construir consulta optimizada usando las nuevas columnas directamente
            clauses = [
                "account_id = :account_id",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"account_id": account_id}

            if team_id:
                clauses.append("team_id = :team_id")
                params["team_id"] = team_id

            if workspace_id:
                # Para workspaces, incluir tanto los documentos específicos del workspace
                # como los del contexto general (workspace_id IS NULL)
                clauses.append("(workspace_id = :workspace_id OR workspace_id IS NULL)")
                params["workspace_id"] = workspace_id

            if topic:
                clauses.append("topic = :topic")
                params["topic"] = topic

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

            logger.info(f"🔧 Query SQL optimizada: {query_str}")
            logger.info(f"📋 Parámetros: {params}")

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
    logger.info(f"📋 Listando TODOS los documentos del usuario {account_id} (Workspace: {workspace_id if workspace_id else 'N/A'})")

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
                params["topic"] = topic

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

            logger.info(f"🔧 Query SQL para todos los documentos: {query_str}")
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
            
            # Añadir todas las colecciones definidas por el usuario (con 0 documentos por defecto)
            for topic in user_topics:
                collections_map[topic.name] = {
                    "topic": topic.name,
                    "document_count": 0,
                    "description": topic.description
                }
            
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
                    COUNT(DISTINCT cmetadata->>'file_name') as document_count
                FROM langchain_pg_embedding
                WHERE {final_where_clause}
                GROUP BY topic
                ORDER BY topic;
                """
            )
            
            result = await db.execute(collections_query, params)
            embedding_collections = [dict(row) for row in result.mappings()]
            
            # 3. Actualizar conteos y agregar colecciones que solo existen en embeddings
            for collection in embedding_collections:
                topic_name = collection["topic"]
                if topic_name in collections_map:
                    # Actualizar el conteo para colecciones definidas por el usuario
                    collections_map[topic_name]["document_count"] = collection["document_count"]
                else:
                    # Agregar colecciones que solo existen en embeddings (no definidas por el usuario)
                    collections_map[topic_name] = {
                        "topic": topic_name,
                        "document_count": collection["document_count"],
                        "description": None
                    }
            
            return list(collections_map.values())
            
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
            # 1. Actualizar en UserDocumentTopic
            query = select(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == old_topic_name
            )

            if workspace_id:
                query = query.where(UserDocumentTopic.workspace_id == uuid.UUID(workspace_id))
            elif team_id:
                query = query.where(UserDocumentTopic.team_id == uuid.UUID(team_id))
            else:
                query = query.where(
                    UserDocumentTopic.workspace_id.is_(None),
                    UserDocumentTopic.team_id.is_(None)
                )

            collection = await db.scalar(query)
            if not collection:
                logger.warning(f"No se encontró la colección '{old_topic_name}' para actualizar.")
                return False

            # Actualizar los campos en UserDocumentTopic
            if new_topic_name is not None:
                collection.name = new_topic_name
            if new_description is not None:
                collection.description = new_description

            # 2. Si se cambió el nombre, actualizar también en langchain_pg_embedding
            if new_topic_name is not None and new_topic_name != old_topic_name:
                # Construir filtros para langchain_pg_embedding
                clauses = [
                    "account_id = :account_id",
                    "topic = :old_topic_name",
                    "cmetadata->>'type' = 'document_chunk'"
                ]
                params: Dict[str, Any] = {
                    "account_id": account_id,
                    "old_topic_name": old_topic_name
                }

                if workspace_id:
                    clauses.append("workspace_id = :workspace_id")
                    params["workspace_id"] = workspace_id
                elif team_id:
                    clauses.append("team_id = :team_id")
                    params["team_id"] = team_id

                # Obtener cmetadata actual para preservar otros metadatos
                select_sql = text(f"""
                    SELECT cmetadata
                    FROM langchain_pg_embedding
                    WHERE {" AND ".join(clauses)}
                    LIMIT 1
                """)

                cmetadata_result = await db.execute(select_sql, params)
                current_cmetadata = cmetadata_result.scalar_one_or_none()

                if current_cmetadata:
                    # Actualizar metadatos preservando otros campos
                    values_to_update = current_cmetadata.copy()
                    values_to_update['topic'] = new_topic_name

                    # Actualizar tanto cmetadata como la columna topic
                    update_sql = text(f"""
                        UPDATE langchain_pg_embedding
                        SET
                            cmetadata = :new_cmetadata,
                            topic = :new_topic_name
                        WHERE {" AND ".join(clauses)}
                    """)

                    update_params = params.copy()
                    update_params.update({
                        "new_cmetadata": json.dumps(values_to_update),
                        "new_topic_name": new_topic_name
                    })

                    result = await db.execute(update_sql, update_params)
                    logger.info(f"✅ Se actualizaron {result.rowcount} documentos con el nuevo nombre de colección.")

            await db.commit()
            logger.info(f"✅ Colección '{old_topic_name}' actualizada exitosamente.")
            return True

        except Exception as e:
            logger.error(f"❌ Error actualizando colección '{old_topic_name}': {e}", exc_info=True)
            await db.rollback()
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
        account_id: ID de la cuenta del usuario.
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
            
            # Eliminar el registro de la colección de UserDocumentTopic
            delete_query = delete(UserDocumentTopic).where(
                UserDocumentTopic.account_id == uuid.UUID(account_id),
                UserDocumentTopic.name == topic_name
            )
            
            if workspace_id:
                delete_query = delete_query.where(
                    UserDocumentTopic.workspace_id == uuid.UUID(workspace_id)
                )
            elif team_id:
                delete_query = delete_query.where(
                    UserDocumentTopic.team_id == uuid.UUID(team_id)
                )
            else:
                delete_query = delete_query.where(
                    UserDocumentTopic.workspace_id.is_(None),
                    UserDocumentTopic.team_id.is_(None)
                )
            
            result = await db.execute(delete_query)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Colección '{topic_name}' eliminada exitosamente para cuenta {account_id}")
                return True
            else:
                logger.warning(f"La colección '{topic_name}' no se encontró para la cuenta {account_id}")
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
                params["topic"] = topic

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
