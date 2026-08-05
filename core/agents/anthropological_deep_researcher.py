"""
core/agents/anthropological_deep_researcher.py

Grafo de Investigación Antropológica y Cualitativa Profunda (LangGraph).
Fork de `deep_researcher.py` que integra:
1. Marco Teórico (extraído de archivos/notas de contexto seleccionados).
2. `deepen_theoretical_framework` (bool): Si es True, el supervisor y los investigadores dedican unidades de investigación a profundizar/expandir los conceptos del marco teórico antes/durante la investigación empírica.
3. Pregunta de Investigación e Hipótesis opcionales.
4. Integración con `AnthropologicalGraphProcessor` para codificación exhaustiva 1:1 (Cita -> Código Atómico) y jerarquización en Categorías.
"""

import asyncio
import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict, cast

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig, Runnable
from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.pregel import Pregel

from core.llm_manager import (
    get_main_llm,
    get_fast_llm,
    get_fallback_llm,
    get_llm_for_user,
)
from core.utils.llm_utils import (
    safe_bind_tools,
    is_token_limit_exceeded,
    prune_messages_to_fit_token_limit,
    invoke_structured_output,
)
from core.utils.date_utils import get_today_str
from core.agents.deep_researcher_config import Configuration
from core.agents.deep_researcher_state import (
    AgentState,
    SupervisorState,
    ResearcherState,
    ConductResearch,
    CreateExpertAgent,
    ResearchComplete,
    ResearchQuestion,
)
from core.agents.deep_researcher_utils import (
    get_all_tools,
    deep_research_think_tool,
    execute_tool_safely,
    generate_stable_id,
)
from knowledge_graph.anthropological_graph_processor import AnthropologicalGraphProcessor

logger = logging.getLogger(__name__)


# --- Estados Extendidos para Investigación Antropológica ---

class AnthropologicalAgentState(TypedDict, total=False):
    messages: List[BaseMessage]
    account_id: Optional[str]
    research_brief: str
    notes: List[str]
    raw_notes: List[str]
    sources: List[dict]
    final_report: Optional[str]
    clarification_attempts: int
    supervisor_messages: List[BaseMessage]
    research_iterations: int

    # Parámetros Antropológicos
    theoretical_framework_content: str
    ethnographic_material_content: Optional[str]  # Material etnográfico de corpus
    deepen_theoretical_framework: bool
    research_question: Optional[str]
    hypothesis: Optional[str]
    active_theoretical_framework: Optional[str]
    graph_result: Optional[dict]


# --- Prompts Especializados para Antropología / Cualitativo ---

ANTHROPOLOGICAL_BRIEF_PROMPT = """Eres un metodólogo y etnógrafo cualitativo experto.
Tu función es convertir la solicitud de investigación y los insumos conceptuales en un Resumen de Investigación Antropológica estructurado.

Insumos del Proyecto:
- Marco Teórico Inicial: {theoretical_framework}
- Material Etnográfico (Corpus): {ethnographic_material}
- Pregunta de Investigación: {research_question}
- Hipótesis de Trabajo: {hypothesis}
- Profundizar Marco Teórico: {deepen_theoretical_framework}

Mensajes / Contexto:
{messages}

Genera un Resumen de Investigación Claro y Exhaustivo que defina los objetivos de campo, las categorías emic/etic a indagar y la estrategia de análisis cualitativo.
"""

ANTHROPOLOGICAL_SUPERVISOR_PROMPT = """Eres el Investigador Principal (Supervisor Antropológico).
Tu objetivo es planificar e iterar la investigación antropológica sobre el corpus y las fuentes de datos.

MARCO TEÓRICO DE LENTE ANALÍTICO:
{theoretical_framework}

PREGUNTA DE INVESTIGACIÓN: {research_question}
HIPÓTESIS: {hypothesis}
PROFUNDIZAR MARCO TEÓRICO: {deepen_theoretical_framework}

INSTRUCCIONES:
1. Si 'Profundizar Marco Teórico' es verdadero y aún no se ha indagado en los conceptos teóricos fundamentales, delega una unidad de investigación a indagar y descomponer teóricamente dichos conceptos.
2. Planea sub-temas de investigación para levantar datos empíricos y evidencia cualitativa.
3. Utiliza la herramienta ConductResearch o CreateExpertAgent para delegar tareas a los investigadores.
4. Cuando hayas cubierto el marco teórico y la evidencia empírica suficiente, llama a ResearchComplete.
"""

ANTHROPOLOGICAL_FINAL_REPORT_PROMPT = """Eres un destacado antropólogo y analista cualitativo. Redacta un Informe Final de Investigación Etnográfica completo en Markdown.

Resumen de Investigación: {research_brief}
Marco Teórico Aplicado: {theoretical_framework}
Pregunta de Investigación: {research_question}
Hipótesis de Trabajo: {hypothesis}

Hallazgos e Información Recopilada:
{findings}

ESTRUCTURA EXIGIDA DEL INFORME:
# Informe de Investigación Antropológica y Cualitativa

## 1. Resumen Ejecutivo
## 2. Marco Teórico y Lente Analítico
## 3. Metodología de Codificación y Análisis
## 4. Hallazgos Cualitativos por Categorías (con citas textuales y códigos 1:N)
## 5. Triangulación y Discusión Teórica (Pregunta de Investigación e Hipótesis)
## 6. Conclusiones y Matriz Sintética de Codificación (1:N)
"""


# --- Nodos del Grafo Antropológico ---

async def write_anthropological_brief(state: AnthropologicalAgentState, config: RunnableConfig) -> dict:
    """Genera el resumen de investigación antropológica guiado por el marco teórico."""
    logger.debug("--- [AnthropologicalDeepResearcher] Node: write_anthropological_brief ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")

    if progress_callback:
        await progress_callback(10, "Formulando resumen de investigación antropológica...", "write_anthropological_brief")

    account_id = state.get("account_id")
    if account_id:
        fast_llm = await get_llm_for_user(account_id, purpose="fast")
        main_llm = await get_llm_for_user(account_id, purpose="main")
    else:
        fast_llm = get_fast_llm()
        main_llm = get_main_llm()

    target_llm = fast_llm or main_llm
    if not target_llm:
        raise ValueError("LLM no inicializado.")

    tf_content = state.get("theoretical_framework_content", "No especificado")
    ethno_material = state.get("ethnographic_material_content") or "No especificado"
    rq = state.get("research_question", "No especificada")
    hyp = state.get("hypothesis", "No especificada")
    deepen_tf = state.get("deepen_theoretical_framework", False)

    messages_from_state = [cast(BaseMessage, msg) for msg in state.get("messages", [])]
    pruned_messages = await prune_messages_to_fit_token_limit(messages_from_state, target_llm, cfg.max_input_tokens)

    prompt = ANTHROPOLOGICAL_BRIEF_PROMPT.format(
        theoretical_framework=tf_content[:3000],
        ethnographic_material=ethno_material[:2000] if ethno_material != "No especificado" else "No especificado",
        research_question=rq,
        hypothesis=hyp,
        deepen_theoretical_framework=deepen_tf,
        messages=get_buffer_string(pruned_messages),
    )

    retry_cfg = {"stop_after_attempt": cfg.max_structured_output_retries}
    try:
        response = await invoke_structured_output(target_llm, ResearchQuestion, prompt, retry_cfg)
        brief = response.research_brief if response else f"Investigación etnográfica guiada por el marco teórico: {tf_content[:200]}"
    except Exception as e:
        logger.warning(f"⚠️ Error generando brief antropológico: {e}. Usando fallback.")
        brief = f"Investigación antropológica sobre la pregunta '{rq}' bajo el marco teórico suministrado."

    # Si se solicitó profundizar el marco teórico, realizar una pasada de síntesis teórica inicial
    active_tf = tf_content
    if deepen_tf:
        logger.info("🔍 Deepen theoretical framework habilitado. Realizando expansión conceptual...")
        deepen_prompt = f"""Analiza y profundiza los siguientes insumos teóricos para ampliar sus definiciones operacionales:
Marco Teórico: {tf_content}
Pregunta de Investigación: {rq}
Hipótesis: {hyp}"""
        try:
            expanded_res = await target_llm.ainvoke([HumanMessage(content=deepen_prompt)])
            active_tf = f"{tf_content}\n\n### Profundización Conceptual del Marco Teórico:\n{expanded_res.content}"
        except Exception as e:
            logger.error(f"❌ Error al profundizar marco teórico: {e}")

    if progress_callback:
        await progress_callback(20, "Resumen antropológico listo. Iniciando supervisión...", "brief_complete")

    return {
        "research_brief": brief,
        "active_theoretical_framework": active_tf,
    }


async def anthropological_supervisor(state: AnthropologicalAgentState, config: RunnableConfig) -> dict:
    """Planifica iterativamente la investigación guiándose por el marco teórico."""
    logger.debug("--- [AnthropologicalDeepResearcher] Node: anthropological_supervisor ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")

    current_iteration = state.get("research_iterations", 0)
    total_iterations = cfg.max_researcher_iterations or 1

    if progress_callback:
        progress = int(20 + (current_iteration / total_iterations) * 60)
        await progress_callback(progress, f"Supervisor Antropológico: Iteración {current_iteration + 1}/{total_iterations}", "supervisor")

    account_id = state.get("account_id")
    if account_id:
        llm = await get_llm_for_user(account_id, purpose="fast")
    else:
        llm = get_fast_llm()

    if not llm:
        raise ValueError("LLM no inicializado.")

    chat_llm = cast(BaseChatModel, llm)
    lead_tools = [ConductResearch, CreateExpertAgent, ResearchComplete, deep_research_think_tool]

    tf_content = state.get("active_theoretical_framework") or state.get("theoretical_framework_content", "")
    rq = state.get("research_question", "No especificada")
    hyp = state.get("hypothesis", "No especificada")
    deepen_tf = state.get("deepen_theoretical_framework", False)

    system_prompt = ANTHROPOLOGICAL_SUPERVISOR_PROMPT.format(
        theoretical_framework=tf_content[:3000],
        research_question=rq,
        hypothesis=hyp,
        deepen_theoretical_framework=deepen_tf,
    )

    research_model = safe_bind_tools(chat_llm, lead_tools)
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

    if not state.get("supervisor_messages"):
        messages.append(HumanMessage(content=f"Plan de investigación para: {state.get('research_brief', '')}"))
    else:
        messages.extend([cast(BaseMessage, msg) for msg in state["supervisor_messages"]])
        if not isinstance(messages[-1], HumanMessage):
            messages.append(HumanMessage(content="Continúa planificando la investigación antropológica."))

    pruned = await prune_messages_to_fit_token_limit(messages, chat_llm, cfg.max_input_tokens)
    response = await research_model.ainvoke(pruned)

    return {
        "supervisor_messages": [response],
        "research_iterations": current_iteration + 1,
    }


async def anthropological_final_report_generation(state: AnthropologicalAgentState, config: RunnableConfig) -> dict:
    """Genera el informe final e invoca al AnthropologicalGraphProcessor para la codificación 1:1."""
    logger.debug("--- [AnthropologicalDeepResearcher] Node: anthropological_final_report_generation ---")
    progress_callback = config.get("configurable", {}).get("progress_callback")

    if progress_callback:
        await progress_callback(85, "Procesando grafo antropológico (codificación 1:1) y redactando informe...", "final_report")

    account_id = state.get("account_id")
    if account_id:
        writer_model = (await get_llm_for_user(account_id, purpose="main")) or get_main_llm()
    else:
        writer_model = get_main_llm()

    if not writer_model:
        raise ValueError("Main LLM no inicializado.")

    notes = state.get("notes", [])
    raw_notes = state.get("raw_notes", [])
    findings = "\n\n".join(notes if notes else raw_notes)

    tf_content = state.get("active_theoretical_framework") or state.get("theoretical_framework_content", "")
    rq = state.get("research_question", "No especificada")
    hyp = state.get("hypothesis", "No especificada")

    # FASE DE PROCESAMIENTO DE GRAFO (AnthropologicalGraphProcessor)
    graph_processor = AnthropologicalGraphProcessor(llm=writer_model)
    documents = [{"title": f"Hallazgo_{i+1}", "content": note} for i, note in enumerate(notes if notes else raw_notes)]
    if not documents and findings:
        documents = [{"title": "Registro de Investigación", "content": findings}]

    graph_result = {}
    try:
        graph_result = await graph_processor.process_documents_anthropologically(
            documents=documents,
            theoretical_framework=tf_content,
            research_question=rq,
            hypothesis=hyp,
            account_id=account_id,
        )
    except Exception as e:
        logger.error(f"❌ Error procesando grafo antropológico: {e}")

    # REDACCIÓN DEL INFORME FINAL
    prompt = ANTHROPOLOGICAL_FINAL_REPORT_PROMPT.format(
        research_brief=state.get("research_brief", ""),
        theoretical_framework=tf_content[:2500],
        research_question=rq,
        hypothesis=hyp,
        findings=findings[:80000],
    )

    final_report_msg = await writer_model.ainvoke([HumanMessage(content=prompt)])
    report_content = final_report_msg.content

    if progress_callback:
        await progress_callback(100, "Investigación antropológica completada.", "complete")

    return {
        "final_report": report_content,
        "graph_result": graph_result,
        "sources": state.get("sources", []),
        "messages": [final_report_msg],
    }


# --- Compilación del Grafo de Investigación Antropológica ---

def compile_anthropological_deep_researcher_graph() -> Pregel:
    """Compila y retorna el grafo completo de Investigación Antropológica Profunda."""
    from core.agents.deep_researcher import (
        create_researcher_graph,
        create_expert_agent_graph,
        supervisor_tools,
    )

    researcher_subgraph = create_researcher_graph()
    expert_agent_subgraph = create_expert_agent_graph()

    # Sub-grafo Supervisor
    supervisor_builder = StateGraph(SupervisorState)
    supervisor_builder.add_node("supervisor", anthropological_supervisor)

    async def supervisor_tools_node(state: SupervisorState, config: RunnableConfig) -> dict:
        return await supervisor_tools(state, config, researcher_subgraph, expert_agent_subgraph)

    supervisor_builder.add_node("supervisor_tools", supervisor_tools_node)
    supervisor_builder.add_edge(START, "supervisor")
    supervisor_builder.add_edge("supervisor", "supervisor_tools")

    def should_continue_supervision(state: SupervisorState, config: RunnableConfig) -> Literal["supervisor", "__end__"]:
        cfg = Configuration.from_runnable_config(config)
        last_message = state["supervisor_messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            if any(tc["name"] == "ResearchComplete" for tc in last_message.tool_calls):
                return "__end__"
        if state.get("research_iterations", 0) >= cfg.max_researcher_iterations:
            return "__end__"
        return "supervisor"

    supervisor_builder.add_conditional_edges("supervisor_tools", should_continue_supervision)
    supervisor_subgraph = supervisor_builder.compile()

    # Grafo Principal
    main_builder = StateGraph(AnthropologicalAgentState)
    main_builder.add_node("write_research_brief", write_anthropological_brief)
    main_builder.add_node("research_supervisor", supervisor_subgraph)
    main_builder.add_node("final_report_generation", anthropological_final_report_generation)

    main_builder.add_edge(START, "write_research_brief")
    main_builder.add_edge("write_research_brief", "research_supervisor")
    main_builder.add_edge("research_supervisor", "final_report_generation")
    main_builder.add_edge("final_report_generation", END)

    return main_builder.compile()


async def run_anthropological_deep_research(
    query_or_topic: str,
    theoretical_framework_content: str,
    ethnographic_material_content: Optional[str] = None,
    deepen_theoretical_framework: bool = False,
    research_question: Optional[str] = None,
    hypothesis: Optional[str] = None,
    account_id: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar una investigación antropológica profunda.
    """
    graph = compile_anthropological_deep_researcher_graph()

    inputs: AnthropologicalAgentState = {
        "messages": [HumanMessage(content=query_or_topic)],
        "account_id": account_id,
        "theoretical_framework_content": theoretical_framework_content,
        "ethnographic_material_content": ethnographic_material_content,
        "deepen_theoretical_framework": deepen_theoretical_framework,
        "research_question": research_question,
        "hypothesis": hypothesis,
    }

    run_config = config or RunnableConfig(
        configurable={
            "account_id": account_id,
            "progress_callback": progress_callback,
            "base_progress": 0,
            "max_sub_progress": 100,
        }
    )

    result = await graph.ainvoke(inputs, config=run_config)
    return result
