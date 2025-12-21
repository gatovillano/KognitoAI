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
    logger.info("--- [DeepResearcher] Node: clarify_with_user ---")
    cfg = Configuration.from_runnable_config(config)
    clarification_model = get_main_llm().with_retry(
        stop_after_attempt=cfg.max_structured_output_retries
    )
    
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
        research_brief = data.get("research_brief", "No brief generated.")
        logger.info(f"📝 [DeepResearcher] Generated research_brief: '{research_brief}'")
        return {"research_brief": research_brief}
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error processing clarification model response: {e}. Response: {response.content}")
        return {"research_brief": "Error: Could not generate a valid research brief."}


async def write_research_brief(state: AgentState, config: RunnableConfig) -> dict:
    logger.info("--- [DeepResearcher] Node: write_research_brief ---")
    # This node is currently a pass-through. The brief is generated in the previous step.
    logger.info(f"📋 [DeepResearcher] Proceeding with research_brief: '{state.get('research_brief')}'")
    return {}

async def final_report_generation(state: AgentState, config: RunnableConfig) -> dict:
    """Generates the final comprehensive research report."""
    logger.info("--- [DeepResearcher] Node: final_report_generation ---")
    cfg = Configuration.from_runnable_config(config)
    notes = state.get("notes", [])
    findings = "\n\n".join(notes)
    logger.info(f"📝 [DeepResearcher] Generating final report based on {len(notes)} notes/findings.")
    logger.debug(f"Findings for final report: {findings}")
    
    writer_model = get_main_llm()

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
    
    logger.info(f"📄 [DeepResearcher] Final report generated. Preview: {str(final_report.content)[:300]}...")
    return {
        "final_report": final_report.content,
        "messages": [final_report],
    }

# --- Supervisor Sub-Graph Nodes ---

async def supervisor(state: SupervisorState, config: RunnableConfig) -> dict:
    """Plans research strategy and delegates to researchers."""
    logger.info("--- [DeepResearcher] Node: supervisor ---")
    cfg = Configuration.from_runnable_config(config)
    llm = get_main_llm()

    # Forceful prompt to ensure the LLM calls a tool
    forceful_prompt = """You are a research director. Your only purpose is to choose the next action in a research plan.
You MUST call one of the following tools:
1. `ConductResearch`: If the research is not yet complete and there are more topics to investigate.
2. `ResearchComplete`: If you have sufficient information to answer the user's query.

Do NOT under any circumstances respond with plain text. You must call a tool.
Based on the research so far, what is the next step?
"""

    think_tool = {"name": "think_tool", "description": "Reflect on the research plan and progress.", "args": {"reflection": "string"}}
    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]

    # Force the model to use a tool
    research_model = llm.bind_tools(
        lead_researcher_tools,
        tool_choice="auto" # Use 'auto' for broader compatibility with VertexAI
    ).with_retry(
        stop_after_attempt=cfg.max_structured_output_retries
    )

    messages: list[BaseMessage] = [SystemMessage(content=forceful_prompt)]
    if not state["supervisor_messages"]:
        logger.info("First supervisor run. Planning initial research.")
        messages.append(HumanMessage(content=f"Plan research for: {state.get('research_brief', '')}"))
    else:
        logger.info(f"Supervisor continuing with {len(state['supervisor_messages'])} previous messages.")
        # Add previous messages to the context
        messages.extend(state["supervisor_messages"])

    # This final message prompts the LLM to make its mandatory tool call
    messages.append(HumanMessage(content="Based on the provided context, decide the next step. You must call a tool."))
    response = await research_model.ainvoke(messages)

    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            logger.info(f"📋 [Supervisor] LLM decided to call tool: {tool_call['name']} with args: {tool_call['args']}")
    else:
        logger.warning("[Supervisor] LLM did not generate any tool calls, despite being forced. This indicates a potential issue with the model or prompt.")

    return {
        "supervisor_messages": state["supervisor_messages"] + [response],
        "research_iterations": state.get("research_iterations", 0) + 1,
    }

async def supervisor_tools(state: SupervisorState, config: RunnableConfig, researcher_subgraph: Pregel) -> dict:
    """Executes tools called by the supervisor."""
    logger.info("--- [DeepResearcher] Node: supervisor_tools ---")
    cfg = Configuration.from_runnable_config(config)
    most_recent_message = state["supervisor_messages"][-1]
    
    if not isinstance(most_recent_message, AIMessage) or not getattr(most_recent_message, 'tool_calls', None):
        logger.warning("[Supervisor Tools] No tool calls in the last message. Checking iteration count.")
        if state["research_iterations"] > cfg.max_researcher_iterations:
            logger.info("[Supervisor Tools] Max iterations reached. Ending research.")
            return {"notes": get_notes_from_tool_calls(state["supervisor_messages"])}
        else:
            logger.info("[Supervisor Tools] Not at max iterations. Returning to supervisor.")
            return {"supervisor_messages": state["supervisor_messages"]}

    all_tool_messages = []
    update_payload = {}

    conduct_research_calls = [tc for tc in getattr(most_recent_message, 'tool_calls', []) if tc["name"] == "ConductResearch"]
    logger.info(f"[Supervisor Tools] Found {len(conduct_research_calls)} 'ConductResearch' tool calls.")

    if conduct_research_calls:
        research_tasks = [
            researcher_subgraph.ainvoke({
                "researcher_messages": [HumanMessage(content=tc["args"]["research_topic"])],
                "research_topic": tc["args"]["research_topic"],
                "account_id": state["account_id"],
            }, config)
            for tc in conduct_research_calls[:cfg.max_concurrent_research_units]
        ]
        logger.info(f"🚀 [Supervisor Tools] Starting {len(research_tasks)} parallel research tasks.")
        tool_results = await asyncio.gather(*research_tasks)
        logger.info("✅ [Supervisor Tools] All parallel research tasks completed.")

        for observation, tool_call in zip(tool_results, conduct_research_calls):
            compressed_result = observation.get("compressed_research", "Error: No compressed research found.")
            logger.info(f"📝 [Supervisor Tools] Result for '{tool_call['args']['research_topic']}': '{compressed_result[:200]}...'")
            all_tool_messages.append(ToolMessage(
                content=compressed_result,
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
    logger.info(f"--- [DeepResearcher] Node: researcher ---")
    logger.info(f"🔍 [Researcher] Researching topic: '{state['research_topic']}'")
    cfg = Configuration.from_runnable_config(config)
    
    # Obtener todas las herramientas disponibles una vez por contexto
    account_id = str(config.get("configurable", {}).get("account_id"))
    telegram_id_int = config.get("configurable", {}).get("telegram_id")
    telegram_id_str = str(telegram_id_int) if telegram_id_int is not None else None
    workspace_id = str(config.get("configurable", {}).get("workspace_id")) if config.get("configurable", {}).get("workspace_id") else None

    all_tools = await get_all_langchain_tools(
        account_id=account_id,
        telegram_id=telegram_id_int,
        thread_id=workspace_id, # Usamos workspace_id como thread_id si no hay otro
        workspace_id=workspace_id
    )
    
    if not all_tools:
        logger.error("[Researcher] No tools found for research. Aborting.")
        raise ValueError("No tools found for research.")

    llm = get_main_llm()
    researcher_prompt = research_system_prompt.format(mcp_prompt="", date=get_today_str())
    research_model = llm.bind_tools(all_tools).with_retry( # type: ignore
        stop_after_attempt=cfg.max_structured_output_retries
    )
    
    messages = [SystemMessage(content=researcher_prompt)] + state["researcher_messages"]
    response = await research_model.ainvoke(messages)
    
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            logger.info(f"🛠️ [Researcher] LLM decided to call tool: {tool_call['name']} with args: {tool_call['args']}")
    else:
        logger.warning("[Researcher] LLM did not generate any tool calls for this step.")
    
    return {
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
    }

async def researcher_tools(state: ResearcherState, config: RunnableConfig) -> dict:
    """Executes tools called by the researcher."""
    logger.info("--- [DeepResearcher] Node: researcher_tools ---")
    most_recent_message = state["researcher_messages"][-1]

    if not hasattr(most_recent_message, 'tool_calls') or not most_recent_message.tool_calls:
        logger.warning("[Researcher Tools] No tool calls in the last message. Skipping tool execution.")
        return {}

    # Obtener todas las herramientas disponibles una vez por contexto
    account_id = str(config.get("configurable", {}).get("account_id"))
    telegram_id_int = config.get("configurable", {}).get("telegram_id")
    telegram_id_str = str(telegram_id_int) if telegram_id_int is not None else None
    workspace_id = str(config.get("configurable", {}).get("workspace_id")) if config.get("configurable", {}).get("workspace_id") else None

    all_tools = await get_all_langchain_tools(
        account_id=account_id,
        telegram_id=telegram_id_int,
        thread_id=workspace_id, # Usamos workspace_id como thread_id si no hay otro
        workspace_id=workspace_id
    )
    
    tools_by_name = {tool.name: tool for tool in all_tools}

    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tc["name"]], tc["args"], config)
        for tc in most_recent_message.tool_calls
    ]
    logger.info(f"🚀 [Researcher Tools] Executing {len(tool_execution_tasks)} tool(s) in parallel.")
    observations = await asyncio.gather(*tool_execution_tasks)
    logger.info("✅ [Researcher Tools] All tools executed.")

    tool_outputs = []
    for obs, tc in zip(observations, most_recent_message.tool_calls):
        logger.info(f"🔧 [Researcher Tools] Result for '{tc['name']}': '{str(obs)[:200]}...'")
        tool_outputs.append(ToolMessage(content=str(obs), name=tc["name"], tool_call_id=tc["id"]))

    return {"researcher_messages": tool_outputs}

async def compress_research(state: ResearcherState, config: RunnableConfig) -> dict:
    """Compresses and synthesizes research findings."""
    logger.info("--- [DeepResearcher] Node: compress_research ---")
    cfg = Configuration.from_runnable_config(config)
    synthesizer_model = get_main_llm()

    researcher_messages = state["researcher_messages"] + [HumanMessage(content=compress_research_simple_human_message)]
    
    compression_prompt = compress_research_system_prompt.format(date=get_today_str())
    messages = [SystemMessage(content=compression_prompt)] + researcher_messages

    logger.info(f"📚 [Compress Research] Compressing {len(researcher_messages)} messages.")
    response = await synthesizer_model.ainvoke(messages)

    raw_notes_content = "\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])

    logger.info(f"📦 [Compress Research] Compressed research output preview: '{str(response.content)[:200]}...'")

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
    
    def should_continue_research(state: ResearcherState) -> Literal["researcher", "compress_research"]:
        if state["tool_call_iterations"] >= state.get("max_react_tool_calls", 3):
            logger.info("[Researcher Edge] Max tool calls reached. Compressing research.")
            return "compress_research"
        logger.info("[Researcher Edge] Continuing research.")
        return "researcher"
        
    researcher_builder.add_conditional_edges("researcher_tools", should_continue_research)
    researcher_builder.add_edge("compress_research", END)
    
    return researcher_builder.compile()

def create_supervisor_graph(researcher_subgraph: Pregel, max_researcher_iterations: int) -> Pregel:
    """Creates the supervisor sub-graph."""
    supervisor_builder = StateGraph(SupervisorState)
    supervisor_builder.add_node("supervisor", supervisor)

    async def supervisor_tools_node(state: SupervisorState, config: RunnableConfig) -> dict:
        return await supervisor_tools(state, config, researcher_subgraph)

    supervisor_builder.add_node("supervisor_tools", supervisor_tools_node)

    supervisor_builder.add_edge(START, "supervisor")
    supervisor_builder.add_edge("supervisor", "supervisor_tools")
    
    def should_continue_supervision(state: SupervisorState) -> Literal["supervisor", "__end__"]:
        if state["supervisor_messages"] and state["supervisor_messages"][-1].tool_calls and any(tc["name"] == "ResearchComplete" for tc in state["supervisor_messages"][-1].tool_calls):
            logger.info("[Supervisor Edge] 'ResearchComplete' called. Ending supervision.")
            return END
        if state.get("research_iterations", 0) > max_researcher_iterations:
            logger.info("[Supervisor Edge] Max supervisor iterations reached. Ending supervision.")
            return END
        logger.info("[Supervisor Edge] Continuing supervision.")
        return "supervisor"

    supervisor_builder.add_conditional_edges("supervisor_tools", should_continue_supervision)
    return supervisor_builder.compile()

def compile_deep_researcher_graph() -> Pregel:
    """Compiles and returns the full Deep Researcher graph."""
    researcher_subgraph = create_researcher_graph()
    cfg = Configuration()
    supervisor_subgraph = create_supervisor_graph(researcher_subgraph, cfg.max_researcher_iterations)

    deep_researcher_builder = StateGraph(AgentState)
    
    deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
    deep_researcher_builder.add_node("write_research_brief", write_research_brief)
    deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)
    deep_researcher_builder.add_node("final_report_generation", final_report_generation)
    
    deep_researcher_builder.add_edge(START, "clarify_with_user")
    
    def should_start_research(state: AgentState) -> Literal["write_research_brief", "__end__"]:
        if state.get("final_report") == "CLARIFICATION" or "Error:" in state.get("research_brief", ""):
            logger.warning(f"[Main Graph Edge] Clarification needed or error in brief. Ending graph. Brief: {state.get('research_brief')}")
            return END
        logger.info("[Main Graph Edge] Brief is clear. Proceeding to research.")
        return "write_research_brief"

    deep_researcher_builder.add_conditional_edges("clarify_with_user", should_start_research)
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