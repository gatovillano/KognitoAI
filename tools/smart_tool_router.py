# tools/smart_tool_router.py

"""
Router inteligente que analiza consultas del usuario y recomienda
la herramienta más apropiada para ejecutar.
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

logger = logging.getLogger(__name__)

# Singleton para el modelo de routing
_router_llm: Optional[ChatGoogleGenerativeAI] = None

async def get_router_llm() -> ChatGoogleGenerativeAI:
    global _router_llm
    if _router_llm is None:
        logger.info("🧭 Inicializando LLM para routing inteligente de herramientas...")
        _router_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            disable_streaming=True
        )
    return _router_llm


class SmartRouterInput(BaseModel):
    """Input schema para el router inteligente."""
    user_query: str = Field(
        ..., 
        description="La consulta completa del usuario"
    )
    context: Optional[str] = Field(
        None, 
        description="Contexto adicional de la conversación"
    )


class SmartToolRouter(BaseTool):
    name: str = "smart_tool_router"
    description: str = (
        "🧭 ROUTER INTELIGENTE DE HERRAMIENTAS - Analiza consultas complejas del usuario "
        "y recomienda la herramienta más apropiada para ejecutar. "
        "Útil cuando no estés seguro de qué herramienta usar o cuando la consulta "
        "sea ambigua y necesite análisis de intención."
    )
    args_schema: Type[BaseModel] = SmartRouterInput
    return_direct: bool = True

    async def _analyze_query_intent(self, query: str, context: str = "") -> Dict[str, Any]:
        """Analiza la intención de la consulta y recomienda herramientas."""
        llm = await get_router_llm()
        
        prompt = f"""
Eres un experto en análisis de intenciones para un sistema de IA con múltiples herramientas especializadas.
Analiza la consulta del usuario y recomienda la herramienta más apropiada.

CONSULTA DEL USUARIO: "{query}"
CONTEXTO: "{context}"

HERRAMIENTAS DISPONIBLES:

1. **natural_query_interpreter**: Para consultas abiertas que necesitan interpretación automática
   - Ejemplos: "busca información sobre X", "¿qué tengo de Y?", "encuentra documentos de la semana pasada"
   - Ideal para: consultas ambiguas, múltiples filtros implícitos, lenguaje natural

2. **memory_search_optimized**: Para búsquedas específicas con parámetros conocidos
   - Ejemplos: búsquedas directas con filtros claros (topic, category, content_type)
   - Ideal para: control granular, parámetros exactos conocidos

3. **knowledge_base_analyzer**: Para análisis profundos y conexiones
   - Ejemplos: "analiza mis notas", "busca nuevas conexiones", "revisa mi base de conocimiento"
   - Ideal para: análisis de patrones, relaciones, insights proactivos

4. **document_rag_tool**: Para procesar y añadir documentos a la base de conocimiento
   - Ejemplos: cuando el usuario sube un documento para guardar
   - Ideal para: procesamiento de documentos nuevos

5. **web_search**: Para búsquedas en internet
   - Ejemplos: "busca información actual sobre X", "qué está pasando con Y"
   - Ideal para: información externa, noticias, datos actuales

6. **add_note_tool**: Para crear notas rápidas
   - Ejemplos: "recuerda que...", "anota esto...", "guarda esta idea"
   - Ideal para: captura rápida de información

CRITERIOS DE DECISIÓN:
- Si la consulta es ambigua o en lenguaje natural → natural_query_interpreter
- Si necesita análisis profundo → knowledge_base_analyzer  
- Si busca información externa → web_search
- Si quiere guardar algo → add_note_tool o document_rag_tool
- Si tiene parámetros específicos claros → memory_search_optimized

Responde en formato JSON:
{{
    "recommended_tool": "nombre_herramienta",
    "confidence": 0.95,
    "reasoning": "explicación de por qué esta herramienta",
    "alternative_tools": ["herramienta2", "herramienta3"],
    "extracted_parameters": {{
        "param1": "valor1",
        "param2": "valor2"
    }},
    "user_friendly_explanation": "explicación simple para el usuario"
}}
"""
        
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            result = json.loads(content)
            logger.info(f"🧭 Análisis de intención completado: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analizando intención: {e}", exc_info=True)
            return {
                "recommended_tool": "natural_query_interpreter",
                "confidence": 0.5,
                "reasoning": f"Error en análisis, usando herramienta por defecto: {str(e)}",
                "alternative_tools": ["memory_search_optimized"],
                "extracted_parameters": {},
                "user_friendly_explanation": "Hubo un error en el análisis, pero puedo ayudarte con la búsqueda general."
            }

    async def _arun(
        self,
        user_query: str,
        context: Optional[str] = None
    ) -> str:
        """Ejecuta el análisis de routing."""
        try:
            logger.info(f"🧭 Analizando routing para consulta: '{user_query[:100]}...'")
            
            # Analizar la intención
            analysis = await self._analyze_query_intent(user_query, context or "")
            
            # Extraer resultados
            recommended_tool = analysis.get("recommended_tool", "natural_query_interpreter")
            confidence = analysis.get("confidence", 0.5)
            reasoning = analysis.get("reasoning", "")
            alternatives = analysis.get("alternative_tools", [])
            parameters = analysis.get("extracted_parameters", {})
            explanation = analysis.get("user_friendly_explanation", "")
            
            # Formatear respuesta
            response = f"🧭 **Análisis de tu consulta:**\n\n"
            response += f"**Consulta:** {user_query}\n\n"
            response += f"🎯 **Herramienta recomendada:** `{recommended_tool}`\n"
            response += f"📊 **Confianza:** {confidence:.0%}\n"
            response += f"💭 **Razonamiento:** {reasoning}\n\n"
            
            if parameters:
                response += f"⚙️ **Parámetros detectados:**\n"
                for param, value in parameters.items():
                    response += f"- {param}: {value}\n"
                response += "\n"
            
            if alternatives:
                response += f"🔄 **Alternativas:** {', '.join(alternatives)}\n\n"
            
            response += f"💡 **Explicación:** {explanation}\n\n"
            response += f"🚀 **Siguiente paso:** Ahora ejecutaré la herramienta `{recommended_tool}` con tu consulta."
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error en smart_tool_router: {e}", exc_info=True)
            return f"❌ Error analizando tu consulta: {str(e)}\n\nUsaré la herramienta de búsqueda general por defecto."

    def _run(self, *args, **kwargs) -> str:
        """Versión síncrona - redirige a la asíncrona."""
        import asyncio
        return asyncio.run(self._arun(*args, **kwargs))
