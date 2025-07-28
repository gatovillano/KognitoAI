# tools/extract_document_titles_tool.py

"""
Herramienta de LangChain para extraer títulos de documentos y actualizar sus metadatos en la base de conocimiento de un usuario.

Esta herramienta permite al agente de IA procesar documentos almacenados y extraer títulos automáticamente, actualizando los metadatos correspondientes en la base de datos.
"""

import logging
from typing import Type, Optional, Any

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa las dependencias necesarias para interactuar con la base de datos y el LLM.
from core.database import SessionLocal
from utils.db_session import DBSession
from sqlalchemy import select, update, text, Table, MetaData
from core.config import settings
from sqlalchemy import create_engine
from core.memory_manager import update_document_metadata, get_full_document_content
from core.llm_manager import get_fast_llm
from core.websocket_manager import send_personal_message
import logging
from typing import Optional, Any, Type
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class ExtractDocumentTitlesInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de extracción de títulos de documentos.
    Valida que el argumento necesario sea proporcionado por el LLM.
    """
    topic: Optional[str] = Field(
        None,
        description="El tema o categoría de los documentos a procesar. Si no se proporciona, se procesarán todos los documentos del usuario."
    )


class ExtractDocumentTitlesTool(BaseTool):
    """
    Una herramienta de LangChain que extrae títulos de documentos y actualiza sus metadatos en la base de datos vectorial.
    Los metadatos, como el título, se almacenan en el campo 'cmetadata' de la tabla 'langchain_pg_embedding',
    que es parte de la integración con LangChain y PGVector.
    """
    name: str = "extract_document_titles_tool"
    description: str = (
        "Útil para extraer títulos de documentos y actualizar sus metadatos en la base de conocimiento del usuario. "
        "Esta herramienta procesa los documentos almacenados y actualiza automáticamente los títulos en los metadatos. "
        "Los metadatos se almacenan en el campo 'cmetadata' de la tabla 'langchain_pg_embedding', parte de la integración "
        "con LangChain y PGVector, permitiendo almacenar información estructurada junto con los embeddings vectoriales."
    )
    args_schema: Type[BaseModel] = ExtractDocumentTitlesInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(self, topic: Optional[str] = None, file_name: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            topic: El tema de los documentos a procesar (opcional).
            file_name: El nombre del archivo específico a procesar (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando ExtractDocumentTitlesTool para la cuenta '{self.account_id}' con tema: '{topic}', archivo: '{file_name}'.")
        try:
<<<<<<< HEAD
            if not settings.database_url:
                raise ValueError("Database URL is not configured")
                
=======
            # Engine síncrono para conectar con la base de datos
>>>>>>> parent of 9cadb85 (Refactor UI, enhance RAG capabilities, and improve tool functionalities)
            PGVECTOR_SYNC_ENGINE = create_engine(settings.database_url)
            metadata = MetaData()
            langchain_pg_collection = Table('langchain_pg_collection', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)
            langchain_pg_embedding = Table('langchain_pg_embedding', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)

            async with DBSession(SessionLocal) as db:
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS process_status (
                        account_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        progress INTEGER NOT NULL DEFAULT 0,
                        total INTEGER NOT NULL DEFAULT 0,
                        message TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await db.commit()

                await db.execute(text("""
                    INSERT INTO process_status (account_id, status, progress, total, message)
                    VALUES (:account_id, 'in_progress', 0, 0, 'Iniciando proceso de extracción de títulos...')
                    ON CONFLICT (account_id) DO UPDATE
                    SET status = 'in_progress', progress = 0, total = 0, message = 'Iniciando proceso de extracción de títulos...', last_updated = CURRENT_TIMESTAMP
                """), {"account_id": self.account_id})
                await db.commit()

<<<<<<< HEAD
                clauses = [
                    "account_id = :account_id",
                    "content_type = 'user_documents'",
                    "cmetadata->>'type' = 'document_chunk'"
                ]
                params = {"account_id": self.account_id}
=======
                # Obtener el UUID de la colección para el usuario
                col_q = text("SELECT uuid FROM langchain_pg_collection WHERE name = :cname")
                res = await db.execute(col_q, {"cname": f"user_memories_{account_id}"})
                collection_uuid = res.scalar_one_or_none()
                if not collection_uuid:
                    logger.info(f"No existe la colección 'user_memories_{account_id}', no hay documentos para procesar.")
                    await db.execute(text("""
                        UPDATE process_status
                        SET status = 'completed', message = 'No se encontraron documentos para procesar en tu base de conocimiento.', last_updated = CURRENT_TIMESTAMP
                        WHERE account_id = :account_id
                    """), {"account_id": account_id})
                    await db.commit()
                    return "No se encontraron documentos para procesar en tu base de conocimiento."
>>>>>>> parent of 9cadb85 (Refactor UI, enhance RAG capabilities, and improve tool functionalities)

                # Construir la consulta para obtener los documentos
                clauses = ["collection_id = :col_id", "cmetadata->>'type' = 'document_chunk'"]
                params = {"col_id": collection_uuid}
                if topic:
                    clauses.append("cmetadata->>'topic' = :tpc")
                    params["tpc"] = topic
                if file_name:
                    clauses.append("cmetadata->>'file_name' = :fname")
                    params["fname"] = file_name

<<<<<<< HEAD
                # CORREGIDO: Usar document_id en lugar de file_name para evitar pérdida de documentos
                select_sql = text("SELECT DISTINCT ON (cmetadata->>'document_id') * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses) + " ORDER BY cmetadata->>'document_id', id")
=======
                select_sql = text("SELECT DISTINCT ON (cmetadata->>'file_name') * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses))
>>>>>>> parent of 9cadb85 (Refactor UI, enhance RAG capabilities, and improve tool functionalities)
                logger.info(f"Ejecutando consulta SQL: {select_sql} con parámetros: {params}")
                result = await db.execute(select_sql, params)
                chunks = result.mappings().all()
                logger.info(f"Se encontraron {len(chunks)} documentos únicos para procesar.")

                if not chunks:
                    logger.info("No se encontraron documentos para procesar.")
                    message = f"No se encontraron documentos para procesar en tu base de conocimiento. {'Archivo no encontrado: ' + file_name if file_name else ''}"
                    await db.execute(text("""
                        UPDATE process_status
                        SET status = 'completed', message = :message, last_updated = CURRENT_TIMESTAMP
                        WHERE account_id = :account_id
                    """), {"account_id": self.account_id, "message": message})
                    await db.commit()
                    return message

                await send_personal_message(self.account_id, {
                    "type": "title_extraction_started",
                    "total_documents": len(chunks),
                    "message": f"Iniciando extracción de títulos para {len(chunks)} documento(s)..."
                })

                # Actualizar el total de documentos a procesar
                total_docs = len(chunks)
                message = f"Procesando {'documento ' + file_name if file_name else 'documentos...'}"
                await db.execute(text("""
                    UPDATE process_status
                    SET total = :total, message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": self.account_id, "total": total_docs, "message": message})
                await db.commit()

                updated_count = 0
                processed_count = 0
                # Obtener el LLM rápido para la extracción de títulos
                llm = get_fast_llm()
                if not llm:
                    logger.error("No hay LLM disponible para extraer títulos.")
                    await db.execute(text("""
                        UPDATE process_status
                        SET status = 'error', message = 'LLM no disponible para extracción de títulos.', last_updated = CURRENT_TIMESTAMP
                        WHERE account_id = :account_id
                    """), {"account_id": self.account_id})
                    await db.commit()
                    raise ValueError("LLM no disponible para extracción de títulos.")
                for chunk in chunks:
                    file_name = chunk['cmetadata'].get('file_name')
                    if file_name:
                        # Obtener solo el primer fragmento del documento para mayor eficiencia
                        first_chunk_query = text("""
                            SELECT document
                            FROM langchain_pg_embedding
                            WHERE collection_id = :col_id
                            AND cmetadata->>'file_name' = :file_name
                            AND cmetadata->>'type' = 'document_chunk'
                            ORDER BY (cmetadata->>'chunk_index')::integer ASC
                            LIMIT 3
                        """)
<<<<<<< HEAD
                        chunk_result = await db.execute(first_chunk_query, {"account_id": self.account_id, "file_name": file_name})
=======
                        chunk_result = await db.execute(first_chunk_query, {"col_id": collection_uuid, "file_name": file_name})
>>>>>>> parent of 9cadb85 (Refactor UI, enhance RAG capabilities, and improve tool functionalities)
                        first_chunk = chunk_result.mappings().first()
                        
                        if first_chunk and 'document' in first_chunk:
                            content = first_chunk['document']
                            # Usar el contenido del primer fragmento para el LLM
                            prompt = (
                                "Analiza el siguiente fragmento de un documento y extrae el título más probable. "
                                "Un título suele ser una frase corta y descriptiva al inicio del documento,  que puede ser similar al títuloi del documento"
                                "a menudo en formato de encabezado, negrita o mayúsculas. Pero no siempre es así. Considera que los documentos vectorizados pierden su formato original. Por tanto busca analiticamente cual podría ser su título"
                                "Devuelve solo el título, sin explicaciones ni texto adicional. "
                                "Si no encuentras un título claro, devuelve 'Sin título'. "
                                f"\n\nFragmento:\n{content}"
                            )
                            try:
                                response = await llm.ainvoke(prompt)
                                # Extraer el contenido de texto del objeto AIMessage
                                potential_title = response.content if hasattr(response, 'content') else str(response)
                                potential_title = potential_title.strip()
                                if potential_title and potential_title != 'Sin título' and len(potential_title) > 5 and len(potential_title) < 250:
                                    logger.info(f"Título extraído por LLM para {file_name}: {potential_title}")
                                    success = await update_document_metadata(self.account_id, file_name, new_title=potential_title, new_topic=None)
                                    if success:
                                        updated_count += 1
                                        logger.info(f"Actualizado título para el documento {file_name}.")

                                        await send_personal_message(self.account_id, {
                                            "type": "title_updated",
                                            "file_name": file_name,
                                            "new_title": potential_title,
                                            "progress": processed_count,
                                            "total": total_docs
                                        })
                                    else:
                                        logger.warning(f"No se pudo actualizar el título para el documento {file_name}.")
                                else:
                                    logger.info(f"No se encontró un título válido por LLM para {file_name}: {potential_title}")
                            except Exception as e:
                                logger.error(f"Error al usar LLM para extraer título de {file_name}: {e}")
                                # Respaldo: Usar la primera línea no vacía si el LLM falla
                                lines = content.split('\n')[:5]
                                potential_title = None
                                for line in lines:
                                    if line.strip():
                                        potential_title = line.strip()
                                        break
                                if potential_title and len(potential_title) > 5 and len(potential_title) < 250:
                                    logger.info(f"Título de respaldo extraído para {file_name}: {potential_title}")
                                    success = await update_document_metadata(self.account_id, file_name, new_title=potential_title, new_topic=None)
                                    if success:
                                        updated_count += 1
                                        logger.info(f"Actualizado título de respaldo para el documento {file_name}.")

                                        await send_personal_message(self.account_id, {
                                            "type": "title_updated",
                                            "file_name": file_name,
                                            "new_title": potential_title,
                                            "progress": processed_count,
                                            "total": total_docs
                                        })
                                    else:
                                        logger.warning(f"No se pudo actualizar el título de respaldo para el documento {file_name}.")
                                else:
                                    logger.info(f"No se encontró un título de respaldo válido para {file_name}.")
                        else:
                            logger.warning(f"No se pudo obtener el primer fragmento del documento {file_name}.")
                    else:
                        logger.warning(f"Fragmento sin 'file_name' en cmetadata: {chunk['cmetadata']}")
                    
                    processed_count += 1
                    # Actualizar el progreso
                    await db.execute(text("""
                        UPDATE process_status
                        SET progress = :progress, message = :message, last_updated = CURRENT_TIMESTAMP
                        WHERE account_id = :account_id
                    """), {"account_id": self.account_id, "progress": processed_count, "message": f"Procesando documento {processed_count} de {total_docs}..."})
                    await db.commit()

                if updated_count > 0:
                    logger.info(f"Se actualizaron los títulos de {updated_count} documentos para la cuenta {self.account_id}.")
                    final_message = f"Se han procesado y actualizado los títulos de {updated_count} {'documento' if file_name else 'documentos'} en tu base de conocimiento."
                else:
                    logger.info(f"No se encontraron títulos para actualizar en los documentos de la cuenta {self.account_id}.")
                    final_message = f"No se encontraron títulos para actualizar en {'el documento ' + file_name if file_name else 'los documentos de tu base de conocimiento'}."
                
                await db.execute(text("""
                    UPDATE process_status
                    SET status = 'completed', progress = :progress, message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": self.account_id, "progress": processed_count, "message": final_message})
                await db.commit()

                await send_personal_message(self.account_id, {
                    "type": "title_extraction_completed",
                    "updated_count": updated_count,
                    "total_processed": processed_count,
                    "message": final_message
                })

                return final_message
        except Exception as e:
            logger.error(f"Error en ExtractDocumentTitlesTool para la cuenta '{self.account_id}': {e}", exc_info=True)
            async with DBSession(SessionLocal) as db:
                await db.execute(text("""
                    UPDATE process_status
                    SET status = 'error', message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": self.account_id, "message": f"Ocurrió un error inesperado: {str(e)}"})
                await db.commit()
            return f"Ocurrió un error inesperado al intentar extraer y actualizar los títulos de los documentos: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("extract_document_titles_tool no soporta ejecución síncrona.")
