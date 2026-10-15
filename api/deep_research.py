import logging
import uuid
import asyncio
import re
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Union, Optional
from langchain_core.messages import HumanMessage, AIMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.agents.deep_researcher import compile_deep_researcher_graph
from core.llm_manager import get_main_llm, get_llm_for_user, set_active_account_id
from core.utils.llm_utils import safe_bind_tools  # OpenRouter compatibility
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from skills.document_management_skill.scripts.create_pdf_tool import CreatePDFTool
from utils.security import get_current_account_id, decode_access_token
from core.websocket_manager import manager as websocket_manager


def _resolve_effective_account_id(request: Optional[Request], body_account_id: Optional[str]) -> str:
    """Prioriza el account_id del JWT (modelo configurado en frontend por usuario).

    Antes se usaba solo el account_id del body (por defecto "api_user"),
    lo que hacía que deep_research usara el LLM global (.env) en vez del
    modelo configurado por el usuario.
    """
    if request is not None:
        try:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                payload = decode_access_token(auth[len("Bearer "):].strip())
                sub = (payload or {}).get("sub")
                if sub:
                    if body_account_id and body_account_id not in ("api_user", sub):
                        logger.warning(
                            f"account_id del body ('{body_account_id}') difiere del JWT ('{sub}'). Usando JWT."
                        )
                    return sub
        except Exception as e:
            logger.warning(f"No se pudo resolver account_id desde JWT, usando body: {e}")
    return body_account_id or "api_user"

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for async research jobs. In production, this should be Redis or a Database.
# format: {run_id: {"status": "processing" | "success" | "error" | "clarification_needed", "result": {...}, "error": "..."}}
research_jobs: Dict[str, Any] = {}

# Compilar el grafo una sola vez al iniciar la aplicación
try:
    deep_researcher_graph = compile_deep_researcher_graph()
    logger.info("Deep Researcher graph compiled successfully.")
except Exception as e:
    logger.error(f"Failed to compile Deep Researcher graph: {e}", exc_info=True)
    deep_researcher_graph = None

class DeepResearchRequest(BaseModel):
    query: str
    account_id: str = "api_user"
    workspace_id: Optional[str] = None

class ClarificationResponse(BaseModel):
    run_id: str
    user_response: str
    account_id: str = "api_user"

class DeepResearchPDFExportRequest(BaseModel):
    title: str
    final_report: str
    sources: List[dict] = []
    recommendations: List[str] = []
    workspace_id: Optional[str] = None
    kai_synthesis: Optional[str] = None
    visual_schema: Optional[str] = None
    # account_id se obtiene del token, no del body

async def _run_deep_research_background(run_id: str, inputs: dict, config: dict):
    logger.info(f"Background Task: Invoking Deep Research graph with run_id: {run_id}")
    account_id = inputs.get("account_id") or config.get("configurable", {}).get("account_id")
    thread_id = config.get("configurable", {}).get("thread_id")
    if account_id:
        set_active_account_id(account_id)
        try:
            await get_llm_for_user(account_id, purpose="fast")
            await get_llm_for_user(account_id, purpose="main")
        except Exception as warm_err:
            logger.warning(f"Error pre-warming user LLMs: {warm_err}")

    async def api_progress_callback(progress: int, message: str, current_node: str = "main"):
        if run_id in research_jobs:
            research_jobs[run_id]["progress"] = progress
            research_jobs[run_id]["message"] = message
        if account_id:
            payload = {
                "type": "progress",
                "progress": progress,
                "message": message,
                "current_node": current_node,
                "tool_name": "deep_research",
                "taskId": run_id,
            }
            if thread_id:
                payload["thread_id"] = str(thread_id)
            try:
                await websocket_manager.send_personal_message(payload, account_id)
            except Exception as e:
                logger.warning(f"Error sending ws progress in api_deep_research: {e}")

    config.setdefault("configurable", {})["progress_callback"] = api_progress_callback
    config.setdefault("configurable", {})["base_progress"] = 0
    config.setdefault("configurable", {})["max_sub_progress"] = 100

    try:
        max_retries = 5
        final_state = None
        for attempt in range(max_retries):
            try:
                final_state = await deep_researcher_graph.ainvoke(inputs, config=config)
                break
            except Exception as e:
                error_str = f"{type(e).__name__}: {str(e)} {repr(e)}"
                if ("MidStreamFallbackError" in error_str or "APIError" in error_str or "OpenrouterException" in error_str or "unmapped" in error_str) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"Background Task LLM API Error detected (attempt {attempt + 1}/{max_retries}): {error_str}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise e

        if final_state and "final_report" in final_state:
            if final_state.get("final_report") == "CLARIFICATION":
                logger.info(f"Background Task: Deep research for run_id {run_id} requires clarification.")
                clarification_question = "No clarification question found."
                if final_state.get("messages") and isinstance(final_state["messages"], list):
                    for msg in reversed(final_state["messages"]):
                        if isinstance(msg, AIMessage):
                            clarification_question = msg.content
                            break
                research_jobs[run_id] = {
                    "status": "clarification_needed",
                    "message": clarification_question,
                    "run_id": run_id
                }
            else:
                logger.info(f"Background Task: Deep research completed successfully for run_id: {run_id}")
                final_sources = final_state.get("sources", [])
                if isinstance(final_sources, dict) and final_sources.get("type") == "override":
                    final_sources = final_sources.get("value", [])
                
                # --- SAVE PARALLEL WORD DOC ---
                try:
                    from utils.deep_research_word_saver import save_deep_research_as_word
                    await save_deep_research_as_word(
                        account_id=inputs.get("account_id"),
                        query=inputs.get("messages")[0].content if inputs.get("messages") else "Investigación Profunda",
                        report_text=final_state.get("final_report"),
                        workspace_id=inputs.get("workspace_id")
                    )
                except Exception as save_err:
                    logger.error(f"Error saving deep research Word document in background task: {save_err}", exc_info=True)
                
                research_jobs[run_id] = {
                    "status": "success",
                    "report": {
                        "final_report": final_state.get("final_report"),
                        "summary": final_state.get("summary", ""),
                        "findings": final_state.get("findings", ""),
                        "recommendations": final_state.get("recommendations", []),
                        "sources": final_sources,
                        "visual_schema": final_state.get("visual_schema")
                    }
                }
        else:
            logger.error(f"Background Task: Deep research for run_id {run_id} finished without a final report.")
            research_jobs[run_id] = {"status": "error", "detail": "The deep research process finished, but no final report was generated."}

    except Exception as e:
        logger.error(f"Background Task: Error in deep research run_id {run_id}: {e}", exc_info=True)
        research_jobs[run_id] = {"status": "error", "detail": str(e)}

@router.post("/deep_research/async")
async def run_deep_research_async(
    request: DeepResearchRequest,
    background_tasks: BackgroundTasks,
    http_request: Request = None,
):
    """
    Inicia una investigación profunda en segundo plano y devuelve un run_id inmediatamente.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    effective_account_id = _resolve_effective_account_id(http_request, request.account_id)
    logger.info(f"Received async deep research request for: '{request.query}' by account '{effective_account_id}'")

    run_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "account_id": effective_account_id,
            "thread_id": run_id,
        }
    }
    inputs = {
        "messages": [HumanMessage(content=request.query)],
        "account_id": effective_account_id,
        "workspace_id": request.workspace_id
    }

    # Initialize job state
    research_jobs[run_id] = {"status": "processing"}

    # Add to background tasks
    background_tasks.add_task(_run_deep_research_background, run_id, inputs, config)

    return {"status": "processing", "run_id": run_id, "message": "Investigación profunda iniciada en segundo plano."}

@router.get("/deep_research/status/{run_id}")
async def get_deep_research_status(run_id: str):
    """
    Consulta el estado de una investigación profunda asíncrona.
    """
    job = research_jobs.get(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"run_id": run_id, **job}

@router.post("/deep_research/")
async def run_deep_research(
    request: DeepResearchRequest,
    http_request: Request = None,
):
    """
    Ejecuta una investigación profunda sobre una consulta dada utilizando el agente LangGraph.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    effective_account_id = _resolve_effective_account_id(http_request, request.account_id)
    if effective_account_id:
        set_active_account_id(effective_account_id)
        try:
            await get_llm_for_user(effective_account_id, purpose="fast")
            await get_llm_for_user(effective_account_id, purpose="main")
        except Exception as warm_err:
            logger.warning(f"Error pre-warming user LLMs: {warm_err}")
    logger.info(f"Received deep research request for: '{request.query}' by account '{effective_account_id}'")
    
    try:
        # Configuración para el grafo
        run_id = str(uuid.uuid4())
        
        async def api_progress_callback(progress: int, message: str, current_node: str = "main"):
            if run_id in research_jobs:
                research_jobs[run_id]["progress"] = progress
                research_jobs[run_id]["message"] = message
            if effective_account_id:
                payload = {
                    "type": "progress",
                    "progress": progress,
                    "message": message,
                    "current_node": current_node,
                    "tool_name": "deep_research",
                    "taskId": run_id,
                }
                if run_id:
                    payload["thread_id"] = str(run_id)
                try:
                    await websocket_manager.send_personal_message(payload, effective_account_id)
                except Exception as e:
                    logger.warning(f"Error sending ws progress in run_deep_research: {e}")

        config = {
            "configurable": {
                "account_id": effective_account_id,
                "thread_id": run_id,
                "progress_callback": api_progress_callback,
                "base_progress": 0,
                "max_sub_progress": 100,
            }
        }

        # Entradas para el grafo
        inputs = {
            "messages": [HumanMessage(content=request.query)],
            "account_id": effective_account_id
        }

        logger.info(f"Invoking Deep Research graph with run_id: {run_id}")
        
        # Implementación de reintentos para manejar MidStreamFallbackError y otros errores de API
        max_retries = 5
        for attempt in range(max_retries):
            try:
                final_state = await deep_researcher_graph.ainvoke(inputs, config=config)
                break # Éxito, salir del loop de reintentos
            except Exception as e:
                error_str = f"{type(e).__name__}: {str(e)} {repr(e)}"
                if ("MidStreamFallbackError" in error_str or "APIError" in error_str or "OpenrouterException" in error_str or "unmapped" in error_str) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"LLM API Error detected (attempt {attempt + 1}/{max_retries}): {error_str}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise e

        if final_state and "final_report" in final_state:
            # Manejar el caso de clarificación
            if final_state.get("final_report") == "CLARIFICATION":
                logger.info(f"Deep research for run_id {run_id} requires clarification.")
                clarification_question = "No clarification question found."
                # Asegurarse de que messages sea una lista y no esté vacío
                if final_state.get("messages") and isinstance(final_state["messages"], list):
                    # Buscar el último mensaje que sea AIMessage (la pregunta del LLM)
                    for msg in reversed(final_state["messages"]):
                        if isinstance(msg, AIMessage):
                            clarification_question = msg.content
                            break
                return {"status": "clarification_needed", "message": clarification_question, "run_id": run_id}
            
            logger.info(f"Deep research completed successfully for run_id: {run_id}")
            
            # --- SAVE PARALLEL WORD DOC ---
            try:
                from utils.deep_research_word_saver import save_deep_research_as_word
                await save_deep_research_as_word(
                    account_id=effective_account_id,
                    query=request.query,
                    report_text=final_state.get("final_report"),
                    workspace_id=request.workspace_id
                )
            except Exception as save_err:
                logger.error(f"Error saving deep research Word document: {save_err}", exc_info=True)

             # Deserializar formato de "override" para fuentes
            final_sources = final_state.get("sources", [])
            if isinstance(final_sources, dict) and final_sources.get("type") == "override":
                final_sources = final_sources.get("value", [])
            
            return {
                "status": "success", 
                "report": {
                    "final_report": final_state.get("final_report"),
                    "summary": final_state.get("summary", ""),
                    "findings": final_state.get("findings", ""),
                    "recommendations": final_state.get("recommendations", []),
                    "sources": final_sources,
                    "visual_schema": final_state.get("visual_schema")
                }
            }
        else:
            logger.error(f"Deep research for run_id {run_id} finished without a final report.")
            return {"status": "error", "detail": "The deep research process finished, but no final report was generated."}

    except Exception as e:
        logger.error(f"Error in /deep_research/ endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@router.post("/deep_research/clarify")
async def clarify_deep_research(
    request: ClarificationResponse,
    http_request: Request = None,
):
    """
    Proporciona una respuesta a una pregunta de clarificación para una investigación profunda en curso.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    effective_account_id = _resolve_effective_account_id(http_request, request.account_id)
    if effective_account_id:
        set_active_account_id(effective_account_id)
        try:
            await get_llm_for_user(effective_account_id, purpose="fast")
            await get_llm_for_user(effective_account_id, purpose="main")
        except Exception as warm_err:
            logger.warning(f"Error pre-warming user LLMs: {warm_err}")
    logger.info(f"Received clarification response for run_id: {request.run_id} with response: '{request.user_response}'")

    try:
        config = {
            "configurable": {
                "account_id": effective_account_id,
                "thread_id": request.run_id,
            }
        }

        # El grafo se reanuda desde el último estado.
        # Añadimos la respuesta del usuario a los mensajes.
        inputs = {
            "messages": [HumanMessage(content=request.user_response)],
            "account_id": effective_account_id
        }

        logger.info(f"Re-invoking Deep Research graph with run_id: {request.run_id} after clarification.")
        
        # Implementación de reintentos para manejar MidStreamFallbackError y otros errores de API
        max_retries = 5
        for attempt in range(max_retries):
            try:
                final_state = await deep_researcher_graph.ainvoke(inputs, config=config)
                break # Éxito, salir del loop de reintentos
            except Exception as e:
                error_str = f"{type(e).__name__}: {str(e)} {repr(e)}"
                if ("MidStreamFallbackError" in error_str or "APIError" in error_str or "OpenrouterException" in error_str or "unmapped" in error_str) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"LLM API Error detected (attempt {attempt + 1}/{max_retries}): {error_str}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise e

        if final_state and "final_report" in final_state:
            if final_state.get("final_report") == "CLARIFICATION":
                logger.info(f"Deep research for run_id {request.run_id} still requires clarification.")
                clarification_question = "No clarification question found."
                if final_state.get("messages") and isinstance(final_state["messages"], list):
                    for msg in reversed(final_state["messages"]):
                        if isinstance(msg, AIMessage):
                            clarification_question = msg.content
                            break
                return {"status": "clarification_needed", "message": clarification_question, "run_id": request.run_id}
            
            logger.info(f"Deep research completed successfully for run_id: {request.run_id} after clarification.")
            
            # --- SAVE PARALLEL WORD DOC ---
            try:
                original_query = "Investigación Profunda"
                if final_state.get("messages"):
                    original_query = final_state["messages"][0].content
                from utils.deep_research_word_saver import save_deep_research_as_word
                await save_deep_research_as_word(
                    account_id=effective_account_id,
                    query=original_query,
                    report_text=final_state.get("final_report"),
                    workspace_id=None
                )
            except Exception as save_err:
                logger.error(f"Error saving deep research Word document after clarification: {save_err}", exc_info=True)

             # Deserializar formato de "override" para fuentes
            final_sources = final_state.get("sources", [])
            if isinstance(final_sources, dict) and final_sources.get("type") == "override":
                final_sources = final_sources.get("value", [])
            
            return {
                "status": "success", 
                "report": {
                    "final_report": final_state.get("final_report"),
                    "sources": final_sources,
                    "recommendations": final_state.get("recommendations", []),
                    "visual_schema": final_state.get("visual_schema")
                }
            }
        else:
            logger.error(f"Deep research for run_id {request.run_id} finished without a final report after clarification.")
            return {"status": "error", "detail": "The deep research process finished, but no final report was generated after clarification."}

    except Exception as e:
        logger.error(f"Error in /deep_research/clarify endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@router.post("/deep_research/export_pdf")
async def export_deep_research_pdf(
    request: DeepResearchPDFExportRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Genera un PDF profesional con el contenido EXACTO E IDÉNTICO de la investigación profunda
    utilizando CreatePDFTool, garantizando que todo el informe, capítulos, análisis, recomendaciones
    y fuentes se preserven íntegramente (1:1) sin resúmenes, omisiones ni alteraciones por LLM,
    y se guarde en la nube del usuario en Documentos.
    """
    try:
        report_content = request.final_report.strip() if request.final_report else ""
        if not report_content or len(report_content) < 10:
            raise HTTPException(status_code=400, detail="El contenido del informe de investigación está vacío.")

        title = request.title.strip() if request.title else "Informe de Investigación Profunda"

        # Construir el documento con fidelidad 1:1, asegurando que nada sea resumido ni omitido
        parts = []

        # Título principal si no está ya como encabezado al inicio del reporte
        lower_report = report_content.lower()
        has_title_header = report_content.startswith("# ") or f"# {title.lower()}" in lower_report[:200]
        if not has_title_header:
            parts.append(f"# {title}\n")

        # El cuerpo EXACTO e ÍNTEGRO del informe final de la investigación (fidelidad absoluta 1:1)
        parts.append(report_content)

        # Recomendaciones si fueron pasadas y no están ya en el texto del informe
        if request.recommendations and len(request.recommendations) > 0:
            first_rec = request.recommendations[0][:30].strip() if len(request.recommendations) > 0 else ""
            if not first_rec or first_rec.lower() not in lower_report:
                rec_section = "\n\n## Recomendaciones Estratégicas\n\n"
                for r in request.recommendations:
                    rec_section += f"- {r.strip()}\n"
                parts.append(rec_section)

        # Fuentes consultadas si no están ya listadas en el cuerpo del informe
        if request.sources and len(request.sources) > 0:
            if "fuentes consultadas" not in lower_report and "bibliografía" not in lower_report and "referencias de investigación" not in lower_report:
                sources_section = "\n\n## Referencias y Fuentes Consultadas\n\n"
                for idx, s in enumerate(request.sources, 1):
                    source_id = s.get("id", idx)
                    s_title = s.get("title") or s.get("name") or f"Fuente {source_id}"
                    s_url = s.get("url") or s.get("link") or ""
                    s_snippet = s.get("snippet") or s.get("content") or ""
                    
                    if s_url and s_url != "#":
                        sources_section += f"**[{source_id}]** [{s_title}]({s_url})\n\n"
                    else:
                        sources_section += f"**[{source_id}]** {s_title}\n\n"
                    
                    if s_snippet:
                        clean_snippet = s_snippet.replace("\n", " ").strip()
                        if len(clean_snippet) > 300:
                            clean_snippet = clean_snippet[:300] + "..."
                        sources_section += f"> *{clean_snippet}*\n\n"
                parts.append(sources_section)

        # Perspectiva de Inteligencia (KAI) si está disponible y no está ya en el texto
        if request.kai_synthesis and request.kai_synthesis.strip():
            if request.kai_synthesis[:30].lower() not in lower_report:
                kai_section = f"\n\n## Perspectiva de Inteligencia (KAI)\n\n> *{request.kai_synthesis.strip()}*\n"
                parts.append(kai_section)

        full_document = "\n\n".join(parts)

        # Preparar la herramienta CreatePDFTool configurada con el usuario y workspace
        pdf_tool = CreatePDFTool(
            account_id=current_account_id,
            workspace_id=request.workspace_id
        )

        clean_filename = re.sub(r'[^\w\s-]', '', title).strip().replace(" ", "_")
        if not clean_filename:
            clean_filename = "investigacion_profunda"
        filename = f"{clean_filename[:50]}.pdf"

        logger.info(f"Generando PDF idéntico para '{title}' (longitud: {len(full_document)} caracteres)...")

        tool_output = await pdf_tool._arun(
            content=full_document,
            is_html=False,
            title=title,
            filename=filename,
            theme="modern"
        )

        if tool_output and "sources" in tool_output and tool_output["sources"]:
            pdf_source = tool_output["sources"][0]
            metadata = pdf_source.get("metadata", {})
            doc_id = metadata.get("onlyoffice_document_id")
            return {
                "status": "success",
                "url": pdf_source.get("url"),
                "filename": metadata.get("filename", filename),
                "document_id": doc_id,
                "saved_to_documents": bool(doc_id)
            }
        else:
            logger.error(f"Error generando PDF idéntico: {tool_output}")
            raise HTTPException(status_code=500, detail="Error al generar el PDF idéntico.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando PDF idéntico: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar el PDF: {str(e)}")
