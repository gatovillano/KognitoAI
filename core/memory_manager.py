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
from sqlalchemy import select, text, create_engine, delete
from typing import Optional, List, Union, Dict, Any
import datetime
from tools.proactive_knowledge_linker_tool import proactive_knowledge_linker_trigger

import uuid
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import Table, MetaData, update, and_

from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.database import (
    Perfil,
    SessionLocal,
    Account,
    Memory,
    engine,
    LangchainPgCollection,
    WorkspaceCollectionAssociation
)
from utils.db_session import DBSession
from utils.embeddings import initialize_embeddings
from core.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap
GLOBAL_COLLECTION_NAME = "global_knowledge_base"
USER_MEMORIES_PREFIX = "user_memories_"

PGVECTOR_SYNC_ENGINE = create_engine(settings.database_url)

metadata = MetaData()
langchain_pg_collection = Table('langchain_pg_collection', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)
langchain_pg_embedding = Table('langchain_pg_embedding', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)


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

            db.add(perfil)
            if nombre is not None:
                perfil.nombre = nombre
            if gustos is not None:
                perfil.gustos = gustos
            if intereses is not None:
                perfil.intereses = intereses
            if otros_datos is not None:
                perfil.otros_datos = otros_datos

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
    account_id: str, content: str, type: str = "general_memory", team_id: Optional[str] = None, workspace_id: Optional[str] = None
) -> None:
    """
    Genera embeddings para el contenido y lo guarda en la DB vectorial del usuario o equipo.
    """
    logger.info(
        f"Añadiendo memoria a la DB vectorial para la cuenta {account_id}: '{content[:50]}...'"
    )
    try:
        embeddings: Embeddings = await initialize_embeddings()
        if not embeddings:
            logger.error(
                "Los Embeddings no están inicializados. No se puede añadir memoria."
            )
            return

        collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"

        vectorstore = await asyncio.to_thread(
            PGVector.from_existing_index,
            embedding=embeddings,
            collection_name=collection_name,
            connection=PGVECTOR_SYNC_ENGINE,
        )

        metadata = {"account_id": str(account_id), "type": type}
        if team_id:
            metadata["team_id"] = str(team_id)
        if workspace_id:
            metadata["workspace_id"] = str(workspace_id)
        await vectorstore.aadd_documents(
            documents=[Document(page_content=content, metadata=metadata)]
        )
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
    workspace_id: Optional[str] = None
) -> str:
    """
    Recupera memorias relevantes.
    """
    logger.info(
        f"Buscando memorias relevantes para la cuenta {account_id} con la consulta: '{query[:50]}...'"
    )
    try:
        embeddings: Embeddings = await initialize_embeddings()
        if not embeddings:
            return "Error: El modelo de memoria no está disponible."

        query_embedding = await embeddings.aembed_query(query)
        
        all_docs = []
        
        # Obtener las colecciones relevantes (UUIDs)
        relevant_collection_uuids = []
        async with DBSession(SessionLocal) as db:
            if workspace_id:
                # Si se especifica un workspace, obtener todas las colecciones asociadas a ese workspace
                stmt = select(WorkspaceCollectionAssociation.langchain_collection_id).where(
                    WorkspaceCollectionAssociation.workspace_id == uuid.UUID(workspace_id)
                )
                result = await db.execute(stmt)
                relevant_collection_uuids.extend([str(u) for u in result.scalars().all()])
                logger.info(f"Buscando en colecciones asociadas al workspace {workspace_id}: {relevant_collection_uuids}")
            
            # Siempre incluir la colección personal del usuario y la global
            user_collection_name = f"user_memories_{account_id}"
            global_collection_name = GLOBAL_COLLECTION_NAME
            team_collection_name = f"team_memories_{team_id}" if team_id else None

            for c_name in [user_collection_name, global_collection_name, team_collection_name]:
                if c_name:
                    stmt = select(LangchainPgCollection.uuid).where(LangchainPgCollection.name == c_name)
                    result = await db.execute(stmt)
                    c_uuid = result.scalar_one_or_none()
                    if c_uuid and str(c_uuid) not in relevant_collection_uuids: # Evitar duplicados
                        relevant_collection_uuids.append(str(c_uuid))
            
            if not relevant_collection_uuids:
                logger.info("No se encontraron colecciones relevantes para la búsqueda.")
                return "No se encontraron memorias relevantes."

        # Realizar la búsqueda en todas las colecciones relevantes
        # LangChain PGVector no soporta buscar en múltiples colecciones a la vez directamente.
        # Tendremos que iterar o construir una consulta SQL más compleja.
        # Por simplicidad, iteraremos sobre las colecciones relevantes.
        
        # Filtros de metadatos adicionales
        final_filters = metadata_filters if metadata_filters else {}
        if workspace_id:
            final_filters["workspace_id"] = str(workspace_id) # Asegurar que el metadato workspace_id coincida

        search_tasks = []
        for col_uuid_str in relevant_collection_uuids:
            # Obtener el nombre de la colección a partir del UUID para inicializar PGVector
            async with DBSession(SessionLocal) as db_inner:
                col_name_obj = await db_inner.scalar(
                    select(LangchainPgCollection.name).where(LangchainPgCollection.uuid == uuid.UUID(col_uuid_str))
                )
                if not col_name_obj:
                    logger.warning(f"No se encontró el nombre para la colección UUID: {col_uuid_str}. Saltando.")
                    continue
                collection_name_for_vectorstore = col_name_obj

            vectorstore = await asyncio.to_thread(
                PGVector.from_existing_index,
                embedding=embeddings,
                collection_name=collection_name_for_vectorstore,
                connection=PGVECTOR_SYNC_ENGINE,
            )
            search_tasks.append(vectorstore.asimilarity_search(query, k=k, filter=final_filters))

        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, list):
                all_docs.extend(res)
            else:
                logger.warning(f"⚠️ Error al buscar en una colección: {res}")

        if not all_docs:
            return "No se encontraron memorias relevantes."

        # Eliminar duplicados si un documento aparece en múltiples colecciones
        unique_docs = {}
        for doc in all_docs:
            # Usar una combinación de document_id y chunk_index para identificar chunks únicos
            doc_key = (doc.metadata.get("document_id"), doc.metadata.get("chunk_index"))
            if doc_key not in unique_docs:
                unique_docs[doc_key] = doc
        all_docs = list(unique_docs.values())

        memories_list = [
            f"- [Fuente: {d.metadata.get('scope', 'N/A')}] (Tema: {d.metadata.get('topic', 'N/A')}): {d.page_content}"
            for d in all_docs
        ]
        return "\n".join(memories_list)
    except Exception as e:
        logger.error(f"❌ Error al recuperar memorias relevantes: {e}", exc_info=True)
        return "Error al obtener memorias relevantes."


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

    try:
        embeddings = await initialize_embeddings()
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
            # y la asociación se hará en WorkspaceCollectionAssociation.
            # El topic es el nombre de la colección dentro del workspace.
            langchain_collection_name = topic # El topic es el nombre de la colección
            scope = "workspace"
        elif is_global:
            langchain_collection_name = GLOBAL_COLLECTION_NAME
            scope = "global"
        elif account_id:
            langchain_collection_name = f"user_memories_{account_id}"
            scope = "personal"
        elif team_id:
            langchain_collection_name = f"team_memories_{team_id}"
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
        vectorstore = await asyncio.to_thread(
            PGVector.from_documents,
            documents=lc_documents, 
            embedding=embeddings,
            collection_name=langchain_collection_name, # Usar el nombre de colección determinado
            connection=PGVECTOR_SYNC_ENGINE,
        )
        
        # Obtener el UUID de la colección de LangChain recién creada/existente
        async with DBSession(SessionLocal) as db:
            collection_obj = await db.scalar(
                select(LangchainPgCollection).where(LangchainPgCollection.name == langchain_collection_name)
            )
            if not collection_obj:
                logger.error(f"No se pudo encontrar la colección LangChain '{langchain_collection_name}' después de from_documents.")
                return 0
            langchain_collection_uuid = collection_obj.uuid

            # Si es un documento de workspace, crear la asociación
            if workspace_id:
                existing_association = await db.scalar(
                    select(WorkspaceCollectionAssociation).where(
                        WorkspaceCollectionAssociation.workspace_id == uuid.UUID(workspace_id),
                        WorkspaceCollectionAssociation.langchain_collection_id == langchain_collection_uuid
                    )
                )
                if not existing_association:
                    new_association = WorkspaceCollectionAssociation(
                        workspace_id=uuid.UUID(workspace_id),
                        langchain_collection_id=langchain_collection_uuid
                    )
                    db.add(new_association)
                    await db.commit()
                    logger.info(f"Asociación creada entre workspace {workspace_id} y colección LangChain {langchain_collection_name}.")
                else:
                    logger.info(f"Asociación entre workspace {workspace_id} y colección LangChain {langchain_collection_name} ya existe.")

        logger.info(f"✅ Procesado y añadido {len(lc_documents)} chunks a la colección '{langchain_collection_name}'.")
        
        # Trigger proactivo (si es necesario)
        if account_id or team_id:
            doc_embedding = await embeddings.aembed_query(
                extracted_text[:10000] + "..." if len(extracted_text) > 10000 else extracted_text
            )
            asyncio.create_task(proactive_knowledge_linker_trigger({
                "account_id": account_id, 
                "team_id": team_id, 
                "content": extracted_text,
                "title": file_name, 
                "type": "document", 
                "embedding": doc_embedding,
                "workspace_id": workspace_id
            }))
            
        return len(lc_documents)

    except Exception as e:
        logger.error(f"❌ Error durante el procesamiento RAG para '{file_name}': {e}", exc_info=True)
        return 0


async def delete_document_chunks(
    account_id: str,
    file_name: Optional[str] = None,
    topic: Optional[str] = None,
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> int:
    """
    Elimina los chunks de documentos.
    """
    if not file_name and not topic:
        logger.warning("Se llamó a delete_document_chunks sin file_name ni topic.")
        return 0

    # Lógica unificada para eliminar chunks
    async with DBSession(SessionLocal) as db:
        # Obtener los UUIDs de las colecciones relevantes
        relevant_collection_uuids = []
        if workspace_id:
            stmt = select(WorkspaceCollectionAssociation.langchain_collection_id).where(
                WorkspaceCollectionAssociation.workspace_id == uuid.UUID(workspace_id)
            )
            result = await db.execute(stmt)
            relevant_collection_uuids.extend([str(u) for u in result.scalars().all()])
        
        # Siempre incluir la colección personal del usuario y la global/equipo si aplica
        user_collection_name = f"user_memories_{account_id}"
        global_collection_name = GLOBAL_COLLECTION_NAME
        team_collection_name = f"team_memories_{team_id}" if team_id else None

        for c_name in [user_collection_name, global_collection_name, team_collection_name]:
            if c_name:
                stmt = select(LangchainPgCollection.uuid).where(LangchainPgCollection.name == c_name)
                result = await db.execute(stmt)
                c_uuid = result.scalar_one_or_none()
                if c_uuid and str(c_uuid) not in relevant_collection_uuids:
                    relevant_collection_uuids.append(str(c_uuid))

        if not relevant_collection_uuids:
            logger.info("No se encontraron colecciones relevantes para eliminar.")
            return 0

        deleted_count = 0
        for col_uuid_str in relevant_collection_uuids:
            clauses = ["collection_id = :col_id", "cmetadata->>'type' = 'document_chunk'"]
            params: Dict[str, Any] = {"col_id": uuid.UUID(col_uuid_str)} # Asegurarse de que sea UUID
            
            if file_name:
                clauses.append("cmetadata->>'file_name' = :fname")
                params["fname"] = file_name
            if topic:
                clauses.append("cmetadata->>'topic' = :tpc")
                params["tpc"] = topic
            if workspace_id:
                clauses.append("cmetadata->>'workspace_id' = :wsid")
                params["wsid"] = str(workspace_id) # Filtrar por metadato workspace_id

            delete_sql = text("DELETE FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
            result = await db.execute(delete_sql, params)
            deleted_count += result.rowcount or 0
            logger.info(f"🗑️ Borrados {result.rowcount} chunks de la colección '{col_uuid_str}'.")
        
        await db.commit()
        logger.info(f"🗑️ Total borrados {deleted_count} chunks.")
        return deleted_count


async def get_full_document_content(
    account_id: str,
    file_name: str,
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None, # <-- Nuevo parámetro
) -> Optional[str]:
    """
    Reconstruye y devuelve el contenido completo de un documento desde sus chunks.
    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a reconstruir.
        team_id: El ID del equipo (UUID en formato string) para buscar en la colección del equipo, si aplica.
        workspace_id: El ID del workspace (UUID en formato string) para buscar en la colección del workspace, si aplica.
    Returns:
        El contenido completo del documento como una cadena, o None si no se encuentra.
    """
    logger.info(
        f"Recuperando contenido completo de '{file_name}' para la cuenta {account_id}"
        f" (Workspace: {workspace_id if workspace_id else 'N/A'})"
    )
    try:
        embeddings: Embeddings = await initialize_embeddings()
        if not embeddings:
            return None

        retrieved_docs = []
        
        # Obtener los UUIDs de las colecciones relevantes
        relevant_collection_uuids = []
        async with DBSession(SessionLocal) as db:
            if workspace_id:
                stmt = select(WorkspaceCollectionAssociation.langchain_collection_id).where(
                    WorkspaceCollectionAssociation.workspace_id == uuid.UUID(workspace_id)
                )
                result = await db.execute(stmt)
                relevant_collection_uuids.extend([str(u) for u in result.scalars().all()])
            
            user_collection_name = f"user_memories_{account_id}"
            global_collection_name = GLOBAL_COLLECTION_NAME
            team_collection_name = f"team_memories_{team_id}" if team_id else None

            for c_name in [user_collection_name, global_collection_name, team_collection_name]:
                if c_name:
                    stmt = select(LangchainPgCollection.uuid).where(LangchainPgCollection.name == c_name)
                    result = await db.execute(stmt)
                    c_uuid = result.scalar_one_or_none()
                    if c_uuid and str(c_uuid) not in relevant_collection_uuids:
                        relevant_collection_uuids.append(str(c_uuid))

        if not relevant_collection_uuids:
            logger.warning(f"No se encontraron colecciones relevantes para el documento '{file_name}'.")
            return None

        # Buscar en cada colección relevante
        for col_uuid_str in relevant_collection_uuids:
            async with DBSession(SessionLocal) as db_inner:
                col_name_obj = await db_inner.scalar(
                    select(LangchainPgCollection.name).where(LangchainPgCollection.uuid == uuid.UUID(col_uuid_str))
                )
                if not col_name_obj:
                    logger.warning(f"No se encontró el nombre para la colección UUID: {col_uuid_str}. Saltando.")
                    continue
                collection_name_for_vectorstore = col_name_obj

            vectorstore = await asyncio.to_thread(
                PGVector.from_existing_index,
                embedding=embeddings,
                collection_name=collection_name_for_vectorstore,
                connection=PGVECTOR_SYNC_ENGINE,
            )
            
            # Filtrar por file_name y tipo de chunk
            docs_in_collection = await vectorstore.asimilarity_search(
                query=" ", # Consulta vacía para obtener todos los documentos que coincidan con el filtro
                k=10000, # Un número grande para asegurar que se recuperen todos los chunks
                filter={"file_name": file_name, "type": "document_chunk"},
            )
            retrieved_docs.extend(docs_in_collection)

        if not retrieved_docs:
            logger.warning(f"No se encontraron chunks para el documento '{file_name}' en el contexto especificado.")
            return None

        # Eliminar duplicados y ordenar
        unique_chunks = {}
        for doc in retrieved_docs:
            doc_key = (doc.metadata.get("document_id"), doc.metadata.get("chunk_index"))
            if doc_key not in unique_chunks:
                unique_chunks[doc_key] = doc
        
        sorted_chunks = sorted(
            unique_chunks.values(), key=lambda d: d.metadata.get("chunk_index", 0)
        )
        full_content = "".join([doc.page_content for doc in sorted_chunks])

        logger.info(
            f"✅ Reconstruido documento '{file_name}'. Longitud: {len(full_content)} chars."
        )
        return full_content
    except Exception as e:
        logger.error(
            f"❌ Error recuperando contenido de '{file_name}' (workspace {workspace_id}): {e}", exc_info=True
        )
        return None


async def list_user_documents(
    account_id: str, 
    team_id: Optional[str] = None, 
    workspace_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todos los documentos únicos.
    - Si se proporciona workspace_id, lista los documentos de ese workspace.
    - Si no, lista los documentos de la colección general del usuario o equipo.
    """
    logger.info(f"Listando documentos para la cuenta {account_id} (Workspace: {workspace_id if workspace_id else 'N/A'})")
    
    async with DBSession(SessionLocal) as db:
        try:
            # Obtener los UUIDs de las colecciones relevantes
            relevant_collection_uuids = []
            if workspace_id:
                stmt = select(WorkspaceCollectionAssociation.langchain_collection_id).where(
                    WorkspaceCollectionAssociation.workspace_id == uuid.UUID(workspace_id)
                )
                result = await db.execute(stmt)
                relevant_collection_uuids.extend([str(u) for u in result.scalars().all()])
            
            user_collection_name = f"user_memories_{account_id}"
            global_collection_name = GLOBAL_COLLECTION_NAME
            team_collection_name = f"team_memories_{team_id}" if team_id else None

            for c_name in [user_collection_name, global_collection_name, team_collection_name]:
                if c_name:
                    stmt = select(LangchainPgCollection.uuid).where(LangchainPgCollection.name == c_name)
                    result = await db.execute(stmt)
                    c_uuid = result.scalar_one_or_none()
                    if c_uuid and str(c_uuid) not in relevant_collection_uuids:
                        relevant_collection_uuids.append(str(c_uuid))

            if not relevant_collection_uuids:
                logger.info("No se encontraron colecciones relevantes para listar documentos.")
                return []

            # Construir la consulta para obtener documentos únicos de langchain_pg_embedding
            # Filtrar por collection_id y metadatos
            clauses = [
                "collection_id = ANY(:col_uuids)", # Usar ANY para buscar en múltiples UUIDs
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"col_uuids": [uuid.UUID(u) for u in relevant_collection_uuids]}
            
            if team_id:
                clauses.append("cmetadata->>'team_id' = :tid")
                params["tid"] = str(team_id)
            if workspace_id:
                clauses.append("cmetadata->>'workspace_id' = :wsid")
                params["wsid"] = str(workspace_id)

            document_list_query = text(
                f"""
                SELECT DISTINCT ON (cmetadata->>'document_id')
                       cmetadata->>'file_name' AS file_name,
                       cmetadata->>'topic' AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author,
                       cmetadata->>'document_id' AS document_id,
                       cmetadata->>'workspace_id' AS workspace_id,
                       cmetadata->>'team_id' AS team_id
                FROM langchain_pg_embedding
                WHERE {" AND ".join(clauses)}
                ORDER BY cmetadata->>'document_id', id;
                """
            )
            
            document_list_result = await db.execute(document_list_query, params)
            documents = [dict(row) for row in document_list_result.mappings()]
            logger.info(f"✅ Listados {len(documents)} documentos para la cuenta {account_id}.")
            return documents
        except Exception as e:
            logger.error(f"❌ Error listando documentos para la cuenta {account_id}: {e}", exc_info=True)
            return []


async def update_document_metadata(
    account_id: str, 
    file_name: str, 
    new_title: Optional[str], 
    new_topic: Optional[str],
    team_id: Optional[str] = None,
    workspace_id: Optional[str] = None, # <-- Nuevo parámetro
) -> bool:
    """
    Actualiza el título y/o la categoría (topic) de todos los chunks de un documento.
    
    Esta función construye y ejecuta una consulta SQL de actualización directamente
    sobre la tabla de embeddings de LangChain o sobre WorkspaceDocumentChunk.
    
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
        f"Actualizando metadatos para '{file_name}' (cuenta {account_id}). "
        f"Nuevo título: {new_title}, Nuevo tema: {new_topic}. Workspace ID: {workspace_id if workspace_id else 'N/A'}."
    )
    
    async with DBSession(SessionLocal) as db:
        try:
            # Obtener los UUIDs de las colecciones relevantes
            relevant_collection_uuids = []
            if workspace_id:
                stmt = select(WorkspaceCollectionAssociation.langchain_collection_id).where(
                    WorkspaceCollectionAssociation.workspace_id == uuid.UUID(workspace_id)
                )
                result = await db.execute(stmt)
                relevant_collection_uuids.extend([str(u) for u in result.scalars().all()])
            
            user_collection_name = f"user_memories_{account_id}"
            global_collection_name = GLOBAL_COLLECTION_NAME
            team_collection_name = f"team_memories_{team_id}" if team_id else None

            for c_name in [user_collection_name, global_collection_name, team_collection_name]:
                if c_name:
                    stmt = select(LangchainPgCollection.uuid).where(LangchainPgCollection.name == c_name)
                    result = await db.execute(stmt)
                    c_uuid = result.scalar_one_or_none()
                    if c_uuid and str(c_uuid) not in relevant_collection_uuids:
                        relevant_collection_uuids.append(str(c_uuid))

            if not relevant_collection_uuids:
                logger.warning(f"No se encontraron colecciones relevantes para actualizar metadatos para '{file_name}'.")
                return False

            # Construir la consulta de actualización para langchain_pg_embedding
            # Actualizar cmetadata para todos los chunks del documento en las colecciones relevantes
            
            # Primero, obtener el cmetadata actual de un chunk para no sobrescribir otros metadatos
            # Hacemos esto para el primer chunk encontrado que coincida con el file_name
            select_stmt = select(langchain_pg_embedding.c.cmetadata).where(
                and_(
                    langchain_pg_embedding.c.collection_id.in_([uuid.UUID(u) for u in relevant_collection_uuids]),
                    langchain_pg_embedding.c.cmetadata['file_name'].astext == file_name,
                    langchain_pg_embedding.c.cmetadata['type'].astext == 'document_chunk'
                )
            ).limit(1)
            
            cmetadata_result = await db.execute(select_stmt)
            current_cmetadata = cmetadata_result.scalar_one_or_none()
            
            if not current_cmetadata:
                logger.warning(f"No se encontraron chunks para el archivo '{file_name}' en las colecciones relevantes para actualizar.")
                return False

            values_to_update = current_cmetadata.copy()
            if new_title is not None:
                values_to_update['title'] = new_title
            if new_topic is not None:
                values_to_update['topic'] = new_topic
            if workspace_id: # Asegurarse de que workspace_id se actualice si es necesario
                values_to_update['workspace_id'] = str(workspace_id)

            update_stmt = (
                update(langchain_pg_embedding)
                .where(
                    and_(
                        langchain_pg_embedding.c.collection_id.in_([uuid.UUID(u) for u in relevant_collection_uuids]),
                        langchain_pg_embedding.c.cmetadata['file_name'].astext == file_name,
                        langchain_pg_embedding.c.cmetadata['type'].astext == 'document_chunk'
                    )
                )
                .values(cmetadata=values_to_update)
            )

            result = await db.execute(update_stmt)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Se actualizaron {result.rowcount} chunks para el archivo '{file_name}'.")
                return True
            else:
                logger.warning(f"La consulta de actualización para '{file_name}' no afectó ninguna fila, aunque el documento fue encontrado.")
                return False

        except Exception as e:
            logger.error(f"❌ Error actualizando metadatos de '{file_name}' (workspace {workspace_id}): {e}", exc_info=True)
            await db.rollback()
            return False



async def list_user_collections(account_id: str, team_id: Optional[str] = None, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todas las colecciones (temas) únicas de un usuario o equipo
    y cuenta cuántos documentos hay en cada una.
    
    Args:
        account_id: ID de la cuenta del usuario
        team_id: ID del equipo (opcional)
        workspace_id: ID del workspace para filtrar colecciones (opcional)
    """
    logger.info(f"Listando colecciones para la cuenta {account_id}, workspace: {workspace_id}")
    collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"
    
    async with DBSession(SessionLocal) as db:
        try:
            # Primero, obtener el ID de la colección para este usuario
            collection_uuid_query = text("SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name")
            collection_result = await db.execute(collection_uuid_query, {"collection_name": collection_name})
            collection_uuid = collection_result.scalar_one_or_none()
            
            if not collection_uuid:
                logger.info(f"No se encontró la colección '{collection_name}' para listar.")
                return []

            # Consulta para agrupar por 'topic' y contar los 'file_name' únicos
            # Si se proporciona workspace_id, filtrar por él
            where_clause = "collection_id = :collection_uuid AND cmetadata->>'type' = 'document_chunk'"
            params = {"collection_uuid": collection_uuid}
            
            if workspace_id:
                where_clause += " AND cmetadata->>'workspace_id' = :workspace_id"
                params["workspace_id"] = workspace_id
                
            collections_query = text(
                f"""
                SELECT 
                    cmetadata->>'topic' AS topic,
                    COUNT(DISTINCT cmetadata->>'file_name') as document_count
                FROM langchain_pg_embedding
                WHERE {where_clause}
                GROUP BY cmetadata->>'topic'
                ORDER BY topic;
                """
            )
            result = await db.execute(collections_query, params)
            collections = [dict(row) for row in result.mappings()]
            return collections
        except Exception as e:
            logger.error(f"❌ Error listando colecciones para la cuenta {account_id}: {e}", exc_info=True)
            return []
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
            # Obtener los UUIDs de las colecciones relevantes
            relevant_collection_uuids = []
            if workspace_id:
                stmt = select(WorkspaceCollectionAssociation.langchain_collection_id).where(
                    WorkspaceCollectionAssociation.workspace_id == uuid.UUID(workspace_id)
                )
                result = await db.execute(stmt)
                relevant_collection_uuids.extend([str(u) for u in result.scalars().all()])
            
            user_collection_name = f"user_memories_{account_id}"
            global_collection_name = GLOBAL_COLLECTION_NAME
            team_collection_name = f"team_memories_{team_id}" if team_id else None

            for c_name in [user_collection_name, global_collection_name, team_collection_name]:
                if c_name:
                    stmt = select(LangchainPgCollection.uuid).where(LangchainPgCollection.name == c_name)
                    result = await db.execute(stmt)
                    c_uuid = result.scalar_one_or_none()
                    if c_uuid and str(c_uuid) not in relevant_collection_uuids:
                        relevant_collection_uuids.append(str(c_uuid))

            if not relevant_collection_uuids:
                logger.info(f"No se encontraron colecciones relevantes para extraer títulos para la cuenta {account_id}.")
                return 0

            # Lógica unificada para extraer y actualizar títulos de langchain_pg_embedding
            logger.info(f"Procesando documentos en colecciones PGVector para cuenta {account_id}.")
            
            clauses = [
                "collection_id = ANY(:col_uuids)",
                "cmetadata->>'type' = 'document_chunk'"
            ]
            params: Dict[str, Any] = {"col_uuids": [uuid.UUID(u) for u in relevant_collection_uuids]}
            if topic:
                clauses.append("cmetadata->>'topic' = :tpc")
                params["tpc"] = topic
            if workspace_id:
                clauses.append("cmetadata->>'workspace_id' = :wsid")
                params["wsid"] = str(workspace_id)

            select_sql = text("SELECT * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
            logger.info(f"Ejecutando consulta SQL: {select_sql} con parámetros: {params}")
            result = await db.execute(select_sql, params)
            chunks = result.mappings().all() 
            logger.info(f"Se encontraron {len(chunks)} fragmentos de documentos para procesar.")

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
