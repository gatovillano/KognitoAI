# tools/extract_document_titles_tool.py

"""
Herramienta de LangChain para extraer títulos de documentos y actualizar sus metadatos en la base de conocimiento de un usuario.

Esta herramienta permite al agente de IA procesar documentos almacenados y extraer títulos automáticamente, actualizando los metadatos correspondientes en la base de datos.
"""

import logging
from typing import Type, Optional, Any

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa las dependencias necesarias para interactuar con la base de datos y el LLM.
from core.database import SessionLocal
from utils.db_session import DBSession
from sqlalchemy import select, update, text, Table, MetaData
from core.config import settings
from sqlalchemy import create_engine
from core.memory_manager import update_document_metadata, get_full_document_content
from core.llm_manager import get_fast_llm
import logging


# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class ExtractDocumentTitlesInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de extracción de títulos de documentos.
    Valida que el argumento necesario sea proporcionado por el LLM.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    topic: Optional[str] = Field(
        None,
        description="El tema o categoría de los documentos a procesar. Si no se proporciona, se procesarán todos los documentos del usuario.",
        json_schema_extra={"type": "string"}
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
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, run_manager=None, topic: Optional[str]=None, file_name: Optional[str]=None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            topic: El tema de los documentos a procesar (opcional).
            file_name: El nombre del archivo específico a procesar (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
                # Obtener account_id del contexto de configuración o instancia
        account_id = None
        account_id_source = "unknown"
        
        # Intentar obtener del contexto del run_manager
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
            if account_id:
                account_id_source = "run_manager.config.configurable"
        
        # Fallback: obtener de la instancia
        if not account_id:
            account_id = getattr(self, 'account_id', "")
            if account_id:
                account_id_source = "self.account_id"

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

logger.info(f"Ejecutando ExtractDocumentTitlesTool para la cuenta '{account_id}' con tema: '{topic}', archivo: '{file_name}'.")
        try:
            if not settings.database_url:
                raise ValueError("Database URL is not configured")
                
            # Engine síncrono para conectar con la base de datos
            PGVECTOR_SYNC_ENGINE = create_engine(settings.database_url)
            metadata = MetaData()
            langchain_pg_collection = Table('langchain_pg_collection', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)
            langchain_pg_embedding = Table('langchain_pg_embedding', metadata, autoload_with=PGVECTOR_SYNC_ENGINE)

            # Crear una tabla temporal para almacenar el estado del proceso si no existe
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

                # Inicializar el estado del proceso
                await db.execute(text("""
                    INSERT INTO process_status (account_id, status, progress, total, message)
                    VALUES (:account_id, 'in_progress', 0, 0, 'Iniciando proceso de extracción de títulos...')
                    ON CONFLICT (account_id) DO UPDATE
                    SET status = 'in_progress', progress = 0, total = 0, message = 'Iniciando proceso de extracción de títulos...', last_updated = CURRENT_TIMESTAMP
                """), {"account_id": account_id})
                await db.commit()

                # Construir la consulta optimizada usando las nuevas columnas directamente
                clauses = [
                    "account_id = :account_id",
                    "content_type = 'user_documents'",
                    "cmetadata->>'type' = 'document_chunk'"
                ]
                params = {"account_id": account_id}

                if topic:
                    clauses.append("topic = :topic")
                    params["topic"] = topic
                if file_name:
                    clauses.append("cmetadata->>'file_name' = :fname")
                    params["fname"] = file_name

                select_sql = text("SELECT DISTINCT ON (cmetadata->>'file_name') * FROM langchain_pg_embedding WHERE " + " AND ".join(clauses) + " ORDER BY cmetadata->>'file_name', id")
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
                    """), {"account_id": account_id, "message": message})
                    await db.commit()
                    return message

                # Actualizar el total de documentos a procesar
                total_docs = len(chunks)
                message = f"Procesando {'documento ' + file_name if file_name else 'documentos...'}"
                await db.execute(text("""
                    UPDATE process_status
                    SET total = :total, message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": account_id, "total": total_docs, "message": message})
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
                    """), {"account_id": account_id})
                    await db.commit()
                    raise ValueError("LLM no disponible para extracción de títulos.")
                for chunk in chunks:
                    file_name = chunk['cmetadata'].get('file_name')
                    if file_name:
                        # Obtener solo el primer fragmento del documento para mayor eficiencia
                        first_chunk_query = text("""
                            SELECT document
                            FROM langchain_pg_embedding
                            WHERE account_id = :account_id
                            AND content_type = 'user_documents'
                            AND cmetadata->>'file_name' = :file_name
                            AND cmetadata->>'type' = 'document_chunk'
                            ORDER BY (cmetadata->>'chunk_index')::integer ASC
                            LIMIT 3
                        """)
                        chunk_result = await db.execute(first_chunk_query, {"account_id": account_id, "file_name": file_name})
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
                                    success = await update_document_metadata(account_id, file_name, new_title=potential_title, new_topic=None)
                                    if success:
                                        updated_count += 1
                                        logger.info(f"Actualizado título para el documento {file_name}.")
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
                                    success = await update_document_metadata(account_id, file_name, new_title=potential_title, new_topic=None)
                                    if success:
                                        updated_count += 1
                                        logger.info(f"Actualizado título de respaldo para el documento {file_name}.")
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
                    """), {"account_id": account_id, "progress": processed_count, "message": f"Procesando documento {processed_count} de {total_docs}..."})
                    await db.commit()

                if updated_count > 0:
                    logger.info(f"Se actualizaron los títulos de {updated_count} documentos para la cuenta {account_id}.")
                    final_message = f"Se han procesado y actualizado los títulos de {updated_count} {'documento' if file_name else 'documentos'} en tu base de conocimiento."
                else:
                    logger.info(f"No se encontraron títulos para actualizar en los documentos de la cuenta {account_id}.")
                    final_message = f"No se encontraron títulos para actualizar en {'el documento ' + file_name if file_name else 'los documentos de tu base de conocimiento'}."
                
                await db.execute(text("""
                    UPDATE process_status
                    SET status = 'completed', progress = :progress, message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": account_id, "progress": processed_count, "message": final_message})
                await db.commit()
                return final_message
        except Exception as e:
            logger.error(f"Error en ExtractDocumentTitlesTool para la cuenta '{account_id}': {e}", exc_info=True)
            async with DBSession(SessionLocal) as db:
                await db.execute(text("""
                    UPDATE process_status
                    SET status = 'error', message = :message, last_updated = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id
                """), {"account_id": account_id, "message": f"Ocurrió un error inesperado: {str(e)}"})
                await db.commit()
            return f"Ocurrió un error inesperado al intentar extraer y actualizar los títulos de los documentos: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("extract_document_titles_tool no soporta ejecución síncrona.")
