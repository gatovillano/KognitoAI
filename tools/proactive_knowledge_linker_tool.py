# tools/proactive_knowledge_linker_tool.py

"""
Herramienta de Vinculación Proactiva de Conocimiento para KAI

Esta herramienta se activa automáticamente cada vez que se añade nueva información (nota, memoria, documento).
Analiza la nueva entrada, la compara con el conocimiento existente y genera insights proactivos sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento.
"""

import json
import logging
import asyncio
import datetime
from typing import Any, Dict, List, Optional, Type
import uuid
import numpy as np
from scipy.spatial.distance import cosine  # type: ignore

# Importaciones de la base de datos y la configuración
from core.database import ProactiveInsight, SessionLocal, Nota, AgendaEvent, Recordatorio, Memory, Account
from utils.db_session import DBSession
from core.config import settings
from utils.embeddings import initialize_embeddings
from langchain_core.embeddings import Embeddings
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Modelos para NLP y summarization - cargados de forma singleton
import spacy
from textblob import TextBlob  # type: ignore
from keybert import KeyBERT  # type: ignore
from sqlalchemy import select, text  # Import text for raw SQL if needed

# Importar el modelo de Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# --- Gestión del Estado de Ejecución del Job ---
LAST_RUN_FILE = "proactive_linker_last_run.json"

def get_last_run_timestamp() -> Optional[datetime.datetime]:
    """Lee el timestamp de la última ejecución desde un archivo."""
    logger.info(f"Intentando leer el archivo de última ejecución: {LAST_RUN_FILE}")
    try:
        with open(LAST_RUN_FILE, 'r') as f:
            data = json.load(f)
            # Asegúrate de que la fecha se parsea a un objeto datetime con timezone
            last_run = datetime.datetime.fromisoformat(data['last_run_utc'])
            logger.info(f"Última ejecución encontrada en: {last_run}")
            return last_run
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        # Si no hay archivo o está corrupto, devolvemos una fecha muy antigua para analizar todo.
        logger.warning(f"No se encontró un archivo de última ejecución válido. Se usará una fecha por defecto para analizar todo.")
        return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

def update_last_run_timestamp(run_time: datetime.datetime):
    """Guarda el timestamp de la ejecución actual en el archivo."""
    with open(LAST_RUN_FILE, 'w') as f:
        # Almacenar siempre en formato ISO y en UTC
        json.dump({'last_run_utc': run_time.isoformat()}, f)
    logger.info(f"Timestamp de última ejecución actualizado a: {run_time.isoformat()}")

# --- Singleton Models for NLP and Embeddings ---
_nlp_model: Optional[spacy.Language] = None
_keybert_model: Optional[KeyBERT] = None
_gemini_summarizer_model: Optional[ChatGoogleGenerativeAI] = None
_embedding_model: Optional[Embeddings] = None

async def get_nlp_model() -> spacy.Language:
    """Carga y devuelve el modelo spaCy para NER, inicializándolo solo una vez."""
    global _nlp_model
    if _nlp_model is None:
        logger.info("Cargando modelo spaCy 'en_core_web_sm'...")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            _nlp_model = await loop.run_in_executor(None, lambda: spacy.load("en_core_web_sm"))
            logger.info("Modelo spaCy cargado.")
        except Exception as e:
            logger.error(f"Error al cargar el modelo spaCy 'en_core_web_sm': {e}", exc_info=True)
            raise
    return _nlp_model

async def get_keybert_model_instance() -> KeyBERT:
    """Carga y devuelve el modelo KeyBERT, inicializándolo solo una vez."""
    global _keybert_model
    if _keybert_model is None:
        logger.info("Cargando modelo KeyBERT 'all-MiniLM-L6-v2'...")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        _keybert_model = await loop.run_in_executor(None, lambda: KeyBERT("all-MiniLM-L6-v2"))
        logger.info("Modelo KeyBERT cargado.")
    return _keybert_model

async def get_gemini_summarizer_model_instance() -> ChatGoogleGenerativeAI:
    """Carga y devuelve el modelo Gemini 1.5 Flash para summarization, inicializándolo solo una vez."""
    global _gemini_summarizer_model
    if _gemini_summarizer_model is None:
        logger.info("Inicializando modelo Gemini 1.5 Flash para summarization...")
        _gemini_summarizer_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.1)
        logger.info("Modelo Gemini 1.5 Flash inicializado.")
    return _gemini_summarizer_model

async def get_embedding_model_instance() -> Embeddings:
    """Obtiene y devuelve la instancia del modelo de embeddings, inicializándola si es necesario."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = await initialize_embeddings()  # Esta función ya es asíncrona
    return _embedding_model

# --- Helper Functions for Semantic Analysis ---
async def find_top_k_similar_items(
    new_embedding: List[float],
    knowledge_pool: List[Dict[str, Any]],
    k: int = 5
) -> List[Dict[str, Any]]:
    """
    Encuentra los 'k' ítems más similares de un pool de conocimiento
    basado en la similitud coseno de sus embeddings.
    """
    if not new_embedding or not knowledge_pool:
        return []

    # Calcular similitud para cada ítem que tenga un embedding
    scored_items = []
    for item in knowledge_pool:
        if item.get('embedding'):
            similarity = cosine_similarity(new_embedding, item['embedding'])
            scored_items.append((similarity, item))

    # Ordenar por similitud descendente
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # Devolver los k mejores ítems (solo el diccionario del ítem)
    return [item for similarity, item in scored_items[:k]]

async def get_text_embedding(text: str) -> Optional[List[float]]:
    """Genera el embedding vectorial para un texto dado."""
    embeddings_instance = await get_embedding_model_instance()
    if embeddings_instance:
        try:
            return await embeddings_instance.aembed_query(text)
        except Exception as e:
            logger.error(f"Error generando embedding para texto: {e}", exc_info=True)
            return None
    return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calcula la similitud coseno entre dos vectores."""
    if not vec1 or not vec2:
        return 0.0
    np_vec1 = np.array(vec1)
    np_vec2 = np.array(vec2)
    
    norm_vec1 = np.linalg.norm(np_vec1)
    norm_vec2 = np.linalg.norm(np_vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    
    return 1 - cosine(np_vec1, np_vec2)

async def extract_entities(text: str) -> List[Dict[str, str]]:
    """Extrae entidades nombradas de un texto usando spaCy."""
    try:
        nlp = await get_nlp_model()
        if not nlp:
            return []
        doc = nlp(text)
        return [{"text": ent.text, "type": ent.label_} for ent in doc.ents]
    except Exception as e:
        logger.error(f"Error al extraer entidades con spaCy: {e}", exc_info=True)
        return []

async def analyze_relationship_with_llm(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Usa Gemini para analizar la relación semántica profunda entre dos ítems.
    """
    llm = await get_gemini_summarizer_model_instance()  # Podemos reusar la instancia de Gemini
    if not llm:
        return None

    # Prepara el contenido para el prompt
    content_a = f"Título: {item_a.get('title', 'N/A')}\nContenido: {item_a.get('content')}"
    content_b = f"Título: {item_b.get('title', 'N/A')}\nContenido: {item_b.get('content')}"

    # Un prompt mucho más potente y específico
    prompt = f"""
    Eres un analista experto en gestión del conocimiento. Tu tarea es analizar la relación entre dos piezas de información (Ítem A y Ítem B).

    Aquí están los ítems:

    --- Ítem A ---
    Tipo: {item_a.get('type')}
    Fecha: {item_a.get('timestamp')}
    {content_a}
    --- FIN Ítem A ---

    --- Ítem B ---
    Tipo: {item_b.get('type')}
    Fecha: {item_b.get('timestamp')}
    {content_b}
    --- FIN Ítem B ---

    Analiza la relación semántica y clasifícala en una de las siguientes categorías:

    - "Duplicidad": El Ítem A y el Ítem B contienen esencialmente la misma información.
    - "Sinergia": Los ítems tratan temas complementarios o relacionados que, juntos, ofrecen una visión más completa. No son lo mismo, pero se refuerzan mutuamente.
    - "Evolución": Un ítem (normalmente el más reciente) actualiza, expande o corrige la información del otro.
    - "Contradicción": Los ítems presentan información o afirmaciones que se oponen directamente.
    - "Sin Relación Significativa": A pesar de algunas palabras clave en común, los temas centrales son diferentes y no hay una conexión útil.

    Responde únicamente en formato JSON con la siguiente estructura:
    {{
      "relationship_type": "...", // Una de las categorías de arriba
      "confidence_score": 0.0,    // Tu confianza en esta clasificación (de 0.0 a 1.0)
      "explanation": "...",       // Una justificación concisa de 1-2 frases explicando tu razonamiento.
      "action_suggestion": "..."  // Una sugerencia de acción para el usuario (ej. "Considera fusionar estos ítems", "Explora esta conexión para...", "Revisa esta posible contradicción").
    }}
    """

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        # Importante: El LLM puede devolver texto con formato incorrecto.
        # En producción, se necesita un parseo robusto.
        import json
        analysis_result = json.loads(response.content)
        return analysis_result
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error al analizar la relación con el LLM o parsear su respuesta: {e}", exc_info=True)
        logger.error(f"Respuesta del LLM que causó el error: {response.content if 'response' in locals() else 'N/A'}")
        return None

async def interpret_user_request_for_analysis(user_query: str) -> Dict[str, Any]:
    """
    Usa un LLM para interpretar la solicitud del usuario en lenguaje natural y la traduce
    a una acción estructurada y parámetros.
    """
    llm = await get_gemini_summarizer_model_instance()
    if not llm:
        return {"action": "error", "details": "LLM not available"}

    # Prompt de "tool calling" o "function calling"
    # Le describimos las acciones posibles y le pedimos que elija una y rellene los argumentos.
    prompt = f"""
    Eres un asistente inteligente que interpreta las peticiones de un usuario para activar una herramienta de análisis de conocimiento.
    Tu tarea es analizar la siguiente petición del usuario y determinar la acción a realizar y los parámetros necesarios.

    Petición del usuario: "{user_query}"

    Acciones disponibles:
    1. `run_full_analysis`: Ejecuta un análisis completo de todo el conocimiento. Se usa para peticiones generales como "analiza todo", "busca nuevas conexiones" o "ejecuta el análisis".
    2. `analyze_recent_items`: Analiza solo los ítems creados o modificados en un periodo reciente. Se usa para peticiones como "revisa lo último", "analiza mis notas de hoy" o "mira lo de esta semana".
    3. `analyze_specific_topic`: Analiza ítems relacionados con un tema o palabra clave específica. Se usa para peticiones como "analiza mis notas sobre 'Proyecto Hydra'" o "busca conexiones en mis documentos de marketing".
    4. `no_action`: Si la petición no parece estar relacionada con el análisis de conocimiento.

    Extrae la fecha de hoy si es necesario. Hoy es: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.

    Responde únicamente en formato JSON con la siguiente estructura:
    {{
      "action": "...", // "run_full_analysis", "analyze_recent_items", "analyze_specific_topic", o "no_action"
      "parameters": {{ // Parámetros para la acción elegida
        "days_ago": null, // (Para analyze_recent_items) Número de días hacia atrás a analizar.
        "topic_keywords": null // (Para analyze_specific_topic) Lista de palabras clave o temas.
      }}
    }}

    Ejemplos:
    - Petición: "Ejecuta un re-análisis completo de mi base de conocimiento" -> {{"action": "run_full_analysis", "parameters": {{"days_ago": null, "topic_keywords": null}}}}
    - Petición: "Revisa las conexiones en mis notas de los últimos 3 días" -> {{"action": "analyze_recent_items", "parameters": {{"days_ago": 3, "topic_keywords": null}}}}
    - Petición: "Encuentra sinergias en mis documentos sobre IA y optimización de costes" -> {{"action": "analyze_specific_topic", "parameters": {{"days_ago": null, "topic_keywords": ["IA", "optimización de costes"]}}}}
    - Petición: "¿Qué tiempo hace hoy?" -> {{"action": "no_action", "parameters": {{"days_ago": null, "topic_keywords": null}}}}
    """

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        # El mismo parseo robusto que antes
        import json
        structured_response = json.loads(response.content)
        return structured_response
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error interpretando la petición del usuario: {e}", exc_info=True)
        return {"action": "error", "details": str(e)}

async def summarize_text(text: str, max_length: int = 130) -> str:
    """Genera un resumen ejecutivo de un texto largo usando Gemini 1.5 Flash."""
    if not text:
        return ""

    # Si el texto es muy corto, no es necesario resumir.
    if len(text) < 100:  # Ajusta este umbral según necesites
        return text

    gemini_model = await get_gemini_summarizer_model_instance()
    if not gemini_model:
        logger.warning("Modelo Gemini para resumen no inicializado. Volviendo a texto truncado.")
        return text[:max_length] + "..." if len(text) > max_length else text

    try:
        # Puedes ajustar el prompt para controlar el estilo del resumen
        prompt = f"Por favor, resume el siguiente texto de forma concisa y ejecutiva, manteniendo los puntos clave. El resumen no debe exceder las {max_length} palabras:\n\n{text}"
        
        # Usar invoke para una llamada simple
        response = await gemini_model.ainvoke([HumanMessage(content=prompt)])
        summary = response.content
        
        # Asegurarse de que el resumen no exceda la longitud máxima si es posible
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    except Exception as e:
        logger.warning(f"Error resumiendo texto: {e}. Volviendo a texto truncado.", exc_info=True)
        return text[:max_length] + "..." if len(text) > max_length else text
    return text[:max_length] + "..." if len(text) > max_length else text

# --- Knowledge Retrieval and Standardization ---
async def get_all_knowledge(account_id: str) -> List[Dict[str, Any]]:
    """
    Recupera el conocimiento relevante del usuario (notas, memorias/documentos)
    en un formato estandarizado con embeddings.
    """
    all_items: List[Dict[str, Any]] = []
    account_uuid = uuid.UUID(account_id)
    async with DBSession(SessionLocal) as db:
        # Fetch Notes
        notes_stmt = select(Nota).where(Nota.account_id == account_uuid)
        notes = (await db.execute(notes_stmt)).scalars().all()
        for note in notes:
            # Si las notas ya tienen embedding persistente, úsalo.
            # De lo contrario, se generará aquí (menos eficiente).
            note_embedding = note.embedding if hasattr(note, 'embedding') and note.embedding else await get_text_embedding(note.content)
            all_items.append({
                'id': str(note.id),
                'content': note.content,
                'title': note.title,
                'type': 'note',
                'category': note.category,
                'timestamp': note.created_at,
                'embedding': note_embedding,
                'related_to_id': None
            })

        # Fetch Vector Memories (including document chunks)
        memories_stmt = select(Memory).where(Memory.account_id == account_uuid)
        memories = (await db.execute(memories_stmt)).scalars().all()
        for mem in memories:
            title = mem.content[:50] + "..." if len(mem.content) > 50 else mem.content
            category = mem.type

            all_items.append({
                'id': str(mem.id),
                'content': mem.content,
                'title': title,
                'type': mem.type,
                'category': category,
                'timestamp': mem.created_at,
                'embedding': mem.embedding,  # Memory objects should already have embeddings
                'related_to_id': None
            })
    logger.info(f"Retrieved {len(all_items)} knowledge items for account {account_id}")
    return all_items

async def store_proactive_insight(insight_data: Dict[str, Any]):
    """
    Persiste un insight proactivo en la base de datos, además de loguearlo.
    """
    # 1) Primero lo logeamos como antes
    logger.info(f"\n--- PROACTIVE INSIGHT DETECTADO ---")
    logger.info(f"  Cuenta: {insight_data.get('account_id', 'N/A')}")
    logger.info(f"  Tipo de Insight: {insight_data.get('type', 'N/A')}")
    logger.info(f"  Mensaje: {insight_data.get('insight_message', 'N/A')}")
    logger.info(f"  Confianza: {insight_data.get('confidence_score', 'N/A'):.2f}")
    logger.info(f"  Sugerencia de Acción: {insight_data.get('action_suggestion', 'N/A')}")
    logger.info(f"  Ítems Relacionados:")
    for item in insight_data.get('related_items', []):
        snippet = item.get('content', '')
        # Si el contenido es largo, resumirlo para el log
        if len(snippet) > 150:
            snippet = await summarize_text(snippet, max_length=150)
        logger.info(f"    - ID: {item.get('id', 'N/A')}, Título: '{item.get('title', 'Sin título')}' (Tipo: {item.get('type', 'N/A')}, Cat: {item.get('category', 'N/A')}), Fecha: {item.get('timestamp', 'N/A')}, Snippet: '{snippet}'")
    logger.info(f"-----------------------------------\n")

    # 2) Ahora lo guardamos en la base de datos
    try:
        async with DBSession(SessionLocal) as db:
            # Convert datetime objects in related_items to JSON-serializable format
            related_items = insight_data.get("related_items", [])
            serialized_items = []
            for item in related_items:
                serialized_item = item.copy()
                if 'timestamp' in serialized_item and isinstance(serialized_item['timestamp'], datetime.datetime):
                    serialized_item['timestamp'] = serialized_item['timestamp'].isoformat()
                serialized_items.append(serialized_item)
            
            pi = ProactiveInsight(
                account_id=uuid.UUID(insight_data["account_id"]),
                type=insight_data.get("type", "N/A"),
                insight_message=insight_data.get("insight_message", ""),
                confidence_score=insight_data.get("confidence_score", 0.0),
                action_suggestion=insight_data.get("action_suggestion"),
                related_items=serialized_items  # se serializa automáticamente a JSONB
            )
            db.add(pi)
            await db.commit()
            logger.info(f"Insight guardado en DB con id={pi.id}.")
    except Exception as e:
        logger.error(f"Error guardando insight en BBDD: {e}", exc_info=True)

# --- Main Analysis Logic (REFACTORIZADO) ---
async def analyze_new_entry(new_entry: Dict[str, Any]):
    """
    Analiza la nueva entrada encontrando los ítems más similares y usando un LLM
    para determinar la naturaleza de su relación.
    """
    account_id = new_entry.get('account_id')
    new_content = new_entry.get('content')

    if not account_id or not new_content:
        logger.warning("[Proactive Linker] Faltan datos en la nueva entrada. Abortando.")
        return

    logger.info(f"[Proactive Linker] Iniciando análisis semántico profundo para nueva entrada...")

    # 1. Obtener el embedding de la nueva entrada
    new_entry_embedding = await get_text_embedding(new_content)
    if not new_entry_embedding:
        logger.error("[Proactive Linker] No se pudo generar embedding para la nueva entrada. Abortando.")
        return
    
    # Asignar el embedding a la entrada para tenerlo a mano
    new_entry['embedding'] = new_entry_embedding
    if 'title' not in new_entry or not new_entry['title']:
        new_entry['title'] = new_content[:50] + "..."

    # 2. Recuperar TODO el conocimiento existente (por ahora)
    # En un sistema a gran escala, esto se reemplazaría con una llamada a una DB vectorial.
    all_knowledge = await get_all_knowledge(account_id)
    
    # Filtrar para no compararse a sí mismo
    existing_knowledge = [item for item in all_knowledge if item.get('id') != new_entry.get('id')]

    # 3. Encontrar los 'k' candidatos más prometedores usando la similitud vectorial
    # Este paso es clave para la eficiencia y para reducir falsos positivos.
    top_candidates = await find_top_k_similar_items(new_entry_embedding, existing_knowledge, k=5)

    if not top_candidates:
        logger.info("[Proactive Linker] No se encontraron candidatos semánticamente cercanos para análisis.")
        return

    logger.info(f"[Proactive Linker] Encontrados {len(top_candidates)} candidatos prometedores para análisis profundo con LLM.")

    insights_to_store: List[Dict[str, Any]] = []

    # 4. Iterar SOLO sobre los mejores candidatos y usar el LLM para el análisis
    for candidate_item in top_candidates:
        
        # El LLM ahora hace el trabajo pesado de clasificación
        analysis = await analyze_relationship_with_llm(new_entry, candidate_item)

        if analysis:
            relationship_type = analysis.get("relationship_type", None)
            if relationship_type and isinstance(relationship_type, str) and relationship_type != "Sin Relación Significativa":
                # Usamos la respuesta estructurada del LLM para crear el insight
                insight_type = relationship_type.lower()  # ej. "duplicidad", "sinergia"
                
                # Mapeamos a tus tipos de insight si es necesario
                type_mapping = {
                    "duplicidad": "duplicity",
                    "sinergia": "synergy",
                    "evolución": "evolution",
                    "contradicción": "contradiction"
                }
                mapped_type = type_mapping.get(insight_type, "synergy")  # Default a sinergia
                
                insight_message = f"Análisis de IA detectó: {relationship_type}. {analysis.get('explanation', '')}"

                insights_to_store.append({
                    'account_id': account_id,
                    'type': mapped_type,
                    'insight_message': insight_message,
                    'confidence_score': analysis.get('confidence_score', 0.8),  # Tomamos la confianza del LLM
                    'action_suggestion': analysis.get('action_suggestion', 'Revisa ambos ítems.'),
                    'related_items': [new_entry, candidate_item]
                })

    # (Opcional) La lógica para 'knowledge_gap' puede permanecer, ya que es diferente.
    # Se basa en la ausencia de información, no en la relación entre dos ítems.
    if "riesgo" in new_content.lower() and not any("plan de mitigacion" in item['content'].lower() for item in all_knowledge if item['type'] == 'note' or item['type'] == 'document'):
        insights_to_store.append({
            'account_id': account_id,
            'type': 'knowledge_gap',
            'insight_message': "Se ha identificado un 'riesgo' en la nueva entrada, pero no se encontró un 'plan de mitigación' relacionado en tu base de conocimiento.",
            'confidence_score': 0.8,
            'action_suggestion': "Considera crear un documento o nota detallando un plan para mitigar este riesgo.",
            'related_items': [new_entry]
        })
    
    # Example for project management context: If a project is mentioned without clear deliverables
    if ("proyecto" in new_content.lower() or "project" in new_content.lower()) and \
       not any("deliverable" in item['content'].lower() or "entrega" in item['content'].lower() for item in all_knowledge):
        insights_to_store.append({
            'account_id': account_id,
            'type': 'knowledge_gap',
            'insight_message': "Parece que has añadido información sobre un 'proyecto'. ¿Tienes un registro de sus entregables o fases clave?",
            'confidence_score': 0.7,
            'action_suggestion': "Asegúrate de documentar los entregables y la planificación del proyecto para un seguimiento efectivo.",
            'related_items': [new_entry]
        })

    # Almacenar todos los insights generados
    for insight in insights_to_store:
        await store_proactive_insight(insight)

    logger.info(f"[Proactive Linker] Análisis profundo completado. Se generaron {len(insights_to_store)} insights.")

# run_batch_analysis_job MODIFICADA
from sqlalchemy import or_, and_, func

async def run_batch_analysis_job(
    account_id_filter: Optional[str] = None,
    since_timestamp: Optional[datetime.datetime] = None,
    topic_keywords: Optional[List[str]] = None
):
    """
    Función principal para el trabajo de análisis. Acepta filtros para ejecuciones manuales o programadas.
    - account_id_filter: Ejecuta el análisis solo para una cuenta específica.
    - since_timestamp: Analiza ítems creados o modificados después de esta fecha.
    - topic_keywords: Filtra los ítems a analizar para que contengan estas palabras clave.
    
    Depende de las siguientes funciones auxiliares:
    - get_last_run_timestamp, update_last_run_timestamp
    - get_all_knowledge, get_text_embedding, find_top_k_similar_items
    - analyze_relationship_with_llm, store_proactive_insight
    """
    logger.info(f"--- [ANALYSIS JOB] Iniciando trabajo de vinculación proactiva de conocimiento ---")
    
    # Determinar si es una ejecución programada o manual.
    # Si es programada, se usa el timestamp de la última ejecución.
    is_scheduled_run = since_timestamp is None
    if is_scheduled_run:
        since_timestamp = get_last_run_timestamp()
    
    logger.info(f"Analizando ítems desde: {since_timestamp.isoformat() if since_timestamp else 'N/A'}")

    async with DBSession(SessionLocal) as db:
        # Obtener los IDs de las cuentas a procesar
        if account_id_filter:
            # Si se especifica una cuenta, procesar solo esa
            try:
                account_ids = [uuid.UUID(account_id_filter)]
            except ValueError:
                logger.error(f"El account_id_filter '{account_id_filter}' no es un UUID válido. Abortando.")
                return
        else:
            # Si no, procesar todas las cuentas en el sistema
            account_ids_stmt = select(Account.id).distinct()
            account_ids = (await db.execute(account_ids_stmt)).scalars().all()

        for account_id_uuid in account_ids:
            account_id = str(account_id_uuid)
            logger.info(f"==> Procesando cuenta: {account_id} <==")

            # 1. Obtener el POOL de conocimiento completo para esta cuenta.
            # Este pool sirve como el universo de comparación.
            knowledge_pool = await get_all_knowledge(account_id)
            if not knowledge_pool:
                logger.info(f"La cuenta {account_id} no tiene conocimiento para analizar. Saltando.")
                continue

            # 2. Identificar los ítems a ANALIZAR basados en los filtros aplicados.
            # Estos son los ítems "nuevos" o de interés.
            items_to_analyze = []
            
            # Primero, filtrar por fecha.
            candidate_items = [item for item in knowledge_pool if item.get('timestamp') and item['timestamp'] > since_timestamp]
            
            if topic_keywords:
                # Si se proveen palabras clave, filtrar aún más la lista de candidatos.
                keyword_filtered_items = []
                for item in candidate_items:
                    content_lower = item.get('content', '').lower()
                    if any(keyword.lower() in content_lower for keyword in topic_keywords):
                        keyword_filtered_items.append(item)
                items_to_analyze = keyword_filtered_items
            else:
                items_to_analyze = candidate_items

            if not items_to_analyze:
                logger.info(f"No se encontraron ítems que cumplan los criterios de análisis para la cuenta {account_id}.")
                continue
            
            logger.info(f"Encontrados {len(items_to_analyze)} ítems para analizar en profundidad en la cuenta {account_id}.")

            # 3. Iniciar el análisis profundo para cada ítem de interés.
            for item_to_analyze in items_to_analyze:
                logger.debug(f"Analizando ítem: {item_to_analyze.get('id')} - '{item_to_analyze.get('title', '')[:50]}...'")
                
                # Paso 3.1: Asegurar que tenemos un embedding para el ítem a analizar.
                item_embedding = item_to_analyze.get('embedding')
                if not item_embedding:
                    item_embedding = await get_text_embedding(item_to_analyze.get('content', ''))
                    if not item_embedding:
                        logger.warning(f"No se pudo generar embedding para el ítem {item_to_analyze.get('id')}. Saltando análisis para este ítem.")
                        continue
                
                # Paso 3.2: Encontrar los 'k' candidatos más prometedores del pool de conocimiento.
                # Excluimos el ítem actual de la piscina de candidatos para que no se compare consigo mismo.
                candidate_pool = [item for item in knowledge_pool if item.get('id') != item_to_analyze.get('id')]
                top_candidates = await find_top_k_similar_items(item_embedding, candidate_pool, k=10)

                if not top_candidates:
                    logger.debug(f"No se encontraron candidatos similares para el ítem {item_to_analyze.get('id')}.")
                    continue

                # Paso 3.3: Iterar sobre los mejores candidatos y usar el LLM para el análisis semántico.
                for candidate in top_candidates:
                    logger.debug(f"  -> Comparando con candidato: {candidate.get('id')} - '{candidate.get('title', '')[:50]}...'")
                    
                    # Llamada al LLM para que determine la relación.
                    analysis = await analyze_relationship_with_llm(item_to_analyze, candidate)

                    # Si el LLM encuentra una relación significativa, la procesamos.
                    if analysis and analysis.get("relationship_type") != "Sin Relación Significativa":
                        
                        # Mapear el tipo de relación a los tipos de insight de nuestro sistema.
                        relationship_type = analysis.get("relationship_type", "synergy").lower()
                        type_mapping = {"duplicidad": "duplicity", "sinergia": "synergy", "evolución": "evolution", "contradicción": "contradiction"}
                        mapped_type = type_mapping.get(relationship_type, "synergy")

                        # Preparar los datos para almacenar el insight.
                        insight_data = {
                            'account_id': account_id,
                            'type': mapped_type,
                            'insight_message': analysis.get('explanation', 'Análisis de IA detectó una conexión.'),
                            'confidence_score': analysis.get('confidence_score', 0.75),
                            'action_suggestion': analysis.get('action_suggestion', 'Considera revisar estos dos ítems juntos.'),
                            'related_items': [item_to_analyze, candidate]
                        }
                        
                        # Almacenar el insight en la base de datos (esta función debería manejar la prevención de duplicados).
                        await store_proactive_insight(insight_data)

    # 4. Actualizar el timestamp de la última ejecución solo si fue una ejecución programada completa.
    if is_scheduled_run:
        update_last_run_timestamp(datetime.datetime.now(datetime.timezone.utc))
        logger.info("--- [BATCH JOB] Timestamp de ejecución automática actualizado exitosamente. ---")
    
    logger.info("--- [ANALYSIS JOB] Trabajo de vinculación de conocimiento completado. ---")

# --- Tool Input Schema and Class ---
class ProactiveKnowledgeLinkerInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de vinculación proactiva de conocimiento.
    Valida que el argumento necesario sea proporcionado por el LLM.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    new_entry_content: str = Field(
        ...,
        description="El contenido de la nueva entrada (nota, memoria, documento) a analizar para generar insights proactivos."
    )
    new_entry_title: Optional[str] = Field(
        None,
        description="El título de la nueva entrada, si está disponible."
    )
    new_entry_type: Optional[str] = Field(
        "general",
        description="El tipo de la nueva entrada (por ejemplo, 'note', 'memory', 'document')."
    )
    new_entry_category: Optional[str] = Field(
        None,
        description="La categoría de la nueva entrada, si aplica."
    )

class ProactiveKnowledgeLinkerTool(BaseTool):
    """
    Una herramienta de LangChain que analiza nuevas entradas de información y genera insights proactivos
    sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento.
    """
    name: str = "proactive_knowledge_linker_tool"
    description: str = (
        "Útil para analizar nuevas entradas de información (notas, memorias, documentos) y generar insights "
        "proactivos sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento. "
        "Esta herramienta se activa automáticamente cuando se añade nueva información."
    )
    args_schema: Type[BaseModel] = ProactiveKnowledgeLinkerInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    def __init__(self, **kwargs):
        """Inicializa la herramienta con cualquier configuración necesaria."""
        super().__init__(**kwargs)
        logger.info("Inicializando ProactiveKnowledgeLinkerTool")

    async def _arun(self, account_id: str, new_entry_content: str, new_entry_title: Optional[str] = None, new_entry_type: Optional[str] = "general", new_entry_category: Optional[str] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            new_entry_content: El contenido de la nueva entrada a analizar.
            new_entry_title: El título de la nueva entrada (opcional).
            new_entry_type: El tipo de la nueva entrada (opcional, por defecto 'general').
            new_entry_category: La categoría de la nueva entrada (opcional).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando ProactiveKnowledgeLinkerTool para la cuenta '{account_id}' con nueva entrada.")
        try:
            new_entry = {
                'account_id': account_id,
                'content': new_entry_content,
                'title': new_entry_title,
                'type': new_entry_type,
                'category': new_entry_category,
                'timestamp': datetime.datetime.now(datetime.timezone.utc)
            }
            # Programar el análisis como tarea en segundo plano para no bloquear
            asyncio.create_task(analyze_new_entry(new_entry))
            logger.info(f"Análisis proactivo programado para la cuenta '{account_id}'.")
            return "Análisis proactivo de la nueva entrada iniciado. Se generarán insights en segundo plano."
        except Exception as e:
            logger.error(f"Error en ProactiveKnowledgeLinkerTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al iniciar el análisis proactivo: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("proactive_knowledge_linker_tool no soporta ejecución síncrona.")

# Función para ser llamada automáticamente tras añadir nueva información
async def proactive_knowledge_linker_trigger(new_entry: Dict[str, Any]):
    """
    Trigger principal: se llama tras añadir una nota, memoria o documento.
    
    Esta función ahora es una corrutina y debe ser llamada con `await`
    o programada como una tarea en segundo plano.
    """
    # Añadir timestamp a la nueva entrada si no lo tiene.
    if 'timestamp' not in new_entry:
        new_entry['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

    # Programar analyze_new_entry como una tarea en segundo plano
    # para no bloquear la operación principal (ej. añadir una nota).
    try:
        # Asegurarse de que hay un bucle de eventos ejecutándose
        asyncio.get_running_loop()
    except RuntimeError:
        # Si no hay un bucle ejecutándose (ej. llamada desde un contexto síncrono
        # en desarrollo o pruebas), creamos uno temporal para ejecutar la tarea.
        logger.warning("No hay un bucle de eventos ejecutándose. Creando uno para proactive_knowledge_linker_trigger.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(analyze_new_entry(new_entry))
        return

    # Si hay un bucle ejecutándose, programar la tarea normalmente
    asyncio.create_task(analyze_new_entry(new_entry))
    logger.info("[Proactive Linker] Tarea de análisis proactivo programada en segundo plano.")
