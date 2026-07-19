import logging
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Union, Optional
from langchain_core.messages import HumanMessage, AIMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.agents.deep_researcher import compile_deep_researcher_graph
from core.llm_manager import get_main_llm, get_llm_for_user
from core.utils.llm_utils import safe_bind_tools  # OpenRouter compatibility
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage 
from langchain_core.prompts import ChatPromptTemplate
from skills.document_management_skill.scripts.create_pdf_tool import CreatePDFTool 
from utils.security import get_current_account_id

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
    # account_id se obtiene del token, no del body

async def _run_deep_research_background(run_id: str, inputs: dict, config: dict):
    logger.info(f"Background Task: Invoking Deep Research graph with run_id: {run_id}")
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
    background_tasks: BackgroundTasks
):
    """
    Inicia una investigación profunda en segundo plano y devuelve un run_id inmediatamente.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    logger.info(f"Received async deep research request for: '{request.query}' by account '{request.account_id}'")
    
    run_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "account_id": request.account_id,
            "thread_id": run_id,
        }
    }
    inputs = {
        "messages": [HumanMessage(content=request.query)],
        "account_id": request.account_id,
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
    request: DeepResearchRequest
):
    """
    Ejecuta una investigación profunda sobre una consulta dada utilizando el agente LangGraph.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    logger.info(f"Received deep research request for: '{request.query}' by account '{request.account_id}'")
    
    try:
        # Configuración para el grafo
        run_id = str(uuid.uuid4())
        config = {
            "configurable": {
                "account_id": request.account_id,
                "thread_id": run_id,
            }
        }
        
        # Entradas para el grafo
        inputs = {
            "messages": [HumanMessage(content=request.query)],
            "account_id": request.account_id
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
                    account_id=request.account_id,
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
    request: ClarificationResponse
):
    """
    Proporciona una respuesta a una pregunta de clarificación para una investigación profunda en curso.
    """
    if deep_researcher_graph is None:
        raise HTTPException(status_code=500, detail="Deep Researcher agent is not available.")

    logger.info(f"Received clarification response for run_id: {request.run_id} with response: '{request.user_response}'")

    try:
        config = {
            "configurable": {
                "account_id": request.account_id,
                "thread_id": request.run_id,
            }
        }
        
        # El grafo se reanuda desde el último estado.
        # Añadimos la respuesta del usuario a los mensajes.
        inputs = {
            "messages": [HumanMessage(content=request.user_response)],
            "account_id": request.account_id 
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
                    account_id=request.account_id,
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
    Genera un PDF profesional a partir de los resultados de una investigación profunda
    utilizando un LLM para formatear el contenido y la herramienta CreatePDFTool.
    """
    try:
        # 1. Obtener el LLM configurado para el usuario específico
        llm_instance = await get_llm_for_user(current_account_id, purpose="main")
        if not llm_instance:
            logger.error(f"❌ No se pudo obtener LLM para account_id: {current_account_id}")
            raise HTTPException(status_code=500, detail="Could not initialize LLM for your account. Please check your LLM configuration.")

        # Log del modelo en uso
        model_name = getattr(llm_instance, "model_name", getattr(llm_instance, "model", "unknown"))
        logger.info(f"🤖 Export PDF: Using LLM model '{model_name}' for account {current_account_id}")

        # 2. Preparar las herramientas
        pdf_tool = CreatePDFTool()
        
        # 3. Configurar el LLM con la herramienta
        # Usamos bind_tools para que el LLM sepa que puede usar esta herramienta
        llm_with_tools = safe_bind_tools(llm_instance, [pdf_tool])
        
        # 4. Construir el prompt para el LLM
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en diseño y maquetación de documentos profesionales.
Tu tarea es tomar la información de una investigación profunda y formatearla en un documento HTML elegante y bien estructurado.
DEBES usar la herramienta 'create_pdf_tool' para generar el PDF final.

INSTRUCCIONES DE FORMATO HTML:
- Usa etiquetas HTML semánticas (h1, h2, ul, li, p, strong).
- El título del documento ({title}) debe ser un <h1> centrado.
- Incluye una sección 'Resumen Ejecutivo' (h2).
- Si hay 'Hallazgos Clave', inclúyelos en una lista o secciones claras.
- Si hay 'Recomendaciones', úsalas para una sección de 'Próximos Pasos' o 'Recomendaciones'.
- Al final, agrega una sección 'Fuentes Consultadas' (h2) con una lista de enlaces.
- Usa estilos CSS en línea sutiles si es necesario, pero la herramienta ya aplica estilos modernos.
- NO agregues etiquetas <html>, <head> o <body>, solo el contenido del cuerpo (divs, h1, etc.), ya que la herramienta agrega la estructura base.

INSTRUCCIONES DE HERRAMIENTA:
- DEBES llamar a 'create_pdf_tool'.
- Argumento 'is_html': True
- Argumento 'content': Tu código HTML generado.
- Argumento 'title': El título del reporte.
- Argumento 'filename': Un nombre de archivo seguro basado en el título.
"""),
            ("user", """Genera el PDF para este reporte:

Título: {title}

Resumen del Reporte:
{summary}

Recomendaciones:
{recommendations}

Fuentes:
{sources}

Procede a generar el PDF.""")
        ])
        
        # Formatear datos para el prompt
        sources_text = "\n".join([f"- {s.get('title', 'Fuente')}: {s.get('url', '#')}" for s in request.sources])
        recommendations_text = "\n".join([f"- {r}" for r in request.recommendations])
        
        logger.info(f"Invoking LLM to generate PDF for research: {request.title}")
        
        chain = prompt | llm_with_tools
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                result = await chain.ainvoke({
                    "title": request.title,
                    "summary": request.final_report,
                    "recommendations": recommendations_text,
                    "sources": sources_text
                })
                break
            except Exception as e:
                error_str = f"{type(e).__name__}: {str(e)} {repr(e)}"
                if ("MidStreamFallbackError" in error_str or "APIError" in error_str or "OpenrouterException" in error_str or "unmapped" in error_str) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"LLM API Error detected in PDF export (attempt {attempt + 1}/{max_retries}): {error_str}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise e
        
        # 5. Procesar la respuesta (buscar tool call)
        # El resultado será un AIMessage que puede contener tool_calls
        if hasattr(result, 'tool_calls') and result.tool_calls:
            tool_call = result.tool_calls[0] # Tomamos la primera llamada
            if tool_call['name'] == 'create_pdf_tool':
                tool_args = tool_call['args']
                logger.info("LLM decided to call create_pdf_tool. Executing...")
                
                # Ejecutar la herramienta
                tool_output = await pdf_tool._arun(**tool_args)
                
                # create_pdf_tool devuelve un dict con 'context_for_llm' y 'sources'
                # En 'sources' viene el PDF generado con su URL
                
                if tool_output and "sources" in tool_output and tool_output["sources"]:
                    pdf_source = tool_output["sources"][0]
                    return {
                        "status": "success",
                        "url": pdf_source["url"],
                        "filename": pdf_source["metadata"].get("filename", "document.pdf")
                    }
                else:
                     # Fallback: a veces la herramienta falla silenciosamente o devuelve otro formato
                     logger.error(f"Tool executed but returned unexpected format: {tool_output}")
                     raise HTTPException(status_code=500, detail="Tool execution failed to return a PDF URL.")
        
        # Si no hubo llamada a herramienta
        logger.warning("LLM did not call the CreatePDFTool. Result content: " + str(result.content))
        return {"status": "error", "detail": "LLM failed to generate PDF call. It might have just replied with text."}

    except Exception as e:
        logger.error(f"Error generating PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
