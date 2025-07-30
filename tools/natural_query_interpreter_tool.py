# tools/natural_query_interpreter_tool.py

"""
Herramienta de interpretación de consultas en lenguaje natural.
Analiza la intención del usuario y extrae automáticamente los parámetros
para las herramientas de búsqueda y análisis.
"""

import logging
import json
import re
from typing import Any, Optional, Type, Dict, List
from datetime import datetime, timedelta

from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from core.memory_manager import search_vector_db_optimized

logger = logging.getLogger(__name__)

# Singleton para el modelo de interpretación
_interpreter_llm: Optional[ChatGoogleGenerativeAI] = None

async def get_interpreter_llm() -> ChatGoogleGenerativeAI:
    global _interpreter_llm
    if _interpreter_llm is None:
        logger.info("🧠 Inicializando LLM para interpretación de consultas naturales...")
        _interpreter_llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            disable_streaming=True
        )
    return _interpreter_llm


class NaturalQueryInput(BaseModel):
    """Input schema para interpretación de consultas naturales."""
    query: str = Field(
        ...,
        description="La consulta completa del usuario en lenguaje natural"
    )
    context: Optional[str] = Field(
        None,
        description="Contexto adicional de la conversación",
        json_schema_extra={"type": "string"}
    )


class NaturalQueryInterpreterTool(BaseTool):
    
    name: str = "natural_query_interpreter"
    description: str = (
        "🎯 INTÉRPRETE UNIVERSAL DE CONSULTAS - Usa esta herramienta cuando el usuario haga: "
        "• Preguntas abiertas: '¿qué tengo sobre el proyecto X?', 'busca información de Y' "
        "• Consultas complejas: 'encuentra notas de la semana pasada sobre trabajo' "
        "• Búsquedas con múltiples filtros: 'documentos técnicos del equipo de desarrollo' "
        "• Solicitudes ambiguas que necesitan interpretación automática "
        "\n🔧 FUNCIONALIDAD: Analiza la consulta, extrae parámetros automáticamente "
        "y ejecuta la búsqueda optimizada correspondiente. "
        "\n⚡ RESULTADO: Devuelve directamente los resultados encontrados."
    )
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace actual, inyectado automáticamente.")
    args_schema: Type[BaseModel] = NaturalQueryInput
    return_direct: bool = False  # Devuelve resultados directamente

    async def _interpret_query(self, query: str, context: str = "") -> Dict[str, Any]:
        """Interpreta una consulta natural y extrae parámetros estructurados."""
        llm = await get_interpreter_llm()
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""
Eres un experto en interpretar consultas de búsqueda en lenguaje natural.
Analiza la consulta del usuario y extrae los parámetros estructurados.

CONSULTA DEL USUARIO: "{query}"
CONTEXTO ADICIONAL: "{context}"
FECHA ACTUAL: {current_date}

PARÁMETROS A EXTRAER:
1. content_type: "user_memories" (notas/conversaciones) o "user_documents" (archivos/PDFs) o null (ambos)
2. topic: tema organizacional (ej: "proyecto_hydra", "trabajo", "personal") o null
3. category: categoría automática (ej: "technical", "meeting", "idea", "problem") o null
4. search_terms: términos clave para la búsqueda vectorial
5. time_filter: filtro temporal si se menciona ("last_week", "today", "this_month") o null
6. k: número de resultados (5-15 según la consulta)

EJEMPLOS:
- "busca mis notas sobre el proyecto hydra" → content_type: "user_memories", topic: "proyecto_hydra", search_terms: "proyecto hydra"
- "encuentra documentos técnicos" → content_type: "user_documents", category: "technical", search_terms: "documentos técnicos"
- "¿qué escribí la semana pasada sobre trabajo?" → content_type: "user_memories", topic: "trabajo", time_filter: "last_week", search_terms: "trabajo"

Responde SOLO en formato JSON válido:
{{
    "content_type": "...",
    "topic": "...",
    "category": "...",
    "search_terms": "...",
    "time_filter": "...",
    "k": 20,
    "confidence": 0.95,
    "reasoning": "breve explicación de la interpretación"
}}
"""
        
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', str(content), re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            if not isinstance(content, (dict, list)):
                result = json.loads(content)
            else:
                result = content
            # Ensure return type is always Dict[str, Any]
            if isinstance(result, list):
                result = {"results": result}
            logger.info(f"🎯 Consulta interpretada: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error interpretando consulta: {e}", exc_info=True)
            return {
                "content_type": None,
                "topic": None,
                "category": None,
                "search_terms": query,
                "time_filter": None,
                "k": 20,
                "confidence": 0.5,
                "reasoning": f"Error en interpretación: {str(e)}"
            }

    async def _arun(
        self,
        query: str,
        context: Optional[str] = None,
       **kwargs: Any,
    ) -> str:
        """Ejecuta la interpretación y búsqueda automática."""
        try:
            logger.info(f"🔍 Interpretando consulta natural: '{query[:100]}...'")
            
            # 1. Interpretar la consulta
            interpretation = await self._interpret_query(query, context or "")
            
            # 2. Extraer parámetros
            content_type = interpretation.get("content_type")
            topic = interpretation.get("topic")
            category = interpretation.get("category")
            search_terms = interpretation.get("search_terms", query)
            k = interpretation.get("k", 10)
            confidence = interpretation.get("confidence", 0.5)
            reasoning = interpretation.get("reasoning", "")
            
            logger.info(f"📊 Parámetros extraídos: content_type={content_type}, topic={topic}, category={category}, k={k}")
            logger.info(f"🧠 Confianza: {confidence:.2f} - Razonamiento: {reasoning}")
            
            # 3. Ejecutar búsqueda optimizada
            results = await search_vector_db_optimized(
                account_id=self.account_id,
                query=search_terms,
                content_type=content_type,
                topic=topic,
                category=category,
                workspace_id=self.workspace_id,
                k=k
            )
            
            # 4. Formatear resultados
            if not results:
                return f"❌ No encontré información relevante para: '{query}'\n\n🔍 Parámetros de búsqueda utilizados:\n- Términos: {search_terms}\n- Tipo: {content_type or 'todos'}\n- Tema: {topic or 'cualquiera'}\n- Categoría: {category or 'cualquiera'}"
            
            # Formatear resultados encontrados
            formatted_results = []
            for i, result in enumerate(results[:k], 1):
                # Manejar tanto el formato nuevo (content/metadata) como el antiguo (document/cmetadata)
                metadata = result.get('metadata', result.get('cmetadata', {}))
                content = result.get('content', result.get('document', ''))
                score = result.get('similarity_score', 0)

                result_type = metadata.get('type', 'unknown')
                source = metadata.get('file_name', metadata.get('source', 'memoria'))

                formatted_results.append(
                    f"📄 **Resultado {i}** (relevancia: {1-score:.2f})\n"
                    f"**Fuente:** {source} | **Tipo:** {result_type}\n"
                    f"**Contenido:** {content[:5000]}{'...' if len(content) > 200 else ''}\n"
                )
            
            response = f"✅ **Encontré {len(results)} resultados para:** '{query}'\n\n"
            response += f"🎯 **Interpretación automática:**\n"
            response += f"- Términos de búsqueda: {search_terms}\n"
            response += f"- Tipo de contenido: {content_type or 'todos'}\n"
            response += f"- Tema: {topic or 'cualquiera'}\n"
            response += f"- Categoría: {category or 'cualquiera'}\n"
            response += f"- Confianza: {confidence:.0%}\n\n"
            response += "📋 **Resultados encontrados:**\n\n"
            response += "\n".join(formatted_results)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error en natural_query_interpreter: {e}", exc_info=True)
            return f"❌ Error procesando la consulta: {str(e)}"

    def _run(self, *args, **kwargs) -> str:
        """Versión síncrona - redirige a la asíncrona."""
        import asyncio
        return asyncio.run(self._arun(*args, **kwargs))
