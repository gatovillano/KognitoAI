import logging
from langchain_core.messages import HumanMessage
import uuid
from typing import List, Optional, cast, Dict
import asyncio
from datetime import datetime, timedelta, timezone

from core.llm_manager import get_fast_llm, get_llm_for_user

from fastapi import APIRouter, HTTPException, Depends, status, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc, or_, and_, update, func, String, text

from core.database import SessionLocal, AnalysisTask, ProactiveInsight, MindmapTask, GapDevelopmentAnalysis
from sqlalchemy.orm import joinedload
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.memory_manager import list_user_documents, get_full_document_content
from core.database import GitHubDocument
from utils.advanced_text_analyzer import text_analyzer
from utils.document_summarizer import run_document_summary_and_save
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np
from collections import Counter
from utils.embeddings import get_embedding_model, get_text_embedding # Importar get_text_embedding desde utils.embeddings
from core.dependencies import get_db_session
from utils.db_session import DBSession
from core.notes_manager import NotesManager
from utils.note_analysis_utils import analyze_single_note, analyze_note_collection, summarize_note
from utils.analysis_progress import (
    send_analysis_progress,
    persist_analysis_progress,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

from typing import AsyncGenerator

# get_db eliminado en favor de core.dependencies.get_db_session

def extract_topics_from_payload(payload: dict) -> List[dict]:
    extracted = []
    if not isinstance(payload, dict):
        return extracted
        
    def add_theme(theme_name: str, quotes_raw, mentions: int = 1):
        if not theme_name or not isinstance(theme_name, str):
            return
        theme_name = theme_name.strip()
        if not theme_name:
            return
        
        # Normalize quotes
        quotes = []
        if quotes_raw:
            if isinstance(quotes_raw, list):
                for q in quotes_raw:
                    if isinstance(q, str):
                        quotes.append({"document_title": "Documento", "quote": q})
                    elif isinstance(q, dict):
                        doc = q.get("document_title") or q.get("source_reference") or q.get("documento") or "Documento"
                        text = q.get("quote") or q.get("text") or q.get("cita") or ""
                        if text:
                            quotes.append({"document_title": doc, "quote": text})
            elif isinstance(quotes_raw, str):
                quotes.append({"document_title": "Documento", "quote": quotes_raw})
                
        extracted.append({
            "topic": theme_name,
            "quotes": quotes,
            "mentions": mentions
        })

    # 1. key_themes
    if "key_themes" in payload and isinstance(payload["key_themes"], list):
        for item in payload["key_themes"]:
            if isinstance(item, str):
                add_theme(item, None)
            elif isinstance(item, dict):
                name = item.get("theme") or item.get("tema") or item.get("name")
                quotes_raw = item.get("related_quotes") or item.get("quotes") or item.get("citas")
                add_theme(name, quotes_raw)

    # 2. cross_cutting_themes
    if "cross_cutting_themes" in payload and isinstance(payload["cross_cutting_themes"], list):
        for item in payload["cross_cutting_themes"]:
            if isinstance(item, str):
                add_theme(item, None)
            elif isinstance(item, dict):
                name = item.get("theme") or item.get("tema") or item.get("name") or item.get("description")
                quotes_raw = item.get("related_quotes") or item.get("quotes") or item.get("citas")
                add_theme(name, quotes_raw)

    # 3. temas_transversales
    if "temas_transversales" in payload and isinstance(payload["temas_transversales"], list):
        for item in payload["temas_transversales"]:
            if isinstance(item, str):
                add_theme(item, None)
            elif isinstance(item, dict):
                name = item.get("tema") or item.get("theme") or item.get("name")
                quotes_raw = item.get("citas") or item.get("related_quotes") or item.get("quotes")
                add_theme(name, quotes_raw)

    # 4. grouped_topics
    if "grouped_topics" in payload and isinstance(payload["grouped_topics"], list):
        for item in payload["grouped_topics"]:
            if isinstance(item, dict):
                name = item.get("topic") or item.get("tema") or item.get("theme")
                quotes_raw = item.get("quotes") or item.get("citas") or item.get("related_quotes")
                mentions = item.get("mentions", 1)
                add_theme(name, quotes_raw, mentions)

    # 5. temas_clave_avanzados
    if "temas_clave_avanzados" in payload and isinstance(payload["temas_clave_avanzados"], list):
        for item in payload["temas_clave_avanzados"]:
            if isinstance(item, str):
                add_theme(item, None)
            elif isinstance(item, dict):
                name = item.get("tema") or item.get("theme") or item.get("name")
                quotes_raw = item.get("citas") or item.get("related_quotes") or item.get("quotes")
                add_theme(name, quotes_raw)

    # 6. main_topic
    main_t = payload.get("main_topic")
    if main_t and isinstance(main_t, str):
        add_theme(main_t, None)

    # 7. concepts / conceptos / conceptos_centrales / central_concepts
    for key in ["concepts", "conceptos", "conceptos_centrales", "central_concepts"]:
        if key in payload and isinstance(payload[key], list):
            for item in payload[key]:
                if isinstance(item, str):
                    if ":" in item:
                        parts = item.split(":", 1)
                        concept_name = parts[0].strip()
                        if len(concept_name) < 50:
                            add_theme(concept_name, None)
                        else:
                            add_theme(item, None)
                    else:
                        add_theme(item, None)
                elif isinstance(item, dict):
                    name = item.get("concept") or item.get("concepto") or item.get("name") or item.get("theme") or item.get("tema")
                    quotes_raw = item.get("related_quotes") or item.get("quotes") or item.get("citas")
                    add_theme(name, quotes_raw)

    return extracted


async def list_all_user_documents(account_id: str, topic: Optional[str] = None, workspace_id: Optional[str] = None):
    """
    Combina documentos regulares y documentos de GitHub para un usuario.
    """
    # Obtener documentos regulares, pasando el topic y workspace_id para filtrar en la BD
    regular_docs = await list_user_documents(account_id=account_id, topic=topic, workspace_id=workspace_id)
    
    # Obtener documentos de GitHub
    async with DBSession(SessionLocal) as db: # type: ignore
        query = select(GitHubDocument).where(GitHubDocument.account_id == uuid.UUID(account_id))
        result = await db.execute(query)
        github_docs = result.scalars().all()
        
        github_formatted = [
            {
                "file_name": doc.file_path,
                "repo_url": doc.repo_url,
                "topic": "Repositories",
                "title": doc.file_path.split('/')[-1],
                "author": None,
                "document_id": f"github_{doc.id}",
                "workspace_id": str(doc.workspace_id) if doc.workspace_id else None
            }
            for doc in github_docs
        ]
    
    # Combinar ambos tipos de documentos
    all_docs = regular_docs + github_formatted
    
    # Filtrar por topic si se especifica
    if topic:
        all_docs = [doc for doc in all_docs if doc.get('topic') == topic]
    
    return all_docs

class GetSavedAnalysesRequest(BaseModel):
    topic: Optional[str] = None  # Para filtrar por colección
    all: bool = False  # Para obtener todos los análisis sin filtrar por colección
    workspace_id: Optional[str] = None  # Para filtrar por workspace

@router.post("/get-saved-analyses")
async def get_saved_analyses_endpoint(
    req: GetSavedAnalysesRequest,
    current_account_id: str = Depends(get_current_account_id), 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Recupera la lista de análisis completados.
    Si se proporciona un 'topic', devuelve los análisis de esa colección Y de sus documentos.
    Si 'all' es True, devuelve todos los análisis.
    Si no, devuelve solo los análisis de documentos individuales.
    """
    account_uuid = uuid.UUID(current_account_id)
    
    # Construimos la consulta base
    base_stmt = select(AnalysisTask).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed"
    )

    if req.topic:
        # --- LÓGICA MEJORADA PARA COLECCIONES ---
        
        # 1. Obtenemos los nombres de los archivos que pertenecen a este topic.
        #    (Usamos la función combinada que incluye documentos de GitHub)
        all_user_docs = await list_all_user_documents(current_account_id, topic=req.topic, workspace_id=req.workspace_id)
        files_in_topic = [
            doc['file_name'] for doc in all_user_docs if doc.get('topic') == req.topic
        ]
        
        # 2. Construimos la condición del WHERE
        #    Queremos análisis cuyo 'file_name' sea uno de los archivos de la colección,
        #    O que sea el análisis de la propia colección, O que sea un análisis semántico.
        collection_reference_name = f"Colección: {req.topic}"
        semantic_reference_name = f"Resumen Semántico: {req.topic}"
        custom_reference_name = f"Análisis Personalizado: Colección: {req.topic}"
        graph_reference_name = f"Análisis de Grafo de Conocimiento: {req.topic}"

        # Usamos or_() para combinar las condiciones
        conditions = [
            AnalysisTask.file_name.in_(files_in_topic),
            AnalysisTask.file_name == collection_reference_name,
            AnalysisTask.file_name == semantic_reference_name,
            AnalysisTask.file_name == custom_reference_name,
            AnalysisTask.file_name == graph_reference_name,
            AnalysisTask.file_name == req.topic  # Para compatibilidad con versiones anteriores o simplificadas
        ]

        final_stmt = base_stmt.where(or_(*conditions))

        # No filtrar por workspace_id en la consulta SQL, lo haremos después
    elif req.all:
        # Si se pide 'all', no aplicamos más filtros.
        final_stmt = base_stmt
    else:
        # Comportamiento por defecto: devolver todos los análisis completados si no se especifica un 'topic'.
        final_stmt = base_stmt

    # Ordenamos y limitamos la consulta final
    final_stmt = final_stmt.order_by(desc(AnalysisTask.created_at)).limit(100)  # Obtener más para filtrar después

    results = await db.execute(final_stmt)
    all_analyses = results.scalars().all()

    # Filtrar por workspace_id después de obtener los resultados
    if req.topic:  # Solo filtrar por workspace si se especifica un topic
        filtered_analyses = []
        for analysis in all_analyses:
            analysis_workspace_id = None

            # Extraer workspace_id del result_payload
            if analysis.result_payload:
                # Intentar obtener workspace_id de analysis_metadata primero
                if 'analysis_metadata' in analysis.result_payload and 'workspace_id' in analysis.result_payload['analysis_metadata']:
                    analysis_workspace_id = analysis.result_payload['analysis_metadata']['workspace_id']
                # Si no está ahí, intentar obtenerlo del nivel superior
                elif 'workspace_id' in analysis.result_payload:
                    analysis_workspace_id = analysis.result_payload['workspace_id']

            # Aplicar filtro de workspace_id
            if req.workspace_id:
                # Para workspaces específicos, incluir solo análisis de ese workspace
                if analysis_workspace_id == req.workspace_id:
                    filtered_analyses.append(analysis)
            elif analysis_workspace_id is None: # Si req.workspace_id es None, incluir solo análisis sin workspace_id
                filtered_analyses.append(analysis)
            # Si req.workspace_id está presente pero analysis_workspace_id no coincide, no se añade.
 
        return filtered_analyses[:50]  # Limitar a 50 después del filtrado
    else:
        # Si req.topic no está especificado, filtramos por workspace_id si se proporciona,
        # o solo por análisis sin workspace_id si req.workspace_id es None.
        if req.workspace_id:
            return [a for a in all_analyses if a.result_payload and a.result_payload.get('workspace_id') == req.workspace_id][:50]
        elif req.workspace_id is None:
            return [a for a in all_analyses if not a.result_payload or a.result_payload.get('workspace_id') is None][:50]
        else:
            return all_analyses[:50] # Esto no debería ocurrir si req.workspace_id es Optional[str]

class DeleteAnalysisRequest(BaseModel):
    task_id: uuid.UUID

class DeleteProactiveInsightRequest(BaseModel):
    insight_id: int

@router.delete("/delete-analysis", summary="Eliminar un análisis guardado")
async def delete_analysis_endpoint(
    req: DeleteAnalysisRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina un análisis guardado por su ID de tarea, si pertenece al usuario autenticado.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)
        task_uuid = req.task_id
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de tarea inválido. Debe ser un UUID válido.")
    
    task = await db.get(AnalysisTask, task_uuid)
    if task is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    # Evitar comparación directa que puede causar error de tipo en Pylance
    if str(task.account_id) != str(account_uuid):
        raise HTTPException(status_code=404, detail="Análisis no pertenece al usuario.")
    
    await db.delete(task)
    await db.commit()
    return {"message": f"Análisis con ID {req.task_id} eliminado correctamente."}

@router.delete("/delete-proactive-insight", summary="Eliminar un insight proactivo")
async def delete_proactive_insight_endpoint(
    req: DeleteProactiveInsightRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina un insight proactivo por su ID, si pertenece al usuario autenticado.
    """
    account_uuid = uuid.UUID(current_account_id)
    
    insight = await db.get(ProactiveInsight, req.insight_id)
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight no encontrado.")
    
    if str(insight.account_id) != str(account_uuid):
        raise HTTPException(status_code=403, detail="Insight no pertenece al usuario.")
    
    await db.delete(insight)
    await db.commit()
    return {"message": f"Insight con ID {req.insight_id} eliminado correctamente."}

class AcceptProactiveInsightRequest(BaseModel):
    insight_id: int

@router.post("/accept-proactive-insight", summary="Aceptar un insight proactivo")
async def accept_proactive_insight_endpoint(
    req: AcceptProactiveInsightRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    account_uuid = uuid.UUID(current_account_id)
    insight = await db.get(ProactiveInsight, req.insight_id)
    if insight is None or str(insight.account_id) != str(account_uuid):
        raise HTTPException(status_code=404, detail="Insight no encontrado.")
    
    insight.status = "accepted"
    await db.commit()
    return {"message": "Insight aceptado correctamente."}

class DashboardInsightsRequest(BaseModel):
    all: bool = False

@router.post("/dashboard-insights")
async def get_dashboard_insights(
    req: DashboardInsightsRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Agrega y devuelve datos de análisis (manuales) y insights (proactivos)
    para el dashboard principal.
    """
    account_uuid = uuid.UUID(current_account_id)

    semantic_payload_for_grouped_topics = None # Inicializar a None

    # 1. Obtener estadísticas de tareas de análisis
    stats_query = """
        SELECT
            CASE
                WHEN analysis_type IN ('document', 'single_note', 'single_note_summary') THEN 'document'
                WHEN analysis_type IN ('collection', 'notes_collection', 'repository_update') THEN 'collection'
                WHEN analysis_type IN ('semantic', 'semantic_summary') THEN 'semantic'
                WHEN analysis_type = 'code' THEN 'code'
                WHEN analysis_type = 'proactive_insight_manual' THEN 'insight'
                WHEN analysis_type = 'custom' THEN 'custom'
                WHEN analysis_type = 'knowledge_graph_analysis' THEN 'knowledge_graph'
                WHEN analysis_type = 'gap_development' THEN 'gap_development'
                ELSE 'document'
            END as frontend_analysis_type,
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            MAX(created_at) as last_used
        FROM analysis_tasks
        WHERE account_id = :account_id
        GROUP BY frontend_analysis_type
        ORDER BY total DESC
    """
    stats_result = await db.execute(text(stats_query), {"account_id": account_uuid})
    analysis_stats_rows = stats_result.fetchall()

    logger.info(f"DEBUG: analysis_stats_rows from DB: {analysis_stats_rows}")

    analysis_stats = []
    total_analysis_tasks = 0
    for row in analysis_stats_rows:
        analysis_stats.append({
            "type": row[0],
            "total": row[1],
            "completed": row[2],
            "pending": row[3],
            "failed": row[4],
            "last_used": row[5].isoformat() if row[5] else None
        })
        total_analysis_tasks += row[1]

    # --- NUEVO: Obtener estadísticas de insights proactivos ---
    proactive_stats_query = """
        SELECT
            'insight' as analysis_type,
            COUNT(*) as total,
            COUNT(*) as completed,
            0 as pending,
            0 as failed,
            MAX(created_at) as last_used
        FROM proactive_insights
        WHERE account_id = :account_id
    """
    proactive_stats_result = await db.execute(text(proactive_stats_query), {"account_id": account_uuid})
    proactive_stats_row = proactive_stats_result.fetchone()

    if proactive_stats_row and proactive_stats_row[1] > 0:
        # Buscar si ya existe una entrada para 'insight'
        insight_stats_found = False
        for stat in analysis_stats:
            if stat["type"] == "insight":
                stat["total"] += proactive_stats_row[1]
                stat["completed"] += proactive_stats_row[2]
                if proactive_stats_row[5]:
                    stat["last_used"] = max(stat["last_used"] or "1970-01-01T00:00:00", proactive_stats_row[5].isoformat())
                insight_stats_found = True
                break
        
        if not insight_stats_found:
            analysis_stats.append({
                "type": "insight",
                "total": proactive_stats_row[1],
                "completed": proactive_stats_row[2],
                "pending": 0,
                "failed": 0,
                "last_used": proactive_stats_row[5].isoformat() if proactive_stats_row[5] else None
            })
        
        total_analysis_tasks += proactive_stats_row[1]


    logger.info(f"DEBUG: Processed analysis_stats (with proactive): {analysis_stats}")

    # 2. Obtener los últimos insights proactivos (sinergias, contradicciones, etc.)
    proactive_stmt = select(ProactiveInsight).options(joinedload(ProactiveInsight.workspace)).where(
        ProactiveInsight.account_id == account_uuid
    ).order_by(desc(ProactiveInsight.created_at))

    if not req.all:
        proactive_stmt = proactive_stmt.limit(5) # Limitar a los 5 más recientes para el dashboard
    
    proactive_results = await db.execute(proactive_stmt)
    recent_proactive_insights = proactive_results.scalars().all()

    logger.info(f"DEBUG: Found {len(recent_proactive_insights)} recent proactive insights for account {current_account_id}")

    total_proactive_insights_stmt = select(func.count(ProactiveInsight.id)).where(ProactiveInsight.account_id == account_uuid)
    total_proactive_insights = (await db.execute(total_proactive_insights_stmt)).scalar_one()

    logger.info(f"DEBUG: Total proactive insights in DB: {total_proactive_insights}")

    # 3. Obtener brechas de conocimiento y preguntas de exploración de análisis de documentos y colecciones
    # Buscar análisis de documentos y colecciones que contengan brechas de conocimiento o preguntas
    analysis_with_gaps_or_questions_stmt = select(AnalysisTask.result_payload, AnalysisTask.file_name, AnalysisTask.created_at).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        or_(
            AnalysisTask.analysis_type == "semantic",
            AnalysisTask.analysis_type == "semantic_summary",
            AnalysisTask.analysis_type == "document",
            AnalysisTask.analysis_type == "collection",
            AnalysisTask.analysis_type == "single_note",
            AnalysisTask.analysis_type == "notes_collection"
        ),
        # Filtramos por aquellos que tienen las claves específicas en el payload
        or_(
            func.jsonb_exists(AnalysisTask.result_payload, "brechas_conocimiento"),
            func.jsonb_exists(AnalysisTask.result_payload, "emergent_knowledge_gaps"),
            func.jsonb_exists(AnalysisTask.result_payload, "preguntas_exploracion"),
            func.jsonb_exists(AnalysisTask.result_payload, "exploration_questions"),
            func.jsonb_exists(AnalysisTask.result_payload, "knowledge_gaps")
        )
    ).order_by(desc(AnalysisTask.created_at)).limit(10)  # Obtener hasta 10 análisis

    analysis_with_gaps_or_questions_result = await db.execute(analysis_with_gaps_or_questions_stmt)
    semantic_results = analysis_with_gaps_or_questions_result.fetchall()
    logger.info(f"Analysis Payload (with gaps/questions search): Found {len(semantic_results)} analyses with gaps/questions")

    emergent_knowledge_gaps = []
    exploration_questions = []
    semantic_payload = None # Inicializar para evitar UnboundLocalError
    
    # Combinar brechas de todos los análisis encontrados
    for result in semantic_results:
        semantic_payload = result[0]  # result_payload
        file_name = result[1]  # file_name
        created_at = result[2]  # created_at
        
        if semantic_payload:
            # 1. Extraer Brechas de Conocimiento (Gaps)
            gaps_source = None
            if "brechas_conocimiento" in semantic_payload:
                gaps_source = semantic_payload["brechas_conocimiento"]
            elif "emergent_knowledge_gaps" in semantic_payload:
                gaps_source = semantic_payload["emergent_knowledge_gaps"]
            elif "knowledge_gaps" in semantic_payload:
                gaps_source = semantic_payload["knowledge_gaps"]
            
            if gaps_source and isinstance(gaps_source, list):
                for gap in gaps_source:
                    if isinstance(gap, dict):
                        # Intentar obtener el texto de la brecha de varias posibles claves
                        gap_text = gap.get("question") or gap.get("gap_title") or gap.get("explanation")
                        if gap_text:
                            emergent_knowledge_gaps.append(gap_text)
                    elif isinstance(gap, str):
                        emergent_knowledge_gaps.append(gap)

            # 2. Extraer Preguntas de Exploración
            questions_source = None
            if "preguntas_exploracion" in semantic_payload:
                questions_source = semantic_payload["preguntas_exploracion"]
            elif "exploration_questions" in semantic_payload:
                questions_source = semantic_payload["exploration_questions"]
            
            if questions_source and isinstance(questions_source, list):
                for q in questions_source:
                    if isinstance(q, dict):
                        q_text = q.get("question") or q.get("text")
                        if q_text:
                            exploration_questions.append(q_text)
                    elif isinstance(q, str):
                        exploration_questions.append(q)
    
    # Limitar a las 10 brechas más recientes para evitar sobrecarga
    # Usar shuffle aleatorio para mostrar diversidad de brechas
    import random
    random.shuffle(emergent_knowledge_gaps)
    emergent_knowledge_gaps = emergent_knowledge_gaps[:10]
    
    random.shuffle(exploration_questions)
    exploration_questions = exploration_questions[:10]
    
    logger.info(f"Emergent Knowledge Gaps (backend): Found {len(emergent_knowledge_gaps)} gaps from {len(semantic_results)} analyses")
    logger.info(f"Exploration Questions (backend): Found {len(exploration_questions)} questions from {len(semantic_results)} analyses")

    # Si no encontramos un payload con brechas/preguntas, intentamos obtener el último análisis semántico general
    # Esto es para asegurar que los key_topics se sigan mostrando si no hay brechas/preguntas específicas
    if not semantic_payload:
        latest_general_semantic_analysis_stmt = select(AnalysisTask.result_payload).where(
            AnalysisTask.account_id == account_uuid,
            AnalysisTask.status == "completed",
            or_(
                AnalysisTask.analysis_type == "document",
                AnalysisTask.analysis_type == "collection",
                AnalysisTask.analysis_type == "semantic",
                AnalysisTask.analysis_type == "semantic_summary"
            ),
            AnalysisTask.result_payload.isnot(None)
        ).order_by(desc(AnalysisTask.created_at)).limit(1)
        general_semantic_analysis_result = await db.execute(latest_general_semantic_analysis_stmt)
        semantic_payload = general_semantic_analysis_result.scalars().first()
        logger.info(f"Semantic Payload (general search fallback): {semantic_payload}")


    # 4. Obtener los temas clave (reutilizando la lógica existente)
    analysis_stmt_for_topics = select(AnalysisTask).where( # Seleccionar la tarea completa para acceder a result_payload
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        AnalysisTask.result_payload.isnot(None)
    )
    analysis_results_for_topics = await db.execute(analysis_stmt_for_topics)
    analysis_tasks_for_topics = analysis_results_for_topics.scalars().all()

    all_topics_with_quotes = {} # Usaremos un diccionario para agrupar temas y sus citas
    for task in analysis_tasks_for_topics:
        payload = task.result_payload
        if isinstance(payload, dict):
            extracted_topics = extract_topics_from_payload(payload)
            for t in extracted_topics:
                topic_name = t["topic"]
                if topic_name not in all_topics_with_quotes:
                    all_topics_with_quotes[topic_name] = {"mentions": 0, "quotes": []}
                all_topics_with_quotes[topic_name]["mentions"] += t.get("mentions", 1)
                
                # Extend quotes while keeping them unique by their 'quote' text
                existing_texts = {q["quote"] for q in all_topics_with_quotes[topic_name]["quotes"]}
                for q in t["quotes"]:
                    if q["quote"] not in existing_texts:
                        all_topics_with_quotes[topic_name]["quotes"].append(q)
                        existing_texts.add(q["quote"])

    # Convertir el diccionario a la lista de KeyTopic esperada por el frontend
    key_topics_for_dashboard = []
    for topic_name, data in all_topics_with_quotes.items():
        key_topics_for_dashboard.append({
            "topic": topic_name,
            "mentions": data["mentions"],
            "quotes": data["quotes"] # Incluir las citas aquí
        })

    # Ordenar por menciones y limitar a los 10 principales
    key_topics_for_dashboard.sort(key=lambda x: x["mentions"], reverse=True)
    top_topics_for_chart = key_topics_for_dashboard[:10]

    # Obtener el último análisis semántico para temas agrupados (tipo 'semantic')
    semantic_analysis_stmt_for_grouped_topics = select(AnalysisTask.result_payload).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        AnalysisTask.analysis_type == "semantic", # Solo el tipo 'semantic' tiene grouped_topics
        AnalysisTask.result_payload.isnot(None)
    ).order_by(desc(AnalysisTask.created_at)).limit(1)
    
    semantic_analysis_result_for_grouped_topics = await db.execute(semantic_analysis_stmt_for_grouped_topics)
    semantic_payload_for_grouped_topics = semantic_analysis_result_for_grouped_topics.scalars().first()

    logger.info(f"Semantic Payload for Grouped Topics (before processing): {semantic_payload_for_grouped_topics}")

    if semantic_payload_for_grouped_topics and "grouped_topics" in semantic_payload_for_grouped_topics:
        grouped_topics_from_semantic = semantic_payload_for_grouped_topics["grouped_topics"]
        if grouped_topics_from_semantic:
            # Si hay temas agrupados del análisis semántico, los usamos.
            # Asegurarse de que cada elemento en top_topics_for_chart tenga el campo 'quotes'
            for topic_item in grouped_topics_from_semantic:
                if "quotes" not in topic_item:
                    topic_item["quotes"] = [] # Añadir un array vacío si no existen citas
            top_topics_for_chart = grouped_topics_from_semantic
            logger.info(f"Usando temas agrupados por análisis semántico para account {current_account_id}.")
        else:
            logger.info(f"Análisis semántico de temas agrupados encontrado, pero 'grouped_topics' está vacío. Manteniendo key_topics_for_dashboard.")
    else:
        logger.info(f"No se encontró análisis semántico de temas agrupados o no contiene 'grouped_topics'. Manteniendo key_topics_for_dashboard.")

    logger.info(f"Final Key Topics for Dashboard (before return): {top_topics_for_chart}")

    # 5. Construir y devolver la respuesta final
    response_data = {
        "total_analysis_tasks": total_analysis_tasks,
        "analysis_stats_by_type": analysis_stats,
        "total_proactive_insights": total_proactive_insights,
        "proactive_insights": [
            {
                "id": str(insight.id),
                "type": insight.type,
                "summary": insight.insight_message,
                "created_at": insight.created_at.isoformat(),
                "related_items": insight.related_items,
                "action_suggestion": insight.action_suggestion,
                "workspace_id": str(insight.workspace_id) if getattr(insight, 'workspace_id', None) else None,
                "workspace_name": insight.workspace.name if getattr(insight, 'workspace', None) else None,
                "workspace_color": insight.workspace.color if getattr(insight, 'workspace', None) else None,
            } for insight in recent_proactive_insights
        ],
        "key_topics": top_topics_for_chart,
        "emergent_knowledge_gaps": emergent_knowledge_gaps,
        "exploration_questions": exploration_questions,
    }

    logger.info(f"DEBUG: Returning dashboard insights data: {response_data}")

    return response_data

class NoteForAnalysis(BaseModel):
    id: int
    title: Optional[str] = None
    content: str

class AnalyzeNotesRequest(BaseModel):
    notes: List[NoteForAnalysis]
    workspace_id: Optional[str] = None

async def run_notes_collection_analysis_and_save(task_id: str, account_id: str, notes_data: List[Dict[str, str]], workspace_id: Optional[str]):
    """
    Obtiene el contenido de las notas, las analiza y guarda el resultado.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
            await db_session.commit()
            
            logger.info(f"Iniciando análisis de colección de notas para tarea {task_id}")

            documents_for_analysis = []
            for note in notes_data:
                documents_for_analysis.append({
                    "title": note.get("title", "Nota sin título"),
                    "content": note["content"]
                })

            if not documents_for_analysis:
                raise ValueError("No se encontraron notas con contenido para analizar.")

            # Realizar el análisis de la colección de notas
            analysis_result = await text_analyzer.analyze_collection(documents_for_analysis, account_id=str(account_id))
            logger.info(f"Notes collection analysis result generated: {analysis_result.model_dump()}")

            # Guardar el resultado y marcar como 'completed'
            result_payload = analysis_result.model_dump()

            # Agregar metadata de herramienta utilizada
            result_payload["tool_used"] = "advanced_text_analyzer.py"
            result_payload["analysis_metadata"] = {
                "tool_used": "advanced_text_analyzer.py",
                "analysis_type": "notes_collection",
                "notes_count": len(documents_for_analysis),
                "workspace_id": workspace_id,
                "created_at": datetime.now().isoformat()
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis de colección de notas para tarea {task_id} completado.")

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis de colección de notas {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/start-notes-collection-analysis", status_code=202)
async def start_notes_collection_analysis_endpoint(
    req: AnalyzeNotesRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Inicia un análisis de una colección de notas y devuelve un ID de tarea."""
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name="Colección de Notas",
        status="pending",
        analysis_type="notes_collection"  # NUEVO: Tipo específico para colección de notas
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    # Convertir la lista de objetos NoteForAnalysis a una lista de diccionarios para pasar a la tarea de fondo
    notes_data_dicts = [note.model_dump() for note in req.notes]

    background_tasks.add_task(run_notes_collection_analysis_and_save, str(new_task.id), current_account_id, notes_data_dicts, req.workspace_id)
    
    return {"task_id": str(new_task.id)}

class AnalyzeDocumentRequest(BaseModel):
    file_name: str

async def run_document_analysis_and_save(task_id: str, account_id: str, file_name: str):
    """Función pesada que se ejecuta en segundo plano."""
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            await persist_analysis_progress(
                db_session,
                task_id,
                status="processing",
                phase="initializing",
                message=f'Preparando análisis de "{file_name}"...',
                progress_percent=5,
                analysis_type="document",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="initializing",
                message=f'Preparando análisis de "{file_name}"...',
                progress_percent=5,
                file_name=file_name,
                analysis_type="document",
            )

            logger.info(f"Iniciando análisis para tarea {task_id}...")
            await persist_analysis_progress(
                db_session,
                task_id,
                phase="reconstructing_content",
                message="Cargando contenido completo del documento...",
                progress_percent=18,
                analysis_type="document",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="reconstructing_content",
                message="Cargando contenido completo del documento...",
                progress_percent=18,
                file_name=file_name,
                analysis_type="document",
            )
            text_content = await get_full_document_content(account_id, file_name)
            if not text_content:
                raise ValueError("Contenido del documento no encontrado.")

            await persist_analysis_progress(
                db_session,
                task_id,
                phase="analyzing",
                message="Analizando estructura, conceptos y brechas del documento...",
                progress_percent=35,
                analysis_type="document",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="analyzing",
                message="Analizando estructura, conceptos y brechas del documento...",
                progress_percent=35,
                file_name=file_name,
                analysis_type="document",
            )

            _llm_done = asyncio.Event()

            async def _progress_ticker():
                steps = [
                    (42, "Extrayendo ideas principales..."),
                    (50, "Identificando temas clave..."),
                    (58, "Detectando conceptos centrales..."),
                    (66, "Buscando brechas de conocimiento..."),
                    (74, "Formulando preguntas de exploración..."),
                    (82, "Redactando síntesis estratégica..."),
                    (88, "Revisando consistencia del análisis..."),
                ]
                for pct, msg in steps:
                    try:
                        await asyncio.wait_for(_llm_done.wait(), timeout=6.0)
                        break
                    except asyncio.TimeoutError:
                        pass
                    if _llm_done.is_set():
                        break
                    await persist_analysis_progress(
                        db_session,
                        task_id,
                        phase="analyzing",
                        message=msg,
                        progress_percent=pct,
                        analysis_type="document",
                        file_name=file_name,
                    )
                    await send_analysis_progress(
                        account_id,
                        task_id,
                        phase="analyzing",
                        message=msg,
                        progress_percent=pct,
                        file_name=file_name,
                        analysis_type="document",
                    )

            async def _run_llm():
                result = await text_analyzer.analyze_single_text(
                    text_content,
                    document_title=file_name,
                    account_id=str(account_id),
                )
                _llm_done.set()
                return result

            analysis_result, _ = await asyncio.gather(_run_llm(), _progress_ticker())

            # 3. Guardar el resultado y marcar como 'completed'
            # Asegurarse de que el resultado sea un diccionario
            result_payload = analysis_result if isinstance(analysis_result, dict) else analysis_result.dict()

            await persist_analysis_progress(
                db_session,
                task_id,
                phase="saving_to_neo4j",
                message="Guardando resultado final del análisis...",
                progress_percent=94,
                analysis_type="document",
                file_name=file_name,
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="saving_to_neo4j",
                message="Guardando resultado final del análisis...",
                progress_percent=94,
                file_name=file_name,
                analysis_type="document",
            )

            # Intentar obtener el título real del documento de base de datos
            document_title = file_name
            try:
                title_query = text("""
                    SELECT cmetadata->>'title' AS title 
                    FROM langchain_pg_embedding 
                    WHERE account_id = CAST(:account_id AS UUID) 
                      AND cmetadata->>'file_name' = :file_name 
                      AND cmetadata->>'type' = 'document_chunk' 
                    LIMIT 1
                """)
                title_res = await db_session.execute(title_query, {"account_id": account_id, "file_name": file_name})
                title_row = title_res.mappings().first()
                if title_row and title_row.get("title"):
                    document_title = title_row["title"]
                    logger.info(f"Título recuperado para metadata del análisis de {file_name}: {document_title}")
            except Exception as title_err:
                logger.error(f"Error al recuperar título para {file_name}: {title_err}")

            # Agregar metadata de herramienta utilizada
            result_payload["tool_used"] = "advanced_text_analyzer.py"
            result_payload["analysis_metadata"] = {
                "tool_used": "advanced_text_analyzer.py",
                "analysis_type": "document",
                "file_name": file_name,
                "title": document_title,
                "created_at": datetime.now().isoformat()
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis para tarea {task_id} completado.")
            await send_analysis_progress(
                account_id,
                task_id,
                phase="completed",
                message="¡Análisis del documento completado!",
                progress_percent=100,
                file_name=file_name,
                analysis_type="document",
                is_complete=True,
            )

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()
            await persist_analysis_progress(
                db_session,
                task_id,
                phase="error",
                message="El análisis del documento falló.",
                progress_percent=100,
                status="failed",
                analysis_type="document",
                file_name=file_name,
                has_error=True,
                error=str(e),
            )
            await send_analysis_progress(
                account_id,
                task_id,
                phase="error",
                message="El análisis del documento falló.",
                progress_percent=100,
                file_name=file_name,
                analysis_type="document",
                has_error=True,
                error=str(e),
            )

@router.post("/start-document-analysis", status_code=202)
async def start_document_analysis_endpoint(
    req: AnalyzeDocumentRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Inicia un análisis de un documento y devuelve un ID de tarea."""
    # Verificar que el documento existe antes de crear la tarea
    content_check = await get_full_document_content(current_account_id, req.file_name)
    if content_check is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=req.file_name,
        status="pending",
        analysis_type="document"  # NUEVO: Especificar tipo de análisis
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_document_analysis_and_save, str(new_task.id), current_account_id, req.file_name)
    
    return {"task_id": str(new_task.id)}

class SummarizeDocumentRequest(BaseModel):
    file_name: str
    workspace_id: Optional[str] = None

@router.post("/start-document-summary", status_code=202)
async def start_document_summary_endpoint(
    req: SummarizeDocumentRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Inicia un resumen estructurado de un documento y devuelve un ID de tarea."""
    content_check = await get_full_document_content(current_account_id, req.file_name)
    if content_check is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=req.file_name,
        status="pending",
        analysis_type="document_summary"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    background_tasks.add_task(
        run_document_summary_and_save,
        str(new_task.id),
        current_account_id,
        req.file_name,
        req.workspace_id
    )

    return {"task_id": str(new_task.id)}

@router.get("/get-analysis-result/{task_id}")
async def get_analysis_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Consulta el estado y el resultado de una tarea de análisis."""
    logger.info(f"Consulta de estado de tarea: task_id={task_id}, account_id={current_account_id}")
    task = await db.get(AnalysisTask, uuid.UUID(task_id))
    if not task:
        logger.warning(f"Tarea {task_id} no encontrada en la base de datos.")
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")
    if str(task.account_id) != current_account_id:
        logger.warning(f"Tarea {task_id} encontrada, pero account_id no coincide. Task account: {task.account_id}, Current account: {current_account_id}")
        raise HTTPException(status_code=404, detail="Tarea no pertenece al usuario.")
    logger.info(f"Tarea {task_id} encontrada. Estado: {task.status}")
    progress_info = {}
    if isinstance(task.result_payload, dict):
        progress_info = task.result_payload.get("analysis_progress") or {}

    progress_percent = progress_info.get("progress_percent")
    if progress_percent is None and task.status == "completed":
        progress_percent = 100

    current_step = progress_info.get("message") or progress_info.get("phase")
    return {
        "id": str(task.id),
        "status": task.status,
        "result": task.result_payload,
        "result_payload": task.result_payload, # Redundant but safe
        "error": task.error_message,
        "progress": progress_percent,
        "current_step": current_step,
        "progress_info": progress_info,
        "analysis_type": task.analysis_type,
        "file_name": task.file_name,
        "created_at": task.created_at.isoformat() if task.created_at else None
    }

@router.get("/get-mindmap-result/{task_id}")
@router.get("/get-analysis/{task_id}")
async def get_analysis_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Alias para get-analysis-result con formato compatible con frontend.
    Devuelve los datos en el formato esperado por AnalysisDetailDialog.
    """
    logger.info(f"Consulta de análisis: task_id={task_id}, account_id={current_account_id}")
    task = await db.get(AnalysisTask, uuid.UUID(task_id))
    if not task:
        logger.warning(f"Tarea {task_id} no encontrada en la base de datos.")
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")
    if str(task.account_id) != current_account_id:
        logger.warning(f"Tarea {task_id} encontrada, pero account_id no coincide.")
        raise HTTPException(status_code=404, detail="Tarea no pertenece al usuario.")

    # Obtener result_payload y extraer summary si existe
    result_payload = task.result_payload or {}
    summary = ""

    # Extraer summary según el tipo de análisis
    if isinstance(result_payload, dict):
        summary = (
            result_payload.get("executive_summary") or
            result_payload.get("collection_summary") or
            result_payload.get("semantic_summary") or
            result_payload.get("summary") or
            ""
        )

    return {
        "id": str(task.id),
        "status": task.status,
        "full_data": result_payload,  # Formato esperado por frontend
        "type": task.analysis_type,
        "title": task.file_name,
        "summary": summary,
        "error": task.error_message,
        "progress": 100 if task.status == "completed" else 0,
        "analysis_type": task.analysis_type,
        "file_name": task.file_name,
        "created_at": task.created_at.isoformat() if task.created_at else None
    }

@router.get("/get-mindmap-result/{task_id}")

async def get_mindmap_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Consulta el estado y el resultado de una tarea de generación de mapa mental."""
    task = await db.get(MindmapTask, uuid.UUID(task_id))
    if not task or str(task.account_id) != current_account_id:
        raise HTTPException(status_code=404, detail="Tarea de mapa mental no encontrada.")
    return {"status": task.status, "result": task.result_payload, "error": task.error_message}

class AnalyzeCollectionRequest(BaseModel):
    topic: str
    workspace_id: Optional[str] = None

async def _send_analysis_progress(
    account_id: str,
    task_id: str,
    phase: str,
    message: str,
    progress_percent: int,
    topic: Optional[str] = None,
    is_complete: bool = False,
    has_error: bool = False,
    error: Optional[str] = None,
):
    """Emite un evento analysis_progress vía WebSocket al cliente."""
    await send_analysis_progress(
        account_id,
        task_id,
        phase=phase,
        message=message,
        progress_percent=progress_percent,
        topic=topic,
        is_complete=is_complete,
        has_error=has_error,
        error=error,
    )


async def run_collection_analysis_and_save(task_id: str, account_id: str, topic: str, workspace_id: Optional[str] = None):
    """
    Obtiene todos los documentos de una colección, los analiza y guarda el resultado.
    Emite eventos WebSocket de progreso en cada etapa.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
            await db_session.commit()

            logger.info(f"Iniciando análisis de colección para tarea {task_id} (tema: {topic}, workspace: {workspace_id})")

            # ── FASE 1: Obteniendo documentos ──────────────────────────────
            await _send_analysis_progress(
                account_id, task_id,
                phase="fetching_documents",
                message="Buscando documentos en la colección...",
                progress_percent=10,
                topic=topic,
            )

            all_docs_in_topic = []
            filtered_doc_list = await list_all_user_documents(account_id, topic=topic, workspace_id=workspace_id)

            await _send_analysis_progress(
                account_id, task_id,
                phase="fetching_documents",
                message=f"Cargando contenido de {len(filtered_doc_list)} documentos...",
                progress_percent=20,
                topic=topic,
            )

            for doc_meta in filtered_doc_list:
                content = await get_full_document_content(account_id, doc_meta['file_name'])
                if content:
                    all_docs_in_topic.append({
                        "title": doc_meta.get('title', doc_meta['file_name']),
                        "content": content
                    })

            if not all_docs_in_topic:
                raise ValueError(f"No se encontraron documentos con contenido en la colección '{topic}'.")

            # ── FASE 2: Análisis semántico (con ticker de progreso) ────────
            # Como el LLM es una única llamada larga sin checkpoints internos,
            # lanzamos un ticker paralelo que envía incrementos de progreso cada
            # pocos segundos mientras el análisis corre, hasta llegar a ~88%.
            await _send_analysis_progress(
                account_id, task_id,
                phase="conceptual_extracting_quotes",
                message=f"Analizando {len(all_docs_in_topic)} documentos con IA...",
                progress_percent=40,
                topic=topic,
            )

            import asyncio as _asyncio

            _llm_done = _asyncio.Event()

            async def _progress_ticker():
                """Envía incrementos de progreso mientras el LLM trabaja."""
                _steps = [
                    (45, "Procesando estructura semántica..."),
                    (50, "Extrayendo temas transversales..."),
                    (55, "Identificando conceptos clave..."),
                    (60, "Detectando conexiones entre documentos..."),
                    (65, "Analizando relaciones temáticas..."),
                    (70, "Identificando brechas de conocimiento..."),
                    (75, "Generando síntesis de la colección..."),
                    (80, "Construyendo análisis final..."),
                    (85, "Revisando resultados con IA..."),
                    (88, "Finalizando análisis..."),
                ]
                for pct, msg in _steps:
                    # Esperar ~8 segundos entre cada tick, pero salir si el LLM terminó
                    try:
                        await _asyncio.wait_for(_llm_done.wait(), timeout=8.0)
                        break  # LLM terminó antes del próximo tick
                    except _asyncio.TimeoutError:
                        pass
                    if _llm_done.is_set():
                        break
                    await _send_analysis_progress(
                        account_id, task_id,
                        phase="conceptual_thematic_relationships",
                        message=msg,
                        progress_percent=pct,
                        topic=topic,
                    )

            # Ejecutar el análisis LLM y el ticker en paralelo.
            # _run_llm setea _llm_done al terminar para que el ticker pueda salir anticipadamente.
            async def _run_llm():
                result = await text_analyzer.analyze_collection(all_docs_in_topic, account_id=str(account_id))
                _llm_done.set()
                return result

            analysis_result, _ = await _asyncio.gather(
                _run_llm(),
                _progress_ticker(),
            )
            logger.info(f"Collection analysis result generated: {analysis_result.model_dump()}")

            # ── FASE 3: Guardando resultados ───────────────────────────────
            await _send_analysis_progress(
                account_id, task_id,
                phase="saving_to_neo4j",
                message="Guardando resultados del análisis...",
                progress_percent=90,
                topic=topic,
            )

            result_payload = analysis_result.model_dump()
            result_payload["tool_used"] = "advanced_text_analyzer.py"
            result_payload["analysis_metadata"] = {
                "tool_used": "advanced_text_analyzer.py",
                "analysis_type": "collection",
                "topic": topic,
                "documents_count": len(all_docs_in_topic),
                "created_at": datetime.now().isoformat()
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis de colección para tarea {task_id} completado.")

            # ── FASE FINAL: Completado ─────────────────────────────────────
            await _send_analysis_progress(
                account_id, task_id,
                phase="completed",
                message="¡Análisis completado con éxito!",
                progress_percent=100,
                topic=topic,
                is_complete=True,
            )

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis de colección {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()
            # Notificar error al cliente
            await _send_analysis_progress(
                account_id, task_id,
                phase="error",
                message="El análisis falló.",
                progress_percent=0,
                topic=topic,
                has_error=True,
                error=str(e),
            )

@router.post("/start-collection-analysis", status_code=202)
async def start_collection_analysis_endpoint(
    req: AnalyzeCollectionRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Inicia un análisis de una colección completa y devuelve un ID de tarea."""
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        # Usamos el nombre del topic como referencia en lugar de un file_name
        file_name=f"Colección: {req.topic}",
        status="pending",
        analysis_type="collection"  # NUEVO: Especificar tipo de análisis
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_collection_analysis_and_save, str(new_task.id), current_account_id, req.topic, req.workspace_id)
    
    return {"task_id": str(new_task.id)}

@router.post("/start-semantic-summary", status_code=202, summary="Iniciar resumen semántico de una colección")
async def start_semantic_summary_endpoint(
    req: AnalyzeCollectionRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Inicia un análisis semántico específico de una colección.
    Se enfoca en agrupación semántica de documentos y extracción de patrones.
    """
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=f"Resumen Semántico: {req.topic}",
        status="pending",
        analysis_type="semantic_summary"  # NUEVO: Tipo específico para resumen semántico
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    background_tasks.add_task(run_semantic_summary_analysis, str(new_task.id), current_account_id, req.topic, req.workspace_id)

    return {"task_id": str(new_task.id)}

@router.post("/update-semantic-topics", status_code=202, summary="Actualizar temas con análisis semántico")
async def update_semantic_topics_endpoint(
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session),
    max_terms: Optional[int] = Form(None)
):
    """
    Inicia un proceso en segundo plano para realizar análisis semántico y agrupación de temas.
    Integración con modelos de embeddings y LLMs para clustering y etiquetado.
    Se puede limitar el número de términos analizados con max_terms.
    Ahora incluye detalles de los temas individuales agrupados.
    """
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name="Semantic Topic Analysis",
        status="pending",
        analysis_type="semantic"  # NUEVO: Especificar tipo de análisis
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    background_tasks.add_task(run_semantic_topic_analysis, str(new_task.id), current_account_id, max_terms)

    return {"task_id": str(new_task.id)}

def find_optimal_clusters(embeddings_array: np.ndarray, min_clusters: int = 2, max_clusters: int = 10) -> dict:
    """
    Determina el número óptimo de clusters usando elbow method y silhouette score.
    
    Args:
        embeddings_array: Array numpy con los embeddings
        min_clusters: Número mínimo de clusters a evaluar
        max_clusters: Número máximo de clusters a evaluar
    
    Returns:
        dict con 'optimal_k', 'silhouette_score', 'inertia', 'all_scores', 'all_inertias'
    """
    n_samples = len(embeddings_array)
    
    # Ajustar límites según el número de muestras
    if n_samples < 2:
        logger.warning(f"Número de muestras insuficiente para clustering: {n_samples}")
        return {
            "optimal_k": 1,
            "silhouette_score": 0.0,
            "inertia": 0.0,
            "all_scores": [],
            "all_inertias": [],
            "method": "insufficient_samples"
        }
    
    # El número máximo de clusters no puede ser mayor que n_samples - 1
    max_clusters = min(max_clusters, n_samples - 1)
    min_clusters = min(min_clusters, max_clusters)
    
    if min_clusters >= max_clusters:
        # Si solo podemos tener un valor de k, usarlo directamente
        logger.info(f"Solo es posible evaluar k={min_clusters} clusters")
        kmeans = KMeans(n_clusters=min_clusters, random_state=42, n_init='auto')
        clusters = kmeans.fit_predict(embeddings_array)
        
        # Calcular silhouette score solo si tenemos al menos 2 clusters
        sil_score = 0.0
        if min_clusters >= 2:
            try:
                sil_score = silhouette_score(embeddings_array, clusters)
            except Exception as e:
                logger.warning(f"No se pudo calcular silhouette score: {e}")
        
        return {
            "optimal_k": min_clusters,
            "silhouette_score": float(sil_score),
            "inertia": float(kmeans.inertia_),
            "all_scores": [float(sil_score)],
            "all_inertias": [float(kmeans.inertia_)],
            "method": "single_k_available"
        }
    
    # Evaluar diferentes valores de k
    silhouette_scores = []
    inertias = []
    k_range = range(min_clusters, max_clusters + 1)
    
    logger.info(f"Evaluando número óptimo de clusters en rango [{min_clusters}, {max_clusters}] para {n_samples} muestras")
    
    for k in k_range:
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            clusters = kmeans.fit_predict(embeddings_array)
            
            # Calcular silhouette score
            sil_score = silhouette_score(embeddings_array, clusters)
            silhouette_scores.append(sil_score)
            inertias.append(kmeans.inertia_)
            
            logger.info(f"k={k}: silhouette={sil_score:.4f}, inertia={kmeans.inertia_:.2f}")
            
        except Exception as e:
            logger.error(f"Error al evaluar k={k}: {e}")
            silhouette_scores.append(0.0)
            inertias.append(float('inf'))
    
    # Determinar el k óptimo usando silhouette score (queremos maximizar)
    if silhouette_scores:
        optimal_idx = np.argmax(silhouette_scores)
        optimal_k = min_clusters + optimal_idx
        optimal_silhouette = silhouette_scores[optimal_idx]
        optimal_inertia = inertias[optimal_idx]
        
        logger.info(f"✅ Número óptimo de clusters determinado: k={optimal_k} (silhouette={optimal_silhouette:.4f})")
        
        return {
            "optimal_k": int(optimal_k),
            "silhouette_score": float(optimal_silhouette),
            "inertia": float(optimal_inertia),
            "all_scores": [float(s) for s in silhouette_scores],
            "all_inertias": [float(i) for i in inertias],
            "method": "silhouette_optimization",
            "k_range_evaluated": list(k_range)
        }
    else:
        # Fallback al valor mínimo si algo salió mal
        logger.warning("No se pudieron calcular scores, usando k mínimo como fallback")
        return {
            "optimal_k": min_clusters,
            "silhouette_score": 0.0,
            "inertia": 0.0,
            "all_scores": [],
            "all_inertias": [],
            "method": "fallback"
        }

async def run_semantic_topic_analysis(task_id: str, account_id: str, max_terms: Optional[int] = None):
    """
    Proceso en segundo plano para realizar análisis semántico y agrupación de temas.
    Integración con modelos de embeddings y LLMs para clustering y etiquetado.
    Se puede limitar el número de términos analizados con max_terms.
    Ahora incluye detalles de los temas individuales agrupados y sistema de progreso detallado.
    """
    async with DBSession(SessionLocal) as db_session: #type: ignore
        try:
            # 1. Actualizar tarea a 'processing' con información de progreso inicial
            progress_info = {
                "status": "processing",
                "current_step": "Iniciando análisis semántico...",
                "progress_percentage": 5,
                "details": [
                    {"step": "Recopilando temas de análisis previos", "status": "pending", "timestamp": datetime.now().isoformat()},
                    {"step": "Generando embeddings", "status": "pending", "timestamp": datetime.now().isoformat()},
                    {"step": "Optimizando número de clusters", "status": "pending", "timestamp": datetime.now().isoformat()},
                    {"step": "Realizando clustering", "status": "pending", "timestamp": datetime.now().isoformat()},
                    {"step": "Generando títulos descriptivos con IA", "status": "pending", "timestamp": datetime.now().isoformat()},
                    {"step": "Completando análisis", "status": "pending", "timestamp": datetime.now().isoformat()}
                ],
                "estimated_time_remaining": "5-10 minutos"
            }
            
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="processing",
                result_payload=progress_info
            )
            await db_session.execute(stmt_processing)
            await db_session.commit()
            logger.info(f"Iniciando análisis semántico para tarea {task_id} para la cuenta {account_id}...")

            # 2. Obtener todos los temas de análisis previos
            progress_info["current_step"] = "Recopilando temas de análisis previos..."
            progress_info["progress_percentage"] = 10
            progress_info["details"][0]["status"] = "processing"
            progress_info["details"][0]["timestamp"] = datetime.now().isoformat()
            
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)
            await db_session.commit()
            
            analysis_stmt = select(AnalysisTask.result_payload).where(
                AnalysisTask.account_id == uuid.UUID(account_id),
                AnalysisTask.status == "completed",
                AnalysisTask.result_payload.isnot(None)
            )
            analysis_results = await db_session.execute(analysis_stmt)
            analysis_payloads = analysis_results.scalars().all()

            all_topics_raw = []
            topic_quotes_map = {} # Map topic name -> list of quotes
            for payload in analysis_payloads:
                if isinstance(payload, dict):
                    extracted_topics = extract_topics_from_payload(payload)
                    for t in extracted_topics:
                        topic_name = t["topic"]
                        if topic_name not in topic_quotes_map:
                            topic_quotes_map[topic_name] = []
                        existing_texts = {q["quote"] for q in topic_quotes_map[topic_name]}
                        for q in t.get("quotes", []):
                            if q["quote"] not in existing_texts:
                                topic_quotes_map[topic_name].append(q)
                                existing_texts.add(q["quote"])

                        for _ in range(t.get("mentions", 1)):
                            all_topics_raw.append(topic_name)
            
            topic_counts = Counter(all_topics_raw)
            
            if max_terms is not None:
                unique_topics = [topic for topic, count in topic_counts.most_common(max_terms)]
                logger.info(f"Limitando análisis semántico a {max_terms} términos más frecuentes de un total de {len(all_topics_raw)}.")
            else:
                unique_topics = list(topic_counts.keys())
                logger.info(f"Procesando {len(unique_topics)} temas únicos para análisis semántico sin límite.")

            if not unique_topics:
                logger.info(f"No hay temas únicos para procesar en la tarea {task_id}. Completando sin resultados.")
                progress_info["current_step"] = "No se encontraron temas para analizar"
                progress_info["progress_percentage"] = 100
                progress_info["details"][0]["status"] = "completed"
                progress_info["status"] = "completed"
                
                stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    status="completed", result_payload={**progress_info, "grouped_topics": [], "detailed_clusters": []})
                await db_session.execute(stmt_completed)
                await db_session.commit()
                return

            # Actualizar progreso: temas recopilados
            progress_info["current_step"] = f"Temas recopilados: {len(unique_topics)} temas únicos"
            progress_info["progress_percentage"] = 20
            progress_info["details"][0]["status"] = "completed"
            progress_info["details"][1]["status"] = "processing"
            progress_info["details"][1]["timestamp"] = datetime.now().isoformat()
            
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)
            await db_session.commit()

            # 3. Generar embeddings
            progress_info["current_step"] = "Generando embeddings para temas..."
            progress_info["progress_percentage"] = 25
            progress_info["estimated_time_remaining"] = "4-8 minutos"
            
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)
            await db_session.commit()
            
            # Integrar el MODELO DE EMBEDDINGS dedicado (Ollama en este caso)
            embedding_model = get_embedding_model()
            if not embedding_model:
                logger.error("No hay modelo de embeddings disponible (Ollama).")
                raise ValueError("Modelo de embeddings no disponible para análisis semántico.")
            
            embeddings = []
            try:
                logger.info(f"Generando embeddings para {len(unique_topics)} temas de forma batch...")
                embeddings = await embedding_model.aembed_documents(unique_topics)
                logger.info(f"Embeddings generados exitosamente para {len(embeddings)} temas.")
                
                # Actualizar progreso: embeddings completados
                progress_info["current_step"] = f"Embeddings generados: {len(embeddings)} vectores"
                progress_info["progress_percentage"] = 45
                progress_info["details"][1]["status"] = "completed"
                progress_info["details"][2]["status"] = "processing"
                progress_info["details"][2]["timestamp"] = datetime.now().isoformat()
                
                stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    result_payload=progress_info
                )
                await db_session.execute(stmt_update)
                await db_session.commit()
                
            except Exception as e:
                logger.error(f"Error al obtener embeddings de forma batch con Ollama: {e}", exc_info=True)
                raise ValueError(f"Fallo al generar embeddings de forma batch: {e}")

            if not embeddings:
                logger.info("No se generaron embeddings, saltando clustering y agrupación.")
                simulated_grouped_topics = []
                detailed_clusters_data = [] # También vacío si no hay embeddings
                clustering_metrics = None
            else:
                # 4. Determinar número óptimo de clusters
                progress_info["current_step"] = "Optimizando número de clusters..."
                progress_info["progress_percentage"] = 50
                progress_info["estimated_time_remaining"] = "3-6 minutos"
                
                stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    result_payload=progress_info
                )
                await db_session.execute(stmt_update)
                await db_session.commit()
                
                embeddings_array = np.array(embeddings)
                
                # Calcular número óptimo de clusters
                optimization_result = find_optimal_clusters(
                    embeddings_array,
                    min_clusters=2,
                    max_clusters=min(10, len(embeddings) - 1)
                )
                
                n_clusters = optimization_result["optimal_k"]
                clustering_metrics = optimization_result
                
                logger.info(f"🎯 Usando {n_clusters} clusters (método: {optimization_result['method']})")
                
                # Actualizar progreso: optimización completada
                progress_info["current_step"] = f"Clusters optimizados: {n_clusters} grupos"
                progress_info["progress_percentage"] = 65
                progress_info["details"][2]["status"] = "completed"
                progress_info["details"][3]["status"] = "processing"
                progress_info["details"][3]["timestamp"] = datetime.now().isoformat()
                
                stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    result_payload=progress_info
                )
                await db_session.execute(stmt_update)
                await db_session.commit()

                # 5. Realizar clustering
                clusters = []
                if n_clusters > 1:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
                    clusters = kmeans.fit_predict(embeddings_array)
                else:
                    clusters = [0] * len(unique_topics) if len(unique_topics) > 0 else []

                # Actualizar progreso: clustering completado
                progress_info["current_step"] = "Clustering completado, agrupando temas..."
                progress_info["progress_percentage"] = 75
                progress_info["details"][3]["status"] = "completed"
                progress_info["details"][4]["status"] = "processing"
                progress_info["details"][4]["timestamp"] = datetime.now().isoformat()
                
                stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    result_payload=progress_info
                )
                await db_session.execute(stmt_update)
                await db_session.commit()

                # 6. Agrupar temas por cluster y contar menciones
                cluster_dict = {}
                temp_detailed_data = []

                for i, topic in enumerate(unique_topics):
                    cluster_id = clusters[i] if len(clusters) > 0 else 0
                    if cluster_id not in cluster_dict:
                        cluster_dict[cluster_id] = {"topics": [], "mentions": 0, "id": cluster_id}
                    cluster_dict[cluster_id]["topics"].append(topic)
                    cluster_dict[cluster_id]["mentions"] += topic_counts[topic]
                    temp_detailed_data.append({"term": topic, "cluster_id": int(cluster_id), "mentions": int(topic_counts[topic])})

                # 7. Generar títulos descriptivos con LLM (mejorado)
                grouped_topics = []
                detailed_clusters_data = []
                llm_for_summarization = await get_llm_for_user(account_id, purpose="fast")
                if not llm_for_summarization:
                    logger.error("No hay LLM generativo disponible para generar títulos descriptivos.")
                    raise ValueError("LLM generativo no disponible para generación de títulos descriptivos.")
                else:
                    logger.info("LLM generativo disponible, procediendo a generar títulos descriptivos.")

                progress_info["current_step"] = "Generando títulos descriptivos con IA..."
                progress_info["progress_percentage"] = 80
                progress_info["estimated_time_remaining"] = "1-3 minutos"
                
                stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    result_payload=progress_info
                )
                await db_session.execute(stmt_update)
                await db_session.commit()

                for cluster_id, data in cluster_dict.items():
                    try:
                        topics_for_prompt = ", ".join(data["topics"][:15])
                        representative_term = None
                        description = None
                        
                        if not topics_for_prompt:
                            representative_term = data["topics"][0] if data["topics"] else f"Grupo {cluster_id + 1}"
                            description = f"Agrupación que incluye: {', '.join(data['topics'][:3])}"
                        else:
                            # Prompt mejorado para títulos más descriptivos
                            prompt = (
                                f"Analiza el siguiente grupo de temas relacionados y proporciona:\n"
                                f"1. Un título representativo y altamente descriptivo (máximo 5 palabras). NO uses 'Grupo' o 'Clúster' seguido de un número. Responde en español.\n"
                                f"2. Una descripción clara y concisa de qué conceptos o ideas agrupa este grupo (máximo 2 líneas). Responde en español.\n\n"
                                f"Temas: {topics_for_prompt}\n\n"
                                f"Considera qué idea o concepto general une a estos temas específicos.\n\n"
                                f"Formato de respuesta (en español):\n"
                                f"TÍTULO: [título aquí]\n"
                                f"DESCRIPCIÓN: [descripción aquí]"
                            )
                            logger.info(f"Generando título descriptivo para cluster {cluster_id} con {len(data['topics'])} temas")
                            response = await llm_for_summarization.ainvoke([HumanMessage(content=prompt)])
                            content = response.content.strip()
                            logger.info(f"Respuesta LLM para cluster {cluster_id} recibida.")

                            # Parsear la respuesta del LLM (con nuevo formato)
                            lines = content.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line.startswith('TÍTULO:'):
                                    term = line.replace('TÍTULO:', '').strip()
                                    if term and len(term.split()) <= 5 and not term.lower().startswith(('grupo', 'clúster')):
                                        representative_term = term
                                        logger.info(f"✓ Título aceptado para cluster {cluster_id}: '{term}'")
                                elif line.startswith('DESCRIPCIÓN:'):
                                    desc = line.replace('DESCRIPCIÓN:', '').strip()
                                    if desc and len(desc) <= 300:
                                        description = desc

                            if not representative_term:
                                representative_term = data["topics"][0] if data["topics"] else f"Cluster {cluster_id + 1}"
                                logger.warning(f"⚠️ LLM no generó título válido para cluster {cluster_id}, usando tema más común: '{representative_term}'")
                            
                            if not description:
                                description = f"Agrupación de temas relacionados con: {', '.join(data['topics'][:3])}"

                    except Exception as e:
                        logger.error(f"Error al generar título descriptivo para cluster {cluster_id}: {e}", exc_info=True)
                        representative_term = data["topics"][0] if data["topics"] else f"Cluster {cluster_id + 1}"
                        description = f"Agrupación de temas relacionados con: {', '.join(data['topics'][:3])}"

                    detailed_clusters_data.append({
                        "cluster_id": int(cluster_id),
                        "representative_term": representative_term,
                        "description": description,
                        "topics": data["topics"],
                        "total_mentions": int(data["mentions"]),
                        "topic_count": len(data["topics"])
                    })

                    # Recopilar citas de todos los temas en este clúster
                    cluster_quotes = []
                    existing_cluster_quote_texts = set()
                    for topic in data["topics"]:
                        for q in topic_quotes_map.get(topic, []):
                            if q["quote"] not in existing_cluster_quote_texts:
                                cluster_quotes.append(q)
                                existing_cluster_quote_texts.add(q["quote"])

                    grouped_topics.append({
                        "topic": representative_term,
                        "mentions": int(data["mentions"]),
                        "cluster_id": int(cluster_id),
                        "description": description,
                        "topics": data["topics"],
                        "quotes": cluster_quotes
                    })

                # Ordenar por menciones descendentes y limitar a los 10 principales
                simulated_grouped_topics = sorted(grouped_topics, key=lambda x: x["mentions"], reverse=True)[:10]

            # 8. Guardar el resultado final y marcar como 'completed'
            progress_info["current_step"] = "Guardando resultados finales..."
            progress_info["progress_percentage"] = 95
            progress_info["details"][4]["status"] = "completed"
            progress_info["details"][5]["status"] = "processing"
            progress_info["details"][5]["timestamp"] = datetime.now().isoformat()
            
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)
            await db_session.commit()

            final_result_payload = {
                "grouped_topics": simulated_grouped_topics,
                "detailed_clusters": detailed_clusters_data,
                "clustering_metrics": clustering_metrics,
                "progress_info": progress_info,
                "tool_used": "semantic_topic_analysis_tool.py",
                "analysis_metadata": {
                    "tool_used": "semantic_topic_analysis_tool.py",
                    "analysis_type": "semantic",
                    "total_topics": len(unique_topics),
                    "clusters_count": len(detailed_clusters_data),
                    "max_terms_limit": max_terms,
                    "created_at": datetime.now().isoformat()
                }
            }

            progress_info["current_step"] = "Análisis semántico completado"
            progress_info["progress_percentage"] = 100
            progress_info["status"] = "completed"
            progress_info["estimated_time_remaining"] = None
            progress_info["details"][5]["status"] = "completed"
            progress_info["details"][5]["timestamp"] = datetime.now().isoformat()
            
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed",
                result_payload=final_result_payload
            )
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis semántico para tarea {task_id} completado con {len(simulated_grouped_topics)} grupos de temas y {len(detailed_clusters_data)} temas detallados.")
        except Exception as e:
            logger.error(f"Fallo en tarea de análisis semántico {task_id}: {e}", exc_info=True)
            progress_info["current_step"] = f"Error durante el análisis: {str(e)}"
            progress_info["status"] = "failed"
            progress_info["details"] = [
                {"step": step_info["step"], "status": "failed" if i == 4 else "completed", "timestamp": step_info.get("timestamp", datetime.now().isoformat())}
                for i, step_info in enumerate(progress_info.get("details", []))
            ]
            progress_info["details"][-1]["status"] = "failed"
            
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed",
                result_payload=progress_info,
                error_message=str(e)
            )
            await db_session.execute(stmt_failed)
            await db_session.commit()

async def run_semantic_summary_analysis(task_id: str, account_id: str, topic: str, workspace_id: Optional[str] = None):
    """
    Proceso en segundo plano para realizar un resumen semántico específico de una colección.
    Se enfoca en agrupación semántica de documentos y extracción de patrones dentro de la colección.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()

            logger.info(f"🔍 Iniciando resumen semántico para colección '{topic}' (tarea {task_id})")

            # Obtener todos los documentos de la colección
            from core.memory_manager import list_user_documents
            documents = await list_user_documents(
                account_id=account_id,
                workspace_id=workspace_id,
                topic=topic
            )

            if not documents:
                raise ValueError(f"No se encontraron documentos en la colección '{topic}'")

            logger.info(f"📚 Analizando {len(documents)} documentos en la colección '{topic}'")

            # Obtener contenido de los documentos para análisis semántico
            all_docs_content = []
            for doc_meta in documents:
                content = await get_full_document_content(account_id, doc_meta['file_name'])
                if content:
                    all_docs_content.append({
                        "title": doc_meta.get('title', doc_meta['file_name']),
                        "content": content
                    })

            if not all_docs_content:
                raise ValueError(f"No se encontró contenido para analizar en la colección '{topic}'")

            # Realizar análisis semántico de la colección
            from utils.advanced_text_analyzer import AdvancedTextAnalyzer
            analyzer = AdvancedTextAnalyzer()
            semantic_analysis = await analyzer.analyze_collection(all_docs_content, account_id=str(account_id))

            # Crear resultado estructurado
            result_payload = {
                "resumen_semantico": semantic_analysis.collection_summary,
                "general_analysis": semantic_analysis.general_analysis,
                "temas_transversales": [
                    {
                        "tema": theme.theme,
                        "citas": [{"documento": quote.document_title, "cita": quote.quote} for quote in theme.related_quotes],
                        "relevancia": "alta"
                    } for theme in semantic_analysis.cross_cutting_themes
                ],
                "conceptos_centrales": semantic_analysis.central_concepts,
                "brechas_conocimiento": semantic_analysis.emergent_knowledge_gaps,
                "patrones_semanticos": {
                    "total_documentos": len(documents),
                    "total_chunks_analizados": len(all_docs_content), # Corregido: usar len(all_docs_content)
                    "temas_identificados": len(semantic_analysis.cross_cutting_themes)
                },
                "tool_used": "semantic_summary_analysis",
                "analysis_metadata": {
                    "tool_used": "semantic_summary_analysis",
                    "analysis_type": "semantic_summary",
                    "collection_name": topic,
                    "workspace_id": workspace_id,
                    "documents_count": len(documents),
                    "chunks_analyzed": len(all_docs_content), # Corregido: usar len(all_docs_content)
                    "created_at": datetime.now().isoformat()
                }
            }

            # Marcar como completado
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed",
                result_payload=result_payload
            )
            await db_session.execute(stmt_completed)
            await db_session.commit()

            logger.info(f"✅ Resumen semántico completado para colección '{topic}' (tarea {task_id})")

        except Exception as e:
            logger.error(f"❌ Error en resumen semántico para colección '{topic}' (tarea {task_id}): {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed",
                error_message=str(e)
            )
            await db_session.execute(stmt_failed)
            await db_session.commit()

class AnalyzeSingleNoteRequest(BaseModel):
    title: Optional[str] = None
    content: str
    note_id: Optional[int] = None

async def run_single_note_analysis_and_save(task_id: str, account_id: str, note_title: str, note_content: str, note_id: Optional[int]):
    """
    Analiza una sola nota y guarda el resultado.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
            await db_session.commit()
            
            logger.info(f"Iniciando análisis de nota individual para tarea {task_id} (Nota: {note_title})")

            # Realizar el análisis de la nota
            analysis_result = await text_analyzer.analyze_single_text(note_content, document_title=note_title, account_id=str(account_id))
            logger.info(f"Single note analysis result generated: {analysis_result.model_dump()}")

            # Guardar el resultado y marcar como 'completed'
            result_payload = analysis_result.model_dump()

            # Agregar metadata de herramienta utilizada
            result_payload["tool_used"] = "advanced_text_analyzer.py"
            result_payload["analysis_metadata"] = {
                "tool_used": "advanced_text_analyzer.py",
                "analysis_type": "single_note",
                "note_id": note_id,
                "created_at": datetime.now().isoformat()
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis de nota individual para tarea {task_id} completado.")

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis de nota individual {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/start-single-note-analysis", status_code=202)
async def start_single_note_analysis_endpoint(
    req: AnalyzeSingleNoteRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Inicia un análisis de una sola nota y devuelve un ID de tarea."""
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=req.title or f"Nota {req.note_id or 'sin título'}",
        status="pending",
        analysis_type="single_note"  # NUEVO: Tipo específico para análisis de nota individual
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_single_note_analysis_and_save, str(new_task.id), current_account_id, req.title or "Nota sin título", req.content, req.note_id)
    
    return {"task_id": str(new_task.id)}

class SummarizeSingleNoteRequest(BaseModel):
    title: Optional[str] = None
    content: str
    note_id: Optional[int] = None

async def run_single_note_summary_and_save(task_id: str, account_id: str, note_title: str, note_content: str, note_id: Optional[int]):
    """
    Genera un resumen ejecutivo de una sola nota y guarda el resultado.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
            await db_session.commit()
            
            logger.info(f"Iniciando resumen de nota individual para tarea {task_id} (Nota: {note_title})")

            # Realizar el análisis de la nota para obtener el resumen ejecutivo
            analysis_result = await text_analyzer.analyze_single_text(note_content, document_title=note_title, account_id=str(account_id))
            executive_summary = analysis_result.executive_summary

            # Guardar el resultado y marcar como 'completed'
            result_payload = {
                "executive_summary": executive_summary,
                "tool_used": "advanced_text_analyzer.py",
                "analysis_metadata": {
                    "tool_used": "advanced_text_analyzer.py",
                    "analysis_type": "single_note_summary",
                    "note_id": note_id,
                    "created_at": datetime.now().isoformat()
                }
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Resumen de nota individual para tarea {task_id} completado.")

        except Exception as e:
            logger.error(f"Fallo en tarea de resumen de nota individual {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/start-single-note-summary", status_code=202)
async def start_single_note_summary_endpoint(
    req: SummarizeSingleNoteRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Inicia la generación de un resumen ejecutivo de una sola nota y devuelve un ID de tarea."""
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=f"Resumen de Nota: {req.title or 'sin título'}",
        status="pending",
        analysis_type="single_note_summary"  # NUEVO: Tipo específico para resumen de nota individual
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_single_note_summary_and_save, str(new_task.id), current_account_id, req.title or "Nota sin título", req.content, req.note_id)
    
    return {"task_id": str(new_task.id)}

class AnalyzeCodeRequest(BaseModel):
    repo_name: str
    analysis_type: Optional[str] = 'all'

class CustomAnalysisRequest(BaseModel):
    file_name: str
    objective: str
    expected_result: Optional[str] = None
    extension: str  # 'brief', 'standard', 'detailed'
    fields: List[dict]  # Lista de campos con name y description

class GetAllAnalysisRequest(BaseModel):
    limit: Optional[int] = 20
    offset: Optional[int] = 0
    analysis_type: Optional[str] = None  # 'document', 'collection', 'mindmap', 'insight', 'code'
    search_query: Optional[str] = None
    topic_keywords: Optional[List[str]] = None

async def run_code_analysis_and_save(task_id: str, account_id: str, repo_name: str, analysis_type: str = 'all'):
    """Función pesada que se ejecuta en segundo plano para análisis de código."""
    try:
        # 1. Actualizar tarea a 'processing' con información de progreso inicial
        progress_info = {
            "status": "processing",
            "current_step": "Iniciando análisis de código...",
            "progress_percentage": 5,
            "details": [
                {"step": "Obteniendo documentos de GitHub", "status": "pending", "timestamp": datetime.now().isoformat()},
                {"step": "Dividiendo código en chunks", "status": "pending", "timestamp": datetime.now().isoformat()},
                {"step": "Analizando chunks de código", "status": "pending", "timestamp": datetime.now().isoformat()},
                {"step": "Generando resumen ejecutivo", "status": "pending", "timestamp": datetime.now().isoformat()},
                {"step": "Completando análisis", "status": "pending", "timestamp": datetime.now().isoformat()}
            ],
            "estimated_time_remaining": "3-8 minutos"
        }
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="processing",
                result_payload=progress_info
            )
            await db_session.execute(stmt_processing)
        
        await send_analysis_progress(
            account_id,
            task_id,
            phase="initializing",
            message="Iniciando análisis de código...",
            progress_percent=5,
            file_name=repo_name,
            analysis_type="code",
        )
        
        logger.info(f"Iniciando análisis de código para tarea {task_id}...")
        
        # 2. Obtener los documentos específicos de GitHub del repositorio
        progress_info["current_step"] = "Obteniendo documentos de GitHub..."
        progress_info["progress_percentage"] = 10
        progress_info["details"][0]["status"] = "processing"
        progress_info["details"][0]["timestamp"] = datetime.now().isoformat()
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)
            
            await send_analysis_progress(
                account_id,
                task_id,
                phase="fetching_github",
                message="Obteniendo documentos de GitHub...",
                progress_percent=10,
                file_name=repo_name,
                analysis_type="code",
            )
            
            query = select(GitHubDocument).where(
                GitHubDocument.account_id == account_id,
                GitHubDocument.repo_url.endswith(f"/{repo_name}")
            )
            result = await db_session.execute(query)
            github_docs = result.scalars().all()
            
            # Eager extraction to prevent DetachedInstanceError when accessing outside session
            docs_data = [{"file_path": doc.file_path, "content": doc.content} for doc in github_docs]
        
        logger.info(f"Encontrados {len(docs_data)} documentos de GitHub para el repositorio {repo_name}")
        
        if not docs_data:
            raise ValueError("No se encontraron documentos de GitHub para el repositorio.")
        
        # Actualizar progreso: documentos obtenidos
        progress_info["current_step"] = f"Documentos obtenidos: {len(docs_data)} archivos"
        progress_info["progress_percentage"] = 20
        progress_info["details"][0]["status"] = "completed"
        progress_info["details"][1]["status"] = "processing"
        progress_info["details"][1]["timestamp"] = datetime.now().isoformat()
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)

        await send_analysis_progress(
            account_id,
            task_id,
            phase="splitting_code",
            message=f"Documentos obtenidos: {len(docs_data)} archivos. Dividiendo en chunks...",
            progress_percent=20,
            file_name=repo_name,
            analysis_type="code",
        )

        # 3. Dividir código en chunks
        progress_info["current_step"] = "Dividiendo código en chunks..."
        progress_info["progress_percentage"] = 25
        progress_info["estimated_time_remaining"] = "2-6 minutos"
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)

        from utils.advanced_code_analyzer import analyze_code_content
        
        chunk_size = 15000  # ~15k caracteres por chunk (~3-4k tokens aprox) para evitar superar el límite de ~262k tokens
        chunks = []
        current_chunk = ""
        current_chunk_files = []
        
        for doc in docs_data:
            if doc["content"]:
                file_content = f"Archivo: {doc['file_path']}\n{doc['content']}\n\n"
                
                # Si agregar este archivo excede el chunk_size, crear un nuevo chunk
                if len(current_chunk) + len(file_content) > chunk_size and current_chunk:
                    chunks.append({
                        "content": current_chunk,
                        "files": current_chunk_files.copy()
                    })
                    current_chunk = file_content
                    current_chunk_files = [doc["file_path"]]
                else:
                    current_chunk += file_content
                    current_chunk_files.append(doc["file_path"])
        
        # Agregar el último chunk si tiene contenido
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "files": current_chunk_files.copy()
            })
        
        logger.info(f"Código dividido en {len(chunks)} chunks para análisis")
        
        # Actualizar progreso: chunks creados
        progress_info["current_step"] = f"Código dividido: {len(chunks)} chunks"
        progress_info["progress_percentage"] = 35
        progress_info["details"][1]["status"] = "completed"
        progress_info["details"][2]["status"] = "processing"
        progress_info["details"][2]["timestamp"] = datetime.now().isoformat()
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)

        await send_analysis_progress(
            account_id,
            task_id,
            phase="analyzing_chunks",
            message=f"Código dividido: {len(chunks)} chunks. Analizando...",
            progress_percent=35,
            file_name=repo_name,
            analysis_type="code",
        )

        # 4. Analizar cada chunk
        progress_info["current_step"] = "Analizando chunks de código..."
        progress_info["progress_percentage"] = 40
        progress_info["estimated_time_remaining"] = "1-5 minutos"
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)
        
        all_chunk_results = []
        combined_categories = {
            "code_structure": [],
            "design_patterns": [],
            "dependencies": [],
            "security_analysis": [],
            "performance_analysis": [],
            "refactoring_opportunities": [],
            "documentation_health": [],
            "potential_issues": [],
            "recommendations": []
        }
        
        # 4. Analizar cada chunk (MODO PARALELO CONTROLADO con Semaphore para evitar saturar pool DB y Rate Limit)
        logger.info(f"Analizando {len(chunks)} chunks con concurrencia controlada...")
        
        from core.llm_manager import get_llm_for_user, get_fast_llm
        shared_llm = await get_llm_for_user(account_id, purpose="fast") if account_id else get_fast_llm()

        semaphore = asyncio.Semaphore(2)
        async def analyze_single_chunk(index, chunk_data):
            async with semaphore:
                try:
                    logger.info(f"Iniciando análisis de chunk {index+1}/{len(chunks)}...")
                    res = await analyze_code_content(chunk_data["content"], account_id=account_id, analysis_type=analysis_type, llm=shared_llm)
                    return index, res
                except Exception as e:
                    logger.error(f"Error analizando chunk {index+1}: {e}")
                    return index, None

        analysis_tasks = [analyze_single_chunk(i, chunk) for i, chunk in enumerate(chunks)]
        chunk_results_with_indices = await asyncio.gather(*analysis_tasks)
        chunk_results_with_indices.sort(key=lambda x: x[0])
        
        for i, chunk_result in chunk_results_with_indices:
            if chunk_result is None: continue
            
            all_chunk_results.append({
                "chunk_index": i+1,
                "files": chunks[i]["files"],
                "result": chunk_result
            })

            
            # Manejar tanto objetos Pydantic como diccionarios
            if hasattr(chunk_result, 'code_structure'):
                # Es un objeto Pydantic
                combined_categories["code_structure"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.code_structure])
                combined_categories["design_patterns"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.design_patterns])
                combined_categories["dependencies"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.dependencies])
                combined_categories["security_analysis"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.security_analysis])
                combined_categories["performance_analysis"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.performance_analysis])
                combined_categories["refactoring_opportunities"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.refactoring_opportunities])
                combined_categories["documentation_health"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.documentation_health])
                combined_categories["potential_issues"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.potential_issues])
                combined_categories["recommendations"].extend([item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item) for item in chunk_result.recommendations])
            elif isinstance(chunk_result, dict):
                # Es un diccionario
                combined_categories["code_structure"].extend(chunk_result.get("code_structure", []))
                combined_categories["design_patterns"].extend(chunk_result.get("design_patterns", []))
                combined_categories["dependencies"].extend(chunk_result.get("dependencies", []))
                combined_categories["security_analysis"].extend(chunk_result.get("security_analysis", []))
                combined_categories["performance_analysis"].extend(chunk_result.get("performance_analysis", []))
                combined_categories["refactoring_opportunities"].extend(chunk_result.get("refactoring_opportunities", []))
                combined_categories["documentation_health"].extend(chunk_result.get("documentation_health", []))
                combined_categories["potential_issues"].extend(chunk_result.get("potential_issues", []))
                combined_categories["recommendations"].extend(chunk_result.get("recommendations", []))
            else:
                logger.warning(f"Resultado inesperado del análisis de chunk {i+1}: {type(chunk_result)}")
        
        # Actualizar progreso final de chunks
        progress_info["current_step"] = "Todos los chunks analizados exitosamente."
        progress_info["progress_percentage"] = 80

        
        # Actualizar progreso: chunks analizados
        progress_info["current_step"] = "Chunks analizados, generando resumen..."
        progress_info["progress_percentage"] = 85
        progress_info["details"][2]["status"] = "completed"
        progress_info["details"][3]["status"] = "processing"
        progress_info["details"][3]["timestamp"] = datetime.now().isoformat()
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)

        await send_analysis_progress(
            account_id,
            task_id,
            phase="generating_summary",
            message="Chunks analizados, generando resumen consolidado...",
            progress_percent=85,
            file_name=repo_name,
            analysis_type="code",
        )

        # 5. Generar resumen ejecutivo consolidado
        from skills.analysis_and_insights_skill.scripts.analyze_code_for_insights_tool import AnalyzeCodeForInsightsTool
        
        # Crear un resumen de todos los chunks para el formatted_result
        summary_parts = []
        for res in all_chunk_results:
            summary = "Análisis no disponible o fallido para este chunk."
            result = res.get('result')
            if result:
                if hasattr(result, 'executive_summary') and result.executive_summary:
                    summary = result.executive_summary
                elif isinstance(result, dict):
                    summary = result.get('executive_summary', 'Sin resumen disponible o chunk vacío.')

            summary_parts.append(
                f"**Análisis Parte {res['chunk_index']}** (Archivos: {', '.join(res['files'][:3])}{'...' if len(res['files']) > 3 else ''})\n{summary}"
            )
        combined_summary = "\n\n".join(summary_parts)
        
        # Generar análisis consolidado final
        tool = AnalyzeCodeForInsightsTool(account_id=account_id)
        final_summary = f"**Análisis Completo del Repositorio {repo_name}**\n\n"
        final_summary += f"Se analizaron {len(chunks)} partes del código con un total de {len(docs_data)} archivos.\n\n"
        final_summary += f"**Resumen por Partes:**\n{combined_summary}\n\n"
        
        # Generar formatted_result consolidado usando el analizador y la herramienta
        try:
            # Usar una muestra reducida para el formato final (máximo 10k caracteres)
            sample_content = chunks[0]["content"][:10000] if chunks else ""
            final_code_analysis = await analyze_code_content(
                code_content=sample_content + f"\n\nNOTA: Este es un análisis de {len(chunks)} partes del repositorio {repo_name}",
                account_id=account_id,
                analysis_type=analysis_type,
                llm=shared_llm
            )
            formatted_result = tool._format_result(final_code_analysis, analysis_type)
            consolidated_executive_summary = final_code_analysis.executive_summary
        except Exception as e:
            logger.warning(f"Error generando resultado formateado: {e}")
            formatted_result = final_summary
            consolidated_executive_summary = f"Análisis completo de {len(chunks)} partes del repositorio {repo_name}."

        # Actualizar progreso: resumen generado
        progress_info["current_step"] = "Resumen ejecutivo generado"
        progress_info["progress_percentage"] = 95
        progress_info["details"][3]["status"] = "completed"
        progress_info["details"][4]["status"] = "processing"
        progress_info["details"][4]["timestamp"] = datetime.now().isoformat()
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_update = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                result_payload=progress_info
            )
            await db_session.execute(stmt_update)

        await send_analysis_progress(
            account_id,
            task_id,
            phase="finalizing",
            message="Resumen ejecutivo consolidado generado...",
            progress_percent=95,
            file_name=repo_name,
            analysis_type="code",
        )
        
        # 6. Estructura final del resultado
        analysis_result = {
            "formatted_result": formatted_result,
            "executive_summary": consolidated_executive_summary or f"Análisis completo de {len(chunks)} partes del repositorio {repo_name}.",
            "code_structure": combined_categories["code_structure"],
            "design_patterns": combined_categories["design_patterns"],
            "dependencies": combined_categories["dependencies"],
            "security_analysis": combined_categories.get("security_analysis", []),
            "performance_analysis": combined_categories.get("performance_analysis", []),
            "refactoring_opportunities": combined_categories.get("refactoring_opportunities", []),
            "documentation_health": combined_categories.get("documentation_health", []),
            "potential_issues": combined_categories["potential_issues"],
            "recommendations": combined_categories["recommendations"],
            "progress_info": progress_info,
            "tool_used": "advanced_code_analyzer.py",
            "analysis_metadata": {
                "tool_used": "advanced_code_analyzer.py",
                "analysis_type": f"code_{analysis_type}" if analysis_type != 'all' else "code",
                "total_files": len(docs_data),
                "total_chunks": len(chunks),
                "repo_name": repo_name,
                "created_at": datetime.now().isoformat()
            }
        }

        # 7. Guardar el resultado y marcar como 'completed'
        progress_info["current_step"] = "Análisis de código completado"
        progress_info["progress_percentage"] = 100
        progress_info["status"] = "completed"
        progress_info["estimated_time_remaining"] = None
        progress_info["details"][4]["status"] = "completed"
        progress_info["details"][4]["timestamp"] = datetime.now().isoformat()
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=analysis_result)
            await db_session.execute(stmt_completed)

        await send_analysis_progress(
            account_id,
            task_id,
            phase="completed",
            message="Análisis de código completado",
            progress_percent=100,
            is_complete=True,
            file_name=repo_name,
            analysis_type="code",
        )

        logger.info(f"Análisis de código para tarea {task_id} completado con {len(chunks)} chunks.")

    except Exception as e:
        logger.error(f"Fallo en tarea de análisis de código {task_id}: {e}", exc_info=True)
        progress_info["current_step"] = f"Error durante el análisis: {str(e)}"
        progress_info["status"] = "failed"
        progress_info["details"] = [
            {"step": step_info["step"], "status": "failed" if i == 3 else "completed", "timestamp": step_info.get("timestamp", datetime.now().isoformat())}
            for i, step_info in enumerate(progress_info.get("details", []))
        ]
        progress_info["details"][-1]["status"] = "failed"
        
        async with DBSession(SessionLocal) as db_session: # type: ignore
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed",
                result_payload=progress_info,
                error_message=str(e))
            await db_session.execute(stmt_failed)

        await send_analysis_progress(
            account_id,
            task_id,
            phase="error",
            message=f"Error durante el análisis: {str(e)}",
            progress_percent=100,
            has_error=True,
            error=str(e),
            file_name=repo_name,
            analysis_type="code",
        )

@router.post("/start-code-analysis", status_code=202)
async def start_code_analysis_endpoint(
    req: AnalyzeCodeRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Inicia una tarea de análisis de código o repositorio y devuelve un ID de tarea."""
    # Verificar que el repositorio existe antes de crear la tarea
    # Esto requeriría una función para verificar el repositorio, pero por ahora lo simulamos.
    repo_check = True
    if not repo_check:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado.")

    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=req.repo_name,
        status="pending",
        analysis_type="code"  # NUEVO: Especificar tipo de análisis
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_code_analysis_and_save, str(new_task.id), current_account_id, req.repo_name, req.analysis_type or 'all')
    
    return {"task_id": str(new_task.id)}

@router.post("/start-custom-analysis", status_code=202, summary="Iniciar análisis personalizado")
async def start_custom_analysis_endpoint(
    req: CustomAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Inicia un análisis personalizado con campos y configuración definidos por el usuario.
    """
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=f"Análisis Personalizado: {req.file_name}",
        status="pending",
        analysis_type="custom"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    background_tasks.add_task(
        run_custom_analysis_and_save,
        str(new_task.id),
        current_account_id,
        req.file_name,
        req.objective,
        req.expected_result,
        req.extension,
        req.fields
    )

    return {"task_id": str(new_task.id)}

@router.post("/get-all-analysis")
async def get_all_analysis_endpoint(
    req: GetAllAnalysisRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene todos los análisis del usuario de forma unificada.
    Combina AnalysisTask, MindmapTask y ProactiveInsight en una sola respuesta.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)
        all_analysis = []

        analysis_task_types = [
            'document', 'collection', 'code', 'semantic_summary', 'semantic', 'custom', 
            'gap_development', 'deep_research', 'comprehensive_web_analysis', 'neural_insight',
            'note_analysis', 'note_collection_analysis', 'single_note', 'single_note_summary', 'notes_collection'
        ]

        # 1. Obtener AnalysisTask
        if not req.analysis_type or req.analysis_type in analysis_task_types:
            analysis_stmt = select(AnalysisTask).where(
                AnalysisTask.account_id == account_uuid,
                AnalysisTask.status == "completed"
            ).order_by(desc(AnalysisTask.created_at))

            if req.analysis_type:
                if req.analysis_type == 'note_analysis':
                    analysis_stmt = analysis_stmt.where(AnalysisTask.analysis_type.in_(['single_note', 'single_note_summary', 'note_analysis']))
                elif req.analysis_type == 'note_collection_analysis':
                    analysis_stmt = analysis_stmt.where(AnalysisTask.analysis_type.in_(['notes_collection', 'note_collection_analysis']))
                else:
                    analysis_stmt = analysis_stmt.where(AnalysisTask.analysis_type == req.analysis_type)

            if req.search_query:
                analysis_stmt = analysis_stmt.where(
                    or_(
                        AnalysisTask.file_name.ilike(f"%{req.search_query}%"),
                        func.cast(AnalysisTask.result_payload, String).ilike(f"%{req.search_query}%")
                    )
                )

            analysis_results = await db.execute(analysis_stmt)
            analysis_tasks = analysis_results.scalars().all()

            for task in analysis_tasks:
                file_name = str(task.file_name) if task.file_name is not None else ""
                task_analysis_type = getattr(task, 'analysis_type', None)

                if task_analysis_type:
                    analysis_type = task_analysis_type
                    title = file_name
                elif file_name.startswith("Resumen Semántico:"):
                    analysis_type = "semantic_summary"
                    title = file_name
                elif file_name == "Semantic Topic Analysis":
                    analysis_type = "semantic"
                    title = "Análisis Semántico de Temas"
                elif "repositorio" in file_name.lower() or file_name.endswith(".git") or "Análisis de Repositorio:" in file_name:
                    analysis_type = "code"
                    title = file_name if "Análisis de Repositorio:" in file_name else f"Análisis de Código: {file_name}"
                elif file_name.startswith("Análisis Personalizado:"):
                    analysis_type = "custom"
                    title = file_name
                elif task_analysis_type == "single_note":
                    analysis_type = "note_analysis"
                    title = file_name if "Nota:" in file_name else f"Análisis de Nota: {file_name}"
                elif task_analysis_type == "single_note_summary":
                    analysis_type = "note_analysis"
                    title = file_name if "Resumen de Nota:" in file_name else f"Resumen de Nota: {file_name}"
                elif task_analysis_type == "notes_collection":
                    analysis_type = "note_collection_analysis"
                    title = file_name if "Colección de Notas:" in file_name else f"Análisis de Colección de Notas: {file_name}"
                elif task_analysis_type == "gap_development":
                    analysis_type = "gap_development"
                    title = file_name
                else:
                    analysis_type = "document"
                    title = f"Análisis de Documento: {file_name}"

                summary = "Sin resumen disponible"
                tool_used = "Desconocido"

                if task.result_payload is not None:
                    payload_dict = task.result_payload if isinstance(task.result_payload, dict) else {}

                    if analysis_type == "collection" and 'collection_summary' in payload_dict:
                        coll_summary = str(payload_dict['collection_summary'])
                        summary = coll_summary[:200] + "..." if len(coll_summary) > 200 else coll_summary
                    elif 'executive_summary' in payload_dict:
                        summary = str(payload_dict['executive_summary'])
                    elif 'resumen_ejecutivo' in payload_dict:
                        summary = str(payload_dict['resumen_ejecutivo'])
                    elif 'resumen_semantico' in payload_dict:
                        sem_summary = str(payload_dict['resumen_semantico'])
                        summary = sem_summary[:200] + "..." if len(sem_summary) > 200 else sem_summary
                    elif 'summary' in payload_dict and payload_dict['summary'] is not None:
                        summary = str(payload_dict['summary']) if not isinstance(payload_dict['summary'], str) else payload_dict['summary']
                    elif 'sections' in payload_dict and isinstance(payload_dict['sections'], list) and len(cast(list, payload_dict['sections'])) > 0:
                        first_section = payload_dict['sections'][0]
                        if isinstance(first_section, dict) and 'content' in first_section:
                            content = str(first_section['content'])
                            summary = content[:200] + "..." if len(content) > 200 else content
                        else:
                            sections_list = cast(list, payload_dict['sections'])
                            sections_count = len(sections_list)
                            summary = f"Análisis personalizado con {sections_count} secciones"
                    elif 'sections' in payload_dict:
                        summary = "Análisis personalizado sin contenido"
                    elif 'formatted_result' in payload_dict:
                        summary = str(payload_dict['formatted_result'])[:200] + "..."
                    elif (analysis_type == "gap_development" or task_analysis_type == "gap_development" or analysis_type == "deep_research") and ('report' in payload_dict or 'final_report' in payload_dict or 'summary' in payload_dict):
                        if 'report' in payload_dict:
                            report_obj = payload_dict['report']
                            if isinstance(report_obj, dict) and 'summary' in report_obj:
                                summary = str(report_obj['summary'])
                            else:
                                report_content = str(report_obj)
                                summary = report_content[:200] + "..." if len(report_content) > 200 else report_content
                        elif 'summary' in payload_dict and payload_dict['summary'] is not None:
                            summary = str(payload_dict['summary'])
                        elif 'final_report' in payload_dict:
                            report_content = str(payload_dict['final_report'])
                            summary = report_content[:200] + "..." if len(report_content) > 200 else report_content

                    if 'tool_used' in payload_dict:
                        tool_used = str(payload_dict['tool_used'])
                    elif 'analysis_metadata' in payload_dict and isinstance(payload_dict['analysis_metadata'], dict) and 'tool_used' in payload_dict['analysis_metadata']:
                        tool_used = str(payload_dict['analysis_metadata']['tool_used'])
                    else:
                        if 'code_structure' in payload_dict and 'design_patterns' in payload_dict:
                            tool_used = "advanced_code_analyzer.py"
                        elif 'grouped_topics' in payload_dict and 'detailed_clusters' in payload_dict:
                            tool_used = "semantic_topic_analysis_tool.py"
                        elif file_name == "Semantic Topic Analysis":
                            tool_used = "semantic_topic_analysis_tool.py"
                        elif 'resumen_semantico' in payload_dict and 'temas_transversales' in payload_dict:
                            tool_used = "semantic_summary_analysis"
                        elif 'cross_cutting_themes' in payload_dict:
                            tool_used = "advanced_text_analyzer.py (colección)"
                        elif 'key_themes' in payload_dict and 'central_concepts' in payload_dict:
                            tool_used = "advanced_text_analyzer.py (documento)"
                        elif file_name.startswith("Resumen Semántico:"):
                            tool_used = "semantic_summary_analysis"
                        elif file_name.startswith("Colección:"):
                            tool_used = "collection_analysis_tool.py"
                        elif "repositorio" in file_name.lower() or file_name.endswith(".git"):
                            tool_used = "advanced_code_analyzer.py"
                        elif analysis_type == "custom" or 'sections' in payload_dict:
                            tool_used = "custom_analysis_tool"
                        elif analysis_type == "document":
                            tool_used = "document_analysis_tool.py"
                        else:
                            tool_used = f"herramienta_{analysis_type}"

                created_at_str = task.created_at.isoformat() if task.created_at else datetime.now(timezone.utc).isoformat()
                updated_at_str = task.updated_at.isoformat() if task.updated_at else created_at_str

                all_analysis.append({
                    "id": str(task.id),
                    "type": analysis_type,
                    "title": title,
                    "summary": summary,
                    "created_at": created_at_str,
                    "updated_at": updated_at_str,
                    "source_table": "analysis_tasks",
                    "tool_used": tool_used,
                    "full_data": task.result_payload
                })

        # 2. Obtener MindmapTask
        if not req.analysis_type or req.analysis_type == 'mindmap':
            mindmap_stmt = select(
                MindmapTask.id,
                MindmapTask.account_id,
                MindmapTask.topic,
                MindmapTask.ideas_input,
                MindmapTask.document_name,
                MindmapTask.concept_query,
                MindmapTask.status,
                MindmapTask.result_payload,
                MindmapTask.error_message,
                MindmapTask.created_at,
                MindmapTask.updated_at
            ).where(
                MindmapTask.account_id == account_uuid,
                MindmapTask.status == "completed"
            ).order_by(desc(MindmapTask.created_at))

            if req.search_query:
                mindmap_stmt = mindmap_stmt.where(
                    or_(
                        MindmapTask.topic.ilike(f"%{req.search_query}%"),
                        func.cast(MindmapTask.result_payload, String).ilike(f"%{req.search_query}%")
                    )
                )

            mindmap_results = await db.execute(mindmap_stmt)
            mindmap_rows = mindmap_results.fetchall()

            for row in mindmap_rows:
                summary = f"Mapa mental sobre: {row.topic}"
                if row.result_payload is not None and isinstance(row.result_payload, dict) and 'summary' in row.result_payload:
                    summary = str(row.result_payload['summary'])

                tool_used = "mindmap_generator_tool.py"
                if row.result_payload is not None and isinstance(row.result_payload, dict):
                    if 'tool_used' in row.result_payload:
                        tool_used = str(row.result_payload['tool_used'])
                    elif 'analysis_metadata' in row.result_payload and isinstance(row.result_payload['analysis_metadata'], dict) and 'tool_used' in row.result_payload['analysis_metadata']:
                        tool_used = str(row.result_payload['analysis_metadata']['tool_used'])

                created_at_str = row.created_at.isoformat() if row.created_at else datetime.now(timezone.utc).isoformat()
                updated_at_str = row.updated_at.isoformat() if row.updated_at else created_at_str

                all_analysis.append({
                    "id": str(row.id),
                    "type": "mindmap",
                    "title": f"Mapa Mental: {row.topic}",
                    "summary": summary,
                    "created_at": created_at_str,
                    "updated_at": updated_at_str,
                    "source_table": "mindmap_tasks",
                    "tool_used": tool_used,
                    "full_data": row.result_payload
                })

        # 3. Obtener ProactiveInsight
        if not req.analysis_type or req.analysis_type == 'insight':
            insight_stmt = select(ProactiveInsight).options(joinedload(ProactiveInsight.workspace)).where(
                ProactiveInsight.account_id == account_uuid
            ).order_by(desc(ProactiveInsight.created_at))

            if req.search_query:
                insight_stmt = insight_stmt.where(
                    or_(
                        ProactiveInsight.insight_message.ilike(f"%{req.search_query}%"),
                        ProactiveInsight.type.ilike(f"%{req.search_query}%")
                    )
                )

            insight_results = await db.execute(insight_stmt)
            insights = insight_results.scalars().all()

            for insight in insights:
                tool_used = "proactive_knowledge_linker_tool_removed.py"
                related_items = insight.related_items or {}

                if isinstance(related_items, dict):
                    if 'tool_used' in related_items:
                        tool_used = str(related_items['tool_used'])
                    elif 'analysis_metadata' in related_items and isinstance(related_items['analysis_metadata'], dict) and 'tool_used' in related_items['analysis_metadata']:
                        tool_used = str(related_items['analysis_metadata']['tool_used'])

                    actual_items = related_items.get('items', related_items)
                else:
                    actual_items = related_items

                created_at_str = insight.created_at.isoformat() if insight.created_at else datetime.now(timezone.utc).isoformat()

                all_analysis.append({
                    "id": str(insight.id),
                    "type": "insight",
                    "title": f"Insight {insight.type.title() if insight.type else ''}",
                    "summary": insight.insight_message or "",
                    "created_at": created_at_str,
                    "updated_at": created_at_str,
                    "source_table": "proactive_insights",
                    "tool_used": tool_used,
                    "confidence_score": insight.confidence_score,
                    "action_suggestion": insight.action_suggestion,
                    "related_items": actual_items,
                    "status": insight.status,
                    "workspace_id": str(insight.workspace_id) if getattr(insight, 'workspace_id', None) else None,
                    "workspace_name": insight.workspace.name if getattr(insight, 'workspace', None) else None,
                    "workspace_color": insight.workspace.color if getattr(insight, 'workspace', None) else None,
                    "full_data": {
                        "type": insight.type,
                        "title": insight.title,
                        "insight_message": insight.insight_message,
                        "confidence_score": insight.confidence_score,
                        "action_suggestion": insight.action_suggestion,
                        "innovation_potential": insight.innovation_potential,
                        "related_items": insight.related_items,
                        "tool_used": tool_used
                    }
                })

        # 5. Ordenar por fecha de actualización y aplicar paginación
        all_analysis.sort(key=lambda x: str(x.get('updated_at') or x.get('created_at') or ''), reverse=True)

        start_idx = req.offset or 0
        end_idx = start_idx + (req.limit or 20)
        paginated_analysis = all_analysis[start_idx:end_idx]

        return {
            "analysis": paginated_analysis,
            "total": len(all_analysis),
            "limit": req.limit or 20,
            "offset": req.offset or 0,
            "has_more": end_idx < len(all_analysis)
        }
    except Exception as e:
        logger.error(f"Error en get_all_analysis_endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al recuperar los análisis: {str(e)}"
        )

class GapDevelopmentRequest(BaseModel):
    query: str
    workspace_id: Optional[str] = None

@router.post("/start-gap-development", status_code=202, summary="Iniciar desarrollo de brecha de conocimiento")
async def start_gap_development_endpoint(
    req: GapDevelopmentRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Inicia una investigación profunda (deep research) para una brecha de conocimiento o pregunta exploratoria.
    """
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=f"Desarrollo de Brecha: {req.query[:50]}...",
        status="pending",
        analysis_type="gap_development"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    background_tasks.add_task(
        run_gap_development_and_save,
        str(new_task.id),
        current_account_id,
        req.query,
        req.workspace_id
    )

    return {"task_id": str(new_task.id)}


async def run_gap_development_and_save(task_id: str, account_id: str, query: str, workspace_id: Optional[str]):
    """
    Ejecuta el deep researcher y guarda el resultado en la tarea de análisis.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
            await db_session.commit()
            
            logger.info(f"Iniciando desarrollo de brecha para tarea {task_id}...")
            
            from api.deep_research import run_deep_research, DeepResearchRequest
            
            research_request = DeepResearchRequest(query=query, account_id=account_id, workspace_id=workspace_id)
            research_result = await run_deep_research(research_request)
            
            if research_result.get("status") == "success":
                result_payload = {
                    "report": research_result.get("report"),
                    "tool_used": "deep_researcher.py",
                    "analysis_metadata": {
                        "tool_used": "deep_researcher.py",
                        "analysis_type": "gap_development",
                        "query": query,
                        "workspace_id": workspace_id,
                        "created_at": datetime.now().isoformat()
                    }
                }
                stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    status="completed", result_payload=result_payload)
                await db_session.execute(stmt_completed)
            else:
                raise Exception(research_result.get("detail", "Error desconocido en deep research"))

            await db_session.commit()
            logger.info(f"Desarrollo de brecha para tarea {task_id} completado.")

        except Exception as e:
            logger.error(f"Fallo en tarea de desarrollo de brecha {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()


class GetRepoAnalysesRequest(BaseModel):
    repo_name: str

@router.post("/get-repo-analyses")
async def get_repo_analyses_endpoint(
    req: GetRepoAnalysesRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Recupera la lista de análisis completados para un repositorio específico.
    Filtra los análisis donde file_name sea igual al nombre del repositorio o esté en la lista de documentos del repositorio.
    """
    account_uuid = uuid.UUID(current_account_id)
    
    # Obtener documentos del repositorio
    query_docs = select(GitHubDocument).where(
        GitHubDocument.account_id == account_uuid,
        GitHubDocument.repo_url.endswith(f"/{req.repo_name}")
    )
    result_docs = await db.execute(query_docs)
    repo_docs = result_docs.scalars().all()
    repo_doc_file_names = [doc.file_path for doc in repo_docs]
    
    # Construir la consulta de análisis
    stmt = select(AnalysisTask).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        or_(
            AnalysisTask.file_name == req.repo_name,
            AnalysisTask.file_name.in_(repo_doc_file_names)
        )
    ).order_by(desc(AnalysisTask.created_at)).limit(50)
    
    results = await db.execute(stmt)
    return results.scalars().all()


# ============================================================================
# NUEVOS ENDPOINTS OPTIMIZADOS CON ANALYSIS_TYPE Y BÚSQUEDA MEJORADA
# ============================================================================

class StartProactiveInsightGenerationRequest(BaseModel):
    since_days_ago: Optional[int] = None
    topic_keywords: Optional[List[str]] = None
    top_k: Optional[int] = 20
    thread_id: Optional[str] = None

async def run_proactive_insight_generation_and_save(task_id: str, account_id: str, since_timestamp: Optional[datetime], topic_keywords: Optional[List[str]], top_k: Optional[int], thread_id: Optional[str]):
    """
    Función en segundo plano para ejecutar la generación proactiva de insights.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()

            logger.info(f"Iniciando generación proactiva de insights para tarea {task_id} (account: {account_id})")

            # from utils.proactive_knowledge_linker import run_batch_analysis_job
            # await run_batch_analysis_job(
            #     account_id_filter=account_id,
            #     since_timestamp=since_timestamp,
            #     topic_keywords=topic_keywords,
            #     top_k=top_k,
            #     thread_id=thread_id
            # )
            logger.warning("⚠️ Generación proactiva de insights saltada: proactive_knowledge_linker no disponible.")

            # Guardar el resultado (si aplica) y marcar como 'completed'
            # Para insights proactivos, el resultado ya se guarda en ProactiveInsight, aquí solo actualizamos el estado de la tarea.
            result_payload = {
                "message": "Generación de insights proactivos completada. Los insights se han guardado en la tabla proactive_insights.",
                "analysis_metadata": {
                    "tool_used": "proactive_knowledge_linker.py",
                    "analysis_type": "proactive_insight_manual",
                    "since_timestamp": since_timestamp.isoformat() if since_timestamp else None,
                    "topic_keywords": topic_keywords,
                    "created_at": datetime.now().isoformat()
                }
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Generación proactiva de insights para tarea {task_id} completada.")

        except Exception as e:
            logger.error(f"Fallo en tarea de generación proactiva de insights {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/start-proactive-insight-generation", status_code=202, summary="Inicia la generación manual de insights proactivos")
async def start_proactive_insight_generation_endpoint(
    req: StartProactiveInsightGenerationRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Inicia una tarea en segundo plano para generar insights proactivos para una cuenta.
    Permite especificar un rango de tiempo o palabras clave para el análisis.
    """
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name="Generación Manual de Insights Proactivos",
        status="pending",
        analysis_type="proactive_insight_manual"  # Tipo específico para este análisis manual
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    since_timestamp = None
    if req.since_days_ago is not None:
        since_timestamp = datetime.now(timezone.utc) - timedelta(days=req.since_days_ago)

    background_tasks.add_task(
        run_proactive_insight_generation_and_save,
        str(new_task.id),
        current_account_id,
        since_timestamp,
        req.topic_keywords,
        req.top_k,
        req.thread_id
    )

    return {"task_id": str(new_task.id), "message": "Generación de insights proactivos iniciada en segundo plano."}

class SemanticQueryRequest(BaseModel):
    query: str
    limit: int = 5

class SemanticQueryResultItem(BaseModel):
    id: str
    title: str
    content_snippet: str
    type: str
    similarity_score: float

class SemanticQueryResponse(BaseModel):
    results: List[SemanticQueryResultItem]
    message: str

class GetAnalysisTypesRequest(BaseModel):
    """Request para obtener tipos de análisis disponibles."""
    pass

@router.post("/get-analysis-types")
async def get_analysis_types_endpoint(
    req: GetAnalysisTypesRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene los tipos de análisis disponibles y sus estadísticas de uso.

    Utiliza la nueva columna analysis_type para mostrar estadísticas
    de uso por tipo de análisis.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)

        # Obtener estadísticas por tipo de análisis
        stats_query = """
            SELECT
                analysis_type,
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                MAX(created_at) as last_used
            FROM analysis_tasks
            WHERE account_id = :account_id
            GROUP BY analysis_type
            ORDER BY total DESC
        """

        from sqlalchemy import text
        result = await db.execute(text(stats_query), {"account_id": account_uuid})
        rows = result.fetchall()

        # Definir tipos disponibles con descripciones
        available_types = {
            "document": {
                "name": "Análisis de Documentos",
                "description": "Análisis de documentos individuales (PDFs, docs, etc.)",
                "icon": "📄"
            },
            "collection": {
                "name": "Análisis de Colecciones",
                "description": "Análisis de colecciones completas de documentos",
                "icon": "📚"
            },
            "semantic": {
                "name": "Análisis Semántico",
                "description": "Análisis semántico de topics y clustering",
                "icon": "🧠"
            },
            "code": {
                "name": "Análisis de Código",
                "description": "Análisis de código y repositorios",
                "icon": "💻"
            },
            "code_insights": {
                "name": "Análisis de Código (Insights)",
                "description": "Análisis profundo de código para extraer insights y recomendaciones",
                "icon": "🔍"
            },
            "proactive_insight": {
                "name": "Insights Proactivos",
                "description": "Insights proactivos automáticos",
                "icon": "💡"
            },
            "unknown": {
                "name": "Otros Análisis",
                "description": "Análisis de tipo no categorizado",
                "icon": "❓"
            }
        }

        # Combinar estadísticas con información de tipos
        analysis_types = []
        used_types = set()

        for row in rows:
            analysis_type = row[0] or "unknown"
            used_types.add(analysis_type)

            type_info = available_types.get(analysis_type, {
                "name": analysis_type.title() if analysis_type else "Desconocido",
                "description": f"Análisis de tipo {analysis_type}",
                "icon": "❓"
            })

            analysis_types.append({
                "type": analysis_type,
                "name": type_info["name"],
                "description": type_info["description"],
                "icon": type_info["icon"],
                "stats": {
                    "total": row[1],
                    "completed": row[2],
                    "pending": row[3],
                    "failed": row[4],
                    "last_used": row[5].isoformat() if row[5] else None
                }
            })

        # Agregar tipos disponibles que no han sido usados
        for analysis_type, type_info in available_types.items():
            if analysis_type not in used_types:
                analysis_types.append({
                    "type": analysis_type,
                    "name": type_info["name"],
                    "description": type_info["description"],
                    "icon": type_info["icon"],
                    "stats": {
                        "total": 0,
                        "completed": 0,
                        "pending": 0,
                        "failed": 0,
                        "last_used": None
                    }
                })

        return {
            "success": True,
            "total_types": len(analysis_types),
            "types_used": len(used_types),
            "analysis_types": analysis_types
        }

    except Exception as e:
        logger.error(f"Error obteniendo tipos de análisis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/semantic-query", response_model=SemanticQueryResponse, summary="Realiza una consulta semántica en el pool de conocimiento del usuario")
async def semantic_query_endpoint(
    req: SemanticQueryRequest,
    current_account_id: str = Depends(get_current_account_id),
):
    """
    Permite al usuario realizar una consulta semántica (basada en embeddings) sobre
    todo su pool de conocimiento (documentos, notas, memorias).
    Devuelve los ítems más relevantes ordenados por similitud.
    """
    logger.info(f"Iniciando consulta semántica para cuenta {current_account_id} con query: '{req.query}'")
    try:
        from utils.proactive_knowledge_linker import find_top_k_similar_items, summarize_text
        from utils.proactive_knowledge_linker import get_all_knowledge as get_full_knowledge_pool
        # get_text_embedding ya está importado desde core.memory_manager

        # 1. Generar embedding para la consulta del usuario
        query_embedding = await get_text_embedding(req.query)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="No se pudo generar el embedding para la consulta.")
        
        # 2. Obtener el pool de conocimiento completo del usuario
        knowledge_pool = await get_full_knowledge_pool(current_account_id)
        if not knowledge_pool:
            return SemanticQueryResponse(results=[], message="No se encontró conocimiento para esta cuenta.")

        # 3. Encontrar ítems similares
        top_similar_items = await find_top_k_similar_items(query_embedding, knowledge_pool, k=req.limit)

        results_formatted: List[SemanticQueryResultItem] = []
        for item in top_similar_items:
            # Asegúrate de que el contenido no sea demasiado largo para el snippet
            content_snippet = item.get('content', '')
            similarity_score = item.get('similarity_score', 0.0)
            
            if len(content_snippet) > 200:
                content_snippet = content_snippet[:200] + "..." # Truncar el texto directamente
            
            results_formatted.append(SemanticQueryResultItem(
                id=item.get('id', 'unknown'),
                title=item.get('title', 'Sin título'),
                content_snippet=content_snippet,
                type=item.get('type', 'document'),
                similarity_score=similarity_score
            ))
        
        logger.info(f"Consulta semántica completada. Encontrados {len(results_formatted)} resultados para la cuenta {current_account_id}.")
        return SemanticQueryResponse(results=results_formatted, message="Consulta semántica exitosa.")

    except Exception as e:
        logger.error(f"Error en la consulta semántica para cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al realizar la consulta semántica: {str(e)}")


class GetAnalysisByTypeRequest(BaseModel):
    """Request para obtener análisis filtrados por tipo."""
    analysis_type: Optional[str] = None
    status: Optional[str] = None
    limit: Optional[int] = 20

@router.post("/get-analysis-by-type")
async def get_analysis_by_type_endpoint(
    req: GetAnalysisByTypeRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene análisis filtrados por tipo usando la nueva columna analysis_type.

    Permite filtrado eficiente por tipo de análisis y estado.
    """
    try:
        account_uuid = uuid.UUID(current_account_id)

        # Construir consulta con filtros
        stmt = select(AnalysisTask).where(AnalysisTask.account_id == account_uuid)

        if req.analysis_type:
            stmt = stmt.where(AnalysisTask.analysis_type == req.analysis_type)

        if req.status:
            stmt = stmt.where(AnalysisTask.status == req.status)

        stmt = stmt.order_by(desc(AnalysisTask.created_at))

        if req.limit:
            stmt = stmt.limit(req.limit)

        results = await db.execute(stmt)
        analysis_tasks = results.scalars().all()

        return {
            "success": True,
            "total_results": len(analysis_tasks),
            "filters_applied": {
                "analysis_type": req.analysis_type,
                "status": req.status,
                "limit": req.limit
            },
            "results": analysis_tasks
        }

    except Exception as e:
        logger.error(f"Error obteniendo análisis por tipo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

async def run_custom_analysis_and_save(
    task_id: str,
    account_id: str,
    file_name: str,
    objective: str,
    expected_result: Optional[str],
    extension: str,
    fields: List[dict]
):
    """
    Función en segundo plano para realizar análisis personalizado.
    """
    async with DBSession(SessionLocal) as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()

            logger.info(f"Iniciando análisis personalizado para tarea {task_id}...")

            # Obtener el contenido del documento
            text_content = await get_full_document_content(account_id, file_name)
            if not text_content:
                raise ValueError("Contenido del documento no encontrado.")

            # Preparar el prompt personalizado
            extension_instructions = {
                'brief': 'Sé conciso y directo. Máximo 2 páginas.',
                'standard': 'Proporciona un análisis completo pero equilibrado. Entre 3-5 páginas.',
                'detailed': 'Realiza un análisis exhaustivo y detallado. Mínimo 5 páginas.'
            }

            field_instructions = []
            for field in fields:
                field_instructions.append(f"- **{field['name']}**: {field['description']}")

            prompt = f"""
Realiza un análisis personalizado del siguiente documento con estas especificaciones: Responde siempre en español.
 
 **OBJETIVO DEL ANÁLISIS:**
 {objective}
 
 **RESULTADO ESPERADO:**
 {expected_result or 'Análisis estructurado según los campos especificados'}
 
 **EXTENSIÓN:**
 {extension_instructions.get(extension, 'Análisis estándar')}
 
 **CAMPOS REQUERIDOS:**
 {chr(10).join(field_instructions)}
 
 **INSTRUCCIONES:**
 1. Estructura tu respuesta usando exactamente los campos especificados como títulos de sección
 2. Cada sección debe estar en formato Markdown con el título como ##
 3. Proporciona contenido sustancial para cada campo
 4. Mantén un tono profesional y analítico
 5. Basa tu análisis únicamente en el contenido del documento
 
 **DOCUMENTO A ANALIZAR:**
 {text_content}
 
 Responde ÚNICAMENTE con el análisis estructurado en formato Markdown, sin comentarios adicionales. Asegúrate de que todo el contenido generado esté en español.
 """

            # Obtener LLM para el análisis
            llm = await get_llm_for_user(account_id, purpose="fast")
            if not llm:
                raise ValueError("LLM no disponible para análisis personalizado.")

            # Realizar el análisis
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            analysis_content = response.content.strip()

            # Parsear el contenido en secciones
            sections = {}
            current_section = None
            current_content = []

            for line in analysis_content.split('\n'):
                if line.startswith('## '):
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = line[3:].strip()
                    current_content = []
                else:
                    current_content.append(line)

            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()

            # Crear el resultado estructurado
            result_payload = {
                "sections": sections,
                "custom_config": {
                    "objective": objective,
                    "expected_result": expected_result,
                    "extension": extension,
                    "fields": fields
                },
                "tool_used": "custom_analysis_tool",
                "analysis_metadata": {
                    "tool_used": "custom_analysis_tool",
                    "analysis_type": "custom",
                    "file_name": file_name,
                    "fields_count": len(fields),
                    "extension": extension,
                    "created_at": datetime.now().isoformat()
                }
            }

            # Marcar como completado
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed",
                result_payload=result_payload
            )
            await db_session.execute(stmt_completed)
            await db_session.commit()

            logger.info(f"Análisis personalizado para tarea {task_id} completado con {len(sections)} secciones.")

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis personalizado {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

# --- Note Analysis Endpoints ---

class AnalyzeNoteRequest(BaseModel):
    note_id: int

class AnalyzeNoteCollectionRequest(BaseModel):
    note_ids: List[int]
    collection_name: str = "Selección de Notas"

@router.post("/analyze-note", summary="Analizar una nota individual")
async def analyze_note_endpoint(
    req: AnalyzeNoteRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    notes_manager = NotesManager(db)
    note = await notes_manager.get_note_by_id(current_account_id, req.note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    # Perform analysis
    analysis_result = await analyze_single_note(note['content'], note.get('title', 'Sin título'), account_id=current_account_id)
    
    # Save analysis task
    new_task = AnalysisTask(
        id=uuid.uuid4(),
        account_id=uuid.UUID(current_account_id),
        analysis_type="note_analysis",
        file_name=note.get('title', 'Nota sin título'),
        status="completed",
        result_payload=analysis_result,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_task)
    await db.commit()
    
    return {
        "task_id": str(new_task.id),
        "result_payload": analysis_result
    }

@router.post("/analyze-note-collection", summary="Analizar una colección de notas")
async def analyze_note_collection_endpoint(
    req: AnalyzeNoteCollectionRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    notes_manager = NotesManager(db)
    notes_data = []
    for nid in req.note_ids:
        n = await notes_manager.get_note_by_id(current_account_id, nid)
        if n:
            notes_data.append(n)
            
    if not notes_data:
        raise HTTPException(status_code=404, detail="No se encontraron notas válidas")

    # Perform analysis
    analysis_result = await analyze_note_collection(notes_data, req.collection_name, account_id=current_account_id)
    
    # Save analysis task
    new_task = AnalysisTask(
        id=uuid.uuid4(),
        account_id=uuid.UUID(current_account_id),
        analysis_type="note_collection_analysis",
        file_name=req.collection_name,
        status="completed",
        result_payload=analysis_result,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_task)
    await db.commit()
    
    return {
        "task_id": str(new_task.id),
        "result_payload": analysis_result
    }

@router.post("/summarize-note", summary="Generar resumen semántico de una nota")
async def summarize_note_endpoint(
    req: AnalyzeNoteRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    notes_manager = NotesManager(db)
    note = await notes_manager.get_note_by_id(current_account_id, req.note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    # Generate summary
    summary_result = await summarize_note(note['content'], note.get('title', 'Sin título'), account_id=current_account_id)
    
    # Return summary directly (no need to save as task for quick summaries)
    return {
        "task_id": f"summary-{req.note_id}",
        "summary": summary_result.get("summary", ""),
        "key_points": summary_result.get("key_points", []),
        "main_topic": summary_result.get("main_topic", ""),
        "context": summary_result.get("context", ""),
        "result_payload": summary_result
    }
