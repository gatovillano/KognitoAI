# core/agents/gap_developer.py

import asyncio
import uuid
import json
import logging
from typing import Any, Dict, List, Optional, cast

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from core.llm_manager import get_main_llm, get_fast_llm, get_llm_for_user # Importar get_llm_for_user
from core.utils.llm_utils import safe_bind_tools
from core.utils.date_utils import get_today_str
from core.skill_manager import get_skill_manager

logger = logging.getLogger(__name__)

# --- State Definition ---
from typing import TypedDict, Annotated
import operator

class GapDeveloperState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    account_id: str
    gap_id: str
    context: str
    full_analysis_context: Optional[str] # NUEVO
    research_results: str
    document_id: Optional[str]
    progress: int
    workspace_id: Optional[str]
    sources: Annotated[List[Dict[str, Any]], operator.add] # NUEVO
    visual_schema: Optional[str] # NUEVO

# --- Prompts ---

GAP_ANALYSIS_PROMPT = """Eres un Agente Especialista en Desarrollo de Brechas de Conocimiento. 
Tu objetivo es analizar una brecha de información detectada y proponer una solución estructurada.

Brecha a resolver: {gap_id}
Contexto proporcionado: {context}
Análisis detallado de origen: {full_analysis_context}

Instrucciones:
1. Analiza cómo la brecha se relaciona con el contexto actual y el análisis de origen.
2. Identifica qué información específica falta para cerrar esta brecha.
3. Si es necesario, utiliza tus herramientas de búsqueda para encontrar soluciones o marcos de trabajo externos.
4. Genera una propuesta de "Documento Borrador" que articule la solución.

Fecha actual: {date}
"""

DRAFT_WRITER_PROMPT = """Eres un Redactor Experto de Propuestas Técnicas. 
Basándote en la investigación realizada, redacta un documento borrador completo en formato Markdown.

El documento debe incluir:
1. **Título Sugerido** (Debe ser la primera línea del documento, comenzando con '#')
2. **Introducción y Contexto** (Relación de la brecha con el conocimiento actual)
3. **Análisis del Problema** (Por qué esta brecha es crítica)
4. **Propuesta de Solución Detallada** (Desarrollo técnico o conceptual basado en la investigación)
5. **Conclusiones y Recomendaciones**
6. **Bibliografía** (Lista de fuentes consultadas con sus enlaces si están disponibles)
7. **Esquema Visual** (Obligatorio. Utiliza HTML inline y Tailwind para crear una representación visual de la solución, dentro de etiquetas <visual_schema> y </visual_schema>)

INSTRUCCIONES DE CITACIÓN (ESTÁNDAR KOGNITO):
Cuando uses información de las fuentes proporcionadas, SIEMPRE cita la fuente usando el formato [número] al final de la oración o párrafo que use esa información.

Reglas Críticas:
1. Usa SOLO el número entre corchetes (ej. [1]). NUNCA incluyas palabras como "Fuente", "Ref" o "Cita" dentro de los corchetes.
2. Si usas múltiples fuentes, sepáralas así: [1] [2]. NO uses [1, 2].
3. Coloca las citas al final de las oraciones.
4. NO inventes números de citas.
5. Al final del documento, incluye una sección de "Bibliografía" o "Fuentes" que liste las fuentes utilizadas.

Investigación previa y fuentes:
{research_results}

Escribe el documento de forma profesional, clara y accionable. No uses introducciones como "Aquí tienes el borrador", simplemente escribe el contenido del documento en Markdown.
"""

# --- Nodes ---

async def research_node(state: GapDeveloperState, config: RunnableConfig) -> dict:
    logger.info("--- [GapDeveloper] Node: research_node ---")
    progress_callback = config.get("configurable", {}).get("progress_callback")
    
    if progress_callback:
        await progress_callback(20, "Investigando contexto y buscando soluciones externas...", "research")

    account_id = state.get("account_id")
    llm = await get_llm_for_user(account_id, purpose="main")
    
    if not llm:
        logger.warning(f"No se encontró LLM para el usuario {account_id}, usando fallback.")
        llm = get_main_llm()
    
    # Obtener herramientas de búsqueda y notas
    skill_manager = get_skill_manager()
    tools = await skill_manager.load_skills(
        account_id=account_id,
        relevant_categories=["rag_skill", "notes_skill", "document_management_skill", "analysis_and_insights_skill"]
    )
    
    # Filtrar herramientas de búsqueda web específicamente (Tavily o similar)
    search_tools = [t for t in tools if t.name in ["web_search", "deep_research", "web_scraper_tool"]]
    llm_with_tools = safe_bind_tools(llm, search_tools)

    prompt = GAP_ANALYSIS_PROMPT.format(
        gap_id=state["gap_id"],
        context=state["context"],
        full_analysis_context=state.get("full_analysis_context", "No se proporcionó contexto de análisis adicional."),
        date=get_today_str()
    )

    # Realizar investigación inicial
    response = await llm_with_tools.ainvoke([HumanMessage(content=prompt)])
    
    # Por simplicidad en esta versión, si el LLM decide usar herramientas, las ejecutamos linealmente
    # (En una versión más compleja usaríamos un bucle de ReAct)
    research_summary = response.content
    extracted_sources = []
    
    if hasattr(response, "tool_calls") and response.tool_calls:
        # Ejecutar la primera herramienta de búsqueda sugerida
        tool_call = response.tool_calls[0]
        tool_to_use = next((t for t in search_tools if t.name == tool_call["name"]), None)
        if tool_to_use:
            logger.info(f"Ejecutando herramienta de búsqueda: {tool_call['name']}")
            tool_result = await tool_to_use.ainvoke(tool_call["args"])
            
            # Formatear resultados para el LLM y extraer fuentes estructuradas
            if isinstance(tool_result, list):
                formatted_results = "\n\nFUENTES ENCONTRADAS:\n"
                for idx, item in enumerate(tool_result):
                    source_id = idx + 1
                    title = item.get("title") or item.get("name") or "Fuente externa"
                    url = item.get("url") or item.get("link") or ""
                    snippet = item.get("snippet") or item.get("content") or ""
                    
                    formatted_results += f"[{source_id}] TÍTULO: {title}\nURL: {url}\nCONTENIDO: {snippet}\n\n"
                    
                    if url:
                        extracted_sources.append({
                            "id": source_id,
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "type": "web"
                        })
                research_summary += formatted_results
            elif isinstance(tool_result, dict):
                # Caso: DeepResearchTool devuelve un dict con 'context_for_llm' y 'sources'
                context = tool_result.get("context_for_llm") or str(tool_result)
                research_summary += f"\n\nResultados de investigación externa:\n{context}"
                
                tool_sources = tool_result.get("sources", [])
                if isinstance(tool_sources, list):
                    for idx, s in enumerate(tool_sources):
                        # Evitar duplicados de IDs si ya había fuentes (aunque en este nodo es el primer tool_call)
                        source_id = len(extracted_sources) + 1
                        
                        source_data = s if isinstance(s, dict) else (s.model_dump() if hasattr(s, 'model_dump') else {})
                        
                        title = source_data.get("title") or "Fuente externa"
                        url = source_data.get("url") or ""
                        snippet = source_data.get("snippet") or ""
                        
                        extracted_sources.append({
                            "id": source_id,
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "type": source_data.get("type", "web")
                        })
                        
                        # Añadir al research_summary para que el redactor vea los IDs y el contenido
                        research_summary += f"\n[{source_id}] TÍTULO: {title}\nURL: {url}\nCONTENIDO: {snippet}\n"
            elif isinstance(tool_result, str):
                research_summary += f"\n\nResultados de investigación externa:\n{tool_result}"
            else:
                research_summary += f"\n\nResultados de investigación externa:\n{str(tool_result)}"

    return {"research_results": research_summary, "progress": 50, "sources": extracted_sources}

async def draft_writer_node(state: GapDeveloperState, config: RunnableConfig) -> dict:
    logger.info("--- [GapDeveloper] Node: draft_writer_node ---")
    progress_callback = config.get("configurable", {}).get("progress_callback")
    
    if progress_callback:
        await progress_callback(60, "Redactando el documento borrador detallado...", "writing")

    account_id = state.get("account_id")
    llm = await get_llm_for_user(account_id, purpose="main")
    
    if not llm:
        llm = get_main_llm()
    
    prompt = DRAFT_WRITER_PROMPT.format(
        research_results=state["research_results"]
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    draft_content = response.content
    
    import re
    visual_schema = ""
    schema_match = re.search(r"<visual_schema>(.*?)</visual_schema>", draft_content, re.DOTALL | re.IGNORECASE)
    if schema_match:
        visual_schema = schema_match.group(1).strip()
        draft_content = re.sub(r"<visual_schema>.*?</visual_schema>", "", draft_content, flags=re.DOTALL | re.IGNORECASE).strip()
    else:
        fallback_match = re.search(r"(<div style=.*?>.*?</div>)", draft_content, re.DOTALL | re.IGNORECASE)
        if fallback_match:
            visual_schema = fallback_match.group(1).strip()
            
    response.content = draft_content
    
    return {"messages": [response], "progress": 80, "visual_schema": visual_schema if visual_schema else None}

async def persistence_node(state: GapDeveloperState, config: RunnableConfig) -> dict:
    logger.info("--- [GapDeveloper] Node: persistence_node ---")
    progress_callback = config.get("configurable", {}).get("progress_callback")
    
    if progress_callback:
        await progress_callback(90, "Guardando documento en el sistema de notas...", "persistence")

    account_id = state.get("account_id")
    draft_content = state["messages"][-1].content if state["messages"] else "Sin contenido"
    
    # Obtener herramienta add_note
    skill_manager = get_skill_manager()
    tools = await skill_manager.load_skills(
        account_id=account_id,
        relevant_categories=["notes_skill"]
    )
    add_note_tool = next((t for t in tools if t.name == "add_note"), None)
    
    doc_id = None
    if add_note_tool:
        extracted_title = None
        for line in str(draft_content).split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                extracted_title = line.lstrip('#').strip()
                break
            if "título" in line.lower() and ":" in line:
                extracted_title = line.split(":", 1)[1].strip()
                break
                
        if extracted_title:
            extracted_title = extracted_title.replace("**", "").replace("*", "").strip()
            title = extracted_title
            if len(title) > 100:
                title = title[:97] + "..."
        else:
            title = f"Borrador: Solución a Brecha - {state['gap_id'][:50]}"

        # Limpiar posibles comillas de Markdown si el LLM las puso
        clean_content = str(draft_content).replace("```markdown", "").replace("```", "").strip()
        
        try:
            result = await add_note_tool.ainvoke({
                "title": title,
                "content": clean_content,
                "workspace_id": state.get("workspace_id")
            })
            # El resultado suele ser un JSON con el ID de la nota
            if isinstance(result, str):
                try:
                    res_data = json.loads(result)
                    doc_id = str(res_data.get("id"))
                except:
                    doc_id = "created_successfully"
            elif isinstance(result, dict):
                doc_id = str(result.get("id"))
                
            logger.info(f"Nota de borrador creada con ID: {doc_id}")
        except Exception as e:
            logger.error(f"Error al guardar la nota: {e}")
            doc_id = f"error: {str(e)}"
    
    if progress_callback:
        await progress_callback(100, "Documento borrador desarrollado con éxito.", "complete")

    return {"document_id": doc_id, "progress": 100}

# --- Graph Assembly ---

def compile_gap_developer_graph():
    workflow = StateGraph(GapDeveloperState)
    
    workflow.add_node("research", research_node)
    workflow.add_node("writer", draft_writer_node)
    workflow.add_node("persistence", persistence_node)
    
    workflow.add_edge(START, "research")
    workflow.add_edge("research", "writer")
    workflow.add_edge("writer", "persistence")
    workflow.add_edge("persistence", END)
    
    return workflow.compile()
