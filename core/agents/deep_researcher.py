# core/agents/deep_researcher.py

import asyncio
import json
import logging
import os
from typing import Literal, Sequence, cast

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig, Runnable
from langgraph.graph import END, START, StateGraph
from langgraph.pregel import Pregel
from langchain_core.language_models import BaseChatModel # Import BaseChatModel

from core.llm_manager import get_main_llm, initialize_llms # Import initialize_llms
from core.utils.date_utils import get_today_str
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
from core.agents.deep_researcher_utils import (
    get_all_tools,
    get_notes_from_tool_calls,
    get_today_str,
    think_tool,
    execute_tool_safely,
)


logger = logging.getLogger(__name__)

# --- Main Graph Nodes ---

async def clarify_with_user(state: AgentState, config: RunnableConfig) -> dict:
    logger.info("--- [DeepResearcher] Node: clarify_with_user ---")
    cfg = Configuration.from_runnable_config(config)
    
    if not cfg.allow_clarification:
        return {"messages": [AIMessage(content="Research brief is clear, proceeding to research.")]}

    llm_instance = get_main_llm()
    if not llm_instance:
        raise ValueError("Main LLM not initialized.")

    clarification_model = cast(Runnable[Sequence[BaseMessage], ClarifyWithUser], 
                               llm_instance.with_structured_output(ClarifyWithUser).with_retry(
                                   stop_after_attempt=cfg.max_structured_output_retries
                               ))
    
    current_messages: list[BaseMessage] = [cast(BaseMessage, msg) for msg in state.get("messages", [])]

    prompt = clarify_with_user_instructions.format(messages=get_buffer_string(current_messages), date=get_today_str())
    response: ClarifyWithUser = await clarification_model.ainvoke([HumanMessage(content=prompt)])
    
    if response.need_clarification:
        return {"messages": [AIMessage(content=response.question)], "final_report": "CLARIFICATION"}
    else:
        return {"messages": [AIMessage(content=response.verification)]}


async def write_research_brief(state: AgentState, config: RunnableConfig) -> dict:
    logger.info("--- [DeepResearcher] Node: write_research_brief ---")
    cfg = Configuration.from_runnable_config(config)
    
    llm_instance = get_main_llm()
    if not llm_instance:
        raise ValueError("Main LLM not initialized.")

    research_model = cast(Runnable[Sequence[BaseMessage], ResearchQuestion],
                          llm_instance.with_structured_output(ResearchQuestion).with_retry(
                              stop_after_attempt=cfg.max_structured_output_retries
                          ))
    
    messages_from_state = [cast(BaseMessage, msg) for msg in state.get("messages", [])]
    prompt_content = transform_messages_into_research_topic_prompt.format(
        messages=get_buffer_string(messages_from_state),
        date=get_today_str()
    )
    response: ResearchQuestion = await research_model.ainvoke([HumanMessage(content=prompt_content)])
    
    return {"research_brief": response.research_brief}


async def final_report_generation(state: AgentState, config: RunnableConfig) -> dict:
    """Generates the final comprehensive research report."""
    logger.info("--- [DeepResearcher] Node: final_report_generation ---")
    cfg = Configuration.from_runnable_config(config)
    notes = state.get("notes", [])
    findings = "\n\n".join(notes)
    logger.info(f"📝 [DeepResearcher] Generating final report based on {len(notes)} notes/findings.")
    logger.debug(f"Findings for final report: {findings}")
    
    writer_model = get_main_llm()
    if not writer_model:
        raise ValueError("Main LLM not initialized.")

    current_messages_list: list[BaseMessage] = [cast(BaseMessage, msg) for msg in state.get("messages", [])]

    final_report_prompt = final_report_generation_prompt.format(
        research_brief=state.get("research_brief", ""),
        messages=get_buffer_string(current_messages_list),
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
    if not llm:
        raise ValueError("Main LLM not initialized.")

    # Cast to BaseChatModel to ensure bind_tools is available
    chat_llm = cast(BaseChatModel, llm)

    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]

    research_model = cast(Runnable[Sequence[BaseMessage], AIMessage],
                          chat_llm.bind_tools(
                              lead_researcher_tools,
                              tool_choice="auto"
                          ).with_retry(
                              stop_after_attempt=cfg.max_structured_output_retries
                          ))

    supervisor_system_prompt = lead_researcher_prompt.format(
        date=get_today_str(),
        max_concurrent_research_units=cfg.max_concurrent_research_units,
        max_researcher_iterations=cfg.max_researcher_iterations
    )

    messages: list[BaseMessage] = [SystemMessage(content=supervisor_system_prompt)]
    if not state.get("supervisor_messages"):
        logger.info("First supervisor run. Planning initial research.")
        messages.append(HumanMessage(content=f"Plan research for: {state.get('research_brief', '')}"))
    else:
        logger.info(f"Supervisor continuing with {len(state['supervisor_messages'])} previous messages.")
        # Ensure messages are BaseMessage instances before extending
        valid_messages = [cast(BaseMessage, msg) for msg in state["supervisor_messages"] if isinstance(msg, (AIMessage, HumanMessage, SystemMessage, ToolMessage))]
        messages.extend(valid_messages)

    response: AIMessage = await research_model.ainvoke(messages)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            logger.info(f"📋 [Supervisor] LLM decided to call tool: {tool_call['name']} with args: {tool_call['args']}")
    else:
        logger.warning("[Supervisor] LLM did not generate any tool calls.")

    return {
        "supervisor_messages": state.get("supervisor_messages", []) + [response],
        "research_iterations": state.get("research_iterations", 0) + 1,
    }

async def supervisor_tools(state: SupervisorState, config: RunnableConfig, researcher_subgraph: Pregel) -> dict:
    """Executes tools called by the supervisor."""
    logger.info("--- [DeepResearcher] Node: supervisor_tools ---")
    cfg = Configuration.from_runnable_config(config)
    most_recent_message: AIMessage = cast(AIMessage, state["supervisor_messages"][-1])
    
    if not most_recent_message.tool_calls:
        logger.warning("[Supervisor Tools] No tool calls in the last message. Checking iteration count.")
        if state["research_iterations"] > cfg.max_researcher_iterations:
            logger.info("[Supervisor Tools] Max iterations reached. Ending research.")
            return {"notes": get_notes_from_tool_calls(state["supervisor_messages"])}
        else:
            logger.info("[Supervisor Tools] Not at max iterations. Returning to supervisor.")
            return {"supervisor_messages": state["supervisor_messages"]}

    all_tool_messages = []
    update_payload = {}

    conduct_research_calls = [tc for tc in most_recent_message.tool_calls if tc["name"] == "ConductResearch"]
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
    
    tools = await get_all_tools(config)
    if not tools:
        logger.error("[Researcher] No tools found for research. Aborting.")
        raise ValueError("No tools found for research.")

    llm_instance = get_main_llm()
    if not llm_instance:
        raise ValueError("Main LLM not initialized.")
    chat_llm = cast(BaseChatModel, llm_instance)

    researcher_prompt = research_system_prompt.format(mcp_prompt=cfg.mcp_prompt or "", date=get_today_str())
    research_model = cast(Runnable[Sequence[BaseMessage], AIMessage],
                          chat_llm.bind_tools(tools).with_retry(
                              stop_after_attempt=cfg.max_structured_output_retries
                          ))
    
    messages = [SystemMessage(content=researcher_prompt)] + [cast(BaseMessage, msg) for msg in state["researcher_messages"]]
    response: AIMessage = await research_model.ainvoke(messages)
    
    if response.tool_calls:
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
    most_recent_message: AIMessage = cast(AIMessage, state["researcher_messages"][-1])

    if not most_recent_message.tool_calls:
        logger.warning("[Researcher Tools] No tool calls in the last message. Skipping tool execution.")
        return {}

    tools = await get_all_tools(config)
    tools_by_name = {tool.name: tool for tool in tools if hasattr(tool, 'name')}
    
    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tc["name"]], tc["args"], config)
        for tc in most_recent_message.tool_calls if tc["name"] in tools_by_name
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
    if not synthesizer_model:
        raise ValueError("Main LLM not initialized.")


    researcher_messages = [cast(BaseMessage, msg) for msg in state["researcher_messages"]] + [HumanMessage(content=compress_research_simple_human_message)]
    
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
        cfg = Configuration.from_runnable_config(RunnableConfig()) # Get default config
        if state["tool_call_iterations"] >= cfg.max_react_tool_calls:
            logger.info("[Researcher Edge] Max tool calls reached. Compressing research.")
            return "compress_research"
        logger.info("[Researcher Edge] Continuing research.")
        return "researcher"
        
    researcher_builder.add_conditional_edges("researcher_tools", should_continue_research)
    researcher_builder.add_edge("compress_research", END)
    
    return researcher_builder.compile()

def create_supervisor_graph(researcher_subgraph: Pregel) -> Pregel:
    """Creates the supervisor sub-graph."""
    supervisor_builder = StateGraph(SupervisorState)
    supervisor_builder.add_node("supervisor", supervisor)

    async def supervisor_tools_node(state: SupervisorState, config: RunnableConfig) -> dict:
        return await supervisor_tools(state, config, researcher_subgraph)

    supervisor_builder.add_node("supervisor_tools", supervisor_tools_node)

    supervisor_builder.add_edge(START, "supervisor")
    supervisor_builder.add_edge("supervisor", "supervisor_tools")
    
    def should_continue_supervision(state: SupervisorState) -> Literal["supervisor", "__end__"]:
        cfg = Configuration.from_runnable_config(RunnableConfig()) # Get default config
        last_message = state["supervisor_messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls and any(tc["name"] == "ResearchComplete" for tc in last_message.tool_calls):
            logger.info("[Supervisor Edge] 'ResearchComplete' called. Ending supervision.")
            return "__end__"
        if state.get("research_iterations", 0) > cfg.max_researcher_iterations:
            logger.info("[Supervisor Edge] Max supervisor iterations reached. Ending supervision.")
            return "__end__"
        logger.info("[Supervisor Edge] Continuing supervision.")
        return "supervisor"

    supervisor_builder.add_conditional_edges("supervisor_tools", should_continue_supervision)
    return supervisor_builder.compile()

def compile_deep_researcher_graph() -> Pregel:
    """Compiles and returns the full Deep Researcher graph."""
    researcher_subgraph = create_researcher_graph()
    supervisor_subgraph = create_supervisor_graph(researcher_subgraph)

    deep_researcher_builder = StateGraph(AgentState)
    
    deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
    deep_researcher_builder.add_node("write_research_brief", write_research_brief)
    deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)
    deep_researcher_builder.add_node("final_report_generation", final_report_generation)
    
    deep_researcher_builder.add_edge(START, "clarify_with_user")
    
    def should_start_research(state: AgentState) -> Literal["write_research_brief", "__end__"]:
        research_brief = state.get("research_brief", "")
        if state.get("final_report") == "CLARIFICATION" or (research_brief and "Error:" in research_brief):
            logger.warning(f"[Main Graph Edge] Clarification needed or error in brief. Ending graph. Brief: {research_brief}")
            return "__end__"
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
        # Initialize LLMs before running the graph
        await initialize_llms() # Call the initialization function
        
        graph = compile_deep_researcher_graph()
        
        # Make sure to set TAVILY_API_KEY environment variable
        
        inputs = {
            "messages": [HumanMessage(content="Compare the new AI models from Google and OpenAI.")],
            "account_id": "test-account"
        }
        
        # Create a RunnableConfig instance
        # The 'configurable' dictionary should match the expected structure for Configuration.from_runnable_config
        run_config = RunnableConfig(configurable={"account_id": "test-account", "tavily_api_key": os.getenv("TAVILY_API_KEY")})

        async for event in graph.astream_events(inputs, config=run_config, version="v1"):
            kind = event["event"]
            data = event.get("data", {})
            if kind == "on_chain_end":
                print(f"--- Event: {kind} ---")
                if "output" in data:
                    print(f"Output: {data['output']}")
            elif "chunk" in data and "messages" in data["chunk"]:
                 print(f"--- Event: {kind} ---")
                 print(f"Content: {data['chunk']['messages'][-1].content}")


    asyncio.run(run_example())