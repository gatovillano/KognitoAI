# api/gap_development.py

import logging
import uuid
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from core.database import GapDevelopmentAnalysis, get_db_session, Account, AnalysisTask
from core.agents.deep_researcher import compile_deep_researcher_graph
from core.llm_manager import get_main_llm
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import HumanMessage
from utils.security import get_current_account_id
from core.websocket_manager import send_personal_message

logger = logging.getLogger(__name__)

router = APIRouter()

# Compilar el grafo una sola vez al iniciar la aplicación
try:
    deep_researcher_graph = compile_deep_researcher_graph()
    logger.info("Deep Researcher graph compiled successfully for gap development.")
except Exception as e:
    logger.error(f"Failed to compile Deep Researcher graph for gap development: {e}", exc_info=True)
    deep_researcher_graph = None

class GapDevelopmentRequest(BaseModel):
    gap_id: str
    context: Optional[str] = None
    depth: Optional[int] = 3

class GapDevelopmentStatusResponse(BaseModel):
    status: str
    gap_id: str
    analysis_id: Optional[str] = None
    message: Optional[str] = None

class GapDevelopmentResultResponse(BaseModel):
    status: str
    gap_id: str
    analysis_id: str
    report: Optional[dict] = None
    error: Optional[str] = None

async def get_llm_instance() -> BaseLanguageModel:
    llm = get_main_llm()
    if not llm:
        raise HTTPException(status_code=500, detail="LLM not initialized. Please contact administrator.")
    return llm

def validate_user_role(account: Account):
    """Validar que el usuario tenga permisos para usar esta funcionalidad."""
    if not account.is_admin and not getattr(account, 'is_analyst', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with 'analyst' or 'admin' roles can use this feature."
        )

async def run_gap_development_analysis(
    gap_id: str,
    account_id: str,
    analysis_id: str,
    context: Optional[str] = None,
    depth: int = 3
):
    """
    Ejecuta el análisis de desarrollo de brecha de manera asíncrona.
    Esta función simula el procesamiento asíncrono que luego se implementará con Celery.
    """
    logger.info(f"Starting gap development analysis for gap_id: {gap_id}, account: {account_id}")
    
    # El registro ya fue creado por el endpoint que inició la tarea
    logger.info(f"Starting gap development analysis for gap_id: {gap_id}, account: {account_id}, analysis_id: {analysis_id}")
    
    try:
        # Simular procesamiento (en producción, esto sería una tarea Celery)
        logger.info(f"Analysis {analysis_id} created. Starting deep research...")
        
        # Construir la consulta para el agente
        research_query = context if context else f"Investigate knowledge gap with ID: {gap_id}"
        
        # Definir el callback de progreso
        async def send_progress_update(progress: int, message: str, current_node: str = "main"):
            logger.info(f"Sending progress update: {progress}% - {message} (Node: {current_node}) for analysis_id: {analysis_id}")
            message_data = {
                "type": "gap_development_update",
                "status": "processing",
                "analysis_id": analysis_id,
                "gap_id": gap_id,
                "progress": progress,
                "message": message,
                "current_node": current_node,
            }
            logger.info(f"WebSocket message payload: {json.dumps(message_data, indent=2)}")
            await send_personal_message(
                account_id,
                message_data
            )

        # Ejecutar el agente deep_researcher
        if deep_researcher_graph is None:
            raise ValueError("Deep Researcher agent is not available.")
        
        inputs = {
            "messages": [HumanMessage(content=research_query)],
            "account_id": account_id
        }
        
        config = {
            "configurable": {
                "account_id": account_id,
                "thread_id": analysis_id,
                "progress_callback": send_progress_update,
                "base_progress": 0,  # Progreso base para el grafo principal
                "max_sub_progress": 100, # Rango total de progreso para el grafo principal
            }
        }
        
        await send_progress_update(1, "Iniciando análisis profundo...", "main_graph_init")
        logger.info(f"Initial progress update sent for analysis_id: {analysis_id}")
        
        final_state = await deep_researcher_graph.ainvoke(inputs, config=config)
        
        # Procesar los resultados
        if final_state and "final_report" in final_state:
            if final_state.get("final_report") == "CLARIFICATION":
                clarification_question = "No clarification question found."
                if final_state.get("messages"):
                    clarification_question = final_state["messages"][-1].content
                
                # Actualizar estado a failed con mensaje de clarificación
                async for db in get_db_session():
                    await db.execute(
                        update(GapDevelopmentAnalysis)
                        .where(GapDevelopmentAnalysis.id == analysis_id)
                        .values(
                            status="failed",
                            report={"error": "Clarification needed", "question": clarification_question}
                        )
                    )
                    await db.commit()
                
                logger.warning(f"Gap development analysis {analysis_id} requires clarification.")
                
                # Notificar al frontend mediante WebSocket
                await send_personal_message(
                    account_id,
                    {
                        "type": "gap_development_update",
                        "status": "failed",
                        "analysis_id": analysis_id,
                        "gap_id": gap_id,
                        "message": "Clarification needed",
                        "error": "Clarification needed",
                        "question": clarification_question
                    }
                )
                
                return {
                    "status": "failed",
                    "analysis_id": analysis_id,
                    "error": "Clarification needed",
                    "question": clarification_question
                }
            
             # Estructurar el informe según el formato requerido por el frontend
            # Deserializar formato de "override" para fuentes
            final_sources = final_state.get("sources", [])
            if isinstance(final_sources, dict) and final_sources.get("type") == "override":
                final_sources = final_sources.get("value", [])
            
            report_data = {
                "summary": final_state.get("summary", final_state.get("final_report", "")[:500]),  # Resumen corto para la lista
                "findings": final_state.get("findings", final_state.get("final_report", "")),  # Hallazgos detallados
                "final_report": final_state.get("final_report", ""),  # Texto completo para el componente
                "sources": final_sources,
                "recommendations": final_state.get("recommendations", [])
            }
            
            # Actualizar estado a completed
            async for db in get_db_session():
                await db.execute(
                    update(GapDevelopmentAnalysis)
                    .where(GapDevelopmentAnalysis.id == analysis_id)
                    .values(
                        status="completed",
                        report=report_data
                    )
                )
                
                # --- UNIFICATION: Save to AnalysisTask for Dashboard Visibility ---
                # Create a corresponding AnalysisTask so it shows up in the main analysis list
                analysis_task = AnalysisTask(
                    account_id=uuid.UUID(account_id),
                    file_name=f"Investigación Profunda: {research_query[:50]}...",
                    analysis_type="gap_development",
                    status="completed",
                    result_payload={
                        "report": report_data,
                        "tool_used": "deep_researcher_graph",
                        "analysis_metadata": {
                            "source": "gap_development_endpoint",
                            "gap_id": gap_id,
                            "original_analysis_id": analysis_id,
                            "created_at": datetime.now().isoformat()
                        }
                    }
                )
                db.add(analysis_task)
                
                await db.commit()
            
            logger.info(f"Gap development analysis {analysis_id} completed successfully.")
            
            # Notificar al frontend mediante WebSocket
            await send_personal_message(
                account_id,
                {
                    "type": "gap_development_update",
                    "status": "completed",
                    "analysis_id": analysis_id,
                    "gap_id": gap_id,
                    "message": "Analysis completed successfully",
                    "report": report_data
                }
            )
            
            return {
                "status": "completed",
                "analysis_id": analysis_id,
                "report": report_data
            }
        else:
            error_msg = "The deep research process finished, but no final report was generated."
            logger.error(f"Gap development analysis {analysis_id} failed: {error_msg}")
            
            async for db in get_db_session():
                await db.execute(
                    update(GapDevelopmentAnalysis)
                    .where(GapDevelopmentAnalysis.id == analysis_id)
                    .values(
                        status="failed",
                        report={"error": error_msg}
                    )
                )
                await db.commit()
            
            # Notificar al frontend mediante WebSocket
            await send_personal_message(
                account_id,
                {
                    "type": "gap_development_update",
                    "status": "failed",
                    "analysis_id": analysis_id,
                    "gap_id": gap_id,
                    "message": "Analysis failed",
                    "error": error_msg
                }
            )
            
            return {
                "status": "failed",
                "analysis_id": analysis_id,
                "error": error_msg
            }
    
    except Exception as e:
        logger.error(f"Error in gap development analysis {gap_id}: {e}", exc_info=True)
        
        # Actualizar estado a failed
        async for db in get_db_session():
            await db.execute(
                update(GapDevelopmentAnalysis)
                .where(GapDevelopmentAnalysis.gap_id == gap_id)
                .where(GapDevelopmentAnalysis.account_id == account_id)
                .values(
                    status="failed",
                    report={"error": str(e)}
                )
            )
            await db.commit()
        
        # Notificar al frontend mediante WebSocket
        await send_personal_message(
            account_id,
            {
                "type": "gap_development_update",
                "status": "failed",
                "analysis_id": str(uuid.uuid4()),
                "gap_id": gap_id,
                "message": "Analysis failed with error",
                "error": str(e)
            }
        )
        
        return {
            "status": "failed",
            "analysis_id": str(uuid.uuid4()),
            "error": str(e)
        }

@router.post("/gap-development/", response_model=GapDevelopmentStatusResponse)
async def start_gap_development(
    request: GapDevelopmentRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session),
    llm_instance: BaseLanguageModel = Depends(get_llm_instance)
):
    """
    Inicia una investigación profunda sobre una brecha de conocimiento.
    
    Este endpoint:
    1. Valida los permisos del usuario
    2. Crea un registro inicial en la base de datos
    3. Inicia el procesamiento asíncrono
    4. Devuelve el estado inicial
    """
    # Obtener la cuenta del usuario
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")
    
    # Validar permisos
    validate_user_role(account)
    
    logger.info(f"Received gap development request for gap_id: {request.gap_id} by account {account.id}")
    
    # Validar que gap_id sea un UUID válido, o generar uno determinístico si es texto
    try:
        target_gap_id = uuid.UUID(request.gap_id)
        logger.info(f"Using provided UUID for gap_id: {target_gap_id}")
    except ValueError:
        # Generar un UUID v5 basado en el texto de la pregunta para que sea determinístico
        # Usamos un namespace fijo para Kognito AI
        KOGNITO_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8') # DNS namespace as base
        target_gap_id = uuid.uuid5(KOGNITO_NAMESPACE, request.gap_id)
        logger.info(f"Generated deterministic UUID for text gap_id: {target_gap_id}")

    # Verificar si ya existe un análisis en progreso para esta brecha
    existing_stmt = select(GapDevelopmentAnalysis).where(
        GapDevelopmentAnalysis.gap_id == target_gap_id,
        GapDevelopmentAnalysis.account_id == account.id,
        GapDevelopmentAnalysis.status.in_(["pending", "processing"])
    )
    existing_result = await db.execute(existing_stmt)
    existing_analysis = existing_result.scalars().first()
    
    if existing_analysis:
        logger.warning(f"Existing analysis in progress for gap_id {request.gap_id}")
        return GapDevelopmentStatusResponse(
            status=existing_analysis.status,
            gap_id=request.gap_id,
            analysis_id=str(existing_analysis.id),
            message="Analysis already in progress"
        )
    
    # Crear nuevo análisis
    new_analysis = GapDevelopmentAnalysis(
        gap_id=target_gap_id,
        account_id=account.id,
        status="pending",
        report={}
    )
    db.add(new_analysis)
    await db.commit()
    await db.refresh(new_analysis)
    analysis_id = str(new_analysis.id)
    
    # Iniciar procesamiento asíncrono (en producción, esto sería una tarea Celery)
    background_tasks.add_task(
        run_gap_development_analysis,
        str(target_gap_id),
        str(account.id),
        analysis_id,
        request.context,
        request.depth
    )
    
    logger.info(f"Gap development analysis {analysis_id} started for gap_id: {request.gap_id}")
    
    return GapDevelopmentStatusResponse(
        status="pending",
        gap_id=request.gap_id,
        analysis_id=analysis_id,
        message="Analysis started successfully"
    )

@router.get("/gap-development/{analysis_id}", response_model=GapDevelopmentResultResponse)
async def get_gap_development_status(
    analysis_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene el estado y resultados de un análisis de desarrollo de brecha.
    """
    # Obtener la cuenta del usuario
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")
    
    # Validar permisos
    validate_user_role(account)
    
    logger.info(f"Getting status for gap development analysis {analysis_id}")
    
    stmt = select(GapDevelopmentAnalysis).where(
        GapDevelopmentAnalysis.id == analysis_id,
        GapDevelopmentAnalysis.account_id == account.id
    )
    result = await db.execute(stmt)
    analysis = result.scalars().first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found or you don't have permission to access it"
        )
    
    return GapDevelopmentResultResponse(
        status=analysis.status,
        gap_id=str(analysis.gap_id),
        analysis_id=str(analysis.id),
        report=analysis.report if analysis.status == "completed" else None,
        error=analysis.report.get("error") if analysis.status == "failed" else None
    )

@router.get("/gap-development/by-gap/{gap_id}", response_model=GapDevelopmentResultResponse)
async def get_gap_development_by_gap_id(
    gap_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene el análisis más reciente para una brecha específica.
    """
    # Obtener la cuenta del usuario
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")
    
    # Validar permisos
    validate_user_role(account)
    
    logger.info(f"Getting latest analysis for gap_id {gap_id}")
    
    # Validar que gap_id sea un UUID válido, o generar uno determinístico si es texto
    try:
        target_gap_id = uuid.UUID(gap_id)
    except ValueError:
        KOGNITO_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        target_gap_id = uuid.uuid5(KOGNITO_NAMESPACE, gap_id)

    stmt = select(GapDevelopmentAnalysis).where(
        GapDevelopmentAnalysis.gap_id == target_gap_id,
        GapDevelopmentAnalysis.account_id == account.id
    ).order_by(GapDevelopmentAnalysis.created_at.desc()).limit(1)
    
    result = await db.execute(stmt)
    analysis = result.scalars().first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis found for this gap_id"
        )
    
    return GapDevelopmentResultResponse(
        status=analysis.status,
        gap_id=str(analysis.gap_id),
        analysis_id=str(analysis.id),
        report=analysis.report if analysis.status == "completed" else None,
        error=analysis.report.get("error") if analysis.status == "failed" else None
    )