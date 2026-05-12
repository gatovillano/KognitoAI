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
from core.agents.gap_developer import compile_gap_developer_graph
from core.llm_manager import get_main_llm
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import HumanMessage
from utils.security import get_current_account_id
from core.websocket_manager import send_personal_message

logger = logging.getLogger(__name__)

router = APIRouter()

# Compilar los grafos al iniciar
try:
    deep_researcher_graph = compile_deep_researcher_graph()
    gap_developer_graph = compile_gap_developer_graph()
    logger.info("Deep Researcher and Gap Developer graphs compiled successfully.")
except Exception as e:
    logger.error(f"Failed to compile graphs for gap development: {e}", exc_info=True)
    deep_researcher_graph = None
    gap_developer_graph = None

class GapDevelopmentRequest(BaseModel):
    gap_id: str
    context: Optional[str] = None
    depth: Optional[int] = 3
    mode: Optional[str] = "research"
    workspace_id: Optional[str] = None
    parent_analysis_id: Optional[str] = None  # ID del análisis original que originó la brecha

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
    depth: int = 3,
    mode: str = "research",
    workspace_id: Optional[str] = None,
    parent_analysis_id: Optional[str] = None
):
    """
    Ejecuta el análisis de desarrollo de brecha o la redacción del borrador.
    """
    logger.info(f"Starting gap development ({mode}) for gap_id: {gap_id}, account: {account_id}")
    
    try:
        # Consulta para el agente
        research_query = context if context else f"Investigar brecha: {gap_id}"
        
        # Callback de progreso
        async def send_progress_update(progress: int, message: str, current_node: str = "main", data: Optional[dict] = None):
            payload = {
                "type": "gap_development_update",
                "status": "processing",
                "analysis_id": analysis_id,
                "gap_id": gap_id,
                "progress": progress,
                "message": message,
                "current_node": current_node,
                "mode": mode
            }
            if data:
                payload.update(data)
                
            await send_personal_message(
                account_id,
                payload
            )

        # SELECCIÓN DEL AGENTE SEGÚN EL MODO
        if mode == "draft":
            if gap_developer_graph is None:
                raise ValueError("Gap Developer agent is not available.")
            
            await send_progress_update(5, "Iniciando redacción de borrador...", "init")
            
            # Recuperar el análisis padre si se proporcionó un ID
            analysis_context = ""
            if parent_analysis_id:
                try:
                    parent_uuid = uuid.UUID(parent_analysis_id)
                    async for db in get_db_session():
                        # 1. Intentar buscar en GapDevelopmentAnalysis (investigaciones previas)
                        stmt = select(GapDevelopmentAnalysis).where(GapDevelopmentAnalysis.id == parent_uuid)
                        res = await db.execute(stmt)
                        parent = res.scalar_one_or_none()
                        if parent and parent.report:
                            analysis_context = json.dumps(parent.report, ensure_ascii=False, indent=2)
                        
                        # 2. Si no se encontró, intentar buscar en AnalysisTask (análisis de documentos/colecciones)
                        if not analysis_context:
                            stmt = select(AnalysisTask).where(AnalysisTask.id == parent_uuid)
                            res = await db.execute(stmt)
                            parent_task = res.scalar_one_or_none()
                            if parent_task and parent_task.result_payload:
                                analysis_context = json.dumps(parent_task.result_payload, ensure_ascii=False, indent=2)
                                
                    if analysis_context:
                        logger.info(f"Contexto de análisis original recuperado con éxito para parent_id: {parent_analysis_id}")
                except Exception as e:
                    logger.error(f"Error al recuperar análisis padre {parent_analysis_id}: {e}")

            inputs = {
                "gap_id": gap_id,
                "context": research_query,
                "full_analysis_context": analysis_context,
                "account_id": account_id,
                "workspace_id": workspace_id,
                "messages": []
            }
            
            config = {
                "configurable": {
                    "account_id": account_id,
                    "thread_id": analysis_id,
                    "progress_callback": send_progress_update
                }
            }
            
            final_state = await gap_developer_graph.ainvoke(inputs, config=config)
            
            report_data = {
                "summary": "Documento borrador desarrollado.",
                "findings": final_state.get("research_results", ""),
                "final_report": final_state.get("messages", [])[-1].content if final_state.get("messages") else "Error al generar contenido.",
                "document_id": final_state.get("document_id"),
                "sources": final_state.get("sources", []),
                "visual_schema": final_state.get("visual_schema")
            }
        else:
            # Modo investigación profunda (existente)
            if deep_researcher_graph is None:
                raise ValueError("Deep Researcher agent is not available.")
            
            inputs = {"messages": [HumanMessage(content=research_query)], "account_id": account_id}
            config = {"configurable": {"account_id": account_id, "thread_id": analysis_id, "progress_callback": send_progress_update, "base_progress": 0, "max_sub_progress": 100}}
            
            await send_progress_update(1, "Iniciando análisis profundo...", "main_graph_init")
            final_state = await deep_researcher_graph.ainvoke(inputs, config=config)
            
            # (Resto de la lógica de procesamiento para investigación profunda...)
            # [Mantener lógica original para el modo research]
            
            if final_state.get("final_report") == "CLARIFICATION":
                # ... (Lógica de clarificación existente)
                clarification_question = final_state["messages"][-1].content if final_state.get("messages") else "No clarification question found."
                async for db in get_db_session():
                    await db.execute(update(GapDevelopmentAnalysis).where(GapDevelopmentAnalysis.id == analysis_id).values(status="failed", report={"error": "Clarification needed", "question": clarification_question}))
                    await db.commit()
                await send_personal_message(account_id, {"type": "gap_development_update", "status": "failed", "analysis_id": analysis_id, "gap_id": gap_id, "message": "Clarification needed", "error": "Clarification needed", "question": clarification_question})
                return {"status": "failed", "analysis_id": analysis_id}

            final_sources = final_state.get("sources", [])
            if isinstance(final_sources, dict) and final_sources.get("type") == "override":
                final_sources = final_sources.get("value", [])

            report_data = {
                "summary": final_state.get("summary", final_state.get("final_report", "")[:500]),
                "findings": final_state.get("findings", final_state.get("final_report", "")),
                "final_report": final_state.get("final_report", ""),
                "sources": final_sources,
                "recommendations": final_state.get("recommendations", []),
                "visual_schema": final_state.get("visual_schema")
            }

        # FINALIZACIÓN COMÚN
        async for db in get_db_session():
            await db.execute(
                update(GapDevelopmentAnalysis)
                .where(GapDevelopmentAnalysis.id == analysis_id)
                .values(status="completed", report=report_data)
            )
            
            analysis_task = AnalysisTask(
                account_id=uuid.UUID(account_id),
                file_name=f"{'Borrador' if mode == 'draft' else 'Investigación'}: {research_query[:50]}...",
                analysis_type="gap_development",
                status="completed",
                result_payload={"report": report_data, "mode": mode, "document_id": report_data.get("document_id")}
            )
            db.add(analysis_task)
            await db.commit()
        
        await send_personal_message(
            account_id,
            {
                "type": "gap_development_update",
                "status": "completed",
                "analysis_id": analysis_id,
                "gap_id": gap_id,
                "message": "Operación completada con éxito",
                "report": report_data,
                "mode": mode
            }
        )
        return {"status": "completed", "analysis_id": analysis_id, "report": report_data}
    
    except Exception as e:
        logger.error(f"Error in gap development analysis {gap_id}: {e}", exc_info=True)
        # ... (Lógica de error existente)
        async for db in get_db_session():
            await db.execute(update(GapDevelopmentAnalysis).where(GapDevelopmentAnalysis.id == analysis_id).values(status="failed", report={"error": str(e)}))
            await db.commit()
        await send_personal_message(account_id, {"type": "gap_development_update", "status": "failed", "analysis_id": analysis_id, "gap_id": gap_id, "message": "Analysis failed", "error": str(e)})
        return {"status": "failed", "error": str(e)}

@router.post("/gap-development/", response_model=GapDevelopmentStatusResponse)
async def start_gap_development(
    request: GapDevelopmentRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session),
    llm_instance: BaseLanguageModel = Depends(get_llm_instance)
):
    """
    Inicia una investigación profunda o el desarrollo de un borrador sobre una brecha.
    """
    # Obtener la cuenta del usuario
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")
    
    # Validar permisos
    validate_user_role(account)
    
    logger.info(f"Received gap development request ({request.mode}) for gap_id: {request.gap_id} by account {account.id}")
    logger.info(f"--- DEBUG: Request payload mode: {request.mode} ---")
    
    # Validar que gap_id sea un UUID válido, o generar uno determinístico si es texto
    try:
        target_gap_id = uuid.UUID(request.gap_id)
    except ValueError:
        KOGNITO_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        target_gap_id = uuid.uuid5(KOGNITO_NAMESPACE, request.gap_id)

    # Verificar si ya existe un análisis en progreso
    existing_stmt = select(GapDevelopmentAnalysis).where(
        GapDevelopmentAnalysis.gap_id == target_gap_id,
        GapDevelopmentAnalysis.account_id == account.id,
        GapDevelopmentAnalysis.status.in_(["pending", "processing"])
    )
    existing_result = await db.execute(existing_stmt)
    existing_analysis = existing_result.scalars().first()
    
    if existing_analysis:
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
        report={"mode": request.mode}
    )
    db.add(new_analysis)
    await db.commit()
    await db.refresh(new_analysis)
    analysis_id = str(new_analysis.id)
    
    # Iniciar procesamiento asíncrono
    background_tasks.add_task(
        run_gap_development_analysis,
        str(target_gap_id),
        str(account.id),
        analysis_id,
        request.context,
        request.depth or 3,
        request.mode or "research",
        request.workspace_id,
        request.parent_analysis_id
    )
    
    return GapDevelopmentStatusResponse(
        status="pending",
        gap_id=request.gap_id,
        analysis_id=analysis_id,
        message=f"Gap development ({request.mode}) started successfully"
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