# tools/internal_knowledge_search_tool.py

"""
Herramienta unificada para buscar en la base de conocimiento interna del usuario.
"""

import logging
import json
import re
from typing import Any, Optional, Type, Dict
from datetime import datetime

from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from core.memory_manager import get_relevant_memories

logger = logging.getLogger(__name__)

_interpreter_llm: Optional[ChatGoogleGenerativeAI] = None

async def get_interpreter_llm() -> ChatGoogleGenerativeAI:
    global _interpreter_llm
    if _interpreter_llm is None:
        logger.info("🧠 Inicializando LLM para interpretación de consultas...")
        _interpreter_llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.0,
            disable_streaming=True
        )
    return _interpreter_llm

class InternalKnowledgeSearchInput(BaseModel):
    """Input schema para la búsqueda de conocimiento interno."""
    query: str = Field(
        ...,
        description="La consulta completa del usuario en lenguaje natural."
    )

class InternalKnowledgeSearchTool(BaseTool):
    name: str = "internal_knowledge_search"
    description: str = (
        "CUÁNDO USAR: Cuando necesites buscar en la base de conocimiento INTERNA del usuario. "
        "Esto incluye sus notas, documentos, conversaciones pasadas y cualquier otro dato que haya guardado. "
        "Es la herramienta principal para responder preguntas basadas en la información personal del usuario."
    )
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace actual, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")
    args_schema: Type[BaseModel] = InternalKnowledgeSearchInput
    return_direct: bool = False

    async def _interpret_query(self, query: str) -> Dict[str, Any]:
        llm = await get_interpreter_llm()
        current_date = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
Eres un experto en interpretar consultas de búsqueda en lenguaje natural.
Analiza la consulta del usuario y extrae los parámetros estructurados para buscar en una base de datos vectorial.

CONSULTA: "{query}"
FECHA ACTUAL: {current_date}

PARÁMETROS A EXTRAER:
1. content_type: "user_memories" (para notas/conversaciones) o "user_documents" (para archivos/PDFs) o null (si no se especifica).
2. topic: Un tema organizacional (ej: "proyecto_hydra", "trabajo") o null.
3. category: Una categoría específica (ej: "technical", "meeting", "idea") o null.
4. search_terms: Los términos clave de la consulta para la búsqueda vectorial.
5. k: Número de resultados a devolver (default 15).

Responde SOLO en formato JSON válido.
"""
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content
            json_match = re.search(r'\{.*\}', str(content), re.DOTALL)
            if json_match:
                content = json_match.group(0)
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error interpretando consulta: {e}", exc_info=True)
            return {"search_terms": query, "k": 15}

    async def _arun(self, query: str, **kwargs: Any) -> str:
        try:
            logger.info(f"🔍 Ejecutando búsqueda interna para: '{query[:100]}...' ")
            interpretation = await self._interpret_query(query)
            
            search_terms = interpretation.get("search_terms", query)
            k = interpretation.get("k", 15)
            
            results = await get_relevant_memories(
                account_id=self.account_id,
                query=search_terms,
                content_type=interpretation.get("content_type"),
                filter_topics=[interpretation.get("topic")] if interpretation.get("topic") else None,
                category=interpretation.get("category"),
                workspace_id=self.workspace_id,
                k=k
            )
            
            if not results or not results.sources:
                return f"No se encontró información relevante para: '{query}'."

            formatted_results = []
            for source in results.sources:
                source_name = source.title or source.file_path or "memoria"
                formatted_results.append(f"- Fuente: {source_name}\n  Contenido: {source.snippet[:500]}...")
            
            return f"Se encontraron {len(results.sources)} resultados en tu base de conocimiento:\n\n" + "\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Error en InternalKnowledgeSearchTool: {e}", exc_info=True)
            return f"Error al procesar la búsqueda interna: {str(e)}"

    def _run(self, *args, **kwargs) -> str:
        import asyncio
        return asyncio.run(self._arun(*args, **kwargs))