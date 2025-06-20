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
VertexAIEmbeddings de Google para unificar el stack tecnológico.
"""

import logging
import asyncio
from sqlalchemy import select, text
from typing import Optional, List, Union, Dict, Any
import datetime

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.database import Perfil, SessionLocal, Account
from utils.db_session import DBSession
from utils.embeddings import initialize_embeddings
from core.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap
GLOBAL_COLLECTION_NAME = "global_knowledge_base"


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
                logger.warning(f"No se encontró perfil para la cuenta ID: {account_id}. Creando uno nuevo.")
                account = await db.get(Account, account_id)
                if account:
                    perfil = Perfil(account_id=account_id)
                    db.add(perfil)
                    await db.commit()
                    await db.refresh(perfil)
                    logger.info(f"✅ Perfil vacío creado para la cuenta ID: {account_id}.")
                else:
                    logger.error(f"❌ No se puede crear perfil porque la cuenta ID {account_id} no existe.")
                    return None
            return perfil
        except Exception as e:
            logger.error(f"❌ Error al obtener/crear perfil para la cuenta ID {account_id}: {e}", exc_info=True)
            await db.rollback()
            return None


async def update_user_profile(account_id: str, nombre: Optional[str] = None, gustos: Optional[str] = None, intereses: Optional[str] = None, otros_datos: Optional[str] = None):
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
            # get_user_profile se encarga de crear el perfil si no existe.
            perfil = await get_user_profile(account_id)
            if not perfil:
                logger.error(f"❌ No se pudo obtener o crear un perfil para la cuenta {account_id}. No se puede actualizar.")
                return
            
            db.add(perfil)
            if nombre is not None: perfil.nombre = nombre
            if gustos is not None: perfil.gustos = gustos
            if intereses is not None: perfil.intereses = intereses
            if otros_datos is not None: perfil.otros_datos = otros_datos
            
            await db.commit()
            logger.info(f"✅ Perfil de la cuenta ID {account_id} actualizado exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error al actualizar el perfil de la cuenta ID {account_id}: {e}", exc_info=True)
            await db.rollback()


async def add_memory_to_vector_db(account_id: str, content: str, type: str = "general_memory") -> None:
    """
    Genera embeddings para el contenido y lo guarda en la DB vectorial del usuario.

    Args:
        account_id: El ID universal de la cuenta a la que pertenece la memoria.
        content: El texto de la memoria a guardar.
        type: El tipo de memoria (ej: 'fact', 'idea').
    """
    logger.info(f"Añadiendo memoria a la DB vectorial para la cuenta {account_id}: '{content[:50]}...'")
    try:
        embeddings: Embeddings = initialize_embeddings()
        if not embeddings:
            logger.error("Los Embeddings no están inicializados. No se puede añadir memoria.")
            return

        collection_name = f"user_memories_{account_id}"
        vectorstore = PGVector(
            collection_name=collection_name,
            embeddings=embeddings,
            connection_string=settings.database_url,
            create_extension=False
        )
        
        metadata = {"account_id": str(account_id), "type": type}
        await vectorstore.aadd_documents(documents=[Document(page_content=content, metadata=metadata)])
        logger.info(f"✅ Memoria añadida a la base de datos vectorial de la cuenta {account_id}.")
    except Exception as e:
        logger.error(f"❌ Error al añadir memoria a la DB vectorial para la cuenta {account_id}: {e}", exc_info=True)


async def get_relevant_memories(account_id: str, query: str, k: int = 10, metadata_filters: Optional[Dict[str, Any]] = None) -> str:
    """
    Recupera memorias relevantes de la colección personal del usuario y de la global.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        query: La consulta del usuario para buscar memorias similares.
        k: El número total de memorias a recuperar.
        metadata_filters: Filtros adicionales para aplicar a la búsqueda.

    Returns:
        Una cadena de texto formateada con las memorias relevantes encontradas.
    """
    logger.info(f"Buscando memorias relevantes para la cuenta {account_id} con la consulta: '{query[:50]}...'")
    try:
        embeddings: Embeddings = initialize_embeddings()
        if not embeddings:
            return "Error: El modelo de memoria no está disponible."

        user_vectorstore = PGVector(
            collection_name=f"user_memories_{account_id}",
            embeddings=embeddings,
            connection_string=settings.database_url,
            create_extension=False
        )
        global_vectorstore = PGVector(
            collection_name=GLOBAL_COLLECTION_NAME,
            embeddings=embeddings,
            connection_string=settings.database_url,
            create_extension=False
        )

        k_per_source = k // 2 if k > 1 else 1
        filters = metadata_filters if metadata_filters else {}

        user_search_task = user_vectorstore.asimilarity_search(query, k=k_per_source, filter=filters)
        global_search_task = global_vectorstore.asimilarity_search(query, k=k_per_source, filter=filters)
        
        user_results, global_results = await asyncio.gather(user_search_task, global_search_task, return_exceptions=True)
        
        all_docs = []
        if isinstance(user_results, list):
            for doc in user_results: doc.metadata['source'] = 'Personal'
            all_docs.extend(user_results)
        else:
            logger.warning(f"⚠️ No se pudo buscar en la memoria personal de la cuenta {account_id}: {user_results}")

        if isinstance(global_results, list):
            for doc in global_results: doc.metadata['source'] = 'Global'
            all_docs.extend(global_results)
        else:
            logger.warning(f"⚠️ No se pudo buscar en la memoria global: {global_results}")

        if not all_docs:
            return "No se encontraron memorias relevantes."

        memories_list = [f"- [Fuente: {d.metadata.get('source', 'N/A')}] (Tema: {d.metadata.get('topic', 'N/A')}): {d.page_content}" for d in all_docs]
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
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Divide, embebe y almacena el texto de un documento en la DB vectorial.

    Args:
        file_name: El nombre del archivo original.
        extracted_text: El texto extraído del documento.
        topic: La categoría del documento.
        account_id: El ID universal de la cuenta del usuario (si no es global).
        is_global: Si es True, el documento se guarda en la colección global.
        metadata: Metadatos adicionales sobre el documento.

    Returns:
        El número de fragmentos (chunks) añadidos a la base de datos.
    """
    if is_global:
        collection_name = GLOBAL_COLLECTION_NAME
    elif account_id:
        collection_name = f"user_memories_{account_id}"
    else:
        logger.error("❌ process_document_for_rag llamado sin account_id y sin is_global=True.")
        return 0

    logger.info(f"📊 Iniciando procesamiento RAG para '{file_name}' en la colección '{collection_name}'.")
    if not extracted_text:
        return 0

    try:
        embeddings = initialize_embeddings()
        if not embeddings:
            logger.error("Los Embeddings no están inicializados. No se puede procesar el documento.")
            return 0

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        texts = text_splitter.split_text(extracted_text)
        
        base_metadata = metadata if metadata else {}
        base_metadata.update({
            "file_name": file_name,
            "topic": topic,
            "type": "document_chunk",
            "scope": "global" if is_global else "personal"
        })
        if account_id and not is_global:
            base_metadata["account_id"] = str(account_id)

        lc_documents = []
        for i, text in enumerate(texts):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            # Asegurar que todos los valores de metadatos sean serializables
            for k, v in chunk_metadata.items():
                if isinstance(v, (datetime.datetime, datetime.date)):
                    chunk_metadata[k] = v.isoformat()
            lc_documents.append(Document(page_content=text, metadata=chunk_metadata))

        vectorstore = PGVector(
            collection_name=collection_name,
            embeddings=embeddings,
            connection_string=settings.database_url,
            create_extension=False
        )
        await vectorstore.aadd_documents(documents=lc_documents)
        
        logger.info(f"✅ Añadidos {len(lc_documents)} chunks a la colección '{collection_name}'.")
        return len(lc_documents)
    except Exception as e:
        logger.error(f"❌ Error durante el procesamiento RAG para '{file_name}': {e}", exc_info=True)
        return 0


async def delete_document_chunks(account_id: str, file_name: Optional[str] = None, topic: Optional[str] = None) -> int:
    """
    Elimina los fragmentos de un documento de la base de datos vectorial del usuario.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a eliminar (opcional).
        topic: El tema de los documentos a eliminar (opcional).

    Returns:
        Un entero (1 si tuvo éxito, 0 si no).
    """
    logger.info(f"🗑️ Intentando eliminar chunks para la cuenta {account_id} (Archivo: '{file_name}', Tema: '{topic}')")
    if not file_name and not topic:
        return 0
    try:
        embeddings = initialize_embeddings()
        if not embeddings:
            return 0
            
        vectorstore = PGVector(
            collection_name=f"user_memories_{account_id}",
            embeddings=embeddings,
            connection_string=settings.database_url,
            create_extension=False
        )
        
        delete_filters = {"type": "document_chunk"}
        if file_name:
            delete_filters["file_name"] = file_name
        if topic:
            delete_filters["topic"] = topic
            
        await vectorstore.adelete(filter=delete_filters)
        logger.info(f"✅ Operación de borrado completada para la cuenta {account_id}.")
        return 1
    except Exception as e:
        logger.error(f"❌ Error eliminando chunks para la cuenta {account_id}: {e}", exc_info=True)
        return 0


async def get_full_document_content(account_id: str, file_name: str) -> Optional[str]:
    """
    Reconstruye y devuelve el contenido completo de un documento desde sus chunks.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        file_name: El nombre del archivo a reconstruir.

    Returns:
        El contenido completo del documento como una cadena, o None si no se encuentra.
    """
    logger.info(f"Recuperando contenido completo de '{file_name}' para la cuenta {account_id}")
    try:
        embeddings: Embeddings = initialize_embeddings()
        if not embeddings:
            return None
            
        vectorstore = PGVector(
            collection_name=f"user_memories_{account_id}",
            embeddings=embeddings,
            connection_string=settings.database_url,
            create_extension=False
        )
        
        retrieved_docs = await vectorstore.asimilarity_search(
            query=" ", k=1000, filter={"file_name": file_name, "type": "document_chunk"}
        )
        
        if not retrieved_docs:
            return None
            
        sorted_chunks = sorted(retrieved_docs, key=lambda d: d.metadata.get('chunk_index', 0))
        full_content = "".join([doc.page_content for doc in sorted_chunks])
        
        logger.info(f"✅ Reconstruido documento '{file_name}'. Longitud: {len(full_content)} chars.")
        return full_content
    except Exception as e:
        logger.error(f"❌ Error recuperando contenido de '{file_name}': {e}", exc_info=True)
        return None


async def list_user_documents(account_id: str) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todos los documentos únicos subidos por un usuario.

    Args:
        account_id: El ID universal de la cuenta del usuario.

    Returns:
        Una lista de diccionarios, donde cada diccionario representa un documento.
    """
    logger.info(f"Listando documentos para la cuenta {account_id}")
    try:
        collection_name = f"user_memories_{account_id}"
        async with DBSession(SessionLocal) as db:
            collection_id_query = text("SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name")
            collection_result = await db.execute(collection_id_query, {"collection_name": collection_name})
            collection_uuid = collection_result.scalar_one_or_none()
            
            if not collection_uuid:
                return []

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
            document_list_result = await db.execute(document_list_query, {"collection_uuid": collection_uuid})
            documents = [dict(row) for row in document_list_result.mappings()]
            
            logger.info(f"✅ Listados {len(documents)} documentos para la cuenta {account_id}.")
            return documents
    except Exception as e:
        logger.error(f"❌ Error listando documentos para la cuenta {account_id}: {e}", exc_info=True)
        return []