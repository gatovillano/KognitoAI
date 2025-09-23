# core/llm_manager.py

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings

logger = logging.getLogger(__name__)

# --- Global LLM Instances ---
# These are initialized by `initialize_llms` when the server starts.
_main_agent_llm_instance: Optional[BaseLanguageModel] = None
_fast_task_llm_instance: Optional[BaseLanguageModel] = None

def get_main_llm() -> Optional[BaseLanguageModel]:
    """Returns the initialized main agent LLM instance."""
    return _main_agent_llm_instance

def get_fast_llm() -> Optional[BaseLanguageModel]:
    """Returns the initialized fast task LLM instance, or the main one as a fallback."""
    return _fast_task_llm_instance or _main_agent_llm_instance

async def _invoke_llm_cached(llm: BaseLanguageModel, prompt: str) -> Any:
    """Función wrapper para invocar el LLM."""
    return await llm.ainvoke(prompt)

async def initialize_llms():
    """
    Initializes the global instances of the LLMs (main and fast task).
    This function is called once when the web_server starts.
    """
    global _main_agent_llm_instance, _fast_task_llm_instance
    
    if not settings.google_api_key:
        logger.error("FATAL ERROR! GOOGLE_API_KEY is not configured. The agent cannot function.")
        raise ValueError("Google API key has not been configured.")

    try:
        logger.info(f"🛠️ Initializing main agent LLM (ChatGoogleGenerativeAI - {settings.google_main_model_name})...")
        main_llm = ChatGoogleGenerativeAI(
            model=settings.google_main_model_name,
            temperature=settings.llm_temperature,
            google_api_key=settings.google_api_key,
            stream=True
        )
        _main_agent_llm_instance = main_llm
        logger.info("✅ Main agent LLM initialized.")
    except Exception as e:
        logger.error(f"❌ FATAL: Failed to initialize the main LLM: {e}", exc_info=True)
        raise

    try:
        logger.info(f"🛠️ Initializing fast task LLM (ChatGoogleGenerativeAI - {settings.google_summary_model_name})...")
        fast_llm = ChatGoogleGenerativeAI(
            model=settings.google_summary_model_name,
            temperature=0.0,
            google_api_key=settings.google_api_key,
            stream=True
        )
        _fast_task_llm_instance = fast_llm
        logger.info("✅ Fast task LLM initialized.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize the fast task LLM. The main LLM will be used as a fallback: {e}")
        _fast_task_llm_instance = _main_agent_llm_instance

async def get_enhanced_llm_response(
    user_message: str,
    user_id: str,
    workspace_id: Optional[str] = None,
    use_knowledge_graph: bool = True
) -> Dict[str, Any]:
    """
    Obtiene respuesta del LLM enriquecida con contexto del grafo de conocimiento.

    Args:
        user_message: Mensaje del usuario
        user_id: ID del usuario
        workspace_id: ID del workspace
        use_knowledge_graph: Si usar el grafo de conocimiento

    Returns:
        Dict con respuesta enriquecida
    """
    try:
        logger.info(f"🧠 Generando respuesta enriquecida para: '{user_message[:50]}...'")

        # 1. Obtener contexto enriquecido si está habilitado
        enhanced_context = None
        if use_knowledge_graph:
            enhanced_context = await _get_enhanced_context(user_message, user_id, workspace_id)

        # 2. Construir prompt enriquecido
        enriched_prompt = await _build_enriched_prompt(user_message, enhanced_context)

        # 3. Obtener respuesta del LLM
        llm = get_main_llm()
        if not llm:
            raise ValueError("LLM no inicializado")

        response = await _invoke_llm_cached(llm, enriched_prompt)

        # 4. Procesar y enriquecer la respuesta
        enhanced_response = {
            "response": response.content if hasattr(response, 'content') else str(response),
            "user_message": user_message,
            "enhanced_context": enhanced_context,
            "reasoning_used": enhanced_context is not None,
            "timestamp": datetime.now().isoformat()
        }

        # 5. Guardar memoria enriquecida
        if enhanced_context:
            await _save_enhanced_interaction(enhanced_response, user_id)

        logger.info("✅ Respuesta enriquecida generada exitosamente")
        return enhanced_response

    except Exception as e:
        logger.error(f"❌ Error generando respuesta enriquecida: {e}")
        # Fallback a respuesta tradicional
        return await _get_traditional_response(user_message)

async def _get_enhanced_context(user_message: str, user_id: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Obtiene contexto enriquecido del grafo de conocimiento."""
    try:
        from core.enhanced_memory_manager import EnhancedMemoryManager
        from knowledge_graph.graph_database import GraphDB
        from core.config import settings

        # Inicializar componentes
        if not settings.neo4j_uri:
            logger.error("NEO4J_URI no está configurado.")
            return None
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )

        enhanced_manager = EnhancedMemoryManager(graph_db=graph_db)

        # Obtener contexto enriquecido
        context = await enhanced_manager.get_enhanced_context(
            user_message, user_id, workspace_id
        )

        return context

    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo contexto enriquecido: {e}")
        return None

async def _build_enriched_prompt(user_message: str, enhanced_context: Optional[Dict[str, Any]] = None) -> str:
    """Construye un prompt enriquecido con contexto del grafo de conocimiento."""

    base_prompt = f"Usuario: {user_message}"

    if not enhanced_context:
        return base_prompt

    # Agregar contexto del grafo de conocimiento
    enriched_prompt = f"""Contexto del Grafo de Conocimiento:

"""

    # Agregar entidades relevantes
    entities = enhanced_context.get("sources", {}).get("knowledge_graph", {}).get("entities", [])
    if entities:
        enriched_prompt += "Entidades relevantes encontradas:\n"
        for entity in entities[:5]:
            enriched_prompt += f"- {entity.get('name', '')}: {entity.get('description', '')} (confianza: {entity.get('confidence', 0):.2f})\n"
        enriched_prompt += "\n"

    # Agregar relaciones relevantes
    relationships = enhanced_context.get("sources", {}).get("knowledge_graph", {}).get("relationships", [])
    if relationships:
        enriched_prompt += "Relaciones relevantes:\n"
        for rel in relationships[:3]:
            enriched_prompt += f"- {rel.get('source_name', '')} → {rel.get('target_name', '')} ({rel.get('relationship_type', '')})\n"
        enriched_prompt += "\n"

    # Agregar insights
    insights = enhanced_context.get("enhanced_insights", [])
    if insights:
        enriched_prompt += "Insights del análisis:\n"
        for insight in insights:
            enriched_prompt += f"- {insight.get('description', '')}\n"
        enriched_prompt += "\n"

    # Agregar caminos de razonamiento
    reasoning_paths = enhanced_context.get("reasoning_paths", [])
    if reasoning_paths:
        enriched_prompt += "Caminos de razonamiento identificados:\n"
        for path in reasoning_paths:
            enriched_prompt += f"- {path.get('description', '')}\n"
            for step in path.get("steps", [])[:2]:
                enriched_prompt += f"  {step.get('step', '')}: {step.get('from', '')} → {step.get('to', '')} ({step.get('relationship', '')})\n"
        enriched_prompt += "\n"

    enriched_prompt += f"""
Instrucciones:
1. Usa el contexto del grafo de conocimiento para enriquecer tu respuesta
2. Menciona conexiones relevantes cuando sea apropiado
3. Si hay caminos de razonamiento, úsalos para estructurar tu respuesta
4. Mantén un tono natural y conversacional

Usuario: {user_message}

Asistente:"""

    return enriched_prompt

async def _save_enhanced_interaction(enhanced_response: Dict[str, Any], user_id: str) -> None:
    """Guarda la interacción enriquecida para futuras referencias."""
    try:
        # Aquí integrarías con tu sistema de guardado de memorias
        logger.debug(f"💾 Guardando interacción enriquecida para usuario {user_id}")

    except Exception as e:
        logger.error(f"❌ Error guardando interacción enriquecida: {e}")

async def _get_traditional_response(user_message: str) -> Dict[str, Any]:
    """Fallback a respuesta tradicional sin contexto enriquecido."""
    try:
        llm = get_main_llm()
        if not llm:
            raise ValueError("LLM no inicializado")

        response = await _invoke_llm_cached(llm, user_message)

        return {
            "response": response.content if hasattr(response, 'content') else str(response),
            "user_message": user_message,
            "enhanced_context": None,
            "reasoning_used": False,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error en respuesta tradicional: {e}")
        return {
            "response": "Lo siento, hubo un error procesando tu solicitud.",
            "user_message": user_message,
            "enhanced_context": None,
            "reasoning_used": False,
            "error": str(e)
        }
