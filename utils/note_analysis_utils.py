import logging
import json
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from core.llm_manager import get_fast_llm, get_llm_for_user
from core.utils.llm_utils import safe_json_loads

logger = logging.getLogger(__name__)

async def analyze_single_note(note_content: str, note_title: str = "Sin título", account_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Analiza una nota individual usando el LLM con la personalidad de KAI (Exocerebro).
    """
    if account_id:
        llm = await get_llm_for_user(account_id, purpose="fast")
    else:
        llm = get_fast_llm()
    if not llm:
        logger.error("LLM not initialized in analyze_single_note")
        raise ValueError("LLM not initialized")

    system_prompt = """Eres KAI, una IA avanzada diseñada para actuar como un 'exocerebro' proactivo para el usuario.
Tu objetivo es analizar notas cotidianas y extraer valor oculto, conexiones y propuestas de acción.
No te limites a resumir; busca el 'insight' detrás de la información.
Analiza la nota proporcionada y genera un análisis estructurado en formato JSON con los siguientes campos:
- executive_summary: Un resumen ejecutivo breve y directo.
- general_analysis: Un análisis general extenso del documento que profundiza en el contexto, argumentos principales e implicaciones (500-1000 palabras).
- key_themes: Lista de temas clave identificados (strings).
- potential_implications: Implicaciones potenciales de esta información que el usuario podría no haber notado.
- action_suggestions: Sugerencias de acción concretas basadas en la nota.
- related_concepts: Conceptos relacionados que podrían ampliar la comprensión del tema.
- kai_insight: Un insight único y profundo desde tu perspectiva de exocerebro.

Responde SOLO con el JSON válido, sin bloques de código markdown adicionales si es posible, o dentro de un bloque json."""

    user_prompt = f"Título de la nota: {note_title}\n\nContenido:\n{note_content}"

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        content = response.content

        # Intentar cargar JSON con reintentos si falla el parseo
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                return safe_json_loads(content)
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"JSON decode error in analyze_single_note (attempt {attempt+1}/{max_retries+1}): {e}. Requesting fix...")
                    fix_prompt = f"The JSON response you provided is invalid. Error: {e}\n\nOriginal content:\n{content}\n\nPlease fix the JSON and return ONLY the corrected valid JSON."
                    response = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt), HumanMessage(content=fix_prompt)])
                    content = response.content
                else:
                    raise e
    except Exception as e:
        logger.error(f"Error analyzing note: {e}")
        # Retornar estructura de error o parcial
        return {
            "executive_summary": "Error al analizar la nota.",
            "error": str(e)
        }

async def analyze_note_collection(notes: List[Dict[str, str]], collection_name: str, account_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Analiza una colección de notas para encontrar patrones y síntesis.
    """
    if account_id:
        llm = await get_llm_for_user(account_id, purpose="fast")
    else:
        llm = get_fast_llm()
    if not llm:
        logger.error("LLM not initialized in analyze_note_collection")
        raise ValueError("LLM not initialized")

    # Preparar texto de notas (limitar si es muy largo, aunque fast_llm suele tener ventana decente)
    notes_text = "\n\n".join([f"Nota {i+1} ({n.get('title', 'Sin título')}):\n{n.get('content', '')}" for i, n in enumerate(notes)])

    system_prompt = f"""Eres KAI, el exocerebro del usuario.
Estás analizando una colección de notas llamada '{collection_name}'.
Tu misión es encontrar patrones, conexiones transversales y síntesis de conocimiento que emergen al ver estas notas en conjunto.
Genera un análisis estructurado en formato JSON con los siguientes campos:
- collection_summary: Resumen global de la colección.
- cross_cutting_themes: Temas que aparecen en múltiples notas (lista de strings o objetos con 'theme' y 'description').
- synthesized_insights: Insights que solo surgen al combinar la información de varias notas.
- strategic_recommendations: Recomendaciones estratégicas basadas en el conjunto de información.
- knowledge_gaps: Brechas de información identificadas en la colección.
- kai_synthesis: Una síntesis de alto nivel desde tu perspectiva de IA.

Responde SOLO con el JSON válido."""

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=notes_text)])
        content = response.content

        # Intentar cargar JSON con reintentos si falla el parseo
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                return safe_json_loads(content)
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"JSON decode error in analyze_note_collection (attempt {attempt+1}/{max_retries+1}): {e}. Requesting fix...")
                    fix_prompt = f"The JSON response you provided is invalid. Error: {e}\n\nOriginal content:\n{content}\n\nPlease fix the JSON and return ONLY the corrected valid JSON."
                    response = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=notes_text), HumanMessage(content=fix_prompt)])
                    content = response.content
                else:
                    raise e
    except Exception as e:
        logger.error(f"Error analyzing note collection: {e}")
        return {
            "collection_summary": "Error al analizar la colección.",
            "error": str(e)
        }

async def summarize_note(note_content: str, note_title: str = "Sin título", account_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Genera un resumen semántico conciso de una nota individual.
    """
    if account_id:
        llm = await get_llm_for_user(account_id, purpose="fast")
    else:
        llm = get_fast_llm()
    if not llm:
        logger.error("LLM not initialized in summarize_note")
        raise ValueError("LLM not initialized")

    system_prompt = """Eres KAI, un asistente de IA especializado en crear resúmenes semánticos concisos y útiles.
Tu objetivo es extraer la esencia de la nota y presentarla de forma clara y estructurada.
Genera un resumen en formato JSON con los siguientes campos:
- summary: Un resumen conciso del contenido principal (2-3 oraciones).
- key_points: Lista de puntos clave (máximo 5).
- main_topic: El tema principal de la nota.
- context: Contexto o categoría de la información.

Responde SOLO con el JSON válido."""

    user_prompt = f"Título de la nota: {note_title}\n\nContenido:\n{note_content}"

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        content = response.content

        # Intentar cargar JSON con reintentos si falla el parseo
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                return safe_json_loads(content)
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"JSON decode error in summarize_note (attempt {attempt+1}/{max_retries+1}): {e}. Requesting fix...")
                    fix_prompt = f"The JSON response you provided is invalid. Error: {e}\n\nOriginal content:\n{content}\n\nPlease fix the JSON and return ONLY the corrected valid JSON."
                    response = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt), HumanMessage(content=fix_prompt)])
                    content = response.content
                else:
                    raise e
    except Exception as e:
        logger.error(f"Error summarizing note: {e}")
        return {
            "summary": "Error al generar el resumen.",
            "error": str(e)
        }

