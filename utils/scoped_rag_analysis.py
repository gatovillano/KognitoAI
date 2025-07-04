# utils/scoped_rag_analysis.py

"""
Utilidad para realizar un análisis RAG (Retrieval-Augmented Generation) 
profundo y focalizado sobre la base de conocimiento de un usuario.
"""

import logging
from typing import List, Optional
import uuid

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_community.vectorstores.pgvector import PGVector
from langchain.schema import Document

from core.database import SessionLocal, Nota
from core.llm_manager import get_fast_llm
from utils.embeddings import get_embedding_model
from core.config import settings
from langchain.schema.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

async def _get_notes_context(db: AsyncSession, account_uuid: uuid.UUID, topic: Optional[str], keywords: Optional[List[str]]) -> str:
    """Recupera y formatea el contexto de las notas."""
    stmt = select(Nota).where(Nota.account_id == account_uuid)
    
    if topic:
        stmt = stmt.where(Nota.category.ilike(f"%{topic}%"))
        
    if keywords:
        keyword_filters = [or_(Nota.content.ilike(f"%{kw}%"), Nota.title.ilike(f"%{kw}%")) for kw in keywords]
        stmt = stmt.where(or_(*keyword_filters))
        
    results = await db.execute(stmt.limit(15))
    notes = results.scalars().all()
    
    if not notes:
        return ""
        
    formatted_notes = "\n\n".join([
        f"Nota (Categoría: {n.category}):\n- Título: {n.title or 'Sin título'}\n- Contenido: {n.content[:500]}..."
        for n in notes
    ])
    return formatted_notes

async def _get_documents_context(
    account_uuid: uuid.UUID, 
    query: str,
    topic: Optional[str], 
    keywords: Optional[List[str]]
) -> str:
    """Recupera y formatea el contexto de los documentos usando búsqueda por similitud."""
    if not topic:
        return "Para buscar en documentos, es necesario especificar un 'topic' que corresponda a una colección."

    try:
        embedding_model = get_embedding_model()
        if not embedding_model:
            logger.error("Modelo de embedding no disponible.")
            return "Error: El servicio de búsqueda de documentos no está configurado."

        # La búsqueda se realiza sobre una colección específica (topic)
        store = PGVector(
            connection_string=settings.database_url,
            embedding_function=embedding_model,
            collection_name=topic,
        )
        
        search_query = query
        if keywords:
            search_query += " " + " ".join(keywords)

        # Realizar la búsqueda por similitud
        results: List[Document] = await store.asimilarity_search(search_query, k=10)

        if not results:
            return ""

        formatted_docs = "\n\n".join([
            f"Documento (Fuente: {doc.metadata.get('source', 'Desconocida')}):\n{doc.page_content[:700]}..."
            for doc in results
        ])
        return formatted_docs
    except Exception as e:
        logger.error(f"Error al realizar la búsqueda por similitud en la colección '{topic}': {e}", exc_info=True)
        return f"Error al buscar en la colección de documentos '{topic}'."


async def run_scoped_rag_analysis(
    account_id: str,
    query: str,
    content_types: List[str],
    analysis_goal: str,
    topic: Optional[str] = None,
    keywords: Optional[List[str]] = None
) -> str:
    """
    Ejecuta un análisis RAG profundo y focalizado.
    """
    logger.info(f"Iniciando análisis RAG focalizado para la cuenta {account_id} con el objetivo: '{analysis_goal}'")
    
    context_parts = []
    account_uuid = uuid.UUID(account_id)
    
    async with SessionLocal() as db:
        if "notes" in content_types:
            notes_context = await _get_notes_context(db, account_uuid, topic, keywords)
            if notes_context:
                context_parts.append("--- INICIO DE NOTAS RELEVANTES ---\n" + notes_context + "\n--- FIN DE NOTAS RELEVANTES ---")

    # La búsqueda de documentos se hace fuera de la sesión de DB principal
    if "documents" in content_types:
        docs_context = await _get_documents_context(account_uuid, query, topic, keywords)
        if docs_context:
            context_parts.append("--- INICIO DE DOCUMENTOS RELEVANTES ---\n" + docs_context + "\n--- FIN DE DOCUMENTOS RELEVANTES ---")

    if not context_parts:
        return "No se encontró información relevante para los criterios especificados. Por favor, ajusta los filtros o la consulta."

    full_context = "\n\n".join(context_parts)
    
    system_prompt = (
        "Eres un asistente de IA experto en análisis de información y síntesis. "
        "Tu tarea es analizar el contexto proporcionado para responder a la consulta del usuario. "
        "Debes estructurar tu respuesta final estrictamente de acuerdo con el 'objetivo del análisis' especificado."
    )
    
    user_prompt = (
        f"**Contexto de Información:**\n{full_context}\n\n"
        f"**Consulta del Usuario:**\n{query}\n\n"
        f"**Objetivo del Análisis (Formato de Respuesta Requerido):**\n{analysis_goal}"
    )

    try:
        llm = get_fast_llm()
        if not llm:
            logger.error("No se pudo obtener una instancia del LLM.")
            return "Error: El servicio de análisis no está disponible en este momento."
            
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.error(f"Error al invocar el LLM en run_scoped_rag_analysis: {e}", exc_info=True)
        return "Se produjo un error al generar el análisis. Por favor, inténtalo de nuevo."
