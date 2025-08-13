# tools/extract_document_titles_tool.py

"""
Herramienta de LangChain para extraer títulos de documentos y actualizar sus metadatos en la base de conocimiento de un usuario.

Esta herramienta permite al agente de IA procesar documentos almacenados y extraer títulos automáticamente, actualizando los metadatos correspondientes en la base de datos.
"""

import logging
import uuid
from typing import Type, Optional, Any

from pydantic.v1 import BaseModel, Field
from pydantic.v1.fields import FieldInfo
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

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class ExtractDocumentTitlesInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de extracción de títulos de documentos.
    Valida que el argumento necesario sea proporcionado por el LLM.
    """
    pass


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
    workspace_id: Optional[str] = Field(None, description="El ID del workspace actual, inyectado automáticamente.")
    telegram_id: Optional[str] = Field(None, description="El ID de usuario de Telegram del usuario, inyectado automáticamente.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación de Telegram, inyectado automáticamente.")
    topic: Optional[str] = Field(None, description="El tema o categoría de los documentos a procesar, inyectado automáticamente.")
    collection_id: Optional[str] = Field(None, description="El ID de la colección de documentos a procesar, inyectado automáticamente.")

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Síncrono: Esta herramienta solo soporta ejecución asíncrona."""
        raise NotImplementedError("ExtractDocumentTitlesTool solo soporta ejecución asíncrona. Usa _arun en su lugar.")

    async def _arun(self, **kwargs: Any) -> str:
        file_name = None # Inicializar file_name aquí
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        # Extraer topic y collection_id de kwargs o usar los atributos de la instancia.
        # Si son objetos FieldInfo (inyectados automáticamente), obtener su descripción.
        current_topic_val = kwargs.get("topic", self.topic)
        if isinstance(current_topic_val, FieldInfo):
            current_topic = current_topic_val.description if current_topic_val.description else None
        elif isinstance(current_topic_val, str):
            current_topic = current_topic_val
        else:
            current_topic = None
        
        current_collection_id_val = kwargs.get("collection_id", self.collection_id)
        if isinstance(current_collection_id_val, FieldInfo):
            current_collection_id = None # Si es FieldInfo, el valor no es un UUID válido.
        elif isinstance(current_collection_id_val, str):
            try:
                # Intentar convertir a UUID para validar
                uuid.UUID(current_collection_id_val)
                current_collection_id = current_collection_id_val
            except ValueError:
                current_collection_id = None # No es un UUID válido
        else:
            current_collection_id = None

        logger.info(f"Ejecutando ExtractDocumentTitlesTool para la cuenta '{self.account_id}' con tema: '{current_topic}', archivo: '{file_name}'.")
        try:
            if not settings.database_url:
                raise ValueError("Database URL is not configured")
                
            PGVECTOR_SYNC_ENGINE = create_engine(settings.database_url)
            metadata = MetaData()
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

                clauses = [
                    "account_id = :account_id",
                    "content_type = 'user_documents'", # Asumimos que siempre son user_documents
                    "cmetadata->>'type' = 'document_chunk'"
                ]
                params = {"account_id": self.account_id}

                # Añadir filtro por workspace_id si está disponible
                if self.workspace_id and isinstance(self.workspace_id, str) and self.workspace_id.strip():
                    try:
                        uuid.UUID(self.workspace_id)
                        clauses.append("workspace_id = :ws_id")
                        params["ws_id"] = self.workspace_id
                    except ValueError:
                        logger.warning(f"workspace_id '{self.workspace_id}' no es un UUID válido. Omitiendo filtro.")

                if current_topic:
                    clauses.append("topic = :tpc") # Usar directamente la columna 'topic'
                    params["tpc"] = current_topic
                # Eliminar el filtro por collection_id si se usa topic, o si collection_id es None
                if current_collection_id: # Este collection_id se refiere a 'user_documents' o 'user_memories'
                    clauses.append("collection_id = :col_id")
                    params["col_id"] = current_collection_id

                # CORREGIDO: Usar document_id en lugar de file_name para evitar pérdida de documentos
                select_sql = text("SELECT DISTINCT ON (cmetadata->>'document_id') * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses) + " ORDER BY cmetadata->>'document_id', id")
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
                        first_chunk_query_clauses = [
                            "account_id = :account_id",
                            "cmetadata->>'file_name' = :file_name",
                            "cmetadata->>'type' = 'document_chunk'"
                        ]
                        first_chunk_params = {
                            "account_id": self.account_id,
                            "file_name": file_name
                        }
                        # Añadir filtro por workspace_id si está disponible
                        if self.workspace_id and isinstance(self.workspace_id, str) and self.workspace_id.strip():
                            try:
                                uuid.UUID(self.workspace_id)
                                first_chunk_query_clauses.append("workspace_id = :ws_id")
                                first_chunk_params["ws_id"] = self.workspace_id
                            except ValueError:
                                logger.warning(f"workspace_id '{self.workspace_id}' no es un UUID válido. Omitiendo filtro.")

                        if current_topic:
                            first_chunk_query_clauses.append("topic = :tpc")
                            first_chunk_params["tpc"] = current_topic
                        # Solo añadir el filtro collection_id si se proporciona y no se usa topic
                        elif current_collection_id: # Este collection_id se refiere a 'user_documents' o 'user_memories'
                            first_chunk_query_clauses.append("collection_id = :col_id")
                            first_chunk_params["col_id"] = current_collection_id

                        first_chunk_query = text("SELECT document FROM langchain_pg_embedding WHERE " + " AND ".join(first_chunk_query_clauses) + " ORDER BY (cmetadata->>'chunk_index')::integer ASC LIMIT 3")
                        logger.info(f"Valores para first_chunk_query: {first_chunk_params}")
                        chunk_result = await db.execute(first_chunk_query, first_chunk_params)
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
                                logger.info(f"Enviando prompt al LLM para extracción de título:\n---\n{prompt}\n---")
                                response = await llm.ainvoke(prompt)
                                logger.info(f"Respuesta recibida del LLM: {response}")
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
                    
                    processed_count += 1
                    # Actualizar el progreso
                    await db.execute(text("""
                        UPDATE process_status
                        SET status = 'in_progress', progress = :progress, total = :total, message = :message, last_updated = CURRENT_TIMESTAMP
                        WHERE account_id = :account_id
                    """), {"account_id": self.account_id, "progress": processed_count, "total": total_docs, "message": f"Procesado {processed_count}/{total_docs} documentos."})
                    await db.commit()
                
                final_message = f"Proceso de extracción de títulos completado. Se actualizaron {updated_count} de {total_docs} documentos."
                await db.execute(text("""
                    UPDATE process_status
                    SET status = 'completed', message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": self.account_id, "message": final_message})
                await db.commit()
                return final_message

        except Exception as e:
            logger.error(f"Error inesperado en ExtractDocumentTitlesTool: {e}", exc_info=True)
            await send_personal_message(self.account_id, {
                "type": "error",
                "message": f"Ocurrió un error inesperado durante la extracción de títulos: {e}"
            })
            async with DBSession(SessionLocal) as db:
                await db.execute(text("""
                    UPDATE process_status
                    SET status = 'failed', message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": self.account_id, "message": f"Error inesperado: {e}"})
                await db.commit()
            return "Ocurrió un error inesperado durante la extracción de títulos."