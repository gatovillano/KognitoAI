"""
Herramienta de Análisis y Síntesis Avanzada de Texto (analyze_text_for_insights)
Procesa texto para identificar temas clave, entidades, sentimiento y generar un resumen ejecutivo utilizando el modelo Gemini para un análisis más profundo y summarización.
"""
import spacy
import asyncio
from typing import List, Dict
from keybert import KeyBERT
from textblob import TextBlob
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import logging
import re
import json

logger = logging.getLogger(__name__)

_nlp = None
_kw_model = None
_gemini_model = None

def get_spacy_model():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def get_keybert_model():
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT("all-MiniLM-L6-v2")
    return _kw_model

async def get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        logger.info("Inicializando modelo Gemini 1.5 Flash para análisis y summarización...")
        _gemini_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.1)
        logger.info("Modelo Gemini 1.5 Flash inicializado.")
    return _gemini_model

async def summarize_text_with_gemini(text: str) -> str:
    """Genera un resumen ejecutivo de un texto largo usando Gemini 1.5 Flash."""
    if not text or len(text.split()) < 50: # Si el texto es muy corto, no resumir
        return text

    gemini_model = await get_gemini_model()
    if not gemini_model:
        logger.warning("Modelo Gemini no inicializado. No se puede generar resumen.")
        return "No se pudo generar el resumen."

    try:
        # Un prompt más flexible que pide calidad sobre longitud estricta
        prompt = f"""
        Analiza el siguiente texto y genera un resumen ejecutivo claro y conciso. 
        El resumen debe capturar las ideas principales, conclusiones y puntos clave. 
        Idealmente, debería tener entre 2 y 4 párrafos cortos.

        Texto para resumir:
        ---
        {text}
        ---
        """
        response = await gemini_model.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip()

    except Exception as e:
        logger.warning(f"Error resumiendo texto con Gemini: {e}.", exc_info=True)
        return "Ocurrió un error al generar el resumen."

async def deep_analysis_with_gemini(text):
    """Realiza un análisis profundo del texto usando Gemini para identificar temas clave y conexiones semánticas."""
    if not text:
        return {"temas_clave": [], "conexiones_semanticas": []}

    gemini_model = await get_gemini_model()
    if not gemini_model:
        logger.warning("Modelo Gemini no inicializado para análisis profundo.")
        return {"temas_clave": [], "conexiones_semanticas": []}

    try:
        prompt = f"""
        Eres un analista experto en gestión del conocimiento. Analiza el siguiente texto para identificar temas clave y posibles conexiones semánticas o insights profundos. Responde en formato JSON con la siguiente estructura:
        {{
          "temas_clave": ["tema1", "tema2", ...], // Lista de temas principales (máximo 8)
          "conexiones_semanticas": ["insight1", "insight2", ...] // Lista de conexiones o insights (máximo 5)
        }}
        Texto para analizar: {text}
        """
        response = await gemini_model.ainvoke([HumanMessage(content=prompt)])
        import json
        import re
        
        # Extract JSON content from response if it's embedded in text
        content = response.content
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```|```[\s\S]*?```|\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0).strip('```json').strip('```').strip()
        
        analysis_result = json.loads(content)
        return analysis_result
    except Exception as e:
        logger.warning(f"Error en análisis profundo con Gemini: {e}. Volviendo a análisis básico.", exc_info=True)
        return {"temas_clave": [], "conexiones_semanticas": []}

async def analyze_text_for_insights(text: str) -> dict:
    """
    Ejecuta un análisis COMPLETO (básico + profundo con Gemini) y devuelve un único objeto de resultado.
    """
    logger.info("Iniciando análisis completo del texto...")
    
    # --- Tareas Locales y Rápidas (pueden ejecutarse en paralelo) ---
    nlp = get_spacy_model()
    doc = nlp(text)
    entidades = [{"texto": ent.text, "tipo": ent.label_} for ent in doc.ents]
    
    blob = TextBlob(text)
    sentimiento = {"polarity": blob.sentiment.polarity, "subjectivity": blob.sentiment.subjectivity}
    
    # --- Tareas Pesadas con Gemini (se ejecutan en paralelo) ---
    gemini_model = await get_gemini_model()
    
    # Prompt para obtener todo de una vez de Gemini
    prompt = f"""
    Eres un analista experto. Analiza el siguiente texto y responde ÚNICAMENTE en formato JSON con la siguiente estructura:
    {{
      "resumen_ejecutivo": "Un resumen conciso de 2-4 párrafos capturando las ideas principales.",
      "temas_clave_avanzados": ["Lista de hasta 8 temas clave semánticos, no solo palabras sueltas."],
      "conexiones_semanticas": ["Lista de hasta 5 insights o conexiones profundas encontradas en el texto."]
    }}

    Texto a analizar:
    ---
    {text}
    ---
    """
    
    deep_analysis_result = {}
    try:
        response = await gemini_model.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            clean_json_str = json_match.group(0)
            import json
            deep_analysis_result = json.loads(clean_json_str)
    except Exception as e:
        logger.error(f"Fallo en el análisis profundo con Gemini: {e}", exc_info=True)

    return {
        "entidades": entidades,
        "sentimiento": sentimiento,
        "resumen_ejecutivo": deep_analysis_result.get("resumen_ejecutivo", "No se pudo generar el resumen."),
        "temas_clave_avanzados": deep_analysis_result.get("temas_clave_avanzados", []),
        "conexiones_semanticas": deep_analysis_result.get("conexiones_semanticas", [])
    }

def analyze_text_for_insights_sync(text: str):
    """
    Versión síncrona de analyze_text_for_insights para uso en contextos no asíncronos.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Si ya hay un loop corriendo, usamos una nueva tarea
        return asyncio.ensure_future(analyze_text_for_insights(text))
    else:
        # Si no hay loop, lo ejecutamos directamente
        return loop.run_until_complete(analyze_text_for_insights(text))

# --- NUEVA FUNCIÓN DE ANÁLISIS DE COLECCIÓN ---
async def analyze_entire_collection(documents: List[Dict[str, str]]) -> dict:
    """
    Toma una lista de documentos (con título y contenido), los concatena
    y usa Gemini para encontrar conexiones y temas transversales entre ellos.
    """
    logger.info(f"Iniciando análisis de colección con {len(documents)} documentos...")
    if not documents:
        raise ValueError("La colección no contiene documentos para analizar.")

    gemini_model = await get_gemini_model()
    if not gemini_model:
        raise ValueError("El modelo Gemini no está inicializado.")

    # Concatenamos el contenido de todos los documentos en un solo gran texto
    # para que el LLM pueda ver el contexto completo.
    full_context_text = ""
    for doc in documents:
        full_context_text += f"--- INICIO DOCUMENTO: {doc.get('title', doc.get('file_name', 'Sin título'))} ---\n"
        full_context_text += f"{doc.get('content', '')}\n"
        full_context_text += f"--- FIN DOCUMENTO: {doc.get('title', doc.get('file_name', 'Sin título'))} ---\n\n"

    # Prompt diseñado para encontrar relaciones ENTRE documentos
    prompt = f"""
    Eres un analista de investigación experto. Has recibido una colección de varios documentos sobre un mismo tema. 
    Tu tarea es leerlos todos y encontrar las conexiones, patrones, contradicciones y temas emergentes que existen **entre** ellos.

    Responde ÚNICAMENTE en formato JSON con la siguiente estructura:
    {{
      "resumen_general_coleccion": "Un resumen ejecutivo que sintetice la información de TODOS los documentos como un todo.",
      "temas_transversales": ["Lista de hasta 10 temas o conceptos que aparecen repetidamente en varios documentos."],
      "conexiones_identificadas": [
        {{
          "documentos": ["título_doc_1", "título_doc_2"],
          "insight": "Descripción de la sinergia, evolución o contradicción encontrada entre estos documentos específicos."
        }}
      ],
      "brechas_conocimiento": ["Lista de preguntas o áreas que la colección en su conjunto no responde o deja abiertas."]
    }}

    Aquí está el contenido de la colección:
    {full_context_text}
    """

    try:
        response = await gemini_model.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        # Limpieza robusta del JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            clean_json_str = json_match.group(0)
            return json.loads(clean_json_str)
        else:
            raise ValueError("La respuesta del LLM para el análisis de colección no contenía un JSON válido.")
    except Exception as e:
        logger.error(f"Error en análisis de colección con Gemini: {e}", exc_info=True)
        raise
