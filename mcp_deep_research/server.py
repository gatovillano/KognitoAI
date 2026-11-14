"""
Deep Research MCP (Model Context Protocol) Server.
Expone las capacidades del agente de Deep Research de KognitoAI (api/deep_research.py)
para que cualquier agente externo (Claude Desktop, Cursor, Antigravity, Windsurf, Cline, etc.)
pueda ejecutar investigaciones profundas, consultar su progreso, clarificar dudas
y exportar reportes a PDF.
"""

import os
import sys
import uuid
import json
import logging
import asyncio
import warnings
from typing import Optional, List, Dict, Any

# Suprimir advertencias innecesarias para no interferir con la comunicación
warnings.filterwarnings("ignore")

# Asegurar path raíz del proyecto KognitoAI
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Configurar logger exclusivamente hacia sys.stderr (stdio está reservado para JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("kognito_deep_research_mcp")

# Compatibilidad universal MCP v1 (FastMCP) y MCP v2 (MCPServer)
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError:
        from mcp.server import FastMCP as MCPServer

from langchain_core.messages import HumanMessage, AIMessage

# Configuración por defecto de cuenta KognitoAI
DEFAULT_ACCOUNT_ID = os.environ.get(
    "KOGNITO_ACCOUNT_ID",
    "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6"
)
DEFAULT_WORKSPACE_ID = os.environ.get("KOGNITO_WORKSPACE_ID", None)

# Inicializar servidor MCP
mcp = MCPServer("kognito-deep-research")

# Cargar dependencias de api.deep_research
try:
    from api.deep_research import (
        deep_researcher_graph,
        research_jobs,
        _run_deep_research_background,
        run_deep_research as api_run_deep_research,
        clarify_deep_research as api_clarify_deep_research,
        export_deep_research_pdf as api_export_deep_research_pdf,
        DeepResearchRequest,
        ClarificationResponse,
        DeepResearchPDFExportRequest,
    )
    logger.info("Módulo api.deep_research cargado exitosamente en el servidor MCP.")
except Exception as err:
    logger.error(f"Error al importar api.deep_research: {err}", exc_info=True)
    deep_researcher_graph = None
    research_jobs = {}


# ==============================================================================
# HERRAMIENTAS (TOOLS)
# ==============================================================================

@mcp.tool(
    name="deep_research",
    description=(
        "Ejecuta una investigación profunda, exhaustiva y estructurada sobre cualquier tema o problema complejo. "
        "Utiliza un agente autónomo LangGraph con planificación iterativa, búsqueda web en profundidad, "
        "verificación cruzada de fuentes y síntesis analítica de alto nivel. "
        "Retorna un informe estructurado completo con resumen ejecutivo, hallazgos detallados, "
        "recomendaciones estratégicas y referencias bibliográficas verificadas."
    )
)
async def deep_research(
    query: str,
    account_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    llm_model: Optional[str] = None,
    llm_provider: Optional[str] = None,
    fast_llm_model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Ejecuta una investigación profunda sobre un tema de forma síncrona.
    
    Args:
        query: Tema, pregunta de investigación o problema complejo a investigar a fondo.
        account_id: ID opcional de la cuenta de usuario (por defecto usa la cuenta del cliente activo).
        workspace_id: ID opcional del espacio de trabajo donde asociar la investigación.
        llm_model: Nombre opcional del modelo LLM a utilizar por el cliente (ej: 'openai/gpt-4o', 'gemini-2.5-flash').
        llm_provider: Proveedor opcional del LLM (ej: 'openai', 'gemini', 'openrouter', 'ollama').
        fast_llm_model: Modelo rápido opcional para síntesis y planificación intermedia.
        api_key: Clave API opcional del cliente para el modelo especificado.
        temperature: Temperatura opcional para generación de texto (0.0 a 1.0).
    """
    eff_account_id = account_id or DEFAULT_ACCOUNT_ID
    eff_workspace_id = workspace_id or DEFAULT_WORKSPACE_ID
    
    logger.info(f"MCP deep_research iniciado para consulta: '{query}' (cuenta: {eff_account_id}, modelo: {llm_model or 'auto-cliente'})")
    
    req = DeepResearchRequest(
        query=query,
        account_id=eff_account_id,
        workspace_id=eff_workspace_id,
        llm_model=llm_model,
        llm_provider=llm_provider,
        fast_llm_model=fast_llm_model,
        api_key=api_key,
        temperature=temperature,
    )
    
    try:
        result = await api_run_deep_research(req)
    except Exception as e:
        logger.error(f"Error ejecutando deep_research: {e}", exc_info=True)
        return json.dumps({"status": "error", "detail": str(e)}, ensure_ascii=False, indent=2)
    
    if result.get("status") == "clarification_needed":
        return json.dumps({
            "status": "clarification_needed",
            "run_id": result.get("run_id"),
            "question": result.get("message"),
            "instruction": (
                "El agente de investigación necesita clarificación antes de continuar. "
                "Responde usando la herramienta 'deep_research_clarify' proporcionando este 'run_id' "
                "y tu aclaración en 'user_response'."
            )
        }, ensure_ascii=False, indent=2)
        
    if result.get("status") == "success":
        report_data = result.get("report", {})
        final_report = report_data.get("final_report", "")
        summary = report_data.get("summary", "")
        findings = report_data.get("findings", "")
        recommendations = report_data.get("recommendations", [])
        sources = report_data.get("sources", [])
        visual_schema = report_data.get("visual_schema")
        
        output_parts = []
        if final_report:
            output_parts.append(final_report)
        elif summary or findings:
            if summary:
                output_parts.append(f"## Resumen Ejecutivo\n\n{summary}")
            if findings:
                output_parts.append(f"\n\n## Hallazgos Principales\n\n{findings}")
        
        # Agregar recomendaciones si no están ya embebidas en el reporte
        if recommendations and not any(r.lower() in (final_report or "").lower() for r in recommendations[:2]):
            output_parts.append("\n\n## Recomendaciones Estratégicas\n")
            for r in recommendations:
                output_parts.append(f"- {r}")
                
        # Agregar fuentes verificadas
        if sources:
            output_parts.append("\n\n## Fuentes y Referencias Consultadas\n")
            for idx, s in enumerate(sources, 1):
                s_title = s.get("title") or s.get("name") or f"Fuente {idx}"
                s_url = s.get("url") or s.get("link") or ""
                s_snippet = s.get("snippet") or s.get("content") or ""
                
                if s_url and s_url != "#":
                    output_parts.append(f"**[{idx}]** [{s_title}]({s_url})")
                else:
                    output_parts.append(f"**[{idx}]** {s_title}")
                    
                if s_snippet:
                    clean_snip = s_snippet.replace("\n", " ").strip()
                    if len(clean_snip) > 200:
                        clean_snip = clean_snip[:200] + "..."
                    output_parts.append(f"> *{clean_snip}*\n")
                    
        if visual_schema:
            output_parts.append(f"\n\n## Esquema Visual Sugerido\n```mermaid\n{visual_schema}\n```")
            
        return "\n".join(output_parts)
        
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(
    name="start_deep_research",
    description=(
        "Inicia una investigación profunda en segundo plano y retorna de inmediato un identificador único ('run_id'). "
        "Recomendado para investigaciones muy amplias y clientes MCP con límite de tiempo de espera (timeouts). "
        "Permite monitorear el progreso periódicamente utilizando 'check_deep_research_status'."
    )
)
async def start_deep_research(
    query: str,
    account_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    llm_model: Optional[str] = None,
    llm_provider: Optional[str] = None,
    fast_llm_model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Inicia una investigación profunda asíncrona.
    
    Args:
        query: Tema o pregunta a investigar.
        account_id: ID opcional de la cuenta.
        workspace_id: ID opcional del espacio de trabajo.
        llm_model: Nombre opcional del modelo LLM a utilizar por el cliente.
        llm_provider: Proveedor opcional del LLM.
        fast_llm_model: Modelo rápido opcional para síntesis intermedia.
        api_key: Clave API opcional del cliente.
        temperature: Temperatura opcional para generación de texto.
    """
    if deep_researcher_graph is None:
        return json.dumps({"status": "error", "message": "Deep Researcher graph no está disponible."})
        
    eff_account_id = account_id or DEFAULT_ACCOUNT_ID
    eff_workspace_id = workspace_id or DEFAULT_WORKSPACE_ID
    run_id = str(uuid.uuid4())
    
    client_override = None
    if llm_model or fast_llm_model or api_key:
        client_override = {
            "llm_model": llm_model,
            "llm_provider": llm_provider,
            "fast_llm_model": fast_llm_model,
            "api_key": api_key,
            "temperature": temperature,
        }

    config = {
        "configurable": {
            "account_id": eff_account_id,
            "thread_id": run_id,
            "client_llm_override": client_override,
        }
    }
    inputs = {
        "messages": [HumanMessage(content=query)],
        "account_id": eff_account_id,
        "workspace_id": eff_workspace_id
    }
    
    research_jobs[run_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Iniciando investigación en segundo plano...",
        "query": query
    }
    
    # Iniciar tarea en segundo plano en el bucle de eventos
    asyncio.create_task(_run_deep_research_background(run_id, inputs, config))
    logger.info(f"MCP start_deep_research lanzado con run_id: {run_id}")
    
    return json.dumps({
        "status": "processing",
        "run_id": run_id,
        "query": query,
        "message": "Investigación profunda iniciada en segundo plano.",
        "instruction": "Usa la herramienta 'check_deep_research_status' con este 'run_id' para consultar el progreso y obtener el resultado final."
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="check_deep_research_status",
    description=(
        "Consulta el estado, porcentaje de progreso y resultado de una investigación profunda en segundo plano. "
        "Retorna 'processing' con el progreso actual, 'clarification_needed' si requiere información del usuario, "
        "'success' con el reporte completo una vez finalizado, o 'error' si hubo un fallo."
    )
)
async def check_deep_research_status(run_id: str) -> str:
    """
    Consulta el estado de una investigación asíncrona.
    
    Args:
        run_id: El identificador único obtenido previamente con 'start_deep_research'.
    """
    job = research_jobs.get(run_id)
    if not job:
        return json.dumps({
            "status": "not_found",
            "run_id": run_id,
            "message": f"No se encontró ninguna investigación registrada con run_id '{run_id}'."
        }, ensure_ascii=False, indent=2)
        
    return json.dumps({
        "run_id": run_id,
        **job
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="deep_research_clarify",
    description=(
        "Responde a una solicitud de clarificación formulada por el agente de investigación profunda. "
        "Permite reanudar una investigación que haya quedado pausada en estado 'clarification_needed'."
    )
)
async def deep_research_clarify(
    run_id: str,
    user_response: str,
    account_id: Optional[str] = None,
) -> str:
    """
    Envía la aclaración solicitada para continuar la investigación profunda.
    
    Args:
        run_id: Identificador de la investigación en curso.
        user_response: Respuesta o aclaración proporcionada para orientar la investigación.
        account_id: ID opcional de la cuenta.
    """
    eff_account_id = account_id or DEFAULT_ACCOUNT_ID
    logger.info(f"MCP deep_research_clarify para run_id: {run_id} con respuesta: '{user_response}'")
    
    req = ClarificationResponse(
        run_id=run_id,
        user_response=user_response,
        account_id=eff_account_id
    )
    
    try:
        result = await api_clarify_deep_research(req)
    except Exception as e:
        logger.error(f"Error en deep_research_clarify: {e}", exc_info=True)
        return json.dumps({"status": "error", "detail": str(e)}, ensure_ascii=False, indent=2)
    
    if result.get("status") == "clarification_needed":
        return json.dumps({
            "status": "clarification_needed",
            "run_id": run_id,
            "question": result.get("message"),
            "instruction": "Se requiere aclaración adicional. Vuelve a responder utilizando 'deep_research_clarify'."
        }, ensure_ascii=False, indent=2)
        
    if result.get("status") == "success":
        report_data = result.get("report", {})
        final_report = report_data.get("final_report", "")
        return final_report or json.dumps(result, ensure_ascii=False, indent=2)
        
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(
    name="export_deep_research_pdf",
    description=(
        "Genera un documento PDF profesional con el contenido íntegro y exacto (1:1) del informe "
        "de investigación profunda utilizando CreatePDFTool y lo almacena en la nube de documentos de KognitoAI. "
        "Devuelve la URL y los identificadores del documento generado."
    )
)
async def export_deep_research_pdf(
    title: str,
    final_report: str,
    sources: Optional[List[Dict[str, Any]]] = None,
    recommendations: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
    account_id: Optional[str] = None,
    kai_synthesis: Optional[str] = None,
) -> str:
    """
    Exporta el reporte de investigación profunda a un archivo PDF.
    
    Args:
        title: Título formal para el documento PDF generado.
        final_report: Contenido completo del informe en Markdown.
        sources: Lista opcional de fuentes consultadas (diccionarios con title, url, snippet).
        recommendations: Lista opcional de recomendaciones estratégicas.
        workspace_id: ID opcional del espacio de trabajo.
        account_id: ID opcional de la cuenta.
        kai_synthesis: Síntesis analítica adicional opcional.
    """
    eff_account_id = account_id or DEFAULT_ACCOUNT_ID
    eff_workspace_id = workspace_id or DEFAULT_WORKSPACE_ID
    
    req = DeepResearchPDFExportRequest(
        title=title,
        final_report=final_report,
        sources=sources or [],
        recommendations=recommendations or [],
        workspace_id=eff_workspace_id,
        kai_synthesis=kai_synthesis
    )
    
    try:
        result = await api_export_deep_research_pdf(req, current_account_id=eff_account_id)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error generando PDF de deep research: {e}", exc_info=True)
        return json.dumps({"status": "error", "detail": str(e)}, ensure_ascii=False, indent=2)


# ==============================================================================
# RECURSOS (RESOURCES)
# ==============================================================================

@mcp.resource("deep-research://status")
async def get_system_status() -> str:
    """Retorna el estado operativo y configuración del servicio de Deep Research."""
    return json.dumps({
        "service": "kognito-deep-research",
        "status": "ready" if deep_researcher_graph is not None else "unavailable",
        "active_jobs_count": len(research_jobs),
        "default_account_id": DEFAULT_ACCOUNT_ID,
        "default_workspace_id": DEFAULT_WORKSPACE_ID,
        "available_tools": [
            "deep_research",
            "start_deep_research",
            "check_deep_research_status",
            "deep_research_clarify",
            "export_deep_research_pdf"
        ]
    }, ensure_ascii=False, indent=2)


@mcp.resource("deep-research://jobs")
async def list_research_jobs() -> str:
    """Retorna un resumen de las investigaciones recientes y su estado."""
    jobs_summary = {
        run_id: {
            "status": data.get("status"),
            "progress": data.get("progress", 0),
            "message": data.get("message", ""),
            "has_report": "report" in data or "final_report" in data
        }
        for run_id, data in research_jobs.items()
    }
    return json.dumps(jobs_summary, ensure_ascii=False, indent=2)


# ==============================================================================
# PROMPTS
# ==============================================================================

@mcp.prompt("deep-research-analyst")
def deep_research_analyst_prompt(topic: str) -> str:
    """Prompt guiado para formular investigaciones profundas exhaustivas y estructuradas."""
    return (
        f"Eres un analista de investigación senior de KognitoAI. "
        f"Tu objetivo es realizar una investigación exhaustiva, crítica y fundamentada sobre el tema:\n\n"
        f"'{topic}'\n\n"
        "Directrices de ejecución:\n"
        "1. Ejecuta la herramienta 'deep_research' con una formulación clara y rigurosa del problema.\n"
        "   (Si la tarea es excepcionalmente larga o propensa a tiempos de espera, utiliza 'start_deep_research' y monitorea con 'check_deep_research_status').\n"
        "2. Si el agente solicita información adicional ('clarification_needed'), aclara el alcance con 'deep_research_clarify'.\n"
        "3. Presenta los hallazgos en formato ejecutivo, destacando:\n"
        "   - Resumen Ejecutivo de alto impacto.\n"
        "   - Análisis profundo por dimensiones o ejes temáticos.\n"
        "   - Recomendaciones estratégicas y accionables.\n"
        "   - Citas precisas y referencias verificadas.\n"
        "4. Si el usuario lo solicita, genera un informe en PDF con 'export_deep_research_pdf'."
    )


# ==============================================================================
# ENTRADA PRINCIPAL / RUNNER
# ==============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="KognitoAI Deep Research MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Protocolo de transporte MCP (por defecto: stdio)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host para transporte de red SSE / HTTP (por defecto: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto para transporte de red SSE / HTTP (por defecto: 8000)"
    )
    args = parser.parse_args()

    logger.info(f"Iniciando KognitoAI Deep Research MCP Server (transporte: {args.transport})...")
    
    if hasattr(mcp, "settings"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        try:
            mcp.run(transport="sse", host=args.host, port=args.port)
        except TypeError:
            mcp.run(transport="sse")
    elif args.transport == "streamable-http":
        try:
            mcp.run(transport="streamable-http", host=args.host, port=args.port)
        except TypeError:
            mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
