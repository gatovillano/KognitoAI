# api/analysis.py

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc, or_, update

from core.database import SessionLocal, AnalysisTask, ProactiveInsight
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from core.memory_manager import list_user_documents, get_full_document_content
from utils.advanced_text_analyzer import text_analyzer
from sklearn.cluster import KMeans
import numpy as np
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncSession:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

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
        #    (Reutilizamos la lógica de list_user_documents)
        all_user_docs = await list_user_documents(current_account_id)
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
    if not task or task.account_id != account_uuid:
        raise HTTPException(status_code=404, detail="Análisis no encontrado o no pertenece al usuario.")
    
    await db.delete(task)
    await db.commit()
    return {"message": f"Análisis con ID {req.task_id} eliminado correctamente."}

@router.post("/dashboard-insights")
async def get_dashboard_insights(
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
    ).order_by(desc(ProactiveInsight.created_at)).limit(10)
    
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
    async with SessionLocal() as db_session:
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
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=analysis_result.dict())
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

class AnalyzeCollectionRequest(BaseModel):
    topic: str

async def run_collection_analysis_and_save(task_id: str, account_id: str, topic: str):
    """
    Obtiene todos los documentos de una colección, los analiza y guarda el resultado.
    """
    db_session = SessionLocal()
    try:
        # Marcar la tarea como 'processing'
        await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
        await db_session.commit()
        
        logger.info(f"Iniciando análisis de colección para tarea {task_id} (tema: {topic})")

        # 1. Obtener todos los documentos de la colección
        all_docs_in_topic = []
        # (Aquí usamos la lógica de list_user_documents, pero necesitamos el contenido)
        doc_list = await list_user_documents(account_id)
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
    finally:
        await db_session.close()

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
    max_terms: Optional[int] = Form(default=15, ge=1, description="Número máximo de términos a analizar para el análisis semántico")
):
    """
    Dispara manualmente el proceso de análisis semántico para agrupar temas por similitud.
    Este proceso se ejecuta en segundo plano y actualiza los datos para el endpoint /api/dashboard-insights.
    Opcionalmente, se puede limitar el número de términos analizados con max_terms.
    """
    account_uuid = uuid.UUID(current_account_id)
    new_task = AnalysisTask(
        account_id=account_uuid,
        file_name="Semantic Topic Analysis",
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    logger.info(f"Iniciando tarea de análisis semántico con ID {str(new_task.id)} para la cuenta {current_account_id} con límite de {max_terms if max_terms else 'todos'} términos")
    background_tasks.add_task(run_semantic_topic_analysis, str(new_task.id), current_account_id, max_terms)
    
    return {"task_id": str(new_task.id), "message": f"Análisis semántico iniciado en segundo plano con límite de {max_terms if max_terms else 'todos los'} términos."}

async def run_semantic_topic_analysis(task_id: str, account_id: str, max_terms: Optional[int] = None):
    """
    Proceso en segundo plano para realizar análisis semántico y agrupación de temas.
    Este es un placeholder para la integración con Gemini API.
    Se puede limitar el número de términos analizados con max_terms.
    """
    async with SessionLocal() as db_session:
        try:
            # Marcar la tarea como 'processing' y notificar al usuario
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()
            logger.info(f"Iniciando análisis semántico para tarea {task_id} para la cuenta {account_id}...")
            # Aquí se podría enviar una notificación de inicio a través de un WebSocket o similar

            # 1. Obtener todos los temas de análisis previos
            analysis_stmt = select(AnalysisTask.result_payload).where(
                AnalysisTask.account_id == uuid.UUID(account_id),
                AnalysisTask.status == "completed",
                AnalysisTask.result_payload.isnot(None)
            )
            analysis_results = await db_session.execute(analysis_stmt)
            analysis_payloads = analysis_results.scalars().all()

            all_topics = []
            for payload in analysis_payloads:
                if isinstance(payload, dict):
                    all_topics.extend(payload.get("temas_clave_avanzados", []))
            if max_terms is not None and len(all_topics) > max_terms:
                all_topics = all_topics[:max_terms]
                logger.info(f"Limitando análisis semántico a {max_terms} términos de un total de {len(all_topics)}.")
            else:
                logger.info(f"Procesando {len(all_topics)} temas para análisis semántico sin límite.")

            # 2. Integrar Gemini API para obtener embebidos semánticos usando el LLM ya configurado
            from core.llm_manager import get_fast_llm
            llm_for_embeddings = get_fast_llm()
            if not llm_for_embeddings:
                logger.error("No hay LLM disponible para generar embeddings.")
                raise ValueError("LLM no disponible para análisis semántico.")
                
            embeddings = []
            for topic in all_topics:
                try:
                    logger.info(f"Generando embedding para el tema: {topic}")
                    # Usar un prompt más específico para obtener una representación numérica precisa
                    prompt = f"Convert the topic '{topic}' into a dense numerical vector of 768 dimensions for semantic clustering. Provide the vector as a space-separated list of numbers."
                    response = await llm_for_embeddings.ainvoke(prompt)
                    logger.info(f"Respuesta recibida para el tema: {topic}")
                    # Extraer el contenido como texto y convertir a lista de números
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    # Parsear la respuesta para obtener un vector de números
                    vector = []
                    for val in response_text.split():
                        try:
                            num_val = float(val)
                            vector.append(num_val)
                        except ValueError:
                            continue  # Ignorar valores no numéricos
                    # Ajustar el tamaño del vector a 768 dimensiones
                    while len(vector) < 768:
                        vector.append(0.0)
                    if len(vector) > 768:
                        vector = vector[:768]
                    embeddings.append(vector)
                    logger.info(f"Embedding generado exitosamente para: {topic}")
                except Exception as e:
                    logger.error(f"Error al obtener embedding para {topic}: {e}", exc_info=True)
                    embeddings.append([0.0] * 768)  # Fallback en caso de error
            logger.info(f"Obtenidos embeddings para {len(embeddings)} temas.")

            # 3. Implementar clustering (e.g., K-Means) para agrupar temas por similitud semántica
            if len(embeddings) > 5:  # Solo hacer clustering si hay suficientes temas
                kmeans = KMeans(n_clusters=min(5, len(embeddings) // 2 + 1), random_state=42)
                clusters = kmeans.fit_predict(np.array(embeddings))
            else:
                clusters = list(range(len(embeddings)))  # Asignar un cluster por tema si hay pocos

            # 4. Agrupar temas por cluster y contar menciones
            cluster_dict = {}
            for topic, cluster_id, _ in zip(all_topics, clusters, embeddings):
                if cluster_id not in cluster_dict:
                    cluster_dict[cluster_id] = {"topics": [], "mentions": 0}
                cluster_dict[cluster_id]["topics"].append(topic)
                cluster_dict[cluster_id]["mentions"] += all_topics.count(topic)

            # 5. Generar un término representativo para cada cluster usando el mismo LLM
            grouped_topics = []
            for cluster_id, data in cluster_dict.items():
                try:
                    topics_str = ", ".join(data["topics"][:5])  # Limitar a 5 temas para el prompt
                    prompt = f"Generate a concise tag or term -not phrase, only term-for the following group of topics: {topics_str}. The tag should be a short, specific label (1-3 words) that captures the essence of these topics without any explanation or description. Ensure it is relevant and recognizable to the user."
                    response = await llm_for_embeddings.ainvoke(prompt)
                    representative_term = response.content.strip() if hasattr(response, 'content') else f"Grupo {cluster_id + 1}"
                except Exception as e:
                    logger.error(f"Error al generar término representativo para cluster {cluster_id}: {e}")
                    representative_term = f"Grupo {cluster_id + 1}"
                grouped_topics.append({"topic": representative_term, "mentions": data["mentions"]})

            # Ordenar por menciones descendentes
            simulated_grouped_topics = sorted(grouped_topics, key=lambda x: x["mentions"], reverse=True)[:10]

            # 4. Guardar el resultado y marcar como 'completed'
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload={"grouped_topics": simulated_grouped_topics})
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis semántico para tarea {task_id} completado con {len(simulated_grouped_topics)} grupos de temas.")
            # Aquí se podría enviar una notificación de finalización a través de un WebSocket o similar
        except Exception as e:
            logger.error(f"Fallo en tarea de análisis semántico {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()
            # Aquí se podría enviar una notificación de error a través de un WebSocket o similar
