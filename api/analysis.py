import logging
from langchain.schema.messages import HumanMessage
import uuid
from typing import List, Optional, cast
from datetime import datetime

from core.llm_manager import get_fast_llm

from fastapi import APIRouter, HTTPException, Depends, status, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc, or_, and_, update, func, String

from core.database import SessionLocal, AnalysisTask, ProactiveInsight, MindmapTask
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.memory_manager import list_user_documents, get_full_document_content
from core.database import GitHubDocument
from utils.advanced_text_analyzer import text_analyzer
from sklearn.cluster import KMeans
import numpy as np
from collections import Counter
from utils.embeddings import get_embedding_model
from core.memory_manager import create_memory_context, search_vector_db_optimized
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

from typing import AsyncGenerator

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session: # type: ignore
        try:
            yield session
        finally:
            await session.close()

async def list_all_user_documents(account_id: str, topic: Optional[str] = None):
    """
    Combina documentos regulares y documentos de GitHub para un usuario.
    """
    # Obtener documentos regulares
    regular_docs = await list_user_documents(account_id)
    
    # Obtener documentos de GitHub
    async with SessionLocal() as db: # type: ignore
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
                "workspace_id": str(doc.workspace_id) if doc.workspace_id else None,
                "team_id": None
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
    db: AsyncSession = Depends(get_db)
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
        all_user_docs = await list_all_user_documents(current_account_id, topic=req.topic)
        files_in_topic = [
            doc['file_name'] for doc in all_user_docs if doc.get('topic') == req.topic
        ]
        
        # 2. Construimos la condición del WHERE
        #    Queremos análisis cuyo 'file_name' sea uno de los archivos de la colección,
        #    O que sea el análisis de la propia colección, O que sea un análisis semántico.
        collection_reference_name = f"Colección: {req.topic}"
        semantic_reference_name = f"Resumen Semántico: {req.topic}"

        # Usamos or_() para combinar las condiciones
        conditions = [
            AnalysisTask.file_name.in_(files_in_topic),
            AnalysisTask.file_name == collection_reference_name,
            AnalysisTask.file_name == semantic_reference_name
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
    task_id: str

@router.post("/delete-analysis", summary="Eliminar un análisis guardado")
async def delete_analysis_endpoint(
    req: DeleteAnalysisRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un análisis guardado por su ID de tarea, si pertenece al usuario autenticado.
    """
    account_uuid = uuid.UUID(current_account_id)
    task_uuid = uuid.UUID(req.task_id)
    
    task = await db.get(AnalysisTask, task_uuid)
    if task is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    # Evitar comparación directa que puede causar error de tipo en Pylance
    if str(task.account_id) != str(account_uuid):
        raise HTTPException(status_code=404, detail="Análisis no pertenece al usuario.")
    
    await db.delete(task)
    await db.commit()
    return {"message": f"Análisis con ID {req.task_id} eliminado correctamente."}

class DashboardInsightsRequest(BaseModel):
    all: bool = False

@router.post("/dashboard-insights")
async def get_dashboard_insights(
    req: DashboardInsightsRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Agrega y devuelve datos de análisis (manuales) y insights (proactivos)
    para el dashboard principal.
    """
    account_uuid = uuid.UUID(current_account_id)

    # 1. Obtener todos los resultados de análisis manuales completados de la tabla AnalysisTask
    analysis_stmt = select(AnalysisTask.result_payload).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        AnalysisTask.result_payload.isnot(None)
    )
    analysis_results = await db.execute(analysis_stmt)
    analysis_payloads = analysis_results.scalars().all()

    # 2. Procesar y agregar los datos de esos análisis para los gráficos
    all_topics = []

    for payload in analysis_payloads:
        if isinstance(payload, dict):
            # Usamos los temas avanzados si existen, que son de mayor calidad
            all_topics.extend(payload.get("temas_clave_avanzados", []))
    
    # Contar y obtener el Top 10 de temas clave para el gráfico de barras
    # TODO: Reemplazar con análisis semántico una vez que Gemini esté integrado
    topic_counts = Counter(all_topics)
    top_topics_for_chart = [{"topic": topic, "mentions": count} for topic, count in topic_counts.most_common(10)]

    # 3. Verificar si hay un análisis semántico reciente completado
    semantic_analysis_stmt = select(AnalysisTask.result_payload).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        AnalysisTask.file_name == "Semantic Topic Analysis",
        AnalysisTask.result_payload.isnot(None)
    ).order_by(desc(AnalysisTask.created_at)).limit(1)
    
    semantic_analysis_result = await db.execute(semantic_analysis_stmt)
    semantic_payload = semantic_analysis_result.scalars().first()
    
    if semantic_payload and "grouped_topics" in semantic_payload:
        # Usar los temas agrupados por análisis semántico si están disponibles
        top_topics_for_chart = semantic_payload["grouped_topics"]
        logger.info(f"Usando temas agrupados por análisis semántico para account {current_account_id}.")

    # 4. Obtener los últimos insights proactivos (sinergias, contradicciones, etc.)
    # Estos son los descubrimientos que la IA hace por sí sola.
    proactive_stmt = select(ProactiveInsight).where(
        ProactiveInsight.account_id == account_uuid
    ).order_by(desc(ProactiveInsight.created_at))

    # Si no se solicitan todos, se aplica el límite para el dashboard
    if not req.all:
        proactive_stmt = proactive_stmt.limit(10)
    
    proactive_results = await db.execute(proactive_stmt)
    recent_proactive_insights = proactive_results.scalars().all()

    # 5. Construir y devolver la respuesta final en el formato que el frontend espera
    return {
        "key_topics": top_topics_for_chart,  # Para el gráfico de barras
        "proactive_insights": [
            {
                "id": str(insight.id),
                "type": insight.type,
                "summary": insight.insight_message,
                "created_at": insight.created_at.isoformat(),
                "related_items": insight.related_items,
                "action_suggestion": insight.action_suggestion,
                # No necesitamos devolver result_payload aquí, ya que el insight es el resultado
            } for insight in recent_proactive_insights
        ]
        # Ya no devolvemos 'top_entities' ni 'exploration_questions' para este diseño
    }

class AnalyzeDocumentRequest(BaseModel):
    file_name: str

async def run_document_analysis_and_save(task_id: str, account_id: str, file_name: str):
    """Función pesada que se ejecuta en segundo plano."""
    async with SessionLocal() as db_session: # type: ignore
        try:
            # 1. Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()
            
            logger.info(f"Iniciando análisis para tarea {task_id}...")
            text_content = await get_full_document_content(account_id, file_name)
            if not text_content: raise ValueError("Contenido del documento no encontrado.")

            # 2. Realizar el análisis pesado
            analysis_result = await text_analyzer.analyze_single_text(text_content, document_title=file_name)

            # 3. Guardar el resultado y marcar como 'completed'
            # Asegurarse de que el resultado sea un diccionario
            result_payload = analysis_result if isinstance(analysis_result, dict) else analysis_result.dict()

            # Agregar metadata de herramienta utilizada
            result_payload["tool_used"] = "advanced_text_analyzer.py"
            result_payload["analysis_metadata"] = {
                "tool_used": "advanced_text_analyzer.py",
                "analysis_type": "document",
                "created_at": datetime.now().isoformat()
            }

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis para tarea {task_id} completado.")

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/start-document-analysis", status_code=202)
async def start_document_analysis_endpoint(
    req: AnalyzeDocumentRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Inicia una tarea de análisis de documento y devuelve un ID de tarea."""
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

@router.get("/get-analysis-result/{task_id}")
async def get_analysis_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Consulta el estado y el resultado de una tarea de análisis."""
    task = await db.get(AnalysisTask, uuid.UUID(task_id))
    if not task or str(task.account_id) != current_account_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")
    return {"status": task.status, "result": task.result_payload, "error": task.error_message}

@router.get("/get-mindmap-result/{task_id}")
async def get_mindmap_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Consulta el estado y el resultado de una tarea de generación de mapa mental."""
    task = await db.get(MindmapTask, uuid.UUID(task_id))
    if not task or str(task.account_id) != current_account_id:
        raise HTTPException(status_code=404, detail="Tarea de mapa mental no encontrada.")
    return {"status": task.status, "result": task.result_payload, "error": task.error_message}

class AnalyzeCollectionRequest(BaseModel):
    topic: str
    workspace_id: Optional[str] = None

async def run_collection_analysis_and_save(task_id: str, account_id: str, topic: str):
    """
    Obtiene todos los documentos de una colección, los analiza y guarda el resultado.
    """
    async with SessionLocal() as db_session: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
            await db_session.commit()
            
            logger.info(f"Iniciando análisis de colección para tarea {task_id} (tema: {topic})")

            # 1. Obtener todos los documentos de la colección
            all_docs_in_topic = []
            # (Aquí usamos la función combinada que incluye documentos de GitHub)
            doc_list = await list_all_user_documents(account_id)
            filtered_doc_list = [doc for doc in doc_list if doc.get('topic') == topic]
            
            for doc_meta in filtered_doc_list:
                content = await get_full_document_content(account_id, doc_meta['file_name'])
                if content:
                    all_docs_in_topic.append({
                        "title": doc_meta.get('title', doc_meta['file_name']),
                        "content": content
                    })

            if not all_docs_in_topic:
                raise ValueError(f"No se encontraron documentos con contenido en la colección '{topic}'.")

            # 2. Realizar el análisis de la colección
            analysis_result = await text_analyzer.analyze_collection(all_docs_in_topic)
            logger.info(f"Collection analysis result generated for topic '{topic}': {analysis_result.model_dump()}")

            # 3. Guardar el resultado y marcar como 'completed'
            result_payload = analysis_result.model_dump()

            # Agregar metadata de herramienta utilizada
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

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis de colección {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/start-collection-analysis", status_code=202)
async def start_collection_analysis_endpoint(
    req: AnalyzeCollectionRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
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
    
    background_tasks.add_task(run_collection_analysis_and_save, str(new_task.id), current_account_id, req.topic)
    
    return {"task_id": str(new_task.id)}

@router.post("/start-semantic-summary", status_code=202, summary="Iniciar resumen semántico de una colección")
async def start_semantic_summary_endpoint(
    req: AnalyzeCollectionRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db),
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

async def run_semantic_topic_analysis(task_id: str, account_id: str, max_terms: Optional[int] = None):
    """
    Proceso en segundo plano para realizar análisis semántico y agrupación de temas.
    Integración con modelos de embeddings y LLMs para clustering y etiquetado.
    Se puede limitar el número de términos analizados con max_terms.
    Ahora incluye detalles de los temas individuales agrupados.
    """
    async with SessionLocal() as db_session: #type: ignore
        try:
            # Marcar la tarea como 'processing' y notificar al usuario
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()
            logger.info(f"Iniciando análisis semántico para tarea {task_id} para la cuenta {account_id}...")

            # 1. Obtener todos los temas de análisis previos
            analysis_stmt = select(AnalysisTask.result_payload).where(
                AnalysisTask.account_id == uuid.UUID(account_id),
                AnalysisTask.status == "completed",
                AnalysisTask.result_payload.isnot(None)
            )
            analysis_results = await db_session.execute(analysis_stmt)
            analysis_payloads = analysis_results.scalars().all()

            all_topics_raw = []
            for payload in analysis_payloads:
                if isinstance(payload, dict):
                    # Asumimos que 'temas_clave_avanzados' es la fuente de temas individuales
                    all_topics_raw.extend(payload.get("temas_clave_avanzados", []))
            
            topic_counts = Counter(all_topics_raw)
            
            if max_terms is not None:
                unique_topics = [topic for topic, count in topic_counts.most_common(max_terms)]
                logger.info(f"Limitando análisis semántico a {max_terms} términos más frecuentes de un total de {len(all_topics_raw)}.")
            else:
                unique_topics = list(topic_counts.keys())
                logger.info(f"Procesando {len(unique_topics)} temas únicos para análisis semántico sin límite.")

            if not unique_topics:
                logger.info(f"No hay temas únicos para procesar en la tarea {task_id}. Completando sin resultados.")
                stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    status="completed", result_payload={"grouped_topics": [], "detailed_clusters": []})
                await db_session.execute(stmt_completed)
                await db_session.commit()
                return

            # 2. Integrar el MODELO DE EMBEDDINGS dedicado (Ollama en este caso)
            embedding_model = get_embedding_model()
            if not embedding_model:
                logger.error("No hay modelo de embeddings disponible (Ollama).")
                raise ValueError("Modelo de embeddings no disponible para análisis semántico.")
            
            embeddings = []
            try:
                logger.info(f"Generando embeddings para {len(unique_topics)} temas de forma batch...")
                embeddings = await embedding_model.aembed_documents(unique_topics)
                logger.info(f"Embeddings generados exitosamente para {len(embeddings)} temas.")
            except Exception as e:
                logger.error(f"Error al obtener embeddings de forma batch con Ollama: {e}", exc_info=True)
                raise ValueError(f"Fallo al generar embeddings de forma batch: {e}")

            if not embeddings:
                logger.info("No se generaron embeddings, saltando clustering y agrupación.")
                simulated_grouped_topics = []
                detailed_clusters_data = [] # También vacío si no hay embeddings
            else:
                # 3. Implementar clustering (e.g., K-Means)
                n_clusters = min(5, max(1, len(embeddings) // 2 + 1)) 
                if len(embeddings) < n_clusters:
                    n_clusters = len(embeddings)
                
                clusters = []
                if n_clusters > 1:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto') 
                    clusters = kmeans.fit_predict(np.array(embeddings))
                else:
                    clusters = [0] * len(unique_topics) if len(unique_topics) > 0 else []

                # 4. Agrupar temas por cluster y contar menciones
                cluster_dict = {}
                # Lista temporal para almacenar los detalles de cada tema y su cluster
                temp_detailed_data = []

                for i, topic in enumerate(unique_topics):
                    cluster_id = clusters[i] if len(clusters) > 0 else 0 # Asegurar cluster_id incluso si clusters está vacío

                    if cluster_id not in cluster_dict:
                        cluster_dict[cluster_id] = {"topics": [], "mentions": 0, "id": cluster_id} # Añadir id del cluster
                    cluster_dict[cluster_id]["topics"].append(topic)
                    cluster_dict[cluster_id]["mentions"] += topic_counts[topic]

                    # Capturar el detalle de cada tema único y su asignación de cluster
                    temp_detailed_data.append({"term": topic, "cluster_id": int(cluster_id), "mentions": int(topic_counts[topic])})

                # 5. Generar un término representativo para cada cluster usando el LLM generativo
                grouped_topics = []
                detailed_clusters_data = []  # Lista final con información completa de clusters
                llm_for_summarization = get_fast_llm()
                if not llm_for_summarization:
                    logger.error("No hay LLM generativo disponible para generar términos representativos.")
                    raise ValueError("LLM generativo no disponible para generación de términos representativos.")
                else:
                    logger.info("LLM generativo disponible, procediendo a generar términos representativos.")

                for cluster_id, data in cluster_dict.items():
                    try:
                        topics_for_prompt = ", ".join(data["topics"][:15])
                        if not topics_for_prompt:
                            representative_term = f"Grupo {cluster_id + 1}"
                            description = f"Agrupación que incluye: {', '.join(data['topics'][:3])}"
                        else:
                            prompt = (
                                f"Analiza el siguiente grupo de temas relacionados y proporciona:\n"
                                f"1. Una etiqueta representativa concisa (máximo 3 palabras) NUNCA USES GRUPO nº\n"
                                f"2. Una descripción clara de qué conceptos agrupa (máximo 2 líneas)\n\n"
                                f"Temas: {topics_for_prompt}\n\n"
                                f"Formato de respuesta:\n"
                                f"ETIQUETA: [etiqueta aquí]\n"
                                f"DESCRIPCIÓN: [descripción aquí]"
                            )
                            logger.info(f"Generando término representativo para cluster {cluster_id} con prompt: {prompt[:100]}...")
                            response = await llm_for_summarization.ainvoke([HumanMessage(content=prompt)])
                            content = response.content.strip()
                            logger.info(f"Respuesta generada para cluster {cluster_id}: {content}")

                            # Parsear la respuesta
                            representative_term = f"Grupo {cluster_id + 1}"
                            description = f"Agrupación que incluye: {', '.join(data['topics'][:3])}"

                            lines = content.split('\n')
                            for line in lines:
                                if line.startswith('ETIQUETA:'):
                                    term = line.replace('ETIQUETA:', '').strip()
                                    if term and len(term.split()) <= 3:
                                        representative_term = term
                                elif line.startswith('DESCRIPCIÓN:'):
                                    desc = line.replace('DESCRIPCIÓN:', '').strip()
                                    if desc and len(desc) <= 150:
                                        description = desc

                            if not representative_term or representative_term == f"Grupo {cluster_id + 1}":
                                representative_term = f"Grupo {cluster_id + 1}"

                    except Exception as e:
                        logger.error(f"Error al generar término representativo para cluster {cluster_id}: {e}", exc_info=True)
                        representative_term = f"Grupo {cluster_id + 1}"
                        description = f"Agrupación que incluye: {', '.join(data['topics'][:3])}"

                    # Añadir información completa del cluster a detailed_clusters_data
                    detailed_clusters_data.append({
                        "cluster_id": int(cluster_id),
                        "representative_term": representative_term,
                        "description": description,
                        "topics": data["topics"],
                        "total_mentions": int(data["mentions"]),
                        "topic_count": len(data["topics"])
                    })

                    # Añadir el ID del cluster al grupo final para poder vincularlo con detailed_clusters
                    grouped_topics.append({
                        "topic": representative_term,
                        "mentions": int(data["mentions"]),
                        "cluster_id": int(cluster_id),
                        "description": description,
                        "topics": data["topics"]
                    })

                # Ordenar por menciones descendentes y limitar a los 10 principales
                simulated_grouped_topics = sorted(grouped_topics, key=lambda x: x["mentions"], reverse=True)[:10]

            # 6. Guardar el resultado y marcar como 'completed'
            # El payload ahora incluye 'detailed_clusters' y metadata de herramienta
            result_payload = {
                "grouped_topics": simulated_grouped_topics,
                "detailed_clusters": detailed_clusters_data,
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

            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed",
                result_payload=result_payload
            )
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis semántico para tarea {task_id} completado con {len(simulated_grouped_topics)} grupos de temas y {len(detailed_clusters_data)} temas detallados.")
        except Exception as e:
            logger.error(f"Fallo en tarea de análisis semántico {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

async def run_semantic_summary_analysis(task_id: str, account_id: str, topic: str, workspace_id: Optional[str] = None):
    """
    Proceso en segundo plano para realizar un resumen semántico específico de una colección.
    Se enfoca en agrupación semántica de documentos y extracción de patrones dentro de la colección.
    """
    async with SessionLocal() as db_session: #type: ignore
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
            semantic_analysis = await analyzer.analyze_collection(all_docs_content)

            # Realizar análisis semántico de la colección
            semantic_analysis = await analyzer.analyze_collection(documents_for_analysis)

            # Crear resultado estructurado
            result_payload = {
                "resumen_semantico": semantic_analysis.collection_summary,
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
                    "total_chunks_analizados": len(all_chunks),
                    "temas_identificados": len(semantic_analysis.cross_cutting_themes)
                },
                "tool_used": "semantic_summary_analysis",
                "analysis_metadata": {
                    "tool_used": "semantic_summary_analysis",
                    "analysis_type": "semantic_summary",
                    "collection_name": topic,
                    "workspace_id": workspace_id,
                    "documents_count": len(documents),
                    "chunks_analyzed": len(all_chunks),
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

class AnalyzeCodeRequest(BaseModel):
    repo_name: str

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

async def run_code_analysis_and_save(task_id: str, account_id: str, repo_name: str):
    """Función pesada que se ejecuta en segundo plano para análisis de código."""
    async with SessionLocal() as db_session: # type: ignore
        try:
            # 1. Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()
            
            logger.info(f"Iniciando análisis de código para tarea {task_id}...")
            # Obtener los documentos específicos de GitHub del repositorio
            query = select(GitHubDocument).where(
                GitHubDocument.account_id == account_id,
                GitHubDocument.repo_url.endswith(f"/{repo_name}")
            )
            result = await db_session.execute(query)
            github_docs = result.scalars().all()
            
            logger.info(f"Encontrados {len(github_docs)} documentos de GitHub para el repositorio {repo_name}")
            
            if not github_docs:
                raise ValueError("No se encontraron documentos de GitHub para el repositorio.")
            
            # 2. Análisis por chunks para repositorios grandes
            from utils.advanced_code_analyzer import analyze_code_content
            
            chunk_size = 300000  # ~300k caracteres por chunk (~400k tokens aprox)
            chunks = []
            current_chunk = ""
            current_chunk_files = []
            
            for doc in github_docs:
                if doc.content:
                    file_content = f"Archivo: {doc.file_path}\n{doc.content}\n\n"
                    
                    # Si agregar este archivo excede el chunk_size, crear un nuevo chunk
                    if len(current_chunk) + len(file_content) > chunk_size and current_chunk:
                        chunks.append({
                            "content": current_chunk,
                            "files": current_chunk_files.copy()
                        })
                        current_chunk = file_content
                        current_chunk_files = [doc.file_path]
                    else:
                        current_chunk += file_content
                        current_chunk_files.append(doc.file_path)
            
            # Agregar el último chunk si tiene contenido
            if current_chunk:
                chunks.append({
                    "content": current_chunk,
                    "files": current_chunk_files.copy()
                })
            
            logger.info(f"Código dividido en {len(chunks)} chunks para análisis")
            
            # 3. Analizar cada chunk
            all_chunk_results = []
            combined_categories = {
                "code_structure": [],
                "design_patterns": [],
                "dependencies": [],
                "potential_issues": [],
                "recommendations": []
            }
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Analizando chunk {i+1}/{len(chunks)} ({len(chunk['files'])} archivos)")
                
                # Actualizar progreso en la base de datos
                progress_message = f"Analizando parte {i+1} de {len(chunks)}..."
                stmt_progress = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                    result_payload={"progress": f"{i+1}/{len(chunks)}", "message": progress_message})
                await db_session.execute(stmt_progress)
                await db_session.commit()
                
                chunk_result = await analyze_code_content(chunk["content"])
                all_chunk_results.append({
                    "chunk_index": i+1,
                    "files": chunk["files"],
                    "result": chunk_result
                })
                
                # Manejar tanto objetos Pydantic como diccionarios
                if hasattr(chunk_result, 'code_structure'):
                    # Es un objeto Pydantic
                    combined_categories["code_structure"].extend(chunk_result.code_structure)
                    combined_categories["design_patterns"].extend(chunk_result.design_patterns)
                    combined_categories["dependencies"].extend(chunk_result.dependencies)
                    combined_categories["potential_issues"].extend(chunk_result.potential_issues)
                    combined_categories["recommendations"].extend(chunk_result.recommendations)
                elif isinstance(chunk_result, dict):
                    # Es un diccionario
                    combined_categories["code_structure"].extend(chunk_result.get("code_structure", []))
                    combined_categories["design_patterns"].extend(chunk_result.get("design_patterns", []))
                    combined_categories["dependencies"].extend(chunk_result.get("dependencies", []))
                    combined_categories["potential_issues"].extend(chunk_result.get("potential_issues", []))
                    combined_categories["recommendations"].extend(chunk_result.get("recommendations", []))
                else:
                    logger.warning(f"Resultado inesperado del análisis de chunk {i+1}: {type(chunk_result)}")
            
            # 4. Generar resumen ejecutivo consolidado
            from tools.analyze_code_for_insights_tool import AnalyzeCodeForInsightsTool
            
            # Crear un resumen de todos los chunks para el formatted_result
            combined_summary = "\n\n".join([
                f"**Análisis Parte {res['chunk_index']}** (Archivos: {', '.join(res['files'][:3])}{'...' if len(res['files']) > 3 else ''})\n{res['result'].executive_summary if hasattr(res['result'], 'executive_summary') else res['result'].get('executive_summary', 'Sin resumen disponible')}"
                for res in all_chunk_results
            ])
            
            # Generar análisis consolidado final
            tool = AnalyzeCodeForInsightsTool()
            final_summary = f"**Análisis Completo del Repositorio {repo_name}**\n\n"
            final_summary += f"Se analizaron {len(chunks)} partes del código con un total de {len(github_docs)} archivos.\n\n"
            final_summary += f"**Resumen por Partes:**\n{combined_summary}\n\n"
            
            # Generar formatted_result consolidado usando la herramienta
            try:
                # Usar solo una muestra representativa para el formato final
                sample_content = chunks[0]["content"][:100000] if chunks else ""
                formatted_result = await tool._arun(
                    code_content=sample_content + f"\n\nNOTA: Este es un análisis de {len(chunks)} partes del repositorio {repo_name}",
                    account_id=account_id,
                    file_name=f"Análisis de Repositorio: {repo_name}",
                    save_to_database=False  # No guardar este análisis parcial
                )
            except Exception as e:
                logger.warning(f"Error generando resultado formateado: {e}")
                formatted_result = final_summary
            
            # 5. Estructura final del resultado
            analysis_result = {
                "formatted_result": formatted_result,
                "executive_summary": f"Análisis completo de {len(github_docs)} archivos en {len(chunks)} partes del repositorio {repo_name}",
                "code_structure": combined_categories["code_structure"],
                "design_patterns": combined_categories["design_patterns"],
                "dependencies": combined_categories["dependencies"],
                "potential_issues": combined_categories["potential_issues"],
                "recommendations": combined_categories["recommendations"],
                "tool_used": "advanced_code_analyzer.py",
                "analysis_metadata": {
                    "tool_used": "advanced_code_analyzer.py",
                    "analysis_type": "code",
                    "total_files": len(github_docs),
                    "total_chunks": len(chunks),
                    "repo_name": repo_name,
                    "created_at": datetime.now().isoformat()
                }
            }

            # 6. Guardar el resultado y marcar como 'completed'
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=analysis_result)
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis de código para tarea {task_id} completado con {len(chunks)} chunks.")

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis de código {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@router.post("/start-code-analysis", status_code=202)
async def start_code_analysis_endpoint(
    req: AnalyzeCodeRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
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
    
    background_tasks.add_task(run_code_analysis_and_save, str(new_task.id), current_account_id, req.repo_name)
    
    return {"task_id": str(new_task.id)}

@router.post("/start-custom-analysis", status_code=202, summary="Iniciar análisis personalizado")
async def start_custom_analysis_endpoint(
    req: CustomAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene todos los análisis del usuario de forma unificada.
    Combina AnalysisTask, MindmapTask y ProactiveInsight en una sola respuesta.
    """
    account_uuid = uuid.UUID(current_account_id)
    all_analysis = []

    # 1. Obtener AnalysisTask (análisis de documentos, colecciones, código, semánticos)
    if not req.analysis_type or req.analysis_type in ['document', 'collection', 'code', 'semantic_summary', 'semantic', 'custom']:
        analysis_stmt = select(AnalysisTask).where(
            AnalysisTask.account_id == account_uuid,
            AnalysisTask.status == "completed"
        ).order_by(AnalysisTask.updated_at.desc())

        # Filtrar por analysis_type específico si se solicita
        if req.analysis_type:
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
            # Determinar el tipo específico basado en el file_name y analysis_type
            file_name = str(task.file_name) if task.file_name is not None else ""
            task_analysis_type = getattr(task, 'analysis_type', None)

            # Usar el analysis_type de la tarea si está disponible, sino inferir del file_name
            if task_analysis_type == "semantic_summary":
                analysis_type = "semantic_summary"
                title = file_name
            elif file_name.startswith("Resumen Semántico:"):
                analysis_type = "semantic_summary"
                title = file_name
            elif task_analysis_type == "collection" or file_name.startswith("Colección:"):
                analysis_type = "collection"
                title = file_name
            elif file_name == "Semantic Topic Analysis" or task_analysis_type == "semantic":
                analysis_type = "semantic"
                title = "Análisis Semántico de Temas"
            elif task_analysis_type == "code" or "repositorio" in file_name.lower() or file_name.endswith(".git") or "Análisis de Repositorio:" in file_name:
                analysis_type = "code"
                title = file_name if "Análisis de Repositorio:" in file_name else f"Análisis de Código: {file_name}"
            elif task_analysis_type == "custom" or file_name.startswith("Análisis Personalizado:"):
                analysis_type = "custom"
                title = file_name
            elif task_analysis_type == "document":
                analysis_type = "document"
                title = file_name if file_name.startswith("Análisis de Documento:") else f"Análisis de Documento: {file_name}"
            else:
                # Fallback: inferir del contenido del resultado
                analysis_type = "document"
                title = f"Análisis de Documento: {file_name}"

            # Extraer resumen del resultado
            summary = "Sin resumen disponible"
            tool_used = "Desconocido"

            if task.result_payload is not None:
                # Asegurarse de que result_payload es un diccionario
                payload_dict = task.result_payload if isinstance(task.result_payload, dict) else {}
 
                if 'executive_summary' in payload_dict:
                    summary = payload_dict['executive_summary']
                elif 'resumen_ejecutivo' in payload_dict:
                    summary = payload_dict['resumen_ejecutivo']
                elif 'resumen_semantico' in payload_dict:
                    sem_summary = str(payload_dict['resumen_semantico']) # Convertir a str para len()
                    summary = sem_summary[:200] + "..." if len(sem_summary) > 200 else sem_summary
                elif 'sections' in payload_dict and isinstance(payload_dict['sections'], list) and len(cast(list, payload_dict['sections'])) > 0:
                    # Para análisis personalizados, extraer resumen de la primera sección
                    first_section = payload_dict['sections'][0]
                    if 'content' in first_section:
                        content = str(first_section['content'])
                        summary = content[:200] + "..." if len(content) > 200 else content
                    else:
                        sections_list = cast(list, payload_dict['sections'])
                        sections_count = len(sections_list)
                        summary = f"Análisis personalizado con {sections_count} secciones"
                elif 'sections' in payload_dict:
                    # Si existe 'sections' pero está vacío
                    summary = "Análisis personalizado sin contenido"
                elif 'formatted_result' in payload_dict:
                    summary = str(payload_dict['formatted_result'])[:200] + "..."
 
                # Obtener herramienta usada desde los metadatos o inferir basándose en la estructura
                if 'tool_used' in payload_dict:
                    tool_used = payload_dict['tool_used']
                elif 'analysis_metadata' in payload_dict and 'tool_used' in payload_dict['analysis_metadata']:
                    tool_used = payload_dict['analysis_metadata']['tool_used']
                else:
                    # Fallback: inferir basándose en la estructura del payload y file_name
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

            all_analysis.append({
                "id": str(task.id),
                "type": analysis_type,
                "title": title,
                "summary": summary,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "source_table": "analysis_tasks",
                "tool_used": tool_used,
                "full_data": task.result_payload
            })

    # 2. Obtener MindmapTask
    if not req.analysis_type or req.analysis_type == 'mindmap':
        # Seleccionar solo las columnas que existen en mindmap_tasks (sin analysis_type)
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
        ).order_by(MindmapTask.updated_at.desc())

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
            if row.result_payload is not None and 'summary' in row.result_payload:
                summary = row.result_payload['summary']

            # Obtener herramienta usada desde los metadatos o usar fallback
            tool_used = "mindmap_generator_tool.py"
            if row.result_payload is not None:
                if 'tool_used' in row.result_payload:
                    tool_used = row.result_payload['tool_used']
                elif 'analysis_metadata' in row.result_payload and 'tool_used' in row.result_payload['analysis_metadata']:
                    tool_used = row.result_payload['analysis_metadata']['tool_used']

            all_analysis.append({
                "id": str(row.id),
                "type": "mindmap",
                "title": f"Mapa Mental: {row.topic}",
                "summary": summary,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
                "source_table": "mindmap_tasks",
                "tool_used": tool_used,
                "full_data": row.result_payload
            })

    # 3. Obtener ProactiveInsight
    if not req.analysis_type or req.analysis_type == 'insight':
        insight_stmt = select(ProactiveInsight).where(
            ProactiveInsight.account_id == account_uuid
        ).order_by(ProactiveInsight.created_at.desc())

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
            # Obtener herramienta usada desde los metadatos o usar fallback
            tool_used = "proactive_knowledge_linker_tool.py"
            related_items = insight.related_items or {}

            if isinstance(related_items, dict):
                if 'tool_used' in related_items:
                    tool_used = related_items['tool_used']
                elif 'analysis_metadata' in related_items and 'tool_used' in related_items['analysis_metadata']:
                    tool_used = related_items['analysis_metadata']['tool_used']

                # Extraer los items reales si están en la nueva estructura
                actual_items = related_items.get('items', related_items)
            else:
                # Fallback para estructura antigua
                actual_items = related_items

            all_analysis.append({
                "id": str(insight.id),
                "type": "insight",
                "title": f"Insight {insight.type.title()}",
                "summary": insight.insight_message,
                "created_at": insight.created_at.isoformat(),
                "updated_at": insight.created_at.isoformat(),
                "source_table": "proactive_insights",
                "tool_used": tool_used,
                "confidence_score": insight.confidence_score,
                "action_suggestion": insight.action_suggestion,
                "related_items": actual_items,
                "full_data": {
                    "type": insight.type,
                    "insight_message": insight.insight_message,
                    "confidence_score": insight.confidence_score,
                    "action_suggestion": insight.action_suggestion,
                    "related_items": insight.related_items,
                    "tool_used": tool_used
                }
            })

    # 4. Ordenar por fecha de actualización y aplicar paginación
    all_analysis.sort(key=lambda x: x['updated_at'], reverse=True)

    # Aplicar paginación
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

class GetRepoAnalysesRequest(BaseModel):
    repo_name: str

@router.post("/get-repo-analyses")
async def get_repo_analyses_endpoint(
    req: GetRepoAnalysesRequest,
    current_account_id: str = Depends(get_current_account_id), 
    db: AsyncSession = Depends(get_db)
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

class GetAnalysisTypesRequest(BaseModel):
    """Request para obtener tipos de análisis disponibles."""
    pass

@router.post("/get-analysis-types")
async def get_analysis_types_endpoint(
    req: GetAnalysisTypesRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
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


class GetAnalysisByTypeRequest(BaseModel):
    """Request para obtener análisis filtrados por tipo."""
    analysis_type: Optional[str] = None
    status: Optional[str] = None
    limit: Optional[int] = 20

@router.post("/get-analysis-by-type")
async def get_analysis_by_type_endpoint(
    req: GetAnalysisByTypeRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
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
    async with SessionLocal() as db_session: # type: ignore
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
Realiza un análisis personalizado del siguiente documento con estas especificaciones:

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

Responde ÚNICAMENTE con el análisis estructurado en formato Markdown, sin comentarios adicionales.
"""

            # Obtener LLM para el análisis
            from core.llm_manager import get_fast_llm
            llm = get_fast_llm()
            if not llm:
                raise ValueError("LLM no disponible para análisis personalizado.")

            # Realizar el análisis
            from langchain.schema.messages import HumanMessage
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
