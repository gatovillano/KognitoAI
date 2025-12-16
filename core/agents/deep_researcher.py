# core/agents/deep_researcher.py

import asyncio
import json
import logging
from typing import Literal, Sequence # Importar Sequence


from langchain_core.messages import (
    AIMessage,
    BaseMessage, # Importar BaseMessage
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.pregel import Pregel

from core.llm_manager import get_main_llm
from core.utils.tool_utils import get_tool_by_name
from core.utils.date_utils import get_today_str
from core.utils.llm_utils import (
    is_token_limit_exceeded,
    remove_up_to_last_ai_message,
)

from core.agents.deep_researcher_config import Configuration
from core.agents.deep_researcher_prompts import (
    clarify_with_user_instructions,
    compress_research_simple_human_message,
    compress_research_system_prompt,
    final_report_generation_prompt,
    lead_researcher_prompt,
    research_system_prompt,
    transform_messages_into_research_topic_prompt,
)
from core.agents.deep_researcher_state import (
    AgentInputState,
    AgentState,
    ClarifyWithUser,
    ConductResearch,
    ResearchComplete,
    ResearcherOutputState,
    ResearcherState,
    ResearchQuestion,
    SupervisorState,
)

logger = logging.getLogger(__name__)

# --- Helper Functions ---

async def get_all_tools(config: RunnableConfig):
    """Fetches all available research tools."""
    # For now, we only have web_search and knowledge_search
    account_id = str(config.get("configurable", {}).get("account_id"))
    web_search = await get_tool_by_name("web_search", account_id)
    knowledge_search = await get_tool_by_name("knowledge_search", account_id)
    tools = [t for t in [web_search, knowledge_search] if t]
    return tools

def get_notes_from_tool_calls(messages: list) -> list[str]:
    """Extracts notes from tool calls, especially from 'think_tool'."""
    notes = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "think_tool":
                    reflection_note = tool_call["args"].get("reflection")
                    if reflection_note:
                        notes.append(reflection_note)
    return notes

async def execute_tool_safely(tool, args, config):
    """Safely execute a tool with error handling."""
    try:
        return await tool.ainvoke(args, config)
    except Exception as e:
        logger.error(f"Error executing tool {tool.name}: {e}", exc_info=True)
        return f"Error executing tool: {str(e)}"
# --- Main Graph Nodes ---

async def clarify_with_user(state: AgentState, config: RunnableConfig) -> dict:
    logger.info("--- [DeepResearcher] Clarifying with user ---")
    cfg = Configuration.from_runnable_config(config)
    clarification_model = get_main_llm().with_retry(
        stop_after_attempt=cfg.max_structured_output_retries
    )
    
    # Asegúrate de que messages sea una lista de BaseMessage
    current_messages: list[BaseMessage] = []
    for msg in state.get("messages", []):
        if isinstance(msg, BaseMessage):
            current_messages.append(msg)
        else:
            current_messages.append(HumanMessage(content=str(msg)))

    prompt = transform_messages_into_research_topic_prompt.format(messages=get_buffer_string(current_messages), date=get_today_str()) # type: ignore
    response = await clarification_model.ainvoke([HumanMessage(content=prompt)], response_format={"type": "json_object"})
    try:
        data = json.loads(response.content)
        return {"research_brief": data["research_brief"]}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from clarification model: {e}. Response content: {response.content}")
        # Devuelve un research_brief predeterminado o un mensaje de error si el JSON es inválido
        return {"research_brief": "Error: Invalid JSON response from clarification model."}

async def write_research_brief(state: AgentState, config: RunnableConfig) -> dict:
    logger.info("--- [DeepResearcher] Writing research brief ---")
    # For now, just return the research_brief as is
    return {}

async def final_report_generation(state: AgentState, config: RunnableConfig) -> dict:
    """Generates the final comprehensive research report."""
    logger.info("--- [DeepResearcher] Generating final report ---")
    cfg = Configuration.from_runnable_config(config)
    notes = state.get("notes", [])
    findings = "\n".join(notes)
    
    writer_model = get_main_llm()

    # Asegúrate de que messages sea una lista de BaseMessage
    current_messages_list: list[BaseMessage] = []
    for msg in state.get("messages", []):
        if isinstance(msg, BaseMessage):
            current_messages_list.append(msg)
        else:
            current_messages_list.append(HumanMessage(content=str(msg)))

    final_report_prompt = final_report_generation_prompt.format(
        research_brief=state.get("research_brief", ""),
        messages=get_buffer_string(current_messages_list), # type: ignore
        findings=findings,
        date=get_today_str(),
    )
    
    final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt)])
    
    logger.info("--- [DeepResearcher] Final report generated ---")
    return {
        "final_report": final_report.content,
        "messages": [final_report],
    }

# --- Supervisor Sub-Graph Nodes ---

async def supervisor(state: SupervisorState, config: RunnableConfig) -> dict:
    """Plans research strategy and delegates to researchers."""
    logger.info("--- [DeepResearcher] Planning research ---")
    cfg = Configuration.from_runnable_config(config)
    llm = get_main_llm()

    # think_tool is a special tool for reflection, not a standard tool
    think_tool = {"name": "think_tool", "description": "Reflect on the research plan and progress.", "args": {"reflection": "string"}}

    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]

    # Asegurarse de que el LLM devuelto por get_main_llm() tenga el método bind_tools
    # y que los mensajes sean de tipo BaseMessage.
    # Si 'llm' no es de tipo ChatLiteLLM, esto podría fallar.
    # Asumimos que get_main_llm() ya devuelve un ChatLiteLLM o similar.
    research_model = llm.bind_tools(lead_researcher_tools).with_retry( # type: ignore
        stop_after_attempt=cfg.max_structured_output_retries
    )

    messages: list[BaseMessage] = [SystemMessage(content=lead_researcher_prompt)]
    if not state["supervisor_messages"]:
        messages.append(HumanMessage(content=f"Plan research for: {state.get('research_brief', '')}"))
    else:
        # Asegurarse de que los mensajes existentes sean de tipo BaseMessage
        for msg in state["supervisor_messages"]:
            if isinstance(msg, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
                messages.append(msg)
            else:
                # Convertir a HumanMessage si no es un tipo conocido
                messages.append(HumanMessage(content=str(msg)))

    # Añadir un HumanMessage al final para satisfacer el requisito del LLM
    messages.append(HumanMessage(content="What is the next step in the research plan, or is the research complete?"))
    response = await research_model.ainvoke(messages)

    return {
        "supervisor_messages": state["supervisor_messages"] + [response],
        "research_iterations": state.get("research_iterations", 0) + 1,
    }

async def supervisor_tools(state: SupervisorState, config: RunnableConfig, researcher_subgraph: Pregel) -> dict:
    """Executes tools called by the supervisor."""
    logger.info("--- [Supervisor] Executing tools ---")
    cfg = Configuration.from_runnable_config(config)
    most_recent_message = state["supervisor_messages"][-1]
    
    # Verificar si most_recent_message es un AIMessage y tiene tool_calls
    if not isinstance(most_recent_message, AIMessage) or not getattr(most_recent_message, 'tool_calls', None):
        if state["research_iterations"] > cfg.max_researcher_iterations:
            return {"notes": get_notes_from_tool_calls(state["supervisor_messages"])}
        else:
            # Si no hay tool_calls y no hemos excedido las iteraciones, el supervisor debe continuar
            return {"supervisor_messages": state["supervisor_messages"]}


    all_tool_messages = []
    update_payload = {}

    conduct_research_calls = [tc for tc in getattr(most_recent_message, 'tool_calls', []) if tc["name"] == "ConductResearch"]

    if conduct_research_calls:
        research_tasks = [
            researcher_subgraph.ainvoke({
                "researcher_messages": [HumanMessage(content=tc["args"]["research_topic"])],
                "research_topic": tc["args"]["research_topic"],
                "account_id": state["account_id"],
            }, config)
            for tc in conduct_research_calls[:cfg.max_concurrent_research_units]
        ]

        tool_results = await asyncio.gather(*research_tasks)

        for observation, tool_call in zip(tool_results, conduct_research_calls):
            all_tool_messages.append(ToolMessage(
                content=observation.get("compressed_research", "Error in research."),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            ))

        raw_notes_concat = "\n".join([res.get("raw_notes", "") for res in tool_results])
        if raw_notes_concat:
            update_payload["raw_notes"] = [raw_notes_concat]

    update_payload["supervisor_messages"] = state["supervisor_messages"] + all_tool_messages
    return update_payload

# --- Researcher Sub-Graph Nodes ---

async def researcher(state: ResearcherState, config: RunnableConfig) -> dict:
    """Conducts focused research on a specific topic."""
    logger.info(f"--- [Researcher] Researching topic: {state['research_topic']} ---")
    cfg = Configuration.from_runnable_config(config)
    tools = await get_all_tools(config)
    if not tools:
        raise ValueError("No tools found for research.")

    llm = get_main_llm()
    researcher_prompt = research_system_prompt.format(mcp_prompt="", date=get_today_str())
    research_model = llm.bind_tools(tools).with_retry( # type: ignore
        stop_after_attempt=cfg.max_structured_output_retries
    )
    
    messages = [SystemMessage(content=researcher_prompt)] + state["researcher_messages"]
    response = await research_model.ainvoke(messages)
    
    return {
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
    }

async def researcher_tools(state: ResearcherState, config: RunnableConfig) -> dict:
    """Executes tools called by the researcher."""
    logger.info("--- [Researcher] Executing tools ---")
    cfg = Configuration.from_runnable_config(config)
    most_recent_message = state["researcher_messages"][-1]

    if not getattr(most_recent_message, 'tool_calls', None):
        return {}

    tools = await get_all_tools(config)
    tools_by_name = {tool.name: tool for tool in tools}

    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tc["name"]], tc["args"], config)
        for tc in getattr(most_recent_message, 'tool_calls', [])
    ]
    observations = await asyncio.gather(*tool_execution_tasks)
    
    tool_outputs = [
        ToolMessage(content=str(obs), name=tc["name"], tool_call_id=tc["id"])
        for obs, tc in zip(observations, getattr(most_recent_message, 'tool_calls', []))
    ]
    
    return {"researcher_messages": tool_outputs}

async def compress_research(state: ResearcherState, config: RunnableConfig) -> dict:
    """Compresses and synthesizes research findings."""
    logger.info("--- [Researcher] Compressing research ---")
    cfg = Configuration.from_runnable_config(config)
    synthesizer_model = get_main_llm()

    researcher_messages = state["researcher_messages"] + [HumanMessage(content=compress_research_simple_human_message)]
    
    compression_prompt = compress_research_system_prompt.format(date=get_today_str())
    messages = [SystemMessage(content=compression_prompt)] + researcher_messages
    
    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60), # Espera exponencial entre 4 y 60 segundos
        stop=stop_after_attempt(5), # Reintentar un máximo de 5 veces
        retry=(retry_if_exception_type(ResourceExhausted) | # Reintentar si es un error de cuota de Google
               retry_if_exception_type(httpx.HTTPStatusError)), # Reintentar si es un error HTTP
        reraise=True # Volver a lanzar la excepción si todos los reintentos fallan
    )
    async def _invoke_synthesizer_model():
        try:
            return await synthesizer_model.ainvoke(messages)
        except ResourceExhausted as e:
            logger.warning(f"Rate limit exceeded in compress_research. Retrying... Details: {str(e)}")
            raise # Re-lanzar para que tenacity lo capture
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"HTTP 429 (Too Many Requests) encountered in compress_research. Retrying... Details: {str(e)}")
                raise # Re-lanzar para que tenacity lo capture
            else:
                raise # Re-lanzar otras excepciones HTTP

    response = await _invoke_synthesizer_model()
    
    raw_notes_content = "\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])
    
    return {
        "compressed_research": str(response.content),
        "raw_notes": [raw_notes_content],
    }

# --- Graph Compilation ---

def create_researcher_graph() -> Pregel:
    """Creates the individual researcher sub-graph."""
    researcher_builder = StateGraph(ResearcherState)
    researcher_builder.add_node("researcher", researcher)
    researcher_builder.add_node("researcher_tools", researcher_tools)
    researcher_builder.add_node("compress_research", compress_research)
    
    researcher_builder.add_edge(START, "researcher")
    researcher_builder.add_edge("researcher", "researcher_tools")
    researcher_builder.add_conditional_edges(
        "researcher_tools",
        lambda s: "compress_research" if s["tool_call_iterations"] >= s.get("max_react_tool_calls", 3) else "researcher",
    )
    researcher_builder.add_edge("compress_research", END)
    
    return researcher_builder.compile()

def create_supervisor_graph(researcher_subgraph: Pregel, max_researcher_iterations: int) -> Pregel:
    """Creates the supervisor sub-graph."""
    supervisor_builder = StateGraph(SupervisorState)
    supervisor_builder.add_node("supervisor", supervisor)

    # Define an async wrapper for supervisor_tools
    async def supervisor_tools_node(state: SupervisorState, config: RunnableConfig) -> dict:
        return await supervisor_tools(state, config, researcher_subgraph)

    supervisor_builder.add_node("supervisor_tools", supervisor_tools_node)

    supervisor_builder.add_edge(START, "supervisor")
    supervisor_builder.add_edge("supervisor", "supervisor_tools")
    supervisor_builder.add_conditional_edges(
        "supervisor_tools",
        lambda s: END if (s["supervisor_messages"] and s["supervisor_messages"][-1].tool_calls and any(tc["name"] == "ResearchComplete" for tc in s["supervisor_messages"][-1].tool_calls)) or s.get("research_iterations", 0) > max_researcher_iterations else "supervisor",
    )
    return supervisor_builder.compile()

def compile_deep_researcher_graph() -> Pregel:
    """Compiles and returns the full Deep Researcher graph."""
    researcher_subgraph = create_researcher_graph()
    # Obtener el valor de max_researcher_iterations de la configuración
    # Se asume que la configuración se obtiene en el momento de la compilación del grafo principal
    # para que esté disponible al crear el subgrafo del supervisor.
    cfg = Configuration() # Instanciar Configuration para obtener el valor por defecto
    supervisor_subgraph = create_supervisor_graph(researcher_subgraph, cfg.max_researcher_iterations)

    deep_researcher_builder = StateGraph(AgentState)
    
    deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
    deep_researcher_builder.add_node("write_research_brief", write_research_brief)
    deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)
    deep_researcher_builder.add_node("final_report_generation", final_report_generation)
    
    deep_researcher_builder.add_edge(START, "clarify_with_user")
    deep_researcher_builder.add_conditional_edges(
        "clarify_with_user",
        lambda s: "write_research_brief" if s.get("final_report") != "CLARIFICATION" else END,
    )
    deep_researcher_builder.add_edge("write_research_brief", "research_supervisor")
    deep_researcher_builder.add_edge("research_supervisor", "final_report_generation")
    deep_researcher_builder.add_edge("final_report_generation", END)
    
    return deep_researcher_builder.compile()

if __name__ == "__main__":
    # Example of how to run the graph
    async def run_example():
        graph = compile_deep_researcher_graph()
        
        inputs = {
            "messages": [HumanMessage(content="Compare the new AI models from Google and OpenAI.")],
            "account_id": "test-account"
        }
        
        config = {"configurable": {"account_id": "test-account"}}

        async for event in graph.astream_events(inputs, config=config, version="v1"): # type: ignore
            kind = event["event"]
            if kind == "on_chain_end":
                print(f"--- Event: {kind} ---")
                print(f"Output: {event['data']['output']}") # type: ignore
            elif "messages" in event.get("data", {}).get("chunk", {}):
                 print(f"--- Event: {kind} ---")
                 print(f"Content: {event['data']['chunk']['messages'][-1].content}") # type: ignore


    asyncio.run(run_example())