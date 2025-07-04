import logging
from langchain.schema.messages import HumanMessage
import uuid
from typing import List, Optional

from core.llm_manager import get_fast_llm

from fastapi import APIRouter, HTTPException, Depends, status, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc, or_, update

from core.database import SessionLocal, AnalysisTask, ProactiveInsight, MindmapTask
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.memory_manager import list_user_documents, get_full_document_content
from core.database import GitHubDocument
from utils.advanced_text_analyzer import text_analyzer
from sklearn.cluster import KMeans
import numpy as np
from collections import Counter
from utils.embeddings import initialize_embeddings
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
        all_user_docs = await list_all_user_documents(current_account_id)
        files_in_topic = [
            doc['file_name'] for doc in all_user_docs if doc.get('topic') == req.topic
        ]
        
        # 2. Construimos la condición del WHERE
        #    Queremos análisis cuyo 'file_name' sea uno de los archivos de la colección,
        #    O que sea el análisis de la propia colección.
        collection_reference_name = f"Colección: {req.topic}"
        
        # Usamos or_() para combinar las condiciones
        final_stmt = base_stmt.where(
            or_(
                AnalysisTask.file_name.in_(files_in_topic),
                AnalysisTask.file_name == collection_reference_name
            )
        )
    elif req.all:
        # Si se pide 'all', no aplicamos más filtros.
        final_stmt = base_stmt
    else:
        # Comportamiento por defecto: devolver todos los análisis completados si no se especifica un 'topic'.
        final_stmt = base_stmt

    # Ordenamos y limitamos la consulta final
    final_stmt = final_stmt.order_by(desc(AnalysisTask.created_at)).limit(50)
    
    results = await db.execute(final_stmt)
    return results.scalars().all()

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
            analysis_result = await text_analyzer.analyze_single_text(text_content)

            # 3. Guardar el resultado y marcar como 'completed'
            # Asegurarse de que el resultado sea un diccionario
            result_payload = analysis_result if isinstance(analysis_result, dict) else analysis_result.dict()
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
        status="pending"
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
            logger.info(f"Collection analysis result generated for topic '{topic}': {analysis_result.dict()}")
            
            # 3. Guardar el resultado y marcar como 'completed'
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=analysis_result.dict())
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
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_collection_analysis_and_save, str(new_task.id), current_account_id, req.topic)
    
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
        status="pending"
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
            embedding_model = await initialize_embeddings()
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
                # Nueva lista para almacenar los detalles de cada tema y su cluster
                detailed_clusters_data = [] 

                for i, topic in enumerate(unique_topics):
                    cluster_id = clusters[i] if len(clusters) > 0 else 0 # Asegurar cluster_id incluso si clusters está vacío
                    
                    if cluster_id not in cluster_dict:
                        cluster_dict[cluster_id] = {"topics": [], "mentions": 0, "id": cluster_id} # Añadir id del cluster
                    cluster_dict[cluster_id]["topics"].append(topic)
                    cluster_dict[cluster_id]["mentions"] += topic_counts[topic]

                    # Capturar el detalle de cada tema único y su asignación de cluster
                    detailed_clusters_data.append({"term": topic, "cluster_id": int(cluster_id), "mentions": int(topic_counts[topic])})

                # 5. Generar un término representativo para cada cluster usando el LLM generativo
                grouped_topics = []
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
                        else:
                            prompt = (
                                f"Genera una etiqueta o término conciso (1-3 palabras, sin explicación) "
                                f"que represente mejor el siguiente grupo de temas: {topics_for_prompt}. "
                                f"La etiqueta debe ser altamente relevante y reconocible. "
                                f"Ejemplo: 'Ética IA' para ['consideraciones éticas en IA', 'sesgo en aprendizaje automático', 'desarrollo responsable de IA']."
                            )
                            logger.info(f"Generando término representativo para cluster {cluster_id} con prompt: {prompt[:100]}...")
                            response = await llm_for_summarization.ainvoke([HumanMessage(content=prompt)])
                            representative_term = response.content.strip()
                            logger.info(f"Término representativo generado para cluster {cluster_id}: {representative_term}")
                            
                            if "Ejemplo:" in representative_term:
                                representative_term = representative_term.split("Ejemplo:")[0].strip()
                            if ":" in representative_term:
                                representative_term = representative_term.split(":")[-1].strip()
                            representative_term = representative_term.replace('\n', ' ').replace('\r', '').strip()
                            if len(representative_term.split()) > 3: 
                                representative_term = " ".join(representative_term.split()[:3])
                            if not representative_term:
                                representative_term = f"Grupo {cluster_id + 1}"

                    except Exception as e:
                        logger.error(f"Error al generar término representativo para cluster {cluster_id}: {e}", exc_info=True)
                        representative_term = f"Grupo {cluster_id + 1}"
                    
                    # Añadir el ID del cluster al grupo final para poder vincularlo con detailed_clusters
                    grouped_topics.append({"topic": representative_term, "mentions": int(data["mentions"]), "cluster_id": int(cluster_id)})

                # Ordenar por menciones descendentes y limitar a los 10 principales
                simulated_grouped_topics = sorted(grouped_topics, key=lambda x: x["mentions"], reverse=True)[:10]

            # 6. Guardar el resultado y marcar como 'completed'
            # El payload ahora incluye 'detailed_clusters'
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", 
                result_payload={
                    "grouped_topics": simulated_grouped_topics,
                    "detailed_clusters": detailed_clusters_data # ¡Nueva información aquí!
                }
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

class AnalyzeCodeRequest(BaseModel):
    repo_name: str

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
                formatted_result = await tool._arun(sample_content + f"\n\nNOTA: Este es un análisis de {len(chunks)} partes del repositorio {repo_name}")
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
                "analysis_metadata": {
                    "total_files": len(github_docs),
                    "total_chunks": len(chunks),
                    "repo_name": repo_name
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
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_code_analysis_and_save, str(new_task.id), current_account_id, req.repo_name)
    
    return {"task_id": str(new_task.id)}

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
