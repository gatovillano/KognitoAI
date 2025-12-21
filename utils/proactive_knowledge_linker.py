# utils/proactive_knowledge_linker.py (VERSIÓN MEJORADA)

"""
Utilidad de Vinculación Proactiva de Conocimiento para KAI

Esta utilidad contiene la lógica central para el análisis proactivo de conocimiento.
Se activa automáticamente dos veces al día para analizar notas, memorias y documentos del usuario,
y también puede ser llamada por el agente bajo demanda si el usuario lo solicita.
"""

import json
import logging
import asyncio
import datetime
from typing import Any, Dict, List, Optional
import uuid
import numpy as np
from scipy.spatial.distance import cosine

# Importaciones de la base de datos y la configuración
from core.database import ProactiveInsight, SessionLocal, Nota, Account, AnalyzedPair
from utils.db_session import DBSession
from sqlalchemy import select, or_, and_

from langchain_core.embeddings import Embeddings

# Modelos para NLP y summarization - cargados de forma singleton
import spacy
from keybert import KeyBERT

# Importar el modelo de Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)
logging.getLogger("langchain_community.vectorstores.pgvector").setLevel(logging.DEBUG)
# --- MODELOS SINGLETON ---
_nlp_model: Optional["spacy.language.Language"] = None
_keybert_model: KeyBERT | None = None
_gemini_model: Optional[ChatGoogleGenerativeAI] = None
_embedding_model: Optional[Embeddings] = None

async def get_nlp_model() -> "spacy.language.Language":
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
            _nlp_model = await loop.run_in_executor(None, lambda: spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"]))
            if _nlp_model is None:
                raise ValueError("Failed to load spaCy model")
            logger.info("Modelo spaCy cargado.")
        except Exception as e:
            logger.error(f"Error al cargar el modelo spaCy 'en_core_web_sm': {e}", exc_info=True)
            raise
    return _nlp_model  # type: ignore

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
    assert _keybert_model is not None
    return _keybert_model

async def get_gemini_model() -> ChatGoogleGenerativeAI:
    """Carga y devuelve el modelo Gemini 1.5 Flash para summarization, inicializándolo solo una vez."""
    global _gemini_model
    if _gemini_model is None:
        logger.info("Inicializando modelo Gemini...")
        _gemini_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2,
            disable_streaming=False  # Habilita streaming
        )
        logger.info("Modelo Gemini inicializado.")
    return _gemini_model

async def get_embedding_model_instance() -> Embeddings:
    """Obtiene y devuelve la instancia del modelo de embeddings."""
    from utils.embeddings import get_embedding_model
    embedding_model = get_embedding_model()
    if embedding_model is None:
        raise ValueError("El modelo de embeddings no está inicializado. Debe llamarse initialize_embeddings() al inicio de la aplicación.")
    return embedding_model

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
        if 'embedding' in item and item['embedding'] is not None:
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
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    np_vec1 = np.array(vec1)
    np_vec2 = np.array(vec2)
    
    norm_vec1 = np.linalg.norm(np_vec1)
    norm_vec2 = np.linalg.norm(np_vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    
    return 1 - cosine(np_vec1, np_vec2)

async def has_been_analyzed(db_session: Any, account_id: str, item1_id: str, item2_id: str) -> bool:
    """Verifica si un par de ítems ya ha sido analizado."""
    # Asegurar orden lexicográfico para la unicidad
    doc_id_a, doc_id_b = sorted([item1_id, item2_id])
    stmt = select(AnalyzedPair).where(
        AnalyzedPair.account_id == uuid.UUID(account_id),
        AnalyzedPair.document_id_a == doc_id_a,
        AnalyzedPair.document_id_b == doc_id_b
    )
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none() is not None

async def mark_as_analyzed(db_session: Any, account_id: str, item1_id: str, item2_id: str):
    """Marca un par de ítems como analizado."""
    doc_id_a, doc_id_b = sorted([item1_id, item2_id])
    analyzed_pair = AnalyzedPair(
        account_id=uuid.UUID(account_id),
        document_id_a=doc_id_a,
        document_id_b=doc_id_b,
        last_analyzed_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(analyzed_pair)
    await db_session.commit()

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

# --- NUEVA FUNCIÓN DE ANÁLISIS CON LLM ---
async def analyze_relationship_with_llm(item_a: Dict[str, Any], item_b: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Usa Gemini para analizar la relación semántica profunda entre dos ítems."""
    llm = await get_gemini_model()
    if not llm: 
        return None

    prompt = f"""
    Eres un analista de relaciones de conocimientos en ideas innovadoras experto. Analiza la relación entre dos documentos de manera objetiva y considera todas las posibles relaciones sin sesgo hacia ninguna en particular.

    --- {item_a.get('title', 'Documento 1')} ---
    Tipo: {item_a.get('type')}
    Contenido: {item_a.get('content')}
    --- FIN {item_a.get('title', 'Documento 1')} ---

    --- {item_b.get('title', 'Documento 2')} ---
    Tipo: {item_b.get('type')}
    Contenido: {item_b.get('content')}
    --- FIN {item_b.get('title', 'Documento 2')} ---

    Clasifica la relación en una de las siguientes categorías, asegurándote de evaluar cada una de manera equitativa:
    - "Duplicidad": Los documentos contienen información casi idéntica o redundante.
    - "Sinergia": Los documentos se complementan, aportando valor conjunto mayor que individual.
    - "Evolución": Un documento parece ser una versión actualizada o desarrollada del otro.
    - "Contradicción": Los documentos presentan información opuesta o incompatible.
    - "Sin Relación Significativa": No hay conexión relevante entre los documentos.

    Responde ÚNICAMENTE en formato JSON:
    {{
      "relationship_type": "...",
      "confidence_score": 0.0,
      "explanation": "...",
      "action_suggestion": "..."
    }}
    """
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, str):
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
        else:
            content = str(content)
        analysis_result = json.loads(content)
        return analysis_result
    except Exception as e:
        logger.error(f"Error analizando relación con LLM: {e}", exc_info=True)
        return None

# --- NUEVA FUNCIÓN PARA INTERPRETAR PETICIONES ---
async def interpret_user_request_for_analysis(user_query: str) -> Dict[str, Any]:
    """Usa un LLM para traducir la petición del usuario en una acción estructurada."""
    llm = await get_gemini_model()
    if not llm:
        return {"action": "error", "details": "LLM not available"}

    # Prompt de "tool calling" o "function calling"
    prompt = f"""
    Eres un investigador experto en la área de análisis de conocimiento. Interpreta las peticiones de un usuario para activar una herramienta de análisis de conocimiento.
    Tu tarea es analizar la siguiente petición del usuario y determinar la acción a realizar y los parámetros necesarios.

    Petición del usuario: "{user_query}"

    Acciones disponibles:
    1. `run_full_analysis`: Ejecuta un análisis completo de todo el conocimiento.
    2. `analyze_recent_items`: Analiza solo los ítems creados o modificados en un periodo reciente.
    3. `analyze_specific_topic`: Analiza ítems relacionados con un tema o palabra clave específica.
    4. `no_action`: Si la petición no parece estar relacionada con el análisis de conocimiento.

    Extrae la fecha de hoy si es necesario. Hoy es: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.

    Responde únicamente en formato JSON con la siguiente estructura:
    {{
      "action": "...",
      "parameters": {{ 
        "days_ago": null,
        "topic_keywords": null
      }}
    }}
    """

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, str):
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
        else:
            content = str(content)
        structured_response = json.loads(content)
        return structured_response
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error interpretando la petición del usuario: {e}", exc_info=True)
        return {"action": "error", "details": str(e)}

async def summarize_text(text: str, max_length: int = 130) -> str:
    """Genera un resumen ejecutivo de un texto largo usando Gemini 1.5 Flash."""
    if not text:
        return ""

    # Si el texto es muy corto, no es necesario resumir.
    if len(text) < 100:
        return text

    gemini_model = await get_gemini_model()
    if not gemini_model:
        logger.warning("Modelo Gemini para resumen no inicializado. Volviendo a texto truncado.")
        return text[:max_length] + "..." if len(text) > max_length else text

    try:
        prompt = f"Por favor, resume el siguiente texto de forma concisa y ejecutiva, manteniendo los puntos clave. El resumen no debe exceder las {max_length} palabras:\n\n{text}"
        response = await gemini_model.ainvoke([HumanMessage(content=prompt)])
        summary = response.content
        
        if isinstance(summary, str) and len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary if isinstance(summary, str) else str(summary)
    except Exception as e:
        logger.warning(f"Error resumiendo texto: {e}. Volviendo a texto truncado.", exc_info=True)
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
            note_embedding = note.embedding if hasattr(note, 'embedding') and note.embedding is not None else await get_text_embedding(note.content)
            all_items.append({
                'id': str(note.id),
                'content': note.content,
                'title': note.title,
                'type': 'note',
                'category': note.category,
                'timestamp': note.created_at,
                'embedding': note_embedding,
                'related_to_id': None,
                'account_id': account_id
            })

        # Fetch Vector Memories (including document chunks) from langchain_pg_embedding
        from core.database import LangchainPgCollection, LangchainPgEmbedding

        # Obtener los UUIDs de las colecciones relevantes para el usuario
        relevant_collection_uuids = []
        collection_names = [
            f"user_memories_{account_id}",
            f"user_documents_{account_id}",
            "global_knowledge_base"
        ]

        for c_name in collection_names:
            stmt = select(LangchainPgCollection.uuid).where(LangchainPgCollection.name == c_name)
            result = await db.execute(stmt)
            c_uuid = result.scalar_one_or_none()
            if c_uuid:
                relevant_collection_uuids.append(c_uuid)

        # Usar la nueva estructura optimizada con account_id directo
        memories = []
        memories_stmt = select(LangchainPgEmbedding).where(
            LangchainPgEmbedding.account_id == account_uuid,
            LangchainPgEmbedding.content_type == 'user_memories'
        )
        result = await db.execute(memories_stmt)
        memories = result.mappings().all()

        for mem in memories:
            cmetadata = mem['cmetadata'] if 'cmetadata' in mem else {}
            content = mem.get('document', '')
            mem_type = cmetadata.get('type', 'general_memory')
            title = content[:50] + "..." if len(content) > 50 else content
            category = mem_type

            all_items.append({
                'id': str(mem.get('id', '')),
                'content': content,
                'title': title,
                'type': mem_type,
                'category': category,
                'timestamp': cmetadata.get('created_at', None),  # Puede no estar disponible, ajustar según necesidad
                'embedding': mem.get('embedding', None),
                'related_to_id': None,
                'account_id': account_id
            })
    logger.info(f"Retrieved {len(all_items)} knowledge items for account {account_id}")
    return all_items

# --- FUNCIÓN DE GUARDADO MEJORADA ---
async def store_proactive_insight(insight_data: Dict[str, Any]):
    """Persiste un insight proactivo en la base de datos y envía una notificación al frontend."""
    logger.info(f"--- INSIGHT DETECTADO: {insight_data.get('type')} ---")
    logger.info(f"  Cuenta: {insight_data.get('account_id', 'N/A')}")
    logger.info(f"  Tipo de Insight: {insight_data.get('type', 'N/A')}")
    logger.info(f"  Mensaje: {insight_data.get('insight_message', 'N/A')}")
    logger.info(f"  Confianza: {insight_data.get('confidence_score', 'N/A'):.2f}")
    logger.info(f"  Sugerencia de Acción: {insight_data.get('action_suggestion', 'N/A')}")
    logger.info(f"  Ítems Relacionados:")
    for item in insight_data.get('related_items', []):
        snippet = item.get('content', '')
        if len(snippet) > 150:
            snippet = await summarize_text(snippet, max_length=150)
        logger.info(f"    - ID: {item.get('id', 'N/A')}, Título: '{item.get('title', 'Sin título')}' (Tipo: {item.get('type', 'N/A')}, Cat: {item.get('category', 'N/A')}), Fecha: {item.get('timestamp', 'N/A')}, Snippet: '{snippet}'")
    logger.info(f"-----------------------------------\n")

    # Enviar notificación al frontend (esto asume que hay un sistema de notificaciones o websocket en lugar)
    # TODO: Implementar sistema de notificaciones al frontend (por ejemplo, mediante websocket o API)
    logger.info("Notificación al frontend pendiente de implementación para nuevo insight detectado.")

    try:
        account_id_str = insight_data.get("account_id")
        if not account_id_str:
            logger.error("No se proporcionó account_id para guardar el insight.")
            return

        try:
            account_id_uuid = uuid.UUID(account_id_str)
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir account_id '{account_id_str}' a UUID: {e}")
            return

        async with DBSession(SessionLocal) as db:
            # Serializar ítems para JSONB, excluyendo 'embedding' y convirtiendo datetime
            related_items = [
                {k: (v.isoformat() if isinstance(v, datetime.datetime) else v) for k, v in item.items() if k != 'embedding'}
                for item in insight_data.get("related_items", [])
            ]

            # Agregar metadata de herramienta utilizada
            related_items_with_metadata = {
                "items": related_items,
                "tool_used": "proactive_knowledge_linker_tool.py",
                "analysis_metadata": {
                    "tool_used": "proactive_knowledge_linker_tool.py",
                    "analysis_type": "proactive_insight",
                    "insight_type": insight_data.get("type", "unknown"),
                    "created_at": datetime.datetime.now().isoformat()
                }
            }

            pi = ProactiveInsight(
                account_id=account_id_uuid,
                type=insight_data.get("type", "unknown"),
                insight_message=insight_data.get("insight_message", ""),
                confidence_score=insight_data.get("confidence_score", 0.0),
                action_suggestion=insight_data.get("action_suggestion"),
                related_items=related_items_with_metadata
            )
            db.add(pi)
            await db.commit()
            await db.refresh(pi) # Asegurarse de que el ID está cargado
            logger.info(f"Insight guardado en DB con id={pi.id}.")

            # Enviar notificación al frontend via WebSocket AHORA que tenemos el ID
            try:
                from core.dependencies import get_websocket_manager
                manager = get_websocket_manager()
                
                payload = {
                    "type": "proactive_insight",
                    "content": pi.insight_message,
                    "insight_type": pi.type,
                    "confidence": pi.confidence_score,
                    "action_suggestion": pi.action_suggestion,
                    "insight_id": str(pi.id)
                }
                
                await manager.send_personal_message(payload, str(pi.account_id))
                logger.info(f"Notificación de insight {pi.id} enviada a la cuenta {pi.account_id} via WebSocket.")

            except Exception as e:
                logger.error(f"Error enviando la notificación WebSocket para el insight {pi.id}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error guardando insight en BBDD: {e}", exc_info=True)

# --- LÓGICA DE ANÁLISIS REFACTORIZADA ---
async def analyze_entry(entry_to_analyze: Dict[str, Any], knowledge_pool: List[Dict[str, Any]], top_k_candidates: int = 10):
    """
    Analiza una sola entrada contra el pool de conocimiento, evitando re-análisis de pares ya procesados.
    """
    account_id = entry_to_analyze.get('account_id')
    entry_id = entry_to_analyze.get('id')
    if not account_id or not entry_id:
        logger.warning("No se proporcionó account_id o ID de entrada para el análisis. No se guardarán insights.")
        return

    entry_embedding = await get_text_embedding(entry_to_analyze.get('content', ''))
    if not entry_embedding:
        return

    # Filtra el pool para no compararse a sí mismo
    candidate_pool = [item for item in knowledge_pool if item.get('id') != entry_id]
    
    # Encuentra los N mejores candidatos por similitud vectorial
    top_candidates = await find_top_k_similar_items(entry_embedding, candidate_pool, k=top_k_candidates)

    async with DBSession(SessionLocal) as db:
        for candidate in top_candidates:
            candidate_id = candidate.get('id')
            if not candidate_id:
                continue

            # Verificar si el par ya ha sido analizado
            if await has_been_analyzed(db, account_id, entry_id, candidate_id):
                logger.info(f"Par ({entry_id}, {candidate_id}) ya analizado. Saltando.")
                continue

            analysis = await analyze_relationship_with_llm(entry_to_analyze, candidate)
            if analysis and analysis.get("relationship_type") != "Sin Relación Significativa":
                relationship_type = analysis.get("relationship_type")
                insight_data = {
                    'account_id': account_id,
                    'type': relationship_type.lower() if relationship_type else "unknown",
                    'insight_message': analysis.get('explanation', ''),
                    'confidence_score': analysis.get('confidence_score', 0.0),
                    'action_suggestion': analysis.get('action_suggestion', ''),
                    'related_items': [entry_to_analyze, candidate]
                }
                await store_proactive_insight(insight_data)
                await mark_as_analyzed(db, account_id, entry_id, candidate_id) # Marcar como analizado

# --- FUNCIÓN PRINCIPAL DEL JOB REFACTORIZADA ---
async def run_batch_analysis_job(
    account_id_filter: Optional[str] = None,
    since_timestamp: Optional[datetime.datetime] = None,
    topic_keywords: Optional[List[str]] = None,
    top_k: Optional[int] = None, # Nuevo parámetro para top_k
    thread_id: Optional[str] = None # Nuevo parámetro
):
    """
    Función principal para el trabajo de análisis. Acepta filtros para ejecuciones manuales o programadas.
    - account_id_filter: Ejecuta el análisis solo para una cuenta específica.
    - since_timestamp: Analiza ítems creados o modificados después de esta fecha.
    - topic_keywords: Filtra los ítems a analizar para que contengan estas palabras clave.
    """
    logger.info(f"--- [ANALYSIS JOB] Iniciando trabajo de vinculación proactiva de conocimiento ---")
    
    # TODO: Implementar sistema de notificaciones al frontend
    notification_system_available = False
    logger.info("Sistema de notificaciones al frontend pendiente de implementación.")

    async with DBSession(SessionLocal) as db:
        # Obtener los IDs de las cuentas a procesar
        if account_id_filter:
            try:
                account_ids = [uuid.UUID(account_id_filter)]
            except ValueError:
                logger.error(f"El account_id_filter '{account_id_filter}' no es un UUID válido. Abortando.")
                return
        else:
            account_ids_stmt = select(Account.id).distinct()
            account_ids = (await db.execute(account_ids_stmt)).scalars().all()

        for account_id_uuid in account_ids:
            account_id = str(account_id_uuid)
            logger.info(f"==> Procesando cuenta: {account_id} <==")

            # Obtener el pool de conocimiento completo del usuario
            full_knowledge_pool = await get_all_knowledge(account_id)
            if not full_knowledge_pool:
                logger.info(f"La cuenta {account_id} no tiene conocimiento para analizar. Saltando.")
                continue

            # Si hay palabras clave, filtrar el knowledge_pool por ellas
            if topic_keywords:
                knowledge_pool_filtered = [
                    item for item in full_knowledge_pool
                    if any(keyword.lower() in item.get('content', '').lower() for keyword in topic_keywords)
                ]
                logger.info(f"Knowledge pool filtrado por palabras clave. Original: {len(full_knowledge_pool)}, Filtrado: {len(knowledge_pool_filtered)}")
            else:
                knowledge_pool_filtered = full_knowledge_pool
            
            if not knowledge_pool_filtered:
                logger.info(f"El pool de conocimiento filtrado por palabras clave está vacío para la cuenta {account_id}. Saltando.")
                continue

            # Identificar qué ítems analizar (nuevos o todos)
            items_to_analyze = []
            if since_timestamp:
                items_to_analyze = [item for item in knowledge_pool_filtered if item.get('timestamp') and item['timestamp'] > since_timestamp]
            elif topic_keywords:
                items_to_analyze = [item for item in knowledge_pool_filtered if any(keyword.lower() in item.get('content', '').lower() for keyword in topic_keywords)]
            else:
                items_to_analyze = knowledge_pool_filtered

            if not items_to_analyze:
                logger.info(f"No se encontraron ítems que cumplan los criterios de análisis para la cuenta {account_id}.")
                continue
            
            logger.info(f"Encontrados {len(items_to_analyze)} ítems para analizar en profundidad en la cuenta {account_id}.")

            for item in items_to_analyze:
                await analyze_entry(item, knowledge_pool_filtered, top_k_candidates=top_k if top_k is not None else 10)
    
    logger.info("--- [ANALYSIS JOB] Trabajo de vinculación de conocimiento completado. ---")
    
    if thread_id:
        try:
            from langchain_community.chat_message_histories import PostgresChatMessageHistory
            from langchain_core.messages import AIMessage
            from core.database import settings

            db_sync_url = settings.database_url.replace("+psycopg", "")
            chat_message_history = PostgresChatMessageHistory(
                connection_string=db_sync_url,
                session_id=thread_id,
                table_name="langchain_chat_history",
            )
            await chat_message_history.aadd_message(AIMessage(content="El análisis de conocimiento ha finalizado y los insights han sido generados."))
            logger.info(f"Mensaje de finalización de análisis enviado al hilo {thread_id}.")
        except Exception as e:
            logger.error(f"Error al enviar mensaje de finalización de análisis al hilo {thread_id}: {e}", exc_info=True)

# --- TRIGGER REFACTORIZADO ---
async def proactive_knowledge_linker_trigger(new_entry: Dict[str, Any]):
    """Trigger que se llama cuando se añade algo nuevo. Ahora se activa para todos los tipos de contenido."""
    # Eliminar la condición `if new_entry.get('type') == 'note':` para analizar todos los tipos
    async def run_analysis():
        account_id = new_entry.get('account_id')
        if not account_id:
            logger.warning("[Proactive Linker] Entrada sin account_id. No se puede programar el análisis proactivo.")
            return

        knowledge_pool = await get_all_knowledge(account_id)
        # Usar 10 como límite por defecto para el análisis proactivo, como se acordó
        await analyze_entry(new_entry, knowledge_pool, top_k_candidates=10)
    
    asyncio.create_task(run_analysis())
    logger.info("[Proactive Linker] Tarea de análisis proactivo programada en segundo plano para una nueva entrada.")
