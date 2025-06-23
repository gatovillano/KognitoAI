# tools/proactive_knowledge_linker_tool.py

"""
proactive_knowledge_linker_tool.py
Herramienta de Vinculación Proactiva de Conocimiento para KAI

Esta herramienta se activa automáticamente cada vez que se añade nueva información (nota, memoria, documento).
Analiza la nueva entrada, la compara con el conocimiento existente y genera insights proactivos sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento.
"""

import logging
import asyncio
import datetime
from typing import Any, Dict, List, Optional
import uuid
import numpy as np
from scipy.spatial.distance import cosine # type: ignore

# Importaciones de la base de datos y la configuración
from core.database import SessionLocal, Nota, AgendaEvent, Recordatorio, Memory, Account
from utils.db_session import DBSession
from core.config import settings
from utils.embeddings import initialize_embeddings
from langchain_core.embeddings import Embeddings

# Modelos para NLP y summarization - cargados de forma singleton
import spacy
from textblob import TextBlob # type: ignore
from keybert import KeyBERT # type: ignore
# from transformers import pipeline # Ya no necesitamos esto para el resumen local
from sqlalchemy import select, text # Import text for raw SQL if needed

# Importar el modelo de Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# --- Singleton Models for NLP and Embeddings ---
_nlp_model: Optional[spacy.Language] = None
_keybert_model: Optional[KeyBERT] = None
# _summarizer_pipeline: Optional[pipeline] = None # Ya no necesitamos el pipeline de transformers
_gemini_summarizer_model: Optional[ChatGoogleGenerativeAI] = None # Nuevo para Gemini
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
        
        _nlp_model = await loop.run_in_executor(None, lambda: spacy.load("en_core_web_sm"))
        logger.info("Modelo spaCy cargado.")
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
        _gemini_summarizer_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
        logger.info("Modelo Gemini 1.5 Flash inicializado.")
    return _gemini_summarizer_model

async def get_embedding_model_instance() -> Embeddings:
    """Obtiene y devuelve la instancia del modelo de embeddings, inicializándola si es necesario."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = await initialize_embeddings() # Esta función ya es asíncrona
    return _embedding_model

# --- Helper Functions for Semantic Analysis ---

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
    nlp = await get_nlp_model()
    if not nlp:
        return []
    doc = nlp(text)
    return [{"text": ent.text, "type": ent.label_} for ent in doc.ents]

async def summarize_text(text: str, max_length: int = 130) -> str:
    """Genera un resumen ejecutivo de un texto largo usando Gemini 1.5 Flash."""
    if not text:
        return ""

    # Si el texto es muy corto, no es necesario resumir.
    if len(text) < 100: # Ajusta este umbral según necesites
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
            # Ver punto 2 para cómo persistir el embedding de las notas.
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
                'embedding': mem.embedding, # Memory objects should already have embeddings
                'related_to_id': None
            })
    logger.info(f"Retrieved {len(all_items)} knowledge items for account {account_id}")
    return all_items

async def store_proactive_insight(insight_data: Dict[str, Any]):
    """
    Almacena o notifica un insight proactivo generado de forma persistente.
    Para esta implementación, se limitará a imprimir en el log.
    En un sistema real, esto implicaría guardar en una tabla de DB,
    enviar una notificación al usuario (Telegram, email), etc.
    """
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

# --- Main Analysis Logic ---

async def analyze_new_entry(new_entry: Dict[str, Any]):
    """
    Analiza la nueva entrada y busca relaciones, sinergias, duplicidades, contradicciones y brechas.
    Si encuentra algo relevante, genera un insight proactivo.
    """
    account_id = new_entry.get('account_id')
    new_content = new_entry.get('content')
    new_title = new_entry.get('title') or (new_content[:50] + "..." if new_content else "Sin título")
    new_type = new_entry.get('type')
    new_timestamp = new_entry.get('timestamp') or datetime.datetime.now(datetime.timezone.utc)

    if not account_id or not new_content:
        logger.warning("[Proactive Linker] account_id o contenido no proporcionado en la nueva entrada. Abortando análisis.")
        return

    logger.info(f"[Proactive Linker] Iniciando análisis proactivo para nueva entrada (Tipo: {new_type}, Título: '{new_title}')...")

    all_knowledge = await get_all_knowledge(account_id)
    new_entry_embedding = await get_text_embedding(new_content)
    new_entry_entities = await extract_entities(new_content)

    if new_entry_embedding is None:
        logger.error(f"[Proactive Linker] No se pudo generar embedding para la nueva entrada. Saltando análisis semántico.")
        return

    insights_to_store: List[Dict[str, Any]] = []

    # Iterar sobre los elementos de conocimiento existentes
    for existing_item in all_knowledge:
        # No comparar un elemento consigo mismo (ej. si es una actualización)
        if existing_item.get('id') == new_entry.get('id'): 
            continue

        existing_embedding = existing_item.get('embedding')
        existing_content = existing_item.get('content')
        existing_title = existing_item.get('title') or (existing_content[:50] + "..." if existing_content else "Sin título")
        existing_type = existing_item.get('type')
        existing_timestamp = existing_item.get('timestamp')

        if existing_embedding is None:
            # Si el embedding del elemento existente falta y hay contenido, generarlo
            if existing_content:
                existing_embedding = await get_text_embedding(existing_content)
                existing_item['embedding'] = existing_embedding # Actualizar en la lista para futuras comparaciones
            if existing_embedding is None:
                logger.warning(f"No se pudo generar embedding para el elemento existente ID {existing_item.get('id')}. Saltando comparación semántica con este elemento.")
                continue

        # Calcular similitud semántica
        similarity = cosine_similarity(new_entry_embedding, existing_embedding)
        
        # Extraer entidades para el elemento existente (se hace solo si se necesita, puede ser costoso)
        existing_entities = await extract_entities(existing_content) if existing_content else []
        
        # Encontrar entidades comunes entre la nueva entrada y el elemento existente
        common_entities_new = {ent['text'].lower() for ent in new_entry_entities}
        common_entities_existing = {ent['text'].lower() for ent in existing_entities}
        overlapping_entities = common_entities_new.intersection(common_entities_existing)
        
        # --- Regla 1: Detección de Duplicidad (Alta Similitud Semántica + Tipo Similar) ---
        if similarity > settings.DUPLICITY_SIMILARITY_THRESHOLD and new_type == existing_type:
            insight_message = f"Posible duplicidad detectada entre la nueva {new_type} '{new_title}' y la {existing_type} '{existing_title}'."
            action_suggestion = f"Considera fusionar o eliminar una de las entradas. La similitud semántica es alta ({similarity:.2f})."
            insights_to_store.append({
                'account_id': account_id,
                'type': 'duplicity',
                'insight_message': insight_message,
                'confidence_score': similarity,
                'action_suggestion': action_suggestion,
                'related_items': [new_entry, existing_item]
            })
        # --- Regla 2: Sinergia/Conexión (Similitud Semántica Moderada) ---
        elif similarity > settings.SYNERGY_SIMILARITY_THRESHOLD: # Umbral más bajo para sinergias
            insight_message = f"Conexión potencial detectada: La nueva {new_type} '{new_title}' tiene similitud con la {existing_type} '{existing_title}'."
            action_suggestion = f"Ambos tratan temas relacionados (similitud {similarity:.2f}). Podrías explorarlos juntos o vincularlos explícitamente."
            insights_to_store.append({
                'account_id': account_id,
                'type': 'synergy',
                'insight_message': insight_message,
                'confidence_score': similarity,
                'action_suggestion': action_suggestion,
                'related_items': [new_entry, existing_item]
            })

        # --- Regla 3: Detección de Contradicciones Lógicas (Entidades Comunes + Diferencia de Sentimiento/Hechos) ---
        # Esta es una versión simplificada y heurística. Una implementación robusta requeriría un LLM
        # para razonar sobre los hechos o una base de conocimiento más estructurada.
        if overlapping_entities:
            new_text_blob = TextBlob(new_content)
            existing_text_blob = TextBlob(existing_content)
            
            # Heurística simple: Si hay entidades comunes y una gran diferencia de sentimiento
            if abs(new_text_blob.sentiment.polarity - existing_text_blob.sentiment.polarity) > settings.CONTRADICTION_SENTIMENT_THRESHOLD:
                 insight_message = f"Posible contradicción o cambio de perspectiva para entidades como '{', '.join(list(overlapping_entities)[:2])}'."
                 action_suggestion = f"La nueva {new_type} tiene un sentimiento diferente ({new_text_blob.sentiment.polarity:.2f}) a la {existing_type} ({existing_text_blob.sentiment.polarity:.2f}) sobre temas comunes. Revisa ambos contenidos."
                 insights_to_store.append({
                    'account_id': account_id,
                    'type': 'contradiction',
                    'insight_message': insight_message,
                    'confidence_score': (similarity + abs(new_text_blob.sentiment.polarity - existing_text_blob.sentiment.polarity)) / 2,
                    'action_suggestion': action_suggestion,
                    'related_items': [new_entry, existing_item]
                 })
            # Añadir una heurística más específica para contradicciones de fechas/valores si fuera posible
            # (requeriría un parser de fechas y números más robusto)

        # --- Regla 4: Evolución/Cambio de Información en el Tiempo ---
        if overlapping_entities and existing_timestamp and new_timestamp and new_timestamp > existing_timestamp:
            time_diff_days = (new_timestamp - existing_timestamp).days
            if time_diff_days > settings.EVOLUTION_MIN_DAYS_THRESHOLD: # Solo si ha pasado un tiempo relevante
                # Aquí se podría usar un LLM para preguntar si el nuevo texto actualiza el viejo
                # Para simplificar, si hay similitud moderada y una entidad común, y es más reciente:
                if similarity > 0.6: # Umbral para sugerir evolución
                    insight_message = f"Posible evolución en la información sobre '{', '.join(list(overlapping_entities)[:2])}'."
                    action_suggestion = f"La nueva entrada '{new_title}' ({new_timestamp.strftime('%Y-%m-%d')}) parece actualizar o complementar la información de '{existing_title}' ({existing_timestamp.strftime('%Y-%m-%d')}). Revisa cómo ha cambiado el tema."
                    insights_to_store.append({
                        'account_id': account_id,
                        'type': 'evolution',
                        'insight_message': insight_message,
                        'confidence_score': similarity,
                        'action_suggestion': action_suggestion,
                        'related_items': [new_entry, existing_item]
                    })

    # --- Regla 5: Detección de Brechas de Conocimiento (más genérica o basada en patrones) ---
    # Este tipo de regla a menudo depende de un conocimiento predefinido de lo que "debería" existir.
    # Ejemplo: Si se menciona un "riesgo" pero no hay "plan de mitigación"
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

    logger.info(f"[Proactive Linker] Análisis completado para nueva entrada. Se generaron {len(insights_to_store)} insights.")


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
        # En un entorno de servidor como FastAPI, un bucle ya estará ejecutándose.
        logger.warning("No hay un bucle de eventos ejecutándose. Creando uno para proactive_knowledge_linker_trigger.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(analyze_new_entry(new_entry))
        return

    # Si hay un bucle ejecutándose, programar la tarea normalmente
    asyncio.create_task(analyze_new_entry(new_entry))
    logger.info("[Proactive Linker] Tarea de análisis proactivo programada en segundo plano.")