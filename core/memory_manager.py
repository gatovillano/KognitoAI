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
from sqlalchemy import select, text, create_engine
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
    team_id: Optional[str] = None
) -> str:
    """
    Recupera memorias relevantes de la colección personal del usuario, de un equipo y de la global.
    Args:
        account_id: El ID universal de la cuenta del usuario.
        query: La consulta del usuario para buscar memorias similares.
        k: El número total de memorias a recuperar.
        metadata_filters: Filtros adicionales para aplicar a la búsqueda.
        team_id: El ID del equipo (UUID en formato string) para buscar en la colección del equipo, si aplica.

    Returns:
        Una cadena de texto formateada con las memorias relevantes encontradas.
    """
    logger.info(
        f"Buscando memorias relevantes para la cuenta {account_id} con la consulta: '{query[:50]}...'"
    )
    try:
        embeddings: Embeddings = (
            await initialize_embeddings()
        )  # Asegurarse de usar await
        if not embeddings:
            return "Error: El modelo de memoria no está disponible."

        # --- CORRECCIÓN CLAVE AQUÍ para PGVector ---
        # Ejecutar la operación de PGVector en un thread pool para no bloquear el event loop
        import asyncio

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

        # Ejecución asíncrona de búsquedas en paralelo
        user_search_task = user_vectorstore.asimilarity_search(
            query, k=k_per_source, filter=filters
        )
        global_search_task = global_vectorstore.asimilarity_search(
            query, k=k_per_source, filter=filters
        )
        team_search_task = team_vectorstore.asimilarity_search(
            query, k=k_per_source, filter=filters
        ) if team_id and team_vectorstore else asyncio.sleep(0, result=[])

        results = await asyncio.gather(
            user_search_task, global_search_task, team_search_task, return_exceptions=True
        )

        all_docs = []
        user_results, global_results, team_results = results
        if isinstance(user_results, list):
            for doc in user_results:
                doc.metadata["source"] = "Personal"
            all_docs.extend(user_results)
        else:
            logger.warning(
                f"⚠️ No se pudo buscar en la memoria personal de la cuenta {account_id}: {user_results}"
            )

        if isinstance(global_results, list):
            for doc in global_results:
                doc.metadata["source"] = "Global"
            all_docs.extend(global_results)
        else:
            logger.warning(
                f"⚠️ No se pudo buscar en la memoria global: {global_results}"
            )

        if team_id and isinstance(team_results, list):
            for doc in team_results:
                doc.metadata["source"] = "Team"
            all_docs.extend(team_results)
        elif team_id:
            logger.warning(
                f"⚠️ No se pudo buscar en la memoria del equipo {team_id}: {team_results}"
            )

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
) -> int:
    """
    Divide, embebe y almacena el texto de un documento en la DB vectorial.
    Args:
        file_name: El nombre del archivo original.
        extracted_text: El texto extraído del documento.
        topic: La categoría del documento.
        account_id: El ID universal de la cuenta del usuario (si no es global).
        is_global: Si es True, el documento se guarda en la colección global.
        team_id: El ID del equipo (UUID en formato string) al que se asocia el documento, si aplica.
        metadata: Metadatos adicionales sobre el documento.

    Returns:
        El número de fragmentos (chunks) añadidos a la base de datos.
    """
    if is_global:
        collection_name = GLOBAL_COLLECTION_NAME
    elif account_id and not team_id:
        collection_name = f"user_memories_{account_id}"
    elif team_id:
        collection_name = f"team_memories_{team_id}"
    else:
        logger.error(
            "❌ process_document_for_rag llamado sin account_id y sin is_global=True."
        )
        return 0

    logger.info(
        f"📊 Iniciando procesamiento RAG para '{file_name}' en la colección '{collection_name}'."
    )
    if not extracted_text:
        return 0
    try:
        embeddings = await initialize_embeddings()  # Asegurarse de usar await
        if not embeddings:
            logger.error(
                "Los Embeddings no están inicializados. No se puede procesar el documento."
            )
            return 0

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        texts = text_splitter.split_text(extracted_text)

        base_metadata = metadata if metadata else {}
        base_metadata.update(
            {
                "file_name": file_name,
                "topic": topic,
                "type": "document_chunk",
                "scope": "global" if is_global else "personal",
            }
        )
        if account_id and not is_global:
            base_metadata["account_id"] = str(account_id)
        if team_id:
            base_metadata["team_id"] = str(team_id)

        ids = []
        lc_documents = []
        for i, text_content in enumerate(texts):
            if not text_content.strip():  # Skip empty or whitespace-only chunks
                logger.warning(f"Skipping empty chunk at index {i} for file '{file_name}'")
                continue
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            # Asegurar que todos los valores de metadatos sean serializables
            for k, v in chunk_metadata.items():
                if isinstance(v, (datetime.datetime, datetime.date)):
                    chunk_metadata[k] = v.isoformat()
            lc_documents.append(
                Document(page_content=text_content, metadata=chunk_metadata)
            )
            ids.append(str(uuid.uuid4()))
        logger.info(f"Prepared {len(lc_documents)} valid chunks for file '{file_name}'")

        # --- CORRECCIÓN CLAVE AQUÍ para PGVector ---
        # Ejecutar la operación de PGVector en un thread pool para no bloquear el event loop
        import asyncio

        vectorstore = await PGVector.afrom_documents(
            documents=lc_documents,
            embedding=embeddings,
            collection_name=collection_name,
            connection=PGVECTOR_SYNC_ENGINE,
        )

        await vectorstore.aadd_documents(documents=lc_documents, ids=ids)
        logger.info(
            f"✅ Procesado y añadido {len(lc_documents)} chunks a la colección '{collection_name}'."
        )
        # // INICIO EDICIÓN
        # Generate an embedding for the entire document or a summary if the text is too long
        doc_embedding = None
        if len(extracted_text) > 10000:  # If text is very long, use a summary for embedding
            summary = extracted_text[:10000] + "..."  # Truncate for embedding
            doc_embedding = await embeddings.aembed_query(summary)
        else:
            doc_embedding = await embeddings.aembed_query(extracted_text)
            
        asyncio.create_task(
            proactive_knowledge_linker_trigger({
                "account_id": account_id,
                "team_id": team_id if team_id else None,
                "content": extracted_text,
                "title": file_name,
                "type": "document",
                "embedding": doc_embedding
            })
        )
        # // FIN EDICIÓN
        logger.info(
            f"✅ Añadidos {len(lc_documents)} chunks a la colección '{collection_name}'."
        )
        return len(lc_documents)
    except Exception as e:
        logger.error(
            f"❌ Error durante el procesamiento RAG para '{file_name}': {e}",
            exc_info=True,
        )
        return 0


async def delete_document_chunks(
    account_id: str,
    file_name: Optional[str] = None,
    topic: Optional[str] = None,
    team_id: Optional[str] = None
) -> int:
    """
    Elimina los chunks de la tabla langchain_pg_embedding que pertenecen a una colección de usuario o equipo.
    La eliminación se puede filtrar por nombre de archivo o por tema.
    Devuelve el número de filas borradas.
    """
    if not file_name and not topic:
        logger.warning("Se llamó a delete_document_chunks sin file_name ni topic.")
        return 0

    # Inicializa embeddings para mantener compatibilidad (aunque no se usen aquí)
    embeddings = await initialize_embeddings()
    if not embeddings:
        logger.warning("No pudo inicializar embeddings; abortando borrado.")
        return 0

    collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"
    async with DBSession(SessionLocal) as db:
        # 1) Obtener UUID de la colección
        col_q = text("SELECT uuid FROM langchain_pg_collection WHERE name = :cname")
        res = await db.execute(col_q, {"cname": collection_name})
        collection_uuid = res.scalar_one_or_none()
        if not collection_uuid:
            logger.info(f"No existe la colección '{collection_name}', nada que borrar.")
            return 0

        # 2) Construir cláusulas DELETE
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


async def get_full_document_content(account_id: str, file_name: str, team_id: Optional[str] = None) -> Optional[str]:
    """
    Reconstruye y devuelve el contenido completo de un documento desde sus chunks.
    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a reconstruir.
        team_id: El ID del equipo (UUID en formato string) para buscar en la colección del equipo, si aplica.

    Returns:
        El contenido completo del documento como una cadena, o None si no se encuentra.
    """
    logger.info(
        f"Recuperando contenido completo de '{file_name}' para la cuenta {account_id}"
    )
    try:
        embeddings: Embeddings = (
            await initialize_embeddings()
        )  # Asegurarse de usar await
        if not embeddings:
            return None

        # --- CORRECCIÓN CLAVE AQUÍ para PGVector ---
        collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"
        vectorstore = await asyncio.to_thread(
            PGVector.from_existing_index,
            embedding=embeddings,
            collection_name=collection_name,
            connection=PGVECTOR_SYNC_ENGINE,
        )

        # Una búsqueda muy general para recuperar todos los chunks con el file_name dado.
        # Ajusta `k` a un número suficientemente grande para abarcar todos los chunks de un documento.
        retrieved_docs = await vectorstore.asimilarity_search(
            query=" ",  # Consulta vacía para obtener todos los documentos con el filtro
            k=10000,  # Un número muy alto para asegurar que se traigan todos los chunks
            filter={"file_name": file_name, "type": "document_chunk"},
        )

        if not retrieved_docs:
            return None

        # Ordenar los chunks por índice para reconstruir el documento correctamente
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
            f"❌ Error recuperando contenido de '{file_name}': {e}", exc_info=True
        )
        return None


async def list_user_documents(account_id: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todos los documentos únicos subidos por un usuario o equipo.
    Args:
        account_id: El ID universal de la cuenta del usuario.
        team_id: El ID del equipo (UUID en formato string) para listar documentos del equipo, si aplica.

    Returns:
        Una lista de diccionarios, donde cada diccionario representa un documento.
    """
    logger.info(f"Listando documentos para la cuenta {account_id}")
    try:
        collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"
        async with DBSession(SessionLocal) as db:
            # Primero, verificar si la colección existe para evitar errores en la consulta pg_embedding
            collection_uuid_query = text(
                "SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name"
            )
            collection_result = await db.execute(
                collection_uuid_query, {"collection_name": collection_name}
            )
            collection_uuid = collection_result.scalar_one_or_none()

            if not collection_uuid:
                logger.info(
                    f"No se encontró la colección '{collection_name}' para listar documentos."
                )
                return []  # No hay colección, no hay documentos

            document_list_query = text(
                """
                SELECT DISTINCT ON (cmetadata->>'file_name')
                       cmetadata->>'file_name' AS file_name,
                       cmetadata->>'topic' AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author
                FROM langchain_pg_embedding
                WHERE collection_id = :collection_uuid AND cmetadata->>'type' = 'document_chunk'
                ORDER BY cmetadata->>'file_name', id
                """
            )
            document_list_result = await db.execute(
                document_list_query, {"collection_uuid": collection_uuid}
            )
            documents = [dict(row) for row in document_list_result.mappings()]

            logger.info(
                f"✅ Listados {len(documents)} documentos para la cuenta {account_id}."
            )
            return documents
    except Exception as e:
        logger.error(
            f"❌ Error listando documentos para la cuenta {account_id}: {e}",
            exc_info=True,
        )
        return []


async def update_document_metadata(
    account_id: str, 
    file_name: str, 
    new_title: Optional[str], 
    new_topic: Optional[str],
    team_id: Optional[str] = None
) -> bool:
    """
    Actualiza el título y/o la categoría (topic) de todos los chunks de un documento.
    
    Esta función construye y ejecuta una consulta SQL de actualización directamente
    sobre la tabla de embeddings de LangChain para modificar el campo JSONB `cmetadata`.
    
    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a actualizar.
        new_title: El nuevo título (si se proporciona).
        new_topic: La nueva categoría/base de conocimiento (si se proporciona).
        team_id: El ID del equipo (UUID en formato string) para actualizar en la colección del equipo, si aplica.
        
    Returns:
        True si la operación fue exitosa, False en caso contrario.
    """
    if not new_title and not new_topic:
        logger.warning(f"Se llamó a update_document_metadata para '{file_name}' sin nuevos datos para actualizar.")
        return False

    logger.info(f"Actualizando metadatos para '{file_name}' (cuenta {account_id}) -> Título: {new_title}, Tema: {new_topic}")
    
    collection_name = f"user_memories_{account_id}" if not team_id else f"team_memories_{team_id}"

    async with DBSession(SessionLocal) as db:
        try:
            # 1. Obtener el ID de la colección para este usuario
            collection_stmt = select(langchain_pg_collection.c.uuid).where(langchain_pg_collection.c.name == collection_name)
            collection_id_result = await db.execute(collection_stmt)
            collection_id = collection_id_result.scalar_one_or_none()

            if not collection_id:
                logger.error(f"No se encontró la colección '{collection_name}' para actualizar metadatos.")
                return False

            # 2. Construir la actualización del JSONB
            # Empezamos con el cmetadata existente
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

            # Partimos del cmetadata actual y sobreescribimos los valores
            values_to_update = current_cmetadata.copy()
            if new_title is not None:
                values_to_update['title'] = new_title
            if new_topic is not None:
                values_to_update['topic'] = new_topic

            # 3. Construir y ejecutar la consulta de actualización
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
            
            # result.rowcount nos dice cuántas filas fueron afectadas
            if result.rowcount > 0:
                logger.info(f"✅ Se actualizaron {result.rowcount} chunks para el archivo '{file_name}'.")
                return True
            else:
                logger.warning(f"La consulta de actualización para '{file_name}' no afectó ninguna fila, aunque el documento fue encontrado.")
                return False

        except Exception as e:
            logger.error(f"❌ Error actualizando metadatos de '{file_name}': {e}", exc_info=True)
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
