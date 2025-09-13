import logging
from typing import List, Dict, Any, Optional
import asyncio
from core.memory_manager import get_relevant_memories

logger = logging.getLogger(__name__)

async def query_vector_db(query: str, account_id: str, k: int = 5, collection_name: Optional[str] = None, topic: Optional[str] = None, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
    logger.info(f"Realizando consulta a la base de datos vectorial para el usuario {account_id} con consulta: '{query[:50]}...'")
    try:
        results = await get_relevant_memories(
            account_id=account_id,
            query=query,
            k=k,
            filter_topics=[topic] if topic else None,
            workspace_id=workspace_id,
        )

        if not results or not results.sources:
            logger.info(f"No se encontraron resultados similares para la consulta '{query[:50]}...'")
            return []

        formatted_results = []
        for source in results.sources:
            result_data = {
                "content": source.snippet,
                "metadata": source.metadata,
                "similarity_score": source.metadata.get("similarity_score"),
            }
            formatted_results.append(result_data)

        logger.info(f"Se encontraron {len(formatted_results)} resultados similares para la consulta.")
        return formatted_results

    except Exception as e:
        logger.error(f"Error al realizar la consulta a la base de datos vectorial para el usuario {account_id}: {e}", exc_info=True)
        return []
