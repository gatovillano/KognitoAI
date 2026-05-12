# utils/document_summarizer.py

import logging
from typing import Optional, Dict, Any
from core.llm_manager import get_fast_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

async def generate_simple_summary(
    text: str,
    document_title: Optional[str] = None,
    max_words: int = 150
) -> Dict[str, Any]:
    """
    Genera un resumen simple y estructurado de un documento.

    Args:
        text: Contenido completo del documento
        document_title: Título del documento (opcional)
        max_words: Máximo de palabras para el resumen ejecutivo

    Returns:
        Dict con: summary, key_points, topics, document_type
    """
    if not text or len(text.strip()) < 50:
        return {
            "summary": "El documento tiene muy poco contenido para generar un resumen.",
            "key_points": ["Contenido insuficiente"],
            "topics": ["general"],
            "document_type": "desconocido",
            "confidence": 0.5
        }

    try:
        llm = get_fast_llm()

        prompt = f"""
Eres KAI (Kognito AI). Genera un resumen CONCISO y ESTRUCTURADO del siguiente documento.

INSTRUCCIONES:
1. Resumen Ejecutivo: 1-2 párrafos (máximo {max_words} palabras). Captura la esencia y propósito.
2. Puntos Clave: Lista 3-5 puntos clave como frases cortas.
3. Temas: Lista 3-5 temas/etiquetas principales.
4. Tipo de Documento: Clasifica como: 'informe', 'artículo', 'técnico', 'legal', 'correspondencia', 'contrato', 'acta', 'memorando', 'otro'.

RESPONDE EN FORMATO JSON (sin markdown):
{{
  "summary": "string",
  "key_points": ["string", "string"],
  "topics": ["string", "string"],
  "document_type": "string"
}}

DOCUMENTO:
Título: {document_title or 'No especificado'}
Contenido:
{text[:6000]}
"""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)

        # Intentar extraer JSON de la respuesta
        import json
        import re

        # Buscar bloque JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            data = json.loads(json_str)
        else:
            # Fallback: parsear como texto plano
            data = {
                "summary": content[:300],
                "key_points": ["No se pudieron extraer puntos clave"],
                "topics": ["general"],
                "document_type": "otro"
            }

        # Asegurar campos
        data.setdefault("summary", "Resumen no disponible")
        data.setdefault("key_points", [])
        data.setdefault("topics", [])
        data.setdefault("document_type", "otro")
        data["confidence"] = 0.9

        return data

    except Exception as e:
        logger.error(f"Error generando resumen: {e}", exc_info=True)
        return {
            "summary": f"Error al generar resumen: {str(e)}",
            "key_points": ["Error en procesamiento"],
            "topics": ["error"],
            "document_type": "otro",
            "confidence": 0.0
        }
