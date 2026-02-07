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
from pydantic import BaseModel, Field
from core.llm_manager import get_llm_for_user
from core.memory_manager import get_relevant_memories

logger = logging.getLogger(__name__)

async def get_interpreter_llm(account_id: str) -> Any:
    """Obtiene el modelo de interpretación para el usuario."""
    logger.info(f"🧠 Obteniendo LLM para interpretación de consultas (usuario: {account_id})...")
    return await get_llm_for_user(account_id, purpose="fast")

class InternalKnowledgeSearchInput(BaseModel):
    """Input schema para la búsqueda de conocimiento interno."""
    query: str = Field(
        ...,
        description="La consulta completa del usuario en lenguaje natural."
    )
    document_name: Optional[str] = Field(
        None,
        description="El nombre exacto de un documento específico (ej: 'Reporte Anual 2023.pdf') para buscar solo en él."
    )
    document_id: Optional[str] = Field(
        None,
        description="El ID único de un documento específico (UUID) para buscar solo en él."
    )

class InternalKnowledgeSearchTool(BaseTool):
    name: str = "internal_knowledge_search"
    description: str = (
        "CUÁNDO USAR: Cuando necesites buscar en la base de conocimiento INTERNA del usuario. "
        "Esto incluye sus notas, documentos, conversaciones pasadas y cualquier otro dato que haya guardado. "
        "Es la herramienta principal para responder preguntas basadas en la información personal del usuario. "
        "Puedes especificar un documento por su nombre exacto (ej. 'Reporte Anual 2023.pdf') o por su ID único si lo conoces."
    )
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace actual, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")
    args_schema: Type[BaseModel] = InternalKnowledgeSearchInput
    return_direct: bool = False

    async def _interpret_query(self, query: str) -> Dict[str, Any]:
        llm = await get_interpreter_llm(self.account_id)
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
6. document_name: El nombre exacto de un documento específico (ej: "Reporte Anual 2023.pdf") o null.
7. document_id: El ID único de un documento específico (UUID) o null.

Responde SOLO en formato JSON válido.
"""
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content
            json_match = re.search(r'\{.*\}', str(content), re.DOTALL)
            if json_match:
                content_str = json_match.group(0)
            else:
                content_str = str(content) # Asegurarse de que sea un string

            try:
                return json.loads(content_str)
            except json.JSONDecodeError:
                logger.warning(f"No se pudo decodificar JSON de la respuesta del LLM: {content_str}. Usando valores por defecto.")
                return {"search_terms": query, "k": 15}
        except Exception as e:
            logger.error(f"Error interpretando consulta (fallo inesperado): {e}", exc_info=True)
            return {"search_terms": query, "k": 15}

    async def _arun(self, query: str, **kwargs: Any) -> str:
        try:
            logger.info(f"🔍 Ejecutando búsqueda interna para: '{query[:100]}...' ")
            interpretation = await self._interpret_query(query)
            logger.info(f"🧠 Interpretación del LLM: {interpretation}") # Nuevo log
            
            search_terms = interpretation.get("search_terms", query)
            k = interpretation.get("k", 15)
            document_name = interpretation.get("document_name")
            document_id = interpretation.get("document_id")

            explicit_document_ids = None

            if document_name:
                # Si se proporciona un nombre de documento, buscar su ID
                from core.memory_manager import list_user_documents
                docs = await list_user_documents(
                    account_id=self.account_id,
                    workspace_id=self.workspace_id,
                    document_ids=None, # No filtrar por ID aquí
                    topics=None # No filtrar por topic aquí
                )
                found_doc = next((d for d in docs if d.get("file_name") == document_name), None)
                if found_doc and found_doc.get("document_id"):
                    explicit_document_ids = [found_doc["document_id"]]
                    logger.info(f"🔍 Documento '{document_name}' encontrado con ID: {explicit_document_ids[0]}")
                else:
                    logger.warning(f"Documento '{document_name}' no encontrado para la cuenta {self.account_id} en workspace {self.workspace_id}.")
                    return f"No se encontró el documento '{document_name}' en tu base de conocimiento."
            elif document_id:
                explicit_document_ids = [document_id]
                logger.info(f"🔍 Buscando directamente con document_id: {document_id}")

            # Asegurarse de que content_types y filter_topics sean List[str] o None
            # Castear a str explícitamente para satisfacer el tipo esperado List[str]
            content_types_arg = [str(interpretation["content_type"])] if interpretation.get("content_type") else None
            filter_topics_arg = [str(interpretation["topic"])] if interpretation.get("topic") else None

            results = await get_relevant_memories(
                account_id=self.account_id,
                query=search_terms,
                content_types=content_types_arg,
                filter_topics=filter_topics_arg,
                category=interpretation.get("category"),
                workspace_id=self.workspace_id,
                k=k,
                explicit_document_ids=explicit_document_ids # Pasar el nuevo parámetro
            )
            
            if not results or not results.sources:
                return f"No se encontró información relevante para: '{query}'."

            formatted_results = []
            for source in results.sources:
                source_name = source.title or source.url or "memoria" # Usar source.url
                formatted_results.append(f"- Fuente: {source_name}\n  Contenido: {source.snippet[:500]}...")
            
            return f"Se encontraron {len(results.sources)} resultados en tu base de conocimiento:\n\n" + "\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Error en InternalKnowledgeSearchTool: {e}", exc_info=True)
            return f"Error al procesar la búsqueda interna: {str(e)}"

    def _run(self, *args, **kwargs) -> str:
        import asyncio
        return asyncio.run(self._arun(*args, **kwargs))