# utils/vector_db_query.py

"""
Utilidad para realizar consultas a la base de datos vectorial mediante similitud semántica con embeddings.

Este módulo proporciona una función para buscar documentos o fragmentos de texto similares a una consulta dada,
utilizando embeddings y la base de datos vectorial configurada en el proyecto.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio
import numpy as np
from sqlalchemy import select
from langchain_postgres import PGVector
from core.config import settings
from utils.embeddings import get_embedding_model
from core.database import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import create_async_engine

async def query_vector_db(query: str, account_id: str, k: int = 5, collection_name: Optional[str] = None, topic: Optional[str] = None, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:    
    logger.info(f"Realizando consulta a la base de datos vectorial para el usuario {account_id} con consulta: '{query[:50]}...'")
    if settings.database_url is None:
        logger.error("DATABASE_URL no está configurada. No se puede conectar a la base de datos vectorial.")
        return []

    try:
        # Obtener el modelo de embeddings primero
        embedding_model = get_embedding_model()
        if not embedding_model:
            logger.error("No se pudo obtener el modelo de embeddings.")
            return []
        
        # Determinar el nombre de la colección a buscar
        if collection_name is None:
            collection_name = f"user_memories_{account_id}"
        
        # Construir el diccionario de filtros para los metadatos
        metadata_filter = {}
        if topic:
            metadata_filter["$topic"] = topic  # Usa prefijo $ para JSONB
        if workspace_id:
            metadata_filter["$workspace_id"] = workspace_id
        
        # Configurar el almacén vectorial utilizando el motor asíncrono del proyecto
        from core.database import engine
        vectorstore = PGVector(
            embeddings=embedding_model,
            collection_name=collection_name,
            connection=engine,
            use_jsonb=True
        )
        
        # Realizar la búsqueda por similitud
        results = await vectorstore.asimilarity_search_with_score(query, k=k, filter=metadata_filter if metadata_filter else None)
        if not results:
            logger.info(f"No se encontraron resultados similares para la consulta '{query[:50]}...' en la colección '{collection_name}'.")
            return []
        
        # Formatear los resultados con validación
        formatted_results = []
        for doc, score in results:
            if not hasattr(doc, 'page_content') or not doc.metadata:
                logger.warning(f"Resultado inválido encontrado: {doc}")
                continue
            result_data = {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": score
            }
            formatted_results.append(result_data)
        
        logger.info(f"Se encontraron {len(formatted_results)} resultados similares para la consulta en la colección '{collection_name}'.")
        return formatted_results
    
    except Exception as e:
        logger.error(f"Error al realizar la consulta a la base de datos vectorial para el usuario {account_id}: {e}", exc_info=True)
        return []
