# knowledge_graph/memory_graph_processor.py

"""
Módulo para procesar memorias del agente en un grafo de conocimiento.
Las memorias se procesan con una metodología propia distinta a documentos:
  - Cada memoria es un nodo atómico con tipo correcto (USER_MEMORY, AGENT_MEMORY, etc.)
  - Sin resumen LLM innecesario: el contenido de la memoria es directo y corto
  - Relaciones semánticas entre memorias del lote y cross-lote con memorias existentes
  - Relaciones con entidades existentes en el grafo mediante NER liviano
"""

import asyncio
import json
import logging
import re
from math import sqrt
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text, select, update
import uuid

from core.database import SessionLocal
from utils.db_session import DBSession
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration
from knowledge_graph.neo4j_adapter import Neo4jAdapter
from core.config import settings
from utils.embeddings import get_embedding_model

# Vocabulario controlado de relaciones entre memorias.
# Todos con prefijo MEMORY_ para distinguirlos de relaciones de documentos.
MEMORY_RELATION_TYPES = {
    "MEMORY_RELATED":           "Relación genérica por similitud semántica",
    "MEMORY_COMPLEMENTA":       "Las memorias se complementan mutuamente, aportan información adicional",
    "MEMORY_REFUERZA":          "Una memoria refuerza o corrobora a la otra",
    "MEMORY_CONTRADICE":        "Las memorias presentan información contradictoria o en tensión",
    "MEMORY_CAUSA":             "Una memoria describe la causa de lo que relata la otra",
    "MEMORY_CONSECUENCIA":      "Una memoria describe la consecuencia de lo relatado en la otra",
    "MEMORY_SECUENCIA":         "Las memorias describen eventos en secuencia temporal",
    "MEMORY_CONTEXTO":          "Una memoria provee contexto para entender la otra",
    "MEMORY_PREGUNTA_RESPUESTA": "Una memoria plantea una pregunta que la otra responde",
    "MEMORY_MISMO_TEMA":        "Las memorias tratan el mismo tema desde distintos ángulos",
}

# Configuración del logger
logger = logging.getLogger(__name__)

# Umbral de memorias para procesar en un lote
MEMORY_PROCESSING_THRESHOLD = 1

# Lock para evitar condiciones de carrera al procesar lotes
processing_lock = asyncio.Lock()

MEMORY_NODE_TYPE_MAP = {
    "user_memory": "USER_MEMORY",
    "user_memory_proactive_llm": "USER_MEMORY_PROACTIVE_LLM",
    "agent_memory": "AGENT_MEMORY",
    "chat_summary": "CHAT_SUMMARY",
    "general_memory": "GENERAL_MEMORY",
}


def _resolve_memory_node_type(memory_type: str) -> str:
    normalized_type = (memory_type or "").strip().lower()
    return MEMORY_NODE_TYPE_MAP.get(normalized_type, "USER_MEMORY")


def _build_memory_node_title(memory: Dict[str, Any]) -> str:
    metadata = memory.get("cmetadata") or {}
    raw_content = (memory.get("document") or "").strip()
    topic = (metadata.get("topic") or "").strip()
    provided_title = (
        metadata.get("title")
        or metadata.get("memory_title")
        or metadata.get("file_name")
    )

    if isinstance(provided_title, str) and provided_title.strip() and provided_title.strip().lower() != "memory":
        return provided_title.strip()

    if topic and topic.lower() != "general":
        return topic

    if raw_content:
        compact_content = " ".join(raw_content.split())
        max_length = 80
        return compact_content[:max_length] + ("..." if len(compact_content) > max_length else "")

    return f"Memoria {str(memory.get('uuid'))[:8]}"


def _build_memory_similarity_text(memory_doc: Dict[str, Any]) -> str:
    metadata = memory_doc.get("metadata") or {}
    parts = [
        memory_doc.get("title"),
        metadata.get("topic"),
        metadata.get("category"),
        memory_doc.get("content"),
    ]
    return "\n".join(str(part).strip() for part in parts if isinstance(part, str) and part.strip())


def _cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = sqrt(sum(a * a for a in vector_a))
    norm_b = sqrt(sum(b * b for b in vector_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _calculate_metadata_bonus(
    metadata_a: Dict[str, Any],
    metadata_b: Dict[str, Any]
) -> Tuple[float, List[str]]:
    bonus = 0.0
    shared_signals: List[str] = []

    topic_a = str(metadata_a.get("topic") or "").strip().lower()
    topic_b = str(metadata_b.get("topic") or "").strip().lower()
    if topic_a and topic_a == topic_b and topic_a != "general":
        bonus += 0.08
        shared_signals.append(f"topic:{topic_a}")

    thread_a = str(metadata_a.get("thread_id") or "").strip()
    thread_b = str(metadata_b.get("thread_id") or "").strip()
    if thread_a and thread_a == thread_b:
        bonus += 0.12
        shared_signals.append("thread")

    category_a = str(metadata_a.get("category") or "").strip().lower()
    category_b = str(metadata_b.get("category") or "").strip().lower()
    if category_a and category_a == category_b and category_a != "general":
        bonus += 0.05
        shared_signals.append(f"category:{category_a}")

    return bonus, shared_signals


async def _classify_memory_relationships_with_llm(
    candidates: List[Dict[str, Any]],
    account_id: Optional[str] = None,
) -> Dict[int, Dict[str, str]]:
    """
    Clasifica el tipo de relación entre pares de memorias usando un LLM (una sola llamada batch).

    Args:
        candidates: Lista de pares con idx, source_title, source_content,
                    target_title, target_content, similarity.
        account_id: Para obtener el LLM del usuario si está disponible.

    Returns:
        Diccionario {idx: {"type": "MEMORY_COMPLEMENTA", "description": "..."}}
        Los tipos son del vocabulario MEMORY_RELATION_TYPES. Fallback a MEMORY_RELATED.
    """
    if not candidates:
        return {}

    # Obtener LLM — preferir el del usuario, sino el global rápido
    llm = None
    try:
        if account_id:
            from core.llm_manager import get_llm_for_user
            llm = await get_llm_for_user(account_id, purpose="fast")
        if not llm:
            from core.llm_manager import get_fast_llm
            llm = get_fast_llm()
    except Exception:
        pass

    if not llm:
        logger.warning("⚠️ LLM no disponible para clasificar relaciones. Usando MEMORY_RELATED por defecto.")
        return {}

    # Construir prompt con todos los pares en un solo batch
    tipos_validos = "\n".join(f"  - {k}: {v}" for k, v in MEMORY_RELATION_TYPES.items())
    pares_str = "\n".join(
        f"Par {c['idx']}:\n"
        f"  A: \"{c['source_title']}\" — {c['source_content'][:200]}\n"
        f"  B: \"{c['target_title']}\" — {c['target_content'][:200]}\n"
        f"  Similitud semántica: {c['similarity']:.2f}"
        for c in candidates
    )

    prompt = f"""Analiza los siguientes pares de memorias de usuario y determina el tipo de relación más preciso entre cada par.

**Tipos de relación válidos** (usa EXACTAMENTE uno de estos nombres):
{tipos_validos}

**Pares a clasificar:**
{pares_str}

**Responde SOLO con un JSON válido** con esta estructura exacta, sin texto adicional:
[
  {{"idx": 1, "type": "TIPO_EXACTO", "description": "Una frase explicando la relación específica"}},
  {{"idx": 2, "type": "TIPO_EXACTO", "description": "Una frase explicando la relación específica"}}
]

Si no está claro el tipo, usa MEMORY_RELATED.
"""

    try:
        response = await llm.ainvoke(prompt)
        raw = str(response.content).strip()

        # Extraer JSON del response (puede venir con markdown code blocks)
        json_match = re.search(r'\[[\s\S]*\]', raw)
        if not json_match:
            logger.warning("⚠️ LLM no devolvió JSON válido para clasificación de relaciones.")
            return {}

        parsed: List[Dict] = json.loads(json_match.group())

        # Validar y sanitizar tipos
        valid_types = set(MEMORY_RELATION_TYPES.keys())
        result: Dict[int, Dict[str, str]] = {}

        for item in parsed:
            idx = item.get("idx")
            rel_type = str(item.get("type") or "MEMORY_RELATED").strip().upper()
            # Sanitizar a caracteres válidos para Neo4j
            rel_type = re.sub(r'[^A-Z0-9_]', '_', rel_type)
            if rel_type not in valid_types:
                rel_type = "MEMORY_RELATED"
            result[idx] = {
                "type": rel_type,
                "description": str(item.get("description") or "").strip()[:300],
            }

        logger.info(f"✅ LLM clasificó {len(result)}/{len(candidates)} relaciones entre memorias.")
        return result

    except Exception as e:
        logger.warning(f"⚠️ Error clasificando relaciones con LLM: {e}. Usando MEMORY_RELATED.")
        return {}


async def _create_memory_to_memory_relationships(
    memory_documents: List[Dict[str, Any]],
    graph_integration: GraphIntegration,
    account_id: str,
) -> int:
    if len(memory_documents) < 2:
        return 0

    embeddings_model = get_embedding_model()
    if not embeddings_model:
        logger.warning("⚠️ No hay modelo de embeddings disponible para enlazar memorias entre sí.")
        return 0

    candidate_docs = []
    embedding_texts = []
    for document in memory_documents:
        document_id = document.get("document_id") or document.get("id")
        content = _build_memory_similarity_text(document)
        if not document_id or len(content.strip()) < 20:
            continue
        candidate_docs.append(document)
        embedding_texts.append(content[:2000])

    if len(candidate_docs) < 2:
        return 0

    try:
        embeddings = await embeddings_model.aembed_documents(embedding_texts)
    except Exception as exc:
        logger.error(f"❌ Error generando embeddings para relaciones entre memorias: {exc}", exc_info=True)
        return 0

    min_semantic_similarity = 0.62
    min_combined_score = 0.78

    # ── Paso 1: identificar pares candidatos por similitud ────────────────────
    llm_candidates: List[Dict[str, Any]] = []
    pair_meta: List[Dict[str, Any]] = []  # metadatos paralelos a llm_candidates

    for i, source_doc in enumerate(candidate_docs):
        source_metadata = source_doc.get("metadata") or {}
        source_workspace_id = source_doc.get("workspace_id") or source_metadata.get("workspace_id")
        source_id = source_doc.get("document_id") or source_doc.get("id")
        source_title = source_doc.get("title") or source_doc.get("name") or str(source_id)
        source_workspace = source_doc.get("workspace") or source_metadata.get("workspace")

        for j in range(i + 1, len(candidate_docs)):
            target_doc = candidate_docs[j]
            target_metadata = target_doc.get("metadata") or {}
            target_workspace_id = target_doc.get("workspace_id") or target_metadata.get("workspace_id")

            if str(source_workspace_id or "") != str(target_workspace_id or ""):
                continue

            semantic_similarity = _cosine_similarity(embeddings[i], embeddings[j])
            if semantic_similarity < min_semantic_similarity:
                continue

            metadata_bonus, shared_signals = _calculate_metadata_bonus(source_metadata, target_metadata)
            combined_score = semantic_similarity + metadata_bonus
            if combined_score < min_combined_score:
                continue

            target_id = target_doc.get("document_id") or target_doc.get("id")
            target_title = target_doc.get("title") or target_doc.get("name") or str(target_id)
            idx = len(llm_candidates) + 1

            llm_candidates.append({
                "idx": idx,
                "source_title": source_title,
                "source_content": source_doc.get("content") or "",
                "target_title": target_title,
                "target_content": target_doc.get("content") or "",
                "similarity": semantic_similarity,
            })
            pair_meta.append({
                "idx": idx,
                "source_id": source_id,
                "target_id": target_id,
                "source_title": source_title,
                "target_title": target_title,
                "combined_score": combined_score,
                "semantic_similarity": semantic_similarity,
                "shared_signals": shared_signals,
                "metadata_bonus": metadata_bonus,
                "workspace_id": source_workspace_id,
                "workspace": source_workspace,
            })

    if not llm_candidates:
        logger.info("ℹ️ No se encontraron pares de memorias relacionadas en este lote.")
        return 0

    # ── Paso 2: clasificar tipos de relación con LLM (una sola llamada batch) ─
    logger.info(f"🤖 Clasificando {len(llm_candidates)} pares de memorias con LLM...")
    llm_classifications = await _classify_memory_relationships_with_llm(
        candidates=llm_candidates,
        account_id=account_id,
    )

    # ── Paso 3: construir relaciones enriquecidas ────────────────────────────
    relationships = []
    for meta in pair_meta:
        idx = meta["idx"]
        classification = llm_classifications.get(idx, {})
        rel_type = classification.get("type") or "MEMORY_RELATED"
        llm_desc = classification.get("description") or ""

        signal_suffix = f" | señales: {', '.join(meta['shared_signals'])}" if meta["shared_signals"] else ""
        base_desc = (
            f"'{meta['source_title']}' ↔ '{meta['target_title']}'"
            f" | similitud={meta['semantic_similarity']:.2f}"
            f" | score={meta['combined_score']:.2f}{signal_suffix}"
        )
        full_desc = f"{llm_desc} [{base_desc}]" if llm_desc else base_desc

        relationships.append({
            "source_id": meta["source_id"],
            "target_id": meta["target_id"],
            "type": rel_type,
            "description": full_desc,
            "importance": round(min(1.0, meta["combined_score"]), 3),
            "category": "memory_relationship",
            "extraction_method": "semantic_llm_memory_linking",
            "confidence": round(min(1.0, meta["combined_score"]), 3),
            "shared_signals": meta["shared_signals"],
            "similarity_score": round(meta["semantic_similarity"], 3),
            "metadata_score": round(meta["metadata_bonus"], 3),
            "llm_classified": bool(llm_classifications.get(idx)),
            "workspace_id": meta.get("workspace_id"),
            "workspace": meta.get("workspace"),
        })

    await graph_integration.hybrid_adapter.create_conceptual_relationships(
        relationships=relationships,
        account_id=account_id,
        workspace_id=None,
    )

    type_summary = {}
    for r in relationships:
        type_summary[r["type"]] = type_summary.get(r["type"], 0) + 1
    logger.info(f"🔗 {len(relationships)} relaciones creadas entre memorias: {type_summary}")
    return len(relationships)


async def get_unprocessed_memories_count(account_id: str) -> int:
    """Cuenta las memorias no procesadas para un usuario."""
    async with DBSession(SessionLocal) as db:
        query = text("""
            SELECT COUNT(*) FROM langchain_pg_embedding
            WHERE account_id = :account_id 
            AND (is_graph_processed = false OR is_graph_processed IS NULL)
            AND cmetadata->>'type' IN ('user_memory', 'user_memory_proactive_llm', 'agent_memory', 'chat_summary')
        """)
        result = await db.execute(query, {"account_id": account_id})
        return result.scalar_one_or_none() or 0

async def get_unprocessed_memories(account_id: str, limit: int) -> List[Dict[str, Any]]:
    """Obtiene las memorias no procesadas de la base de datos."""
    async with DBSession(SessionLocal) as db:
        query = text("""
            SELECT id, document, cmetadata FROM langchain_pg_embedding
            WHERE account_id = :account_id 
            AND (is_graph_processed = false OR is_graph_processed IS NULL)
            AND cmetadata->>'type' IN ('user_memory', 'user_memory_proactive_llm', 'agent_memory', 'chat_summary')
            ORDER BY cmetadata->>'created_at' ASC
            LIMIT :limit
        """)
        result = await db.execute(query, {"account_id": account_id, "limit": limit})
        rows = result.mappings().all()
        return [dict(row) for row in rows]


async def reset_memories_processed_flag(account_id: str) -> int:
    """
    Resetea is_graph_processed = false para todas las memorias del usuario.
    Útil para forzar un reprocesamiento completo.
    """
    async with DBSession(SessionLocal) as db:
        query = text("""
            UPDATE langchain_pg_embedding
            SET is_graph_processed = false
            WHERE account_id = :account_id
              AND cmetadata->>'type' IN (
                'user_memory', 'user_memory_proactive_llm',
                'agent_memory', 'chat_summary'
              )
        """)
        result = await db.execute(query, {"account_id": account_id})
        await db.commit()
        return result.rowcount


async def mark_memories_as_processed(memory_ids: List[str]):
    """Marca una lista de memorias como procesadas en la base de datos."""
    if not memory_ids:
        return
    async with DBSession(SessionLocal) as db:
        query = text("""
            UPDATE langchain_pg_embedding
            SET is_graph_processed = true
            WHERE id = ANY(:memory_ids)
        """)
        await db.execute(query, {"memory_ids": memory_ids})
        await db.commit()


async def schedule_memory_graph_processing(account_id: str):
    """
    Verifica si hay suficientes memorias pendientes y, de ser así,
    dispara la tarea de procesamiento en lotes.
    """
    try:
        logger.info(f"Verificando si se debe procesar el grafo de memorias para la cuenta {account_id}...")
        unprocessed_count = await get_unprocessed_memories_count(account_id)

        if unprocessed_count >= MEMORY_PROCESSING_THRESHOLD:
            logger.info(f"Umbral de {MEMORY_PROCESSING_THRESHOLD} memorias alcanzado. Programando procesamiento en lote.")
            asyncio.create_task(process_memory_batches(account_id=account_id))
        else:
            logger.info(f"Aún no se alcanza el umbral de procesamiento. Memorias pendientes: {unprocessed_count}")
    except Exception as e:
        logger.error(f"Error al programar el procesamiento del grafo de memoria: {e}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE DEDICADO PARA MEMORIAS
# Completamente separado del pipeline de documentos. Las memorias no pasan por
# process_documents(), no generan resúmenes LLM y sus nodos tienen el tipo
# correcto (MEMORY + subtipo) en lugar de DOCUMENT.
# ─────────────────────────────────────────────────────────────────────────────

async def _build_memory_graph_nodes(
    memories: List[Dict[str, Any]],
    account_id: str,
    workspace_names: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Transforma las filas de BD al formato de nodo de grafo para memorias.
    Genera embeddings en batch para todos los contenidos.
    No llama a ningún LLM: el contenido de la memoria ya es su representación.
    """
    embeddings_model = get_embedding_model()

    contents: List[str] = []
    nodes: List[Dict[str, Any]] = []

    for mem in memories:
        meta = mem.get("cmetadata") or {}
        raw_content = (mem.get("document") or "").strip()
        node_type = _resolve_memory_node_type(meta.get("type", "user_memory"))
        name = _build_memory_node_title(mem)
        # Texto que se indexa para similitud: título + topic + contenido
        sim_text = "\n".join(filter(None, [name, meta.get("topic"), meta.get("category"), raw_content]))
        contents.append(sim_text[:2000])

        ws_id = meta.get("workspace_id") or ""
        ws_name = ""
        if workspace_names and ws_id:
            ws_name = workspace_names.get(str(ws_id)) or ""

        nodes.append({
            "id": f"memory_{mem['id']}",
            "name": name,
            "content": raw_content,
            "topic": meta.get("topic") or "general",
            "category": meta.get("category") or "",
            "memory_type": meta.get("type") or "user_memory",
            "node_type": node_type,
            "workspace_id": ws_id,
            "workspace": ws_name,
            "thread_id": meta.get("thread_id") or "",
            "account_id": account_id,
            "original_uuid": str(mem["id"]),
            "created_at": meta.get("created_at") or datetime.now().isoformat(),
            "embedding": None,
            # Guardamos el metadata completo para el paso de relaciones
            "_metadata": meta,
        })

    # Generar embeddings en batch
    if embeddings_model and contents:
        try:
            embeddings = await embeddings_model.aembed_documents(contents)
            for node, emb in zip(nodes, embeddings):
                node["embedding"] = emb
        except Exception as exc:
            logger.warning(f"⚠️ No se pudieron generar embeddings para memorias: {exc}")

    return nodes


async def _link_memories_to_existing_entities(
    memory_nodes: List[Dict[str, Any]],
    neo4j_adapter: Neo4jAdapter,
    account_id: str,
    similarity_threshold: float = 0.72,
) -> int:
    """
    Conecta cada memoria nueva con entidades existentes en el grafo mediante
    similitud semántica entre embeddings.
    Solo crea relaciones MEMORY_MENTIONS hacia nodos que ya existen.
    """
    existing = await neo4j_adapter.get_existing_entity_ids_for_account(account_id, limit=500)
    if not existing:
        return 0

    # Filtrar memorias y entidades que tengan embedding
    mems_with_emb = [m for m in memory_nodes if m.get("embedding")]
    ents_with_emb = [e for e in existing if e.get("embedding")]
    if not mems_with_emb or not ents_with_emb:
        return 0

    total_links = 0
    for mem in mems_with_emb:
        mem_emb = mem["embedding"]
        matched_ids: List[str] = []
        for ent in ents_with_emb:
            sim = _cosine_similarity(mem_emb, ent["embedding"])
            if sim >= similarity_threshold:
                matched_ids.append(ent["id"])

        if matched_ids:
            created = await neo4j_adapter.link_memories_to_entities(
                memory_id=mem["id"],
                entity_ids=matched_ids,
                account_id=account_id,
            )
            total_links += created

    logger.info(f"🔗 {total_links} relaciones MEMORY_MENTIONS creadas hacia entidades existentes.")
    return total_links


async def process_memory_batches(account_id: str, task_id: Optional[str] = None, force: bool = False):
    """
    Pipeline dedicado para procesar memorias en el grafo de conocimiento.

    Diferencias clave respecto al pipeline de documentos:
    - Cada memoria es un nodo atómico (sin chunking, sin resumen LLM)
    - Tipo de nodo correcto: MEMORY + subtipo (USER_MEMORY, AGENT_MEMORY, etc.)
    - Embeddings generados directamente del contenido
    - Relaciones semánticas intra-lote (MEMORY_RELATED)
    - Relaciones cross-grafo con entidades existentes (MEMORY_MENTIONS)
    - NO llama a graph_integration.process_documents()
    """
    acquired = await processing_lock.acquire()
    if not acquired:
        logger.info(f"El procesamiento de memorias para {account_id} ya está en curso.")
        return

    from knowledge_graph.progress_tracker import create_progress_tracker, ProcessingPhase

    tracker = create_progress_tracker(
        task_id=task_id,
        processing_mode="memory",
        total_phases=5,
    )

    try:
        logger.info(f"🧠 [Memory Pipeline] Iniciando procesamiento para cuenta {account_id}.")
        tracker.update_phase(ProcessingPhase.INITIALIZING, "Buscando memorias pendientes...", 5)

        if force:
            reset_count = await reset_memories_processed_flag(account_id)
            logger.info(f"🔄 force=True: {reset_count} memorias marcadas para reprocesar.")
            tracker.update_sub_progress(f"Reseteando {reset_count} memorias...", 50)

        memories_raw = await get_unprocessed_memories(account_id, limit=100)
        if not memories_raw:
            logger.info("ℹ️ No hay memorias pendientes para procesar.")
            tracker.complete("ℹ️ No hay memorias pendientes para procesar.")
            return

        logger.info(f"📦 {len(memories_raw)} memorias a procesar.")
        tracker.update_phase(
            ProcessingPhase.FETCHING_DOCUMENTS,
            f"Generando embeddings para {len(memories_raw)} memorias...",
            15,
            {"documents_processed": len(memories_raw)},
        )

        # Mapear workspace_ids del lote a nombres de workspace
        workspace_ids = set()
        for mem in memories_raw:
            meta = mem.get("cmetadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            ws_id = meta.get("workspace_id")
            if ws_id:
                workspace_ids.add(ws_id)
        
        workspace_names = {}
        if workspace_ids:
            try:
                from core.database import Workspace
                from sqlalchemy import select
                import uuid
                uuid_ids = []
                for wid in workspace_ids:
                    try:
                        uuid_ids.append(uuid.UUID(wid) if isinstance(wid, str) else wid)
                    except ValueError:
                        continue
                if uuid_ids:
                    async with SessionLocal() as db_session:
                        stmt = select(Workspace).where(Workspace.id.in_(uuid_ids))
                        res = await db_session.execute(stmt)
                        for ws in res.scalars().all():
                            workspace_names[str(ws.id)] = ws.name
                    logger.info(f"💼 Resolved workspace names for memory batch: {workspace_names}")
            except Exception as e:
                logger.error(f"Error resolviendo nombres de workspace en process_memory_batches: {e}")

        # ── Paso 1: Construir nodos con embeddings ──────────────────────────
        memory_nodes = await _build_memory_graph_nodes(memories_raw, account_id, workspace_names)
        if not memory_nodes:
            logger.warning("⚠️ No se pudieron construir nodos de memoria.")
            tracker.set_error("No se pudieron construir nodos de memoria.")
            return

        # ── Paso 2: Persistir nodos en Neo4j ───────────────────────────────
        tracker.update_phase(
            ProcessingPhase.SAVING_TO_NEO4J,
            f"Persistiendo {len(memory_nodes)} nodos en Neo4j...",
            35,
        )
        graph_db = GraphDB(
            uri=str(settings.neo4j_uri),
            user=str(settings.neo4j_user),
            password=str(settings.neo4j_password),
        )
        graph_db.connect()
        adapter = Neo4jAdapter(graph_db)

        persisted = await adapter.create_memory_nodes(memory_nodes)
        logger.info(f"✅ {persisted} nodos de memoria persistidos en Neo4j.")

        # ── Paso 3: Relaciones semánticas intra-lote (MEMORY_RELATED) ───────
        tracker.update_phase(
            ProcessingPhase.HYBRID_SEMANTIC_RELATIONSHIPS,
            "Clasificando relaciones semánticas entre memorias...",
            55,
            {"entities_count": persisted},
        )
        doc_format = [
            {
                "document_id": n["id"],
                "title": n["name"],
                "content": n["content"],
                "workspace_id": n.get("workspace_id"),
                "workspace": n.get("workspace"),
                "metadata": n.get("_metadata", {}),
            }
            for n in memory_nodes
        ]
        graph_integration = GraphIntegration(graph_db)
        graph_integration.hybrid_adapter = adapter

        related = await _create_memory_to_memory_relationships(
            memory_documents=doc_format,
            graph_integration=graph_integration,
            account_id=account_id,
        )
        logger.info(f"🔗 {related} relaciones MEMORY_RELATED creadas entre memorias del lote.")

        # ── Paso 4: Relaciones cross-grafo con entidades existentes ──────────
        tracker.update_phase(
            ProcessingPhase.HYBRID_LLM_ENRICHMENT,
            "Enlazando memorias con entidades existentes del grafo...",
            75,
            {"relationships_count": related},
        )
        cross_links = await _link_memories_to_existing_entities(
            memory_nodes=memory_nodes,
            neo4j_adapter=adapter,
            account_id=account_id,
        )
        logger.info(f"🔗 {cross_links} relaciones MEMORY_MENTIONS creadas hacia entidades del grafo.")

        # ── Paso 5: Marcar como procesadas ──────────────────────────────────
        tracker.update_phase(
            ProcessingPhase.SAVING_TO_NEO4J,
            "Marcando memorias como procesadas...",
            90,
            {"relationships_count": related + cross_links},
        )
        memory_ids = [mem["id"] for mem in memories_raw]
        await mark_memories_as_processed(memory_ids)

        # ── Limpieza de espacio en Neo4j ─────────────────────────────────────
        # 1. Quitar embeddings de MEMORY nodes (ya guardados en pgvector/Postgres)
        stripped = await adapter.strip_memory_embeddings(account_id)
        # 2. Borrar nodos DOCUMENT huérfanos del pipeline roto (id STARTS WITH 'memory_')
        deleted_orphans = await adapter.cleanup_orphaned_memory_documents(account_id)
        if deleted_orphans > 0:
            logger.info(f"🗑️ {deleted_orphans} nodos DOCUMENT huérfanos eliminados durante limpieza.")

        tracker.complete(
            f"✅ {persisted} memorias integradas al grafo | "
            f"{related} relaciones semánticas | {cross_links} enlaces a entidades"
        )
        logger.info(
            f"🎉 [Memory Pipeline] Completado: {persisted} nodos | "
            f"{related} MEMORY_RELATED | {cross_links} MEMORY_MENTIONS"
        )

    except Exception as e:
        logger.error(
            f"❌ [Memory Pipeline] Error procesando memorias para {account_id}: {e}",
            exc_info=True,
        )
        tracker.set_error(str(e))
    finally:
        processing_lock.release()
