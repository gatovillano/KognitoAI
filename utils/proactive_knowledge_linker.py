# utils/proactive_knowledge_linker.py

"""
Utilidad de Vinculación Proactiva de Conocimiento para KAI

Contiene la lógica central para el análisis proactivo de conocimiento.
La estrategia principal se basa en el clustering temático para descubrir insights emergentes
de grupos de información, en lugar de solo analizar pares.
"""

import json
import logging
import asyncio
import datetime
import uuid
from typing import Any, Dict, List, Optional

# --- Dependencias de terceros ---
import numpy as np
from scipy.spatial.distance import cosine
import spacy
from keybert import KeyBERT
from sqlalchemy import select
from sklearn.cluster import AgglomerativeClustering # ¡Nueva importación!

# --- Importaciones de LangChain y Google ---
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic.v1 import BaseModel, Field

# --- Importaciones locales del proyecto ---
from core.database import ProactiveInsight, SessionLocal, Nota, Memory, Account
from utils.db_session import DBSession
from utils.embeddings import initialize_embeddings

logger = logging.getLogger(__name__)

# --- MODELOS SINGLETON (sin cambios) ---
_nlp_model: Optional[spacy.Language] = None
_keybert_model: Optional[KeyBERT] = None
_gemini_model: Optional[ChatGoogleGenerativeAI] = None
_embedding_model: Optional[Embeddings] = None

# --- Funciones de inicialización de modelos (sin cambios, las mantengo por completitud) ---
async def get_nlp_model() -> spacy.Language:
    """Carga y devuelve el modelo spaCy para NER, inicializándolo solo una vez."""
    global _nlp_model
    if _nlp_model is None:
        logger.info("Cargando modelo spaCy 'en_core_web_sm'...")
        loop = asyncio.get_event_loop()
        _nlp_model = await loop.run_in_executor(None, lambda: spacy.load("en_core_web_sm"))
    return _nlp_model

async def get_keybert_model_instance() -> KeyBERT:
    """Carga y devuelve el modelo KeyBERT, inicializándolo solo una vez."""
    global _keybert_model
    if _keybert_model is None:
        logger.info("Cargando modelo KeyBERT 'all-MiniLM-L6-v2'...")
        loop = asyncio.get_event_loop()
        _keybert_model = await loop.run_in_executor(None, lambda: KeyBERT("all-MiniLM-L6-v2"))
    return _keybert_model

async def get_gemini_model() -> ChatGoogleGenerativeAI:
    """Carga y devuelve el modelo Gemini para análisis, inicializándolo solo una vez."""
    global _gemini_model
    if _gemini_model is None:
        logger.info("Inicializando modelo Gemini...")
        _gemini_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
    return _gemini_model

async def get_embedding_model_instance() -> Embeddings:
    """Obtiene y devuelve la instancia del modelo de embeddings."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = await initialize_embeddings()
    return _embedding_model

# --- Helper Functions (sin cambios) ---
async def get_text_embedding(text: str) -> Optional[List[float]]:
    """Genera el embedding vectorial para un texto dado."""
    embeddings_instance = await get_embedding_model_instance()
    if embeddings_instance:
        try:
            return await embeddings_instance.aembed_query(text)
        except Exception as e:
            logger.error(f"Error generando embedding para texto: {e}", exc_info=True)
    return None

async def summarize_text(text: str, max_length: int = 150) -> str:
    """Genera un resumen ejecutivo de un texto largo usando Gemini."""
    if not text or len(text) < max_length + 50:
        return text

    gemini_model = await get_gemini_model()
    if not gemini_model:
        return text[:max_length] + "..."

    try:
        prompt = f"Resume el siguiente texto de forma concisa. Máximo {max_length//5} palabras:\n\n{text}"
        response = await gemini_model.ainvoke([HumanMessage(content=prompt)])
        summary = response.content.strip()
        return summary
    except Exception as e:
        logger.warning(f"Error resumiendo texto: {e}. Volviendo a texto truncado.")
        return text[:max_length] + "..."
        
# --- ANÁLISIS MEJORADO DE PARES (Para uso futuro o triggers) ---
class RelationshipAnalysis(BaseModel):
    relationship_type: str = Field(description="Clasificación: Duplicidad, Sinergia, Evolución, Contradicción, Contexto Adicional, o Sin Relación Significativa.")
    confidence_score: float = Field(description="Confianza de la clasificación, de 0.0 a 1.0.")
    explanation: str = Field(description="Explicación concisa y clara de la relación. ¿Por qué se clasificó así?")
    action_suggestion: str = Field(description="Sugerencia de acción para el usuario (ej. 'Considera fusionar estas notas', 'Explora esta contradicción').")

async def analyze_relationship_with_llm(item_a: Dict[str, Any], item_b: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Usa Gemini para analizar la relación semántica profunda entre dos ítems con un formato robusto."""
    llm = await get_gemini_model()
    if not llm: return None

    parser = PydanticOutputParser(pydantic_object=RelationshipAnalysis)
    prompt_template = f"""
    Eres un analista experto. Analiza la relación semántica entre los siguientes dos elementos.

    --- Elemento A (Tipo: {item_a.get('type')}, Título: {item_a.get('title', 'N/A')}) ---
    {item_a.get('content')}
    --- FIN Elemento A ---

    --- Elemento B (Tipo: {item_b.get('type')}, Título: {item_b.get('title', 'N/A')}) ---
    {item_b.get('content')}
    --- FIN Elemento B ---

    Evalúa la relación y responde siguiendo el formato JSON especificado. Sé muy específico.

    Ejemplo de SINERGIA:
    - Explicación: "El Elemento A describe un problema técnico en 'Proyecto X' y el B menciona una tecnología que podría resolverlo."
    - Sugerencia: "Investigar si la tecnología del proveedor se puede aplicar a 'Proyecto X'."

    Ejemplo de CONTRADICCIÓN:
    - Explicación: "La nota A dice que la fecha límite es el 15 de julio, mientras que la nota B, más reciente, la pospone al 30 de agosto."
    - Sugerencia: "Clarificar la fecha límite correcta para el proyecto."

    {parser.get_format_instructions()}
    """
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt_template)])
        analysis_result = parser.parse(response.content)
        return analysis_result.dict()
    except Exception as e:
        logger.error(f"Error analizando relación con LLM: {e}", exc_info=True)
        return None

# --- NUEVO: ANÁLISIS DE CÚMULOS ---
class ClusterInsight(BaseModel):
    insight_title: str = Field(description="Un título conciso y accionable para el insight (ej. 'Sinergia entre el Proyecto Hydra y la Investigación de Mercado Q3').")
    executive_summary: str = Field(description="Un resumen de 2-3 frases que explique el tema central del cúmulo y por qué es relevante.")
    key_connections: List[str] = Field(description="Lista de conexiones, sinergias o evoluciones clave encontradas entre las notas del cúmulo.")
    emergent_contradictions_or_gaps: Optional[str] = Field(description="Identifica contradicciones o brechas de conocimiento reveladas por el cúmulo. Si no hay, debe ser null.")
    suggested_next_steps: List[str] = Field(description="Lista de acciones concretas o preguntas que el usuario podría explorar a continuación.")
    confidence_score: float = Field(description="Confianza (0.0 a 1.0) en que este cúmulo representa un insight coherente y valioso.")

async def analyze_cluster_with_llm(cluster_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Usa Gemini para sintetizar un insight ejecutivo a partir de un cúmulo de notas."""
    llm = await get_gemini_model()
    if not llm: return None

    # Prepara el contexto para el prompt, usando resúmenes para no exceder límites
    context_parts = []
    for item in cluster_items:
        summary = await summarize_text(item.get('content', ''), 100)
        context_parts.append(f"- (Tipo: {item.get('type')}, Título: {item.get('title', 'N/A')}) -> '{summary}'")
    cluster_context = "\n".join(context_parts)

    parser = PydanticOutputParser(pydantic_object=ClusterInsight)
    prompt_template = f"""
    Eres un analista de investigación y estratega de clase mundial. Analiza el siguiente cúmulo de notas y documentos relacionados temáticamente y genera un "Insight Ejecutivo" que resuma la conexión subyacente.

    --- INICIO DEL CÚMULO DE CONOCIMIENTO ---
    {cluster_context}
    --- FIN DEL CÚMULO DE CONOCIMIENTO ---

    Analiza este cúmulo y responde ÚNICAMENTE en formato JSON con la estructura especificada.

    {parser.get_format_instructions()}
    """
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt_template)])
        insight_result = parser.parse(response.content)
        return insight_result.dict()
    except Exception as e:
        logger.error(f"Error sintetizando insight de cúmulo con LLM: {e}", exc_info=True)
        return None

# --- Recuperación de Datos y Guardado (sin cambios mayores) ---
async def get_all_knowledge(account_id: str, since_timestamp: Optional[datetime.datetime] = None, topic_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Recupera conocimiento relevante filtrando opcionalmente por fecha o palabras clave."""
    all_items: List[Dict[str, Any]] = []
    account_uuid = uuid.UUID(account_id)
    
    async with DBSession(SessionLocal) as db:
        # Fetch Notes
        notes_stmt = select(Nota).where(Nota.account_id == account_uuid)
        if since_timestamp:
            notes_stmt = notes_stmt.where(Nota.created_at >= since_timestamp)
        notes = (await db.execute(notes_stmt)).scalars().all()
        for note in notes:
            all_items.append({
                'id': str(note.id), 'content': note.content, 'title': note.title, 'type': 'note',
                'category': note.category, 'timestamp': note.created_at, 'embedding': note.embedding,
                'account_id': account_id
            })

        # Fetch Memories/Documents
        memories_stmt = select(Memory).where(Memory.account_id == account_uuid)
        if since_timestamp:
            memories_stmt = memories_stmt.where(Memory.created_at >= since_timestamp)
        memories = (await db.execute(memories_stmt)).scalars().all()
        for mem in memories:
            all_items.append({
                'id': str(mem.id), 'content': mem.content, 'title': mem.metadata.get('title', mem.content[:50]),
                'type': mem.type, 'category': mem.type, 'timestamp': mem.created_at, 'embedding': mem.embedding,
                'account_id': account_id
            })
    
    # Filtrado final por palabras clave (si aplica)
    if topic_keywords:
        keywords_lower = [k.lower() for k in topic_keywords]
        all_items = [
            item for item in all_items 
            if any(key in item.get('content', '').lower() or key in item.get('title', '').lower() for key in keywords_lower)
        ]

    logger.info(f"Retrieved {len(all_items)} knowledge items for account {account_id} with given filters.")
    return all_items

async def store_proactive_insight(insight_data: Dict[str, Any]):
    """Persiste un insight proactivo en la base de datos."""
    logger.info(f"--- INSIGHT DETECTADO: {insight_data.get('type')} ---")
    logger.info(f"  Cuenta: {insight_data.get('account_id', 'N/A')}")
    # ... (el resto del logging puede ser similar)

    try:
        account_id_uuid = uuid.UUID(insight_data["account_id"])
        async with DBSession(SessionLocal) as db:
            # Serializar ítems para JSONB
            related_items_serializable = []
            if insight_data.get("related_items"):
                 related_items_serializable = [
                    {k: (v.isoformat() if isinstance(v, datetime.datetime) else v) for k, v in item.items() if k != 'embedding'}
                    for item in insight_data["related_items"]
                ]

            pi = ProactiveInsight(
                account_id=account_id_uuid,
                type=insight_data.get("type", "cluster_insight"),
                insight_message=insight_data.get("executive_summary") or insight_data.get("explanation", ""),
                confidence_score=insight_data.get("confidence_score", 0.0),
                action_suggestion=json.dumps(insight_data.get("suggested_next_steps")) or insight_data.get("action_suggestion"),
                related_items=related_items_serializable,
                metadata={ # Guardamos el resto de la info valiosa aquí
                    "title": insight_data.get("insight_title"),
                    "key_connections": insight_data.get("key_connections"),
                    "gaps": insight_data.get("emergent_contradictions_or_gaps")
                }
            )
            db.add(pi)
            await db.commit()
            logger.info(f"Insight de tipo '{pi.type}' guardado en DB con id={pi.id}.")
    except Exception as e:
        logger.error(f"Error guardando insight en BBDD: {e}", exc_info=True)

# --- LÓGICA DE ANÁLISIS REFACTORIZADA ---
async def analyze_entry(entry_to_analyze: Dict[str, Any], knowledge_pool: List[Dict[str, Any]]):
    """
    Analiza una sola entrada nueva contra el pool de conocimiento.
    Utiliza el análisis de pares mejorado para una respuesta rápida y enfocada.
    """
    logger.info(f"Análisis de entrada individual para '{entry_to_analyze.get('title')}'...")

    if not entry_to_analyze.get('embedding'):
        logger.warning(f"Entrada '{entry_to_analyze.get('title')}' no tiene embedding. Saltando análisis de pares.")
        return

    new_entry_embedding = np.array(entry_to_analyze['embedding'])
    account_id = entry_to_analyze['account_id']
    
    similarities = []
    for item in knowledge_pool:
        if item.get('embedding') is not None and item['id'] != entry_to_analyze['id']: # Avoid comparing with itself and ensure embedding exists
            item_embedding = np.array(item['embedding'])
            # Cosine similarity is 1 - cosine distance
            sim = 1 - cosine(new_entry_embedding, item_embedding)
            similarities.append((sim, item))
    
    # Sort by similarity in descending order
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    # Consider top K similar items for detailed analysis
    top_k = 3 # You can adjust this number
    for sim_score, similar_item in similarities[:top_k]:
        if sim_score > 0.7: # Only analyze if similarity is high enough
            logger.info(f"Analizando relación entre '{entry_to_analyze.get('title')}' y '{similar_item.get('title')}' (Similitud: {sim_score:.2f}).")
            relationship_insight = await analyze_relationship_with_llm(entry_to_analyze, similar_item)
            
            if relationship_insight and relationship_insight.get("confidence_score", 0) > 0.7: # Higher confidence for pair insights
                insight_data = {
                    'account_id': account_id,
                    'type': relationship_insight.get('relationship_type', 'pair_insight'),
                    'insight_message': relationship_insight.get('explanation'),
                    'confidence_score': relationship_insight.get('confidence_score'),
                    'action_suggestion': relationship_insight.get('action_suggestion'),
                    'related_items': [
                        {k: (v.isoformat() if isinstance(v, datetime.datetime) else v) for k, v in entry_to_analyze.items() if k != 'embedding'},
                        {k: (v.isoformat() if isinstance(v, datetime.datetime) else v) for k, v in similar_item.items() if k != 'embedding'}
                    ],
                    'metadata': {
                        "item_a_title": entry_to_analyze.get('title'),
                        "item_b_title": similar_item.get('title')
                    }
                }
                await store_proactive_insight(insight_data)
        else:
            logger.info(f"Similitud ({sim_score:.2f}) por debajo del umbral para '{similar_item.get('title')}'. Saltando análisis de relación.")


# --- FUNCIÓN PRINCIPAL DEL JOB REFACTORIZADA (con Clustering) ---
async def run_batch_analysis_job(
    account_id_filter: Optional[str] = None,
    since_timestamp: Optional[datetime.datetime] = None,
    topic_keywords: Optional[List[str]] = None
):
    """
    Función principal para el trabajo de análisis basado en CLUSTERING o ANÁLISIS DE PARES.
    """
    logger.info(f"--- [ANALYSIS JOB] Iniciando trabajo de vinculación proactiva ---")
    
    async with DBSession(SessionLocal) as db:
        if account_id_filter:
            account_ids = [uuid.UUID(account_id_filter)]
        else:
            account_ids = (await db.execute(select(Account.id).distinct())).scalars().all()

        for account_id_uuid in account_ids:
            account_id = str(account_id_uuid)
            logger.info(f"==> Procesando cuenta: {account_id} <==")

            # 1. Recuperar conocimiento aplicando filtros primarios
            knowledge_pool = await get_all_knowledge(account_id, since_timestamp, topic_keywords)
            
            items_with_embeddings = [item for item in knowledge_pool if item.get('embedding') is not None and len(item['embedding']) > 0]
            
            # --- LÓGICA DE DECISIÓN: ANÁLISIS DE PARES VS. CLUSTERING ---
            MIN_ITEMS_FOR_CLUSTERING = 20 # Umbral para decidir entre clustering y análisis de pares
            
            if len(items_with_embeddings) < MIN_ITEMS_FOR_CLUSTERING:
                logger.info(f"Pocos ítems ({len(items_with_embeddings)}) para clustering. Realizando análisis de pares para la cuenta {account_id}.")
                # Realizar análisis de pares para cada ítem contra el resto
                for i, item_a in enumerate(items_with_embeddings):
                    for j, item_b in enumerate(items_with_embeddings):
                        if i < j: # Evitar duplicados y auto-comparaciones
                            sim = 1 - cosine(np.array(item_a['embedding']), np.array(item_b['embedding']))
                            if sim > 0.7: # Umbral de similitud para considerar análisis LLM
                                logger.info(f"Analizando relación entre '{item_a.get('title')}' y '{item_b.get('title')}' (Similitud: {sim:.2f}).")
                                relationship_insight = await analyze_relationship_with_llm(item_a, item_b)
                                if relationship_insight and relationship_insight.get("confidence_score", 0) > 0.7:
                                    insight_data = {
                                        'account_id': account_id,
                                        'type': relationship_insight.get('relationship_type', 'pair_insight'),
                                        'insight_message': relationship_insight.get('explanation'),
                                        'confidence_score': relationship_insight.get('confidence_score'),
                                        'action_suggestion': relationship_insight.get('action_suggestion'),
                                        'related_items': [
                                            {k: (v.isoformat() if isinstance(v, datetime.datetime) else v) for k, v in item_a.items() if k != 'embedding'},
                                            {k: (v.isoformat() if isinstance(v, datetime.datetime) else v) for k, v in item_b.items() if k != 'embedding'}
                                        ],
                                        'metadata': {
                                            "item_a_title": item_a.get('title'),
                                            "item_b_title": item_b.get('title')
                                        }
                                    }
                                    await store_proactive_insight(insight_data)
            else:
                logger.info(f"Suficientes ítems ({len(items_with_embeddings)}) para clustering. Realizando clustering aglomerativo para la cuenta {account_id}.")
                # El clustering aglomerativo necesita al menos 2 puntos para formar un cluster significativo
                if len(items_with_embeddings) < 2:
                    logger.info(f"No hay suficiente conocimiento ({len(items_with_embeddings)} items) para clustering aglomerativo en la cuenta {account_id}. Saltando.")
                    continue
                
                embeddings = np.array([item['embedding'] for item in items_with_embeddings])

                # 2. Ejecutar Clustering Jerárquico Aglomerativo
                logger.info(f"Ejecutando clustering Aglomerativo sobre {len(embeddings)} embeddings...")
                
                # Determinar n_clusters dinámicamente para baja cantidad de información y grupos amplios
                # Aseguramos que n_clusters no sea mayor que el número de items - 1
                # y que sea al menos 2 si hay suficientes items.
                n_clusters_to_use = min(4, len(items_with_embeddings) - 1)
                if n_clusters_to_use < 2:
                    logger.info(f"No hay suficientes items para formar al menos 2 clusters con AgglomerativeClustering. Saltando.")
                    continue

                clusterer = AgglomerativeClustering(n_clusters=n_clusters_to_use, metric='euclidean', linkage='ward')
                cluster_labels = clusterer.fit_predict(embeddings)
                
                num_clusters = len(set(cluster_labels)) # AgglomerativeClustering no produce -1 para ruido por defecto
                
                logger.info(f"Encontrados {num_clusters} cúmulos temáticos con AgglomerativeClustering.")

                # 3. Analizar cada cúmulo
                unique_labels = set(cluster_labels)
                for label in unique_labels:
                    # AgglomerativeClustering no produce la etiqueta -1 para ruido con n_clusters definido
                    cluster_indices = np.where(cluster_labels == label)[0]
                    cluster_items = [items_with_embeddings[i] for i in cluster_indices]
                    
                    # Aseguramos que el cluster tenga al menos 2 ítems para un insight significativo
                    if len(cluster_items) < 2:
                        logger.info(f"Cúmulo #{label} tiene solo {len(cluster_items)} item(s). Ignorando para insight.")
                        continue

                    logger.info(f"Analizando Cúmulo #{label} con {len(cluster_items)} items.")
                    
                    # 4. Sintetizar Insight con LLM
                    insight = await analyze_cluster_with_llm(cluster_items)
                    
                    if insight and insight.get("confidence_score", 0) > 0.6: # Umbral de confianza
                        insight_data = {
                            'account_id': account_id,
                            'type': 'cluster_insight',
                            'related_items': cluster_items,
                            **insight # Desempaqueta todo el diccionario del insight
                        }
                        await store_proactive_insight(insight_data)

    logger.info("--- [ANALYSIS JOB] Trabajo de vinculación de conocimiento completado. ---")


# --- TRIGGER REFACTORIZADO (se mantiene igual) ---
async def proactive_knowledge_linker_trigger(new_entry: Dict[str, Any]):
    """Trigger que se llama cuando se añade algo nuevo."""
    async def run_analysis():
        # Para una nueva nota, un análisis de pares puede ser más inmediato y útil
        knowledge_pool = await get_all_knowledge(new_entry['account_id'])
        await analyze_entry(new_entry, knowledge_pool) # Llama a la función de análisis de pares
    asyncio.create_task(run_analysis())
    logger.info("[Proactive Linker] Tarea de análisis de nueva entrada programada en segundo plano.")

# --- INTERPRETADOR DE PETICIÓN ---
class AnalysisRequest(BaseModel):
    analysis_type: str = Field(description="Tipo de análisis solicitado: 'batch_analysis' para análisis de cúmulos, 'single_entry_analysis' para analizar una nueva entrada, 'get_insights' para recuperar insights existentes.")
    account_id: str = Field(description="El ID de la cuenta del usuario para el análisis.")
    since_timestamp: Optional[str] = Field(None, description="Marca de tiempo ISO 8601 desde la cual recuperar el conocimiento (ej. '2023-01-01T00:00:00Z'). Solo para 'batch_analysis'.")
    topic_keywords: Optional[List[str]] = Field(None, description="Lista de palabras clave para filtrar el conocimiento por tema. Solo para 'batch_analysis'.")
    new_entry_content: Optional[str] = Field(None, description="Contenido de la nueva entrada a analizar. Solo para 'single_entry_analysis'.")
    new_entry_title: Optional[str] = Field(None, description="Título de la nueva entrada. Solo para 'single_entry_analysis'.")
    new_entry_category: Optional[str] = Field(None, description="Categoría de la nueva entrada. Solo para 'single_entry_analysis'.")
    new_entry_type: Optional[str] = Field(None, description="Tipo de la nueva entrada (e.g., 'note', 'document'). Solo para 'single_entry_analysis'.")
    limit: Optional[int] = Field(None, description="Límite de insights a recuperar. Solo para 'get_insights'.")


async def interpret_user_request_for_analysis(user_query: str, account_id: str) -> Dict[str, Any]:
    """Usa un LLM para traducir la petición del usuario en una acción estructurada."""
    llm = await get_gemini_model()
    if not llm:
        logger.error("No se pudo inicializar el modelo Gemini para interpretar la petición del usuario.")
        return {"error": "Internal server error: LLM not available."}

    parser = PydanticOutputParser(pydantic_object=AnalysisRequest)
    
    prompt_template = f"""
    Eres un asistente experto en análisis de conocimiento. Tu tarea es interpretar la siguiente petición del usuario y transformarla en un objeto JSON estructurado que represente la solicitud de análisis.

    El `account_id` del usuario es: {account_id}. Usa este valor para el campo `account_id`.

    Considera los siguientes tipos de análisis:
    - 'batch_analysis': Cuando el usuario pide un análisis general de sus notas/documentos, buscar conexiones, sinergias, etc. Puede incluir filtros por fecha o palabras clave.
    - 'single_entry_analysis': Cuando el usuario proporciona un nuevo texto/nota y quiere que se analice en relación con el conocimiento existente.
    - 'get_insights': Cuando el usuario pide ver los insights proactivos que ya se han generado.

    Si el usuario no especifica un tipo de análisis claro, asume 'batch_analysis' por defecto.

    Petición del usuario: "{user_query}"

    {parser.get_format_instructions()}
    """
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt_template)])
        parsed_request = parser.parse(response.content)
        
        # Ensure account_id is always set from the provided parameter
        parsed_request.account_id = account_id
        
        return parsed_request.dict()
    except Exception as e:
        logger.error(f"Error interpretando la petición del usuario con LLM: {e}", exc_info=True)
        # Fallback to a default batch analysis if parsing fails
        return {
            "analysis_type": "batch_analysis",
            "account_id": account_id,
            "since_timestamp": None,
            "topic_keywords": None
        }