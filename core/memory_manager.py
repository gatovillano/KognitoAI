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
# No necesitamos urlparse, parse_qs aquí si usamos el engine directamente para PGVector

import uuid
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import Table, MetaData, update, and_

# Asegúrate de que tu versión de langchain-postgres sea compatible con este uso.
# Si sigue fallando, podría ser un problema de versión específica.

from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.database import (
    Perfil,
    SessionLocal,
    Account,
    Memory,
    WorkspaceDocumentChunk,
    engine,
)  # Importar el engine aquí
from utils.db_session import DBSession
from utils.embeddings import initialize_embeddings
from core.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap
GLOBAL_COLLECTION_NAME = "global_knowledge_base"
USER_MEMORIES_PREFIX = "user_memories_"

# Engine síncrono solo para PGVector
PGVECTOR_SYNC_ENGINE = create_engine(settings.database_url)

# Define tables for LangChain PostgreSQL integration
metadata = MetaData()
langchain_pg_collection = Table('langchain_pg_collection', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)
langchain_pg_embedding = Table('langchain_pg_embedding', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)


# Ya no necesitamos _get_pgvector_connection_args


async def get_user_profile(account_id: str) -> Optional[Perfil]:
    """
    Obtiene el perfil de un usuario a partir de su account_id universal.

    Si no se encuentra un perfil para la cuenta dada, se crea uno nuevo y vacío
    y se asocia a esa cuenta.
    Args:
        account_id: El identificador universal (UUID en formato string) de la cuenta.

    Returns:
        El objeto Perfil del usuario, o None si la cuenta no existe.
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
                )  # Convertir a UUID
                if account:
                    perfil = Perfil(
                        account_id=uuid.UUID(account_id)
                    )  # Convertir a UUID
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
    Args:
        account_id: El ID universal de la cuenta del usuario a actualizar.
        nombre: El nuevo nombre del usuario.
        gustos: Los nuevos gustos del usuario.
        intereses: Los nuevos intereses del usuario.
        otros_datos: Otros datos relevantes.
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
    account_id: str, content: str, type: str = "general_memory", team_id: Optional[str] = None
) -> None:
    """
    Genera embeddings para el contenido y lo guarda en la DB vectorial del usuario o equipo.

    Args:
        account_id: El ID universal de la cuenta a la que pertenece la memoria.
        content: El texto de la memoria a guardar.
        type: El tipo de memoria (ej: 'fact', 'idea').
        team_id: El ID del equipo (UUID en formato string) al que se asocia la memoria, si aplica.
    """
    logger.info(
        f"Añadiendo memoria a la DB vectorial para la cuenta {account_id}: '{content[:50]}...'"
    )
    try:
        embeddings: Embeddings = (
            await initialize_embeddings()
        )  # Asegurarse de usar await
        if not embeddings:
            logger.error(
                "Los Embeddings no están inicializados. No se puede añadir memoria."
            )
            return

        collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"

        # --- CORRECCIÓN CLAVE AQUÍ para PGVector ---
        # Ejecutar la operación de PGVector en un thread pool para no bloquear el event loop
        import asyncio

        vectorstore = await asyncio.to_thread(
            PGVector.from_existing_index,
            embedding=embeddings,
            collection_name=collection_name,
            connection=PGVECTOR_SYNC_ENGINE,
        )
        # Si la colección no existe, afrom_existing_index podría fallar.
        # Una alternativa más robusta es crearla si no existe, o usar PGVector.from_documents
        # con una lista vacía para inicializar la colección si es la primera vez.
        # Por ahora, asumimos que si el índice existe, lo usaremos.
        # Para crear la colección si no existe, PGVector.adelete(filter={}) y luego aadd_documents
        # en la primera adición para una nueva colección.

        metadata = {"account_id": str(account_id), "type": type}
        if team_id:
            metadata["team_id"] = str(team_id)
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
    - Si se proporciona workspace_id, busca solo en los documentos de ese workspace.
    - Si no, busca en la colección personal del usuario, de un equipo (si se proporciona team_id) y en la global.
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

        if workspace_id:
            # Búsqueda específica del Workspace
            logger.info(f"Realizando búsqueda de RAG en el workspace: {workspace_id}")
            async with DBSession(SessionLocal) as db:
                stmt = (
                    select(WorkspaceDocumentChunk)
                    .where(WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id))
                    .order_by(WorkspaceDocumentChunk.embedding.l2_distance(query_embedding))
                    .limit(k)
                )
                result = await db.execute(stmt)
                workspace_chunks = result.scalars().all()
                
                for chunk in workspace_chunks:
                    # Convertir el chunk a un objeto compatible con el formato de Document de LangChain
                    doc = Document(
                        page_content=chunk.content,
                        metadata={
                            "source": "Workspace",
                            "document_id": str(chunk.document_id),
                            "workspace_id": str(chunk.workspace_id)
                        }
                    )
                    all_docs.append(doc)
            logger.info(f"Encontrados {len(all_docs)} chunks relevantes en el workspace.")

        else:
            # Búsqueda general (personal, global, equipo)
            logger.info("Realizando búsqueda de RAG general (no en workspace).")
            user_vectorstore = await asyncio.to_thread(
                PGVector.from_existing_index,
                embedding=embeddings,
                collection_name=f"user_memories_{account_id}",
                connection=PGVECTOR_SYNC_ENGINE,
            )
            global_vectorstore = await asyncio.to_thread(
                PGVector.from_existing_index,
                embedding=embeddings,
                collection_name=GLOBAL_COLLECTION_NAME,
                connection=PGVECTOR_SYNC_ENGINE,
            )
            team_vectorstore = None
            if team_id:
                team_vectorstore = await asyncio.to_thread(
                    PGVector.from_existing_index,
                    embedding=embeddings,
                    collection_name=f"team_memories_{team_id}",
                    connection=PGVECTOR_SYNC_ENGINE,
                )

            k_per_source = k // (3 if team_id else 2) if k > 1 else 1
            filters = metadata_filters if metadata_filters else {}

            user_search_task = user_vectorstore.asimilarity_search(query, k=k_per_source, filter=filters)
            global_search_task = global_vectorstore.asimilarity_search(query, k=k_per_source, filter=filters)
            team_search_task = team_vectorstore.asimilarity_search(query, k=k_per_source, filter=filters) if team_id and team_vectorstore else asyncio.sleep(0, result=[])

            results = await asyncio.gather(user_search_task, global_search_task, team_search_task, return_exceptions=True)

            user_results, global_results, team_results = results
            if isinstance(user_results, list):
                for doc in user_results: doc.metadata["source"] = "Personal"
                all_docs.extend(user_results)
            else:
                logger.warning(f"⚠️ No se pudo buscar en la memoria personal de la cuenta {account_id}: {user_results}")

            if isinstance(global_results, list):
                for doc in global_results: doc.metadata["source"] = "Global"
                all_docs.extend(global_results)
            else:
                logger.warning(f"⚠️ No se pudo buscar en la memoria global: {global_results}")

            if team_id and isinstance(team_results, list):
                for doc in team_results: doc.metadata["source"] = "Team"
                all_docs.extend(team_results)
            elif team_id:
                logger.warning(f"⚠️ No se pudo buscar en la memoria del equipo {team_id}: {team_results}")

        if not all_docs:
            return "No se encontraron memorias relevantes."

        memories_list = [
            f"- [Fuente: {d.metadata.get('source', 'N/A')}] (Tema: {d.metadata.get('topic', 'N/A')}): {d.page_content}"
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
    Si se proporciona workspace_id, los chunks se guardan en la tabla `workspace_document_chunks`.
    Si no, se guardan en la colección general de `langchain_pg_embedding`.
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
        
        if workspace_id:
            logger.info(f"📊 Iniciando procesamiento RAG para '{file_name}' en el workspace '{workspace_id}'.")
            document_id = uuid.uuid4()
            chunks_to_insert = []
            for i, text_content in enumerate(texts):
                if not text_content.strip():
                    continue
                embedding_vector = await embeddings.aembed_query(text_content)
                chunks_to_insert.append(
                    WorkspaceDocumentChunk(
                        workspace_id=uuid.UUID(workspace_id),
                        document_id=document_id,
                        content=text_content,
                        embedding=embedding_vector,
                        chunk_order=i,
                    )
                )
            
            async with DBSession(SessionLocal) as db:
                db.add_all(chunks_to_insert)
                await db.commit()
            
            logger.info(f"✅ Procesado y añadido {len(chunks_to_insert)} chunks al workspace '{workspace_id}'.")
            # Aquí podrías pasar el workspace_id al trigger si es necesario
            # asyncio.create_task(proactive_knowledge_linker_trigger(...))
            return len(chunks_to_insert)

        else:
            # Lógica existente para colecciones generales
            if is_global:
                collection_name = GLOBAL_COLLECTION_NAME
            elif account_id and not team_id:
                collection_name = f"user_memories_{account_id}"
            elif team_id:
                collection_name = f"team_memories_{team_id}"
            else:
                logger.error("❌ process_document_for_rag llamado sin account_id, team_id o is_global=True.")
                return 0

            logger.info(f"📊 Iniciando procesamiento RAG para '{file_name}' en la colección '{collection_name}'.")
            
            base_metadata = metadata if metadata else {}
            base_metadata.update({
                "file_name": file_name, "topic": topic, "type": "document_chunk",
                "scope": "global" if is_global else "personal",
            })
            if account_id and not is_global: base_metadata["account_id"] = str(account_id)
            if team_id: base_metadata["team_id"] = str(team_id)

            ids, lc_documents = [], []
            for i, text_content in enumerate(texts):
                if not text_content.strip():
                    continue
                chunk_metadata = base_metadata.copy()
                chunk_metadata["chunk_index"] = i
                for k, v in chunk_metadata.items():
                    if isinstance(v, (datetime.datetime, datetime.date)):
                        chunk_metadata[k] = v.isoformat()
                lc_documents.append(Document(page_content=text_content, metadata=chunk_metadata))
                ids.append(str(uuid.uuid4()))
            
            vectorstore = await PGVector.afrom_documents(
                documents=lc_documents, embedding=embeddings,
                collection_name=collection_name, connection=PGVECTOR_SYNC_ENGINE,
            )
            await vectorstore.aadd_documents(documents=lc_documents, ids=ids)
            
            logger.info(f"✅ Procesado y añadido {len(lc_documents)} chunks a la colección '{collection_name}'.")
            
            doc_embedding = await embeddings.aembed_query(extracted_text[:10000] + "..." if len(extracted_text) > 10000 else extracted_text)
            asyncio.create_task(proactive_knowledge_linker_trigger({
                "account_id": account_id, "team_id": team_id, "content": extracted_text,
                "title": file_name, "type": "document", "embedding": doc_embedding,
                "workspace_id": workspace_id # Pasar workspace_id al trigger
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
    - Si se proporciona workspace_id, elimina de la tabla `workspace_document_chunks`.
    - Si no, elimina de la colección general de `langchain_pg_embedding`.
    """
    if not file_name and not topic:
        logger.warning("Se llamó a delete_document_chunks sin file_name ni topic.")
        return 0

    if workspace_id:
        logger.info(f"Eliminando chunks del workspace {workspace_id}")
        async with DBSession(SessionLocal) as db:
            try:
                stmt = delete(WorkspaceDocumentChunk).where(WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id))
                if file_name:
                    # Asumiendo que `file_name` corresponde a `document_id` en `WorkspaceDocumentChunk`
                    stmt = stmt.where(WorkspaceDocumentChunk.document_id == uuid.UUID(file_name))
                
                result = await db.execute(stmt)
                await db.commit()
                deleted_count = result.rowcount
                logger.info(f"🗑️ Borrados {deleted_count} chunks del workspace {workspace_id}.")
                return deleted_count
            except Exception as e:
                logger.error(f"❌ Error eliminando chunks del workspace {workspace_id}: {e}", exc_info=True)
                await db.rollback()
                return 0
    else:
        # Lógica existente para colecciones generales
        collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"
        async with DBSession(SessionLocal) as db:
            col_q = text("SELECT uuid FROM langchain_pg_collection WHERE name = :cname")
            res = await db.execute(col_q, {"cname": collection_name})
            collection_uuid = res.scalar_one_or_none()
            if not collection_uuid:
                logger.info(f"No existe la colección '{collection_name}', nada que borrar.")
                return 0

            clauses = ["collection_id = :col_id", "cmetadata->>'type' = 'document_chunk'"]
            params: Dict[str, Any] = {"col_id": collection_uuid}
            if file_name:
                clauses.append("cmetadata->>'file_name' = :fname")
                params["fname"] = file_name
            if topic:
                clauses.append("cmetadata->>'topic' = :tpc")
                params["tpc"] = topic

            delete_sql = text("DELETE FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
            result = await db.execute(delete_sql, params)
            deleted = result.rowcount or 0
            await db.commit()
            logger.info(f"🗑️ Borrados {deleted} chunks de '{collection_name}'.")
            return deleted


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

        if workspace_id:
            # Lógica para recuperar de WorkspaceDocumentChunk
            logger.info(f"Buscando contenido en WorkspaceDocumentChunk para workspace {workspace_id}.")
            async with DBSession(SessionLocal) as db:
                # Para reconstruir por file_name, necesitamos que WorkspaceDocumentChunk
                # tenga un campo 'file_name' o una tabla intermedia.
                # Asumiendo que 'document_id' en WorkspaceDocumentChunk es el UUID del documento
                # y que 'file_name' es el identificador que se mapea a ese document_id.
                # Si 'file_name' no es un UUID, esta lógica necesitaría un mapeo.
                # Por ahora, buscaremos por el UUID del documento si el file_name es un UUID válido.
                # Si no, esto requeriría una tabla WorkspaceDocument para mapear.

                # Opción 1: Si file_name ES el document_id (UUID)
                try:
                    target_document_uuid = uuid.UUID(file_name)
                    stmt = select(WorkspaceDocumentChunk).where(
                        and_(
                            WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id),
                            WorkspaceDocumentChunk.document_id == target_document_uuid
                        )
                    ).order_by(WorkspaceDocumentChunk.chunk_order)
                    result = await db.execute(stmt)
                    workspace_chunks = result.scalars().all()

                    for chunk in workspace_chunks:
                        retrieved_docs.append(
                            Document(
                                page_content=chunk.content,
                                metadata={
                                    "source": "Workspace",
                                    "document_id": str(chunk.document_id),
                                    "workspace_id": str(chunk.workspace_id),
                                    "chunk_index": chunk.chunk_order # Para el ordenamiento
                                }
                            )
                        )
                except ValueError:
                    # Si file_name no es un UUID válido, significa que no es el document_id.
                    # En este caso, necesitaríamos una columna 'file_name' en WorkspaceDocumentChunk
                    # o una tabla intermedia para buscar por nombre de archivo.
                    logger.warning(f"'{file_name}' no es un UUID válido. No se puede buscar directamente en WorkspaceDocumentChunk por document_id.")
                    # Si tu WorkspaceDocumentChunk tiene una columna 'file_name', la consulta sería:
                    # stmt = select(WorkspaceDocumentChunk).where(
                    #     and_(
                    #         WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id),
                    #         WorkspaceDocumentChunk.file_name == file_name
                    #     )
                    # ).order_by(WorkspaceDocumentChunk.chunk_order)
                    # ... y luego procesar los resultados.
                    pass # Dejar vacío si no hay columna file_name o tabla de mapeo.


        else:
            # Lógica existente para recuperar de colecciones generales (langchain_pg_embedding)
            logger.info("Buscando contenido en colecciones PGVector generales.")
            collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"
            vectorstore = await asyncio.to_thread(
                PGVector.from_existing_index,
                embedding=embeddings,
                collection_name=collection_name,
                connection=PGVECTOR_SYNC_ENGINE,
            )

            retrieved_docs = await vectorstore.asimilarity_search(
                query=" ",
                k=10000,
                filter={"file_name": file_name, "type": "document_chunk"},
            )

        if not retrieved_docs:
            logger.warning(f"No se encontraron chunks para el documento '{file_name}' en el contexto especificado.")
            return None

        sorted_chunks = sorted(
            retrieved_docs, key=lambda d: d.metadata.get("chunk_index", 0)
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
    if workspace_id:
        logger.info(f"Listando documentos para el workspace {workspace_id}")
        async with DBSession(SessionLocal) as db:
            try:
                stmt = (
                    select(
                        WorkspaceDocumentChunk.document_id,
                        WorkspaceDocumentChunk.content.label("title")  # Asumiendo que el título puede ser inferido del contenido
                    )
                    .where(WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id))
                    .distinct(WorkspaceDocumentChunk.document_id)
                )
                result = await db.execute(stmt)
                documents = [
                    {
                        "file_name": str(row.document_id),
                        "topic": "Workspace",
                        "title": row.title.split('\n')[0] if row.title else "Sin título",
                        "author": None,
                    }
                    for row in result.mappings()
                ]
                logger.info(f"✅ Listados {len(documents)} documentos para el workspace {workspace_id}.")
                return documents
            except Exception as e:
                logger.error(f"❌ Error listando documentos para el workspace {workspace_id}: {e}", exc_info=True)
                return []
    else:
        logger.info(f"Listando documentos para la cuenta {account_id}")
        try:
            collection_name = f"user_memories_{account_id}"
            async with DBSession(SessionLocal) as db:
                collection_uuid_query = text("SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name")
                collection_result = await db.execute(collection_uuid_query, {"collection_name": collection_name})
                collection_uuid = collection_result.scalar_one_or_none()

                if not collection_uuid:
                    logger.info(f"No se encontró la colección '{collection_name}' para listar documentos.")
                    return []

                if team_id:
                    document_list_query = text(
                        """
                        SELECT DISTINCT ON (cmetadata->>'file_name')
                               cmetadata->>'file_name' AS file_name,
                               cmetadata->>'topic' AS topic,
                               cmetadata->>'title' AS title,
                               cmetadata->>'author' AS author
                        FROM langchain_pg_embedding
                        WHERE collection_id = :collection_uuid 
                        AND cmetadata->>'type' = 'document_chunk'
                        AND cmetadata->>'team_id' = :team_id
                        ORDER BY cmetadata->>'file_name', id
                        """
                    )
                    document_list_result = await db.execute(document_list_query, {"collection_uuid": collection_uuid, "team_id": team_id})
                else:
                    document_list_query = text(
                        """
                        SELECT DISTINCT ON (cmetadata->>'file_name')
                               cmetadata->>'file_name' AS file_name,
                               cmetadata->>'topic' AS topic,
                               cmetadata->>'title' AS title,
                               cmetadata->>'author' AS author
                        FROM langchain_pg_embedding
                        WHERE collection_id = :collection_uuid 
                        AND cmetadata->>'type' = 'document_chunk'
                        AND (cmetadata->>'team_id' IS NULL OR cmetadata->>'team_id' = '')
                        ORDER BY cmetadata->>'file_name', id
                        """
                    )
                    document_list_result = await db.execute(document_list_query, {"collection_uuid": collection_uuid})

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
            if workspace_id:
                # Lógica para actualizar metadatos en WorkspaceDocumentChunk
                logger.info(f"Actualizando metadatos en WorkspaceDocumentChunk para workspace {workspace_id}.")
                
                # Para actualizar por file_name en WorkspaceDocumentChunk, necesitamos que:
                # 1. 'file_name' sea una columna en WorkspaceDocumentChunk.
                # 2. O, que 'file_name' sea el 'document_id' (UUID) que se guarda.
                # 3. O, que exista una tabla intermedia que mapee 'file_name' a 'document_id'.
                
                # Asumiendo que 'document_id' en WorkspaceDocumentChunk es el UUID del documento
                # y que 'file_name' es el identificador que se mapea a ese document_id.
                # Si 'file_name' no es un UUID, esta lógica necesitaría un mapeo.
                
                # Por ahora, intentaremos convertir file_name a UUID para buscar por document_id.
                # Si tu WorkspaceDocumentChunk tiene una columna 'file_name', la lógica sería diferente.
                
                target_document_uuid = None
                try:
                    target_document_uuid = uuid.UUID(file_name)
                except ValueError:
                    logger.warning(f"'{file_name}' no es un UUID válido. No se puede buscar directamente en WorkspaceDocumentChunk por document_id para actualizar.")
                    return False # No podemos actualizar si no encontramos el documento por su ID.

                # Construir la sentencia de actualización para WorkspaceDocumentChunk
                # NOTA: WorkspaceDocumentChunk no tiene campos 'title' o 'topic' directamente.
                # Si quieres almacenar estos metadatos, necesitarías añadirlos como columnas
                # a la tabla WorkspaceDocumentChunk en core/database.py.
                # Por ahora, esta función no puede actualizar 'title' o 'topic' en WorkspaceDocumentChunk
                # a menos que los almacenes como parte del 'content' o en una columna JSONB si la añades.
                
                # Si añades 'title' y 'topic' como columnas a WorkspaceDocumentChunk:
                # update_values = {}
                # if new_title is not None:
                #     update_values['title'] = new_title
                # if new_topic is not None:
                #     update_values['topic'] = new_topic
                
                # if update_values:
                #     stmt = update(WorkspaceDocumentChunk).where(
                #         and_(
                #             WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id),
                #             WorkspaceDocumentChunk.document_id == target_document_uuid
                #         )
                #     ).values(**update_values)
                #     result = await db.execute(stmt)
                #     await db.commit()
                #     if result.rowcount > 0:
                #         logger.info(f"✅ Metadatos de {file_name} en workspace {workspace_id} actualizados.")
                #         return True
                # else:
                #     logger.warning("No hay valores para actualizar en WorkspaceDocumentChunk.")
                #     return False
                
                # Dado que WorkspaceDocumentChunk actualmente solo tiene content y embedding,
                # y no 'title' o 'topic' como columnas directas, esta función no puede
                # actualizar esos metadatos directamente en esa tabla.
                # Si quieres que esto funcione, DEBES añadir esas columnas a WorkspaceDocumentChunk.
                logger.warning(
                    f"No se pueden actualizar 'title' o 'topic' directamente en WorkspaceDocumentChunk "
                    f"para el documento '{file_name}' (workspace {workspace_id}) "
                    f"ya que esas columnas no existen. Considera añadir 'title' y 'topic' a WorkspaceDocumentChunk."
                )
                return False # Retorna False porque no se pudo realizar la actualización deseada.


            else:
                # Lógica existente para actualizar metadatos en colecciones generales (langchain_pg_embedding)
                logger.info("Actualizando metadatos en colecciones PGVector generales.")
                collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"

                collection_stmt = select(langchain_pg_collection.c.uuid).where(langchain_pg_collection.c.name == collection_name)
                collection_id_result = await db.execute(collection_stmt)
                collection_id = collection_id_result.scalar_one_or_none()

                if not collection_id:
                    logger.error(f"No se encontró la colección '{collection_name}' para actualizar metadatos.")
                    return False

                stmt = select(langchain_pg_embedding.c.cmetadata).where(
                    and_(
                        langchain_pg_embedding.c.collection_id == collection_id,
                        langchain_pg_embedding.c.cmetadata['file_name'].astext == file_name
                    )
                ).limit(1)
                
                cmetadata_result = await db.execute(stmt)
                current_cmetadata = cmetadata_result.scalar_one_or_none()
                
                if not current_cmetadata:
                    logger.warning(f"No se encontraron chunks para el archivo '{file_name}' en la colección '{collection_name}'.")
                    return False

                values_to_update = current_cmetadata.copy()
                if new_title is not None:
                    values_to_update['title'] = new_title
                if new_topic is not None:
                    values_to_update['topic'] = new_topic

                update_stmt = (
                    update(langchain_pg_embedding)
                    .where(
                        and_(
                            langchain_pg_embedding.c.collection_id == collection_id,
                            langchain_pg_embedding.c.cmetadata['file_name'].astext == file_name
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



async def list_user_collections(account_id: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todas las colecciones (temas) únicas de un usuario o equipo
    y cuenta cuántos documentos hay en cada una.
    """
    logger.info(f"Listando colecciones para la cuenta {account_id}")
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
            collections_query = text(
                """
                SELECT 
                    cmetadata->>'topic' AS topic,
                    COUNT(DISTINCT cmetadata->>'file_name') as document_count
                FROM langchain_pg_embedding
                WHERE collection_id = :collection_uuid AND cmetadata->>'type' = 'document_chunk'
                GROUP BY cmetadata->>'topic'
                ORDER BY topic;
                """
            )
            result = await db.execute(collections_query, {"collection_uuid": collection_uuid})
            collections = [dict(row) for row in result.mappings()]
            return collections
        except Exception as e:
            logger.error(f"❌ Error listando colecciones para la cuenta {account_id}: {e}", exc_info=True)
            return []
async def extract_titles_and_update_metadata(account_id: str, topic: Optional[str] = None, workspace_id: Optional[str] = None) -> int:
    """
    Extrae títulos de los documentos y actualiza sus metadatos en la base de conocimiento del usuario.
    
    Args:
        account_id: El ID universal de la cuenta del usuario.
        topic: Tema de los documentos a procesar (opcional).
        workspace_id: El ID del workspace (UUID en formato string) para procesar documentos de un workspace específico, si aplica.
    
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
            if workspace_id:
                # Lógica para extraer y actualizar títulos de WorkspaceDocumentChunk
                logger.info(f"Procesando documentos en WorkspaceDocumentChunk para workspace {workspace_id}.")
                
                # Asumo que WorkspaceDocumentChunk ahora tiene 'file_name', 'title', 'topic' como columnas.
                # Si no las tiene, esta sección necesitará ser ajustada o esas columnas añadidas a la DB.
                
                stmt = select(
                    WorkspaceDocumentChunk.document_id,
                    WorkspaceDocumentChunk.file_name,
                    WorkspaceDocumentChunk.content,
                    WorkspaceDocumentChunk.chunk_order,
                    WorkspaceDocumentChunk.title,
                    WorkspaceDocumentChunk.topic # Asegurarse de seleccionar topic si se usa para filtrar
                ).where(
                    WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id)
                ).order_by(
                    WorkspaceDocumentChunk.document_id,
                    WorkspaceDocumentChunk.chunk_order
                )
                
                if topic:
                    stmt = stmt.where(WorkspaceDocumentChunk.topic == topic)
                
                result = await db.execute(stmt)
                # Convertir los resultados a diccionarios para un acceso más robusto y evitar errores de Pylance
                chunks_raw = result.all() # Esto devuelve Row objects/tuples
                
                if not chunks_raw:
                    logger.info(f"No se encontraron fragmentos de documentos en el workspace {workspace_id} para procesar.")
                    return 0 # Asegurar retorno de int

                # Mapear los resultados a un formato de diccionario más amigable
                documents_to_process: Dict[uuid.UUID, Dict[str, Any]] = {}
                for chunk_row in chunks_raw:
                    # Acceder a los elementos por índice o nombre de columna si es un Row object
                    doc_id = chunk_row[0] # document_id
                    file_name = chunk_row[1] # file_name
                    content = chunk_row[2] # content
                    order = chunk_row[3] # chunk_order
                    current_title = chunk_row[4] # title
                    
                    if doc_id not in documents_to_process:
                        documents_to_process[doc_id] = {
                            "file_name": file_name,
                            "current_title": current_title,
                            "chunks": []
                        }
                    documents_to_process[doc_id]["chunks"].append({"content": content, "order": order})

                for doc_id, doc_data in documents_to_process.items():
                    logger.info(f"Procesando documento: {doc_data['file_name']} (ID: {doc_id}) con {len(doc_data['chunks'])} fragmentos.")
                    
                    full_content = "".join([c["content"] for c in sorted(doc_data["chunks"], key=lambda x: x["order"])])
                    
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
                    
                    if new_title and new_title != doc_data['current_title']:
                        logger.info(f"Título extraído para {doc_data['file_name']}: '{new_title}'")
                        
                        update_stmt = update(WorkspaceDocumentChunk).where(
                            and_(
                                WorkspaceDocumentChunk.workspace_id == uuid.UUID(workspace_id),
                                WorkspaceDocumentChunk.document_id == doc_id
                            )
                        ).values(title=new_title)
                        
                        result = await db.execute(update_stmt)
                        if result.rowcount > 0:
                            updated_count += 1
                            logger.info(f"Actualizado título para el documento {doc_data['file_name']} en workspace {workspace_id}.")
                        else:
                            logger.warning(f"No se pudo actualizar el título para el documento {doc_data['file_name']} en workspace {workspace_id}.")
                    else:
                        logger.info(f"No se encontró un nuevo título válido o el título es el mismo para {doc_data['file_name']}.")

                logger.info(f"Se actualizaron los títulos de {updated_count} documentos para el workspace {workspace_id}.")


            else:
                # Lógica existente para colecciones generales (langchain_pg_embedding)
                logger.info(f"Procesando documentos en colecciones PGVector generales para cuenta {account_id}.")
                collection_name = f"user_memories_{account_id}"
                
                col_q = text("SELECT uuid FROM langchain_pg_collection WHERE name = :cname")
                res = await db.execute(col_q, {"cname": collection_name})
                collection_uuid = res.scalar_one_or_none()
                if not collection_uuid:
                    logger.info(f"No existe la colección '{collection_name}', no hay documentos para procesar.")
                    return 0 # Asegurar retorno de int

                clauses = ["collection_id = :col_id", "cmetadata->>'type' = 'document_chunk'"]
                params = {"col_id": collection_uuid}
                if topic:
                    clauses.append("cmetadata->>'topic' = :tpc")
                    params["tpc"] = topic

                select_sql = text("SELECT * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
                logger.info(f"Ejecutando consulta SQL: {select_sql} con parámetros: {params}")
                result = await db.execute(select_sql, params)
                # Usar .mappings().all() para obtener diccionarios directamente y evitar errores de Pylance
                chunks = result.mappings().all() 
                logger.info(f"Se encontraron {len(chunks)} fragmentos de documentos para procesar.")

                if not chunks:
                    logger.info("No se encontraron fragmentos de documentos para procesar.")
                    return 0 # Asegurar retorno de int

                documents = {}
                for chunk in chunks:
                    # Acceso directo a cmetadata como dict
                    file_name = chunk['cmetadata'].get('file_name')
                    if file_name:
                        if file_name not in documents:
                            documents[file_name] = []
                        documents[file_name].append(chunk)
                    else:
                        logger.warning(f"Fragmento sin 'file_name' en cmetadata: {chunk['cmetadata']}")

                for file_name, doc_chunks in documents.items():
                    logger.info(f"Procesando documento: {file_name} con {len(doc_chunks)} fragmentos.")
                    
                    # Acceso a 'document' (contenido del chunk)
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
                        success = await update_document_metadata(account_id, file_name, new_title=new_title, new_topic=None)
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
                
            return updated_count # Asegurar retorno de int
        except Exception as e:
            logger.error(f"Error al extraer y actualizar títulos para la cuenta {account_id} (workspace {workspace_id}): {e}", exc_info=True)
            await db.rollback()
            return 0 # Asegurar retorno de int # Asegurar rollback en caso de error
