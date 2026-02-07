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

from core.llm_manager import get_main_llm, initialize_llms, get_fast_llm, get_fallback_llm # Import initialize_llms and get_fast_llm
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
    deep_research_think_tool,
    execute_tool_safely,
)
from core.utils.llm_utils import is_token_limit_exceeded, remove_up_to_last_ai_message, prune_messages_to_fit_token_limit


logger = logging.getLogger(__name__)

# --- Main Graph Nodes ---

async def clarify_with_user(state: AgentState, config: RunnableConfig) -> dict:
    logger.info("--- [DeepResearcher] Node: clarify_with_user ---")
    # Explicitly convert to list to ensure it's iterable and not a problematic generator
    messages_from_state_list = list(state.get("messages", []))
    current_messages: list[BaseMessage] = [cast(BaseMessage, msg) for msg in messages_from_state_list]
    
    logger.debug(f"🔍 [DeepResearcher] clarify_with_user - Current messages: {current_messages}")
    
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100) # Default to 100 if not set
    
    fast_llm = get_fast_llm()
    if not fast_llm:
        raise ValueError("Fast LLM not initialized.")

    main_llm = get_main_llm()
    if not main_llm:
        raise ValueError("Main LLM not initialized.")

    # Get and increment clarification attempts
    clarification_attempts = state.get("clarification_attempts", 0) + 1
    logger.info(f"🔄 [DeepResearcher] Clarification attempt: {clarification_attempts}")

    # Send initial progress update
    if progress_callback:
        progress = int(base_progress + max_sub_progress * 0.05)
        logger.info(f"Calling progress_callback in clarify_with_user: {progress}%")
        await progress_callback(progress, "Verificando claridad de la consulta...", "clarify_with_user")
    
    # Proactively prune messages to fit within the token limit
    pruned_messages_for_clarification = await prune_messages_to_fit_token_limit(
        current_messages, fast_llm, cfg.max_input_tokens
    )
    
    if not pruned_messages_for_clarification:
        logger.error("❌ [DeepResearcher] clarify_with_user - Pruned messages list is empty. Cannot invoke LLM.")
        return {"messages": [AIMessage(content="Error interno: La solicitud para clarificación está vacía.")], "final_report": "PROCEED", "clarification_attempts": clarification_attempts}

    prompt = clarify_with_user_instructions.format(messages=get_buffer_string(pruned_messages_for_clarification), date=get_today_str())
    logger.debug(f"📝 [DeepResearcher] clarify_with_user - Generated prompt: {prompt}")

    if not prompt:
        logger.error("❌ [DeepResearcher] clarify_with_user - Prompt is empty. Cannot invoke LLM.")
        return {"messages": [AIMessage(content="Error interno: La solicitud para clarificación está vacía.")], "final_report": "PROCEED", "clarification_attempts": clarification_attempts}

    # Try with fast LLM first
    clarification_model_fast = cast(Runnable[Sequence[BaseMessage], ClarifyWithUser],
                               fast_llm.with_structured_output(ClarifyWithUser).with_retry(
                                   stop_after_attempt=cfg.max_structured_output_retries
                               ))

    response = None
    try:
        response = await clarification_model_fast.ainvoke([HumanMessage(content=prompt)])
    except Exception as e:
        logger.warning(f"⚠️ [DeepResearcher] clarify_with_user - Fast LLM failed with error: {e}. Falling back to Main LLM.")
        response = None

    # Fallback to main LLM if fast LLM fails or returns None
    if response is None:
        logger.warning("⚠️ [DeepResearcher] clarify_with_user - Fast LLM returned None. Falling back to Main LLM.")
        clarification_model_main = cast(Runnable[Sequence[BaseMessage], ClarifyWithUser],
                                   main_llm.with_structured_output(ClarifyWithUser).with_retry(
                                       stop_after_attempt=cfg.max_structured_output_retries
                                   ))
        try:
            response = await clarification_model_main.ainvoke([HumanMessage(content=prompt)])
        except Exception as e:
            logger.error(f"❌ [DeepResearcher] clarify_with_user - Main LLM attempt also failed: {e}")
            response = None

    # If still None and error was context length related, try fallback LLM
    if response is None and 'e' in locals() and is_token_limit_exceeded(e):
        logger.warning("⚠️ [DeepResearcher] clarify_with_user - Context length exceeded. Trying fallback LLM.")
        fallback_llm = get_fallback_llm()
        if fallback_llm:
            try:
                clarification_model_fallback = cast(Runnable[Sequence[BaseMessage], ClarifyWithUser],
                                                   fallback_llm.with_structured_output(ClarifyWithUser).with_retry(
                                                       stop_after_attempt=cfg.max_structured_output_retries
                                                   ))
                response = await clarification_model_fallback.ainvoke([HumanMessage(content=prompt)])
                logger.info("✅ [DeepResearcher] clarify_with_user - Fallback LLM succeeded.")
            except Exception as fallback_e:
                logger.error(f"❌ [DeepResearcher] clarify_with_user - Fallback LLM also failed: {fallback_e}")
                response = None

    if response is None:
        logger.error("[DeepResearcher] clarify_with_user - All LLMs failed to return a valid ClarifyWithUser object.")
        # Default fallback to avoid crash - assume no clarification needed to proceed
        return {"messages": [AIMessage(content="Entendido. Procederé con la investigación basada en la información proporcionada.")], "final_report": "PROCEED", "clarification_attempts": clarification_attempts}

    # Check clarification attempts
    if clarification_attempts > cfg.max_clarification_attempts:
        logger.warning(f"⚠️ [DeepResearcher] Max clarification attempts ({cfg.max_clarification_attempts}) exceeded. Proceeding without further clarification.")
        # Force need_clarification to False to proceed
        response.need_clarification = False
        response.verification = "Se ha excedido el número máximo de intentos de clarificación. Procederé con la investigación basada en la información disponible."
        # No return here, let the normal flow handle the response.need_clarification = False

    if response.need_clarification:
        return {"messages": [AIMessage(content=response.question)], "final_report": "CLARIFICATION", "clarification_attempts": clarification_attempts}
    else:
        # If not need_clarification (either by LLM or forced by max attempts), proceed
        # Explicitly set final_report to None to ensure should_start_research proceeds
        return {"messages": [AIMessage(content=response.verification)], "final_report": None, "clarification_attempts": clarification_attempts}


async def write_research_brief(state: AgentState, config: RunnableConfig) -> dict:
    logger.info("--- [DeepResearcher] Node: write_research_brief ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)

    if progress_callback:
        # This node takes 5% of the total range (from 5% to 10%)
        progress = int(base_progress + max_sub_progress * 0.10)
        logger.info(f"Calling progress_callback in write_research_brief: {progress}%")
        await progress_callback(progress, "Generando el resumen de investigación...", "write_research_brief")
    
    fast_llm = get_fast_llm()
    main_llm = get_main_llm()

    if not fast_llm or not main_llm:
        raise ValueError("LLMs not initialized.")

    messages_from_state = [cast(BaseMessage, msg) for msg in state.get("messages", [])]
    
    # Proactively prune messages to fit within the token limit
    pruned_messages_for_brief = await prune_messages_to_fit_token_limit(
        messages_from_state, fast_llm, cfg.max_input_tokens
    )

    if not pruned_messages_for_brief:
        logger.error("❌ [DeepResearcher] write_research_brief - Pruned messages list is empty. Cannot invoke LLM.")
        return {"research_brief": "Error: La lista de mensajes para el resumen de investigación está vacía."}

    prompt_content = transform_messages_into_research_topic_prompt.format(
        messages=get_buffer_string(pruned_messages_for_brief),
        date=get_today_str()
    )

    # Try with fast LLM first
    research_model_fast = cast(Runnable[Sequence[BaseMessage], ResearchQuestion],
                          fast_llm.with_structured_output(ResearchQuestion).with_retry(
                              stop_after_attempt=cfg.max_structured_output_retries
                          ))

    # Prepare main LLM model for fallback
    research_model_main = cast(Runnable[Sequence[BaseMessage], ResearchQuestion],
                          main_llm.with_structured_output(ResearchQuestion).with_retry(
                              stop_after_attempt=cfg.max_structured_output_retries
                          ))

    try:
        response = await research_model_fast.ainvoke([HumanMessage(content=prompt_content)])
    except Exception as e:
        logger.warning(f"⚠️ [DeepResearcher] Fast LLM failed with error: {e}. Falling back to Main LLM.")
        response = None

    # Fallback to main LLM if fast LLM fails or returns None
    if response is None or not response.research_brief:
        logger.warning("⚠️ [DeepResearcher] Fast LLM failed to generate research brief. Falling back to Main LLM.")
        try:
            response = await research_model_main.ainvoke([HumanMessage(content=prompt_content)])
        except Exception as e:
            logger.error(f"❌ [DeepResearcher] Main LLM attempt also failed: {e}")
            response = None

    logger.info(f"📝 [DeepResearcher] write_research_brief - LLM Response: {response}")
    
    if response is None or not response.research_brief:
        logger.error("[DeepResearcher] write_research_brief - Both LLMs returned None for ResearchQuestion.")
        return {"research_brief": "Error: LLM failed to generate a research brief."}
    
    # Send progress update after successful brief generation
    if progress_callback:
        progress = int(base_progress + max_sub_progress * 0.12)
        logger.info(f"Calling progress_callback after research brief: {progress}%")
        await progress_callback(progress, "Resumen de investigación generado. Iniciando investigación...", "write_research_brief_complete")
    
    return {"research_brief": response.research_brief}


async def final_report_generation(state: AgentState, config: RunnableConfig) -> dict:
    """Generates the final comprehensive research report."""
    logger.info("--- [DeepResearcher] Node: final_report_generation ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)

    if progress_callback:
        # This node takes the final 10% of the main graph's progress (from 90% to 100%)
        # So, its base_progress will be 90% of the main range.
        current_global_progress = int(base_progress + max_sub_progress * 0.90)
        logger.info(f"Calling progress_callback in final_report_generation: {current_global_progress}%")
        await progress_callback(current_global_progress, "Generando el informe final...", "final_report_generation")

    raw_notes = state.get("raw_notes", [])
    findings = "\n\n".join(raw_notes)
    logger.info(f"📝 [DeepResearcher] Generating final report based on {len(raw_notes)} raw findings/notes.")
    
    writer_model = get_main_llm()
    if not writer_model:
        raise ValueError("Main LLM not initialized.")

    current_messages_list: list[BaseMessage] = [cast(BaseMessage, msg) for msg in state.get("messages", [])]

    # Proactively prune messages to fit within the token limit
    pruned_messages_for_report = await prune_messages_to_fit_token_limit(
        current_messages_list, writer_model, cfg.max_input_tokens, keep_ratio=0.3
    )

    # Truncate findings if they are excessively large (approx 100k chars ~ 25k tokens)
    max_findings_chars = 100000
    if len(findings) > max_findings_chars:
        logger.warning(f"⚠️ [DeepResearcher] Findings too large ({len(findings)} chars). Truncating to {max_findings_chars} chars.")
        findings = findings[:max_findings_chars] + "\n\n[... Findings truncated due to size ...]"

    final_report_prompt = final_report_generation_prompt.format(
        research_brief=state.get("research_brief", ""),
        messages=get_buffer_string(pruned_messages_for_report),
        findings=findings,
        date=get_today_str(),
    )
    
    try:
        final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt)])
    except Exception as e:
        if is_token_limit_exceeded(e):
            logger.warning("⚠️ [DeepResearcher] Final report generation failed due to token limit. Retrying with more aggressive pruning.")
            # Even more aggressive pruning
            pruned_messages_ultra = await prune_messages_to_fit_token_limit(
                current_messages_list, writer_model, cfg.max_input_tokens, keep_ratio=0.1
            )
            findings_ultra = findings[:50000] + "\n\n[... Findings aggressively truncated ...]"
            
            final_report_prompt_ultra = final_report_generation_prompt.format(
                research_brief=state.get("research_brief", ""),
                messages=get_buffer_string(pruned_messages_ultra),
                findings=findings_ultra,
                date=get_today_str(),
            )
            final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt_ultra)])
        else:
            raise e
    
    # Extract sources and recommendations from the supervisor messages
    sources = []
    recommendations = []
    
    # Use sources directly from state, populated by supervisor/researchers
    sources = state.get("sources", [])
    
    # Deduplicate sources based on URL
    unique_sources = []
    seen_urls = set()
    for source in sources:
        if source['url'] not in seen_urls:
            unique_sources.append(source)
            seen_urls.add(source['url'])
    
    # Re-assign IDs to be sequential
    for i, source in enumerate(unique_sources):
        source['id'] = i + 1
    
    sources = unique_sources

    # Extract recommendations from 'think_tool' calls
    # Access supervisor_messages from the state object
    for msg in state.get("supervisor_messages", []):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "think_tool":
                    reflection = tool_call["args"].get("reflection")
                    if reflection and "Acción:" in reflection:
                        action = reflection.split("Acción:")[1].strip()
                        if action not in recommendations:
                            recommendations.append(action)
    
    logger.info(f"📄 [DeepResearcher] Final report generated. Preview: {str(final_report.content)[:300]}...")
    return {
        "final_report": final_report.content,
        "messages": [final_report],
        "sources": sources,
        "recommendations": recommendations
    }

# --- Supervisor Sub-Graph Nodes ---

async def supervisor(state: SupervisorState, config: RunnableConfig) -> dict:
    """Plans research strategy and delegates to researchers."""
    logger.info("--- [DeepResearcher] Node: supervisor ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)

    if progress_callback:
        # Supervisor's overall range is 10% to 90%
        # Calculate its progress within this range based on iterations
        current_iteration = state.get("research_iterations", 0)
        # Ensure max_researcher_iterations is at least 1 to prevent ZeroDivisionError
        total_iterations = cfg.max_researcher_iterations or 1
        
        # Supervisor's range starts after write_research_brief (which ends at 12%)
        # and goes up to final_report_generation (which starts at 90%).
        # So, the effective range for supervisor is 78% (90-12).
        supervisor_range_start = int(base_progress + max_sub_progress * 0.12) # 12%
        supervisor_range_end = int(base_progress + max_sub_progress * 0.90)   # 90%
        effective_supervisor_range = supervisor_range_end - supervisor_range_start

        # Calculate progress within the supervisor's effective range
        # Add a minimum of 5% to ensure visible progress
        progress_within_supervisor_range = max(5, (current_iteration / total_iterations) * effective_supervisor_range)
        current_global_progress = int(supervisor_range_start + progress_within_supervisor_range)
        
        logger.info(f"Calling progress_callback in supervisor: {current_global_progress}%")
        await progress_callback(current_global_progress, f"Supervisor: Planificando iteración de investigación {current_iteration + 1}/{total_iterations}", "supervisor")

    llm = get_fast_llm()
    if not llm:
        raise ValueError("Main LLM not initialized.")

    # Cast to BaseChatModel to ensure bind_tools is available
    chat_llm = cast(BaseChatModel, llm)

    # Check if think_tool was used in the last AI message
    # If so, remove it from available tools to force action
    lead_researcher_tools = [ConductResearch, ResearchComplete, deep_research_think_tool]
    
    if state.get("supervisor_messages"):
        last_ai_msg = next((m for m in reversed(state["supervisor_messages"]) if isinstance(m, AIMessage)), None)
        if last_ai_msg and last_ai_msg.tool_calls:
            # Check if the last tool call was think_tool
            if any(tc["name"] == "deep_research_think_tool" for tc in last_ai_msg.tool_calls):
                # Remove think_tool to force the LLM to take action
                lead_researcher_tools = [ConductResearch, ResearchComplete]
                logger.info("🚫 [Supervisor] Removing think_tool from available tools to force action execution.")

    supervisor_system_prompt = lead_researcher_prompt.format(
        date=get_today_str(),
        max_concurrent_research_units=cfg.max_concurrent_research_units,
        max_researcher_iterations=cfg.max_researcher_iterations
    )

    research_model = cast(Runnable[Sequence[BaseMessage], AIMessage],
                          chat_llm.bind_tools(
                              lead_researcher_tools
                          ).with_retry(
                              stop_after_attempt=cfg.max_structured_output_retries
                          ))

    messages: list[BaseMessage] = [SystemMessage(content=supervisor_system_prompt)]
    initial_human_message_content = f"Plan research for: {state.get('research_brief', '')}"

    if not state.get("supervisor_messages"):
        logger.info("First supervisor run. Planning initial research.")
        messages.append(HumanMessage(content=initial_human_message_content))
    else:
        logger.info(f"Supervisor continuing with {len(state['supervisor_messages'])} previous messages.")
        valid_messages = [cast(BaseMessage, msg) for msg in state["supervisor_messages"] if isinstance(msg, (AIMessage, HumanMessage, SystemMessage, ToolMessage))]
        messages.extend(valid_messages)
        
        # CRITICAL FIX: Ensure we don't break the tool_call -> tool_message sequence.
        # Only append a HumanMessage if the last message is NOT an AIMessage with tool_calls.
        last_msg = messages[-1] if messages else None
        is_tool_call_pending = isinstance(last_msg, AIMessage) and bool(last_msg.tool_calls)
        
        if not is_tool_call_pending and (not messages or not isinstance(messages[-1], HumanMessage)):
            # Check if the last tool call was 'deep_research_think_tool' to provide a nudge
            last_ai_msg = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
            if last_ai_msg and last_ai_msg.tool_calls and any(tc["name"] == "deep_research_think_tool" for tc in last_ai_msg.tool_calls):
                messages.append(HumanMessage(content="IMPORTANT: Your planning is complete. You MUST now execute your plan by calling the ConductResearch tool for each sub-topic you identified. Do NOT call deep_research_think_tool again. Call ConductResearch now."))
            else:
                messages.append(HumanMessage(content="Continue planning research based on the previous interactions."))

    # Proactively prune messages to fit within the token limit
    pruned_messages_for_supervisor = await prune_messages_to_fit_token_limit(
        messages, chat_llm, cfg.max_input_tokens
    )

    logger.debug(f"🔍 [DeepResearcher] supervisor - Pruned messages for supervisor: {pruned_messages_for_supervisor}")
    if not pruned_messages_for_supervisor:
        logger.error("❌ [DeepResearcher] supervisor - Pruned messages list is empty. Cannot invoke LLM.")
        return {"supervisor_messages": state.get("supervisor_messages", []) + [AIMessage(content="Error interno: La lista de mensajes para el supervisor está vacía.")], "research_iterations": state.get("research_iterations", 0) + 1}

    try:
        response: AIMessage = await research_model.ainvoke(pruned_messages_for_supervisor)
    except Exception as e:
        if is_token_limit_exceeded(e):
            logger.warning("⚠️ [Supervisor] Token limit exceeded. Pruning history and retrying...")
            # Reactive pruning (should be less frequent now)
            pruned_messages = remove_up_to_last_ai_message([cast(BaseMessage, msg) for msg in messages])
            if len(pruned_messages) < len(messages):
                response = await research_model.ainvoke([cast(BaseMessage, msg) for msg in pruned_messages])
            else:
                logger.error("❌ [Supervisor] Token limit exceeded and cannot prune further.")
                raise e
        else:
            raise e

    if response.tool_calls:
        for tool_call in response.tool_calls:
            logger.info(f"📋 [Supervisor] LLM decided to call tool: {tool_call['name']} with args: {tool_call['args']}")
    else:
        logger.warning("[Supervisor] LLM did not generate any tool calls.")

    return {
        "supervisor_messages": [response],
        "research_iterations": state.get("research_iterations", 0) + 1,
    }

async def supervisor_tools(state: SupervisorState, config: RunnableConfig, researcher_subgraph: Pregel) -> dict:
    """Executes tools called by the supervisor."""
    logger.info("--- [DeepResearcher] Node: supervisor_tools ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)
    most_recent_message: AIMessage = cast(AIMessage, state["supervisor_messages"][-1])

    # Supervisor's overall range is 12% to 90% of the main graph's total progress.
    supervisor_range_start = int(base_progress + max_sub_progress * 0.12)
    supervisor_range_end = int(base_progress + max_sub_progress * 0.90)
    effective_supervisor_range = supervisor_range_end - supervisor_range_start
    
    # Calculate progress for supervisor_tools node itself
    if progress_callback:
        # We can allocate a small initial percentage for tool execution setup, e.g., 5% of the supervisor's effective range
        current_global_progress = int(supervisor_range_start + effective_supervisor_range * 0.05)
        logger.info(f"Calling progress_callback in supervisor_tools: {current_global_progress}%")
        await progress_callback(current_global_progress, "Supervisor: Preparando herramientas de investigación...", "supervisor_tools")

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

    all_tool_messages = []
    update_payload = {}

    tool_calls = most_recent_message.tool_calls
    logger.info(f"[Supervisor Tools] Processing {len(tool_calls)} tool calls in exact order.")

    # Prepare to store results in a way that maintains order
    tool_results_map = {}
    conduct_research_tasks = []
    conduct_research_indices = []

    # 1. Identify and initiate ConductResearch tasks
    for i, tc in enumerate(tool_calls):
        if tc["name"] == "ConductResearch":
            conduct_research_indices.append(i)
            
            # Setup progress and config for this specific task
            total_supervisor_iterations = cfg.max_researcher_iterations or 1
            progress_for_researchers_in_supervisor_range = effective_supervisor_range * 0.95
            current_supervisor_iteration_share = progress_for_researchers_in_supervisor_range / total_supervisor_iterations
            iteration_base_progress = supervisor_range_start + (state.get("research_iterations", 0) - 1) * current_supervisor_iteration_share
            
            num_concurrent_research = sum(1 for t in tool_calls if t["name"] == "ConductResearch")
            single_researcher_progress_range = current_supervisor_iteration_share / num_concurrent_research if num_concurrent_research > 0 else 0
            
            subgraph_config = config.copy()
            # Use current count of research tasks for progress calculation
            task_idx = len(conduct_research_tasks)
            subgraph_base_progress = iteration_base_progress + task_idx * single_researcher_progress_range
            subgraph_max_sub_progress = single_researcher_progress_range

            if "configurable" not in subgraph_config:
                subgraph_config["configurable"] = {}
            subgraph_config.get("configurable", {})["progress_callback"] = progress_callback
            subgraph_config.get("configurable", {})["base_progress"] = subgraph_base_progress
            subgraph_config.get("configurable", {})["max_sub_progress"] = subgraph_max_sub_progress
            
            task = researcher_subgraph.ainvoke({
                "researcher_messages": [HumanMessage(content=tc["args"]["research_topic"])],
                "research_topic": tc["args"]["research_topic"],
                "account_id": state["account_id"],
            }, subgraph_config)
            conduct_research_tasks.append(task)
        else:
            # For non-research tools, we can determine the result immediately
            content = "Acknowledged."
            if tc["name"] == "ResearchComplete":
                content = "Research marked as complete. Proceeding to final report."
            elif tc["name"] == "deep_research_think_tool":
                content = f"Thought processed: {tc['args'].get('reflection', 'No reflection provided.')}"
            
            tool_results_map[i] = ToolMessage(
                content=content,
                name=tc["name"],
                tool_call_id=tc["id"]
            )

    # 2. Execute parallel research tasks if any
    if conduct_research_tasks:
        logger.info(f"🚀 [Supervisor Tools] Starting {len(conduct_research_tasks)} parallel research tasks.")
        parallel_results = await asyncio.gather(*conduct_research_tasks)
        logger.info("✅ [Supervisor Tools] All parallel research tasks completed.")
        
        # Store parallel results in the map
        for idx, result in zip(conduct_research_indices, parallel_results):
            compressed_result = result.get("compressed_research", "Error: No compressed research found.")
            tool_results_map[idx] = ToolMessage(
                content=compressed_result,
                name=tool_calls[idx]["name"],
                tool_call_id=tool_calls[idx]["id"],
            )
            
            # Collect notes and sources
            if "raw_notes" in result:
                if "raw_notes" not in update_payload: update_payload["raw_notes"] = []
                update_payload["raw_notes"].extend(result["raw_notes"])
            if "sources" in result:
                if "sources" not in update_payload: update_payload["sources"] = []
                update_payload["sources"].extend(result["sources"])

    # 3. Construct the final list of ToolMessages in the ORIGINAL order
    for i in range(len(tool_calls)):
        if i in tool_results_map:
            all_tool_messages.append(tool_results_map[i])

    update_payload["supervisor_messages"] = all_tool_messages
    return update_payload

# --- Researcher Sub-Graph Nodes ---

async def researcher(state: ResearcherState, config: RunnableConfig) -> dict:
    """Conducts focused research on a specific topic."""
    logger.info(f"--- [DeepResearcher] Node: researcher ---")
    logger.info(f"🔍 [Researcher] Researching topic: '{state['research_topic']}'")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)

    if progress_callback:
        current_tool_iteration = state.get("tool_call_iterations", 0)
        total_tool_calls = cfg.max_react_tool_calls or 1
        
        # Researcher's overall range is max_sub_progress.
        # It will use 90% of its assigned range for tool calls and internal thinking.
        effective_researcher_range = max_sub_progress * 0.90 # 90% of the allocated range for research steps
        
        progress_per_iteration = effective_researcher_range / total_tool_calls
        current_progress_within_researcher_range = current_tool_iteration * progress_per_iteration
        
        current_global_progress = int(base_progress + current_progress_within_researcher_range)
        
        logger.info(f"Calling progress_callback in researcher: {current_global_progress}% for topic {state['research_topic']}")
        await progress_callback(current_global_progress, f"Investigando: {state['research_topic']} (Paso {current_tool_iteration + 1}/{total_tool_calls})", f"researcher_{state['research_topic']}")
    
    tools = await get_all_tools(config)
    if not tools:
        logger.error("[Researcher] No tools found for research. Aborting.")
        raise ValueError("No tools found for research.")

    llm_instance = get_fast_llm()
    if not llm_instance:
        raise ValueError("Main LLM not initialized.")
    chat_llm = cast(BaseChatModel, llm_instance)

    researcher_prompt = research_system_prompt.format(mcp_prompt=cfg.mcp_prompt or "", date=get_today_str())
    research_model = cast(Runnable[Sequence[BaseMessage], AIMessage],
                          chat_llm.bind_tools(tools).with_retry(
                              stop_after_attempt=cfg.max_structured_output_retries
                          ))
    
    messages = [cast(BaseMessage, msg) for msg in state["researcher_messages"]]
    
    # Prepend system prompt to the first HumanMessage if it exists, otherwise create one.
    if messages and isinstance(messages[0], HumanMessage):
        messages[0].content = f"{researcher_prompt}\n\n{messages[0].content}"
    elif messages and isinstance(messages[0], (AIMessage, ToolMessage)):
        # If the first message from history is not Human, inject a HumanMessage with system prompt
        messages.insert(0, HumanMessage(content=researcher_prompt))
    else:
        # If no messages or first is not human, create one with system prompt
        messages.insert(0, HumanMessage(content=researcher_prompt))
    
    # Ensure the conversation always ends with a HumanMessage for Vertex AI compatibility,
    # but ONLY if there are no pending tool calls.
    last_msg = messages[-1] if messages else None
    is_tool_call_pending = isinstance(last_msg, AIMessage) and bool(last_msg.tool_calls)

    if not is_tool_call_pending and (not messages or not isinstance(messages[-1], HumanMessage)):
        if messages and messages[-1].type == "ai":
            messages.append(HumanMessage(content=f"Continue research based on the previous AI response for topic: {state['research_topic']}"))
        elif messages and messages[-1].type == "tool":
            messages.append(HumanMessage(content=f"Process the tool output and continue research for topic: {state['research_topic']}"))
        else:
            messages.append(HumanMessage(content=f"Continue research for topic: {state['research_topic']}"))

    # Proactively prune messages to fit within the token limit
    pruned_messages_for_researcher = await prune_messages_to_fit_token_limit(
        messages, chat_llm, cfg.max_input_tokens
    )

    logger.info(f"PRUNED MESSAGES FOR RESEARCHER: {pruned_messages_for_researcher}")

    try:
        response: AIMessage = await research_model.ainvoke(pruned_messages_for_researcher)
    except Exception as e:
        if is_token_limit_exceeded(e):
            logger.warning(f"⚠️ [Researcher] Token limit exceeded for topic '{state['research_topic']}'. Pruning history and retrying...")
            # Reactive pruning (should be less frequent now)
            pruned_messages = remove_up_to_last_ai_message([cast(BaseMessage, msg) for msg in messages])
            if len(pruned_messages) < len(messages):
                response = await research_model.ainvoke([cast(BaseMessage, msg) for msg in pruned_messages])
            else:
                logger.error(f"❌ [Researcher] Token limit exceeded for topic '{state['research_topic']}' and cannot prune further.")
                raise e
        else:
            raise e
    
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
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)
    most_recent_message: AIMessage = cast(AIMessage, state["researcher_messages"][-1])

    if progress_callback:
        # Calculate progress within the researcher's allocated range
        # Assume tool execution is roughly 20% of the researcher's total allocated range (max_sub_progress)
        progress_at_start_of_tools = base_progress + max_sub_progress * 0.70  # After thinking phase (70%)
        progress_at_end_of_tools = base_progress + max_sub_progress * 0.90    # Before compression phase (10%)
        
        logger.info(f"Calling progress_callback in researcher_tools: {int(progress_at_start_of_tools)}% for topic {state['research_topic']}")
        await progress_callback(int(progress_at_start_of_tools), f"Ejecutando herramientas para: {state['research_topic']}", f"researcher_tools_start_{state['research_topic']}")

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

    if progress_callback:
        logger.info(f"Calling progress_callback in researcher_tools: {int(progress_at_end_of_tools)}% for topic {state['research_topic']}")
        await progress_callback(int(progress_at_end_of_tools), f"Herramientas ejecutadas para: {state['research_topic']}", f"researcher_tools_end_{state['research_topic']}")

    tool_outputs = []
    for obs, tc in zip(observations, most_recent_message.tool_calls):
        logger.info(f"🔧 [Researcher Tools] Result for '{tc['name']}': '{str(obs)[:200]}...'")
        tool_outputs.append(ToolMessage(content=str(obs), name=tc["name"], tool_call_id=tc["id"]))

    return {"researcher_messages": tool_outputs}


async def compress_research(state: ResearcherState, config: RunnableConfig) -> dict:
    """Compresses and synthesizes research findings."""
    logger.info("--- [DeepResearcher] Node: compress_research ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100) # Default to 100 if not explicitly passed

    if progress_callback:
        # This node represents the compression phase, which is the final step of the researcher.
        # It should bring the progress close to the end of the researcher's allocated range.
        # We can set it to 90% of the researcher's max_sub_progress (after the 90% effective range for research steps).
        
        final_researcher_progress = int(base_progress + max_sub_progress * 0.98) # 98% of the allocated range for compression
        logger.info(f"Calling progress_callback in compress_research: {final_researcher_progress}% for topic {state['research_topic']}")
        await progress_callback(final_researcher_progress, f"Sintetizando hallazgos para: {state['research_topic']}", f"compress_research_{state['research_topic']}")

    synthesizer_model = get_fast_llm()
    if not synthesizer_model:
        raise ValueError("Main LLM not initialized.")


    researcher_messages = [cast(BaseMessage, msg) for msg in state["researcher_messages"]] + [HumanMessage(content=compress_research_simple_human_message)]
    
    compression_prompt = compress_research_system_prompt.format(date=get_today_str())
    messages = [SystemMessage(content=compression_prompt)] + researcher_messages

    logger.info(f"📚 [Compress Research] Compressing {len(researcher_messages)} messages.")
    response = await synthesizer_model.ainvoke(messages)

    raw_notes_content = "\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])

    logger.info(f"📦 [Compress Research] Compressed research output preview: '{str(response.content)[:200]}...'")

    # Extract sources from researcher messages
    sources = []
    for msg in researcher_messages:
        if isinstance(msg, ToolMessage) and msg.name == "tavily_search":
            try:
                content_str = str(msg.content)
                import re
                urls = re.findall(r'URL: (https?://\S+)', content_str)
                titles = re.findall(r'--- SOURCE \d+: (.*?) ---', content_str)
                
                if not urls:
                    urls = re.findall(r'https?://[^\s\]\)]+', content_str)
                
                for i, url in enumerate(urls):
                    title = "Source"
                    if i < len(titles):
                        title = titles[i]
                    
                    sources.append({
                        "title": title,
                        "url": url,
                        "snippet": "",
                        "type": "web"
                    })
            except Exception as e:
                logger.warning(f"Error extracting sources in compress_research: {e}")

    return {
        "compressed_research": str(response.content),
        "raw_notes": [raw_notes_content],
        "sources": sources
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
    
    def should_continue_research(state: ResearcherState, config: RunnableConfig) -> Literal["researcher", "compress_research"]:
        cfg = Configuration.from_runnable_config(config)
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
    
    def should_continue_supervision(state: SupervisorState, config: RunnableConfig) -> Literal["supervisor", "__end__"]:
        cfg = Configuration.from_runnable_config(config)
        last_message = state["supervisor_messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls and any(tc["name"] == "ResearchComplete" for tc in last_message.tool_calls):
            logger.info("[Supervisor Edge] 'ResearchComplete' called. Ending supervision.")
            return "__end__"
        if state.get("research_iterations", 0) >= cfg.max_researcher_iterations:
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
    deep_researcher_builder.add_node("await_user_clarification", lambda state: state) # Nodo de pausa, no hace nada más que esperar
    
    deep_researcher_builder.add_edge(START, "clarify_with_user")
    
    def should_start_research(state: AgentState) -> Literal["write_research_brief", "await_user_clarification", "__end__"]:
        research_brief = state.get("research_brief", "")
        if state.get("final_report") == "CLARIFICATION":
            logger.warning(f"[Main Graph Edge] Clarification needed. Moving to await_user_clarification. Brief: {research_brief}")
            return "await_user_clarification"
        elif research_brief and "Error:" in research_brief:
            logger.warning(f"[Main Graph Edge] Error in brief. Ending graph. Brief: {research_brief}")
            return "__end__"
        logger.info("[Main Graph Edge] Brief is clear. Proceeding to research.")
        return "write_research_brief"

    deep_researcher_builder.add_conditional_edges("clarify_with_user", should_start_research)
    
    def should_proceed_to_supervisor(state: AgentState) -> Literal["research_supervisor", "__end__"]:
        research_brief = state.get("research_brief", "")
        if research_brief and "Error:" in research_brief:
            logger.error(f"[Main Graph Edge] Error in research brief. Aborting research. Brief: {research_brief}")
            return "__end__"
        return "research_supervisor"

    deep_researcher_builder.add_conditional_edges("write_research_brief", should_proceed_to_supervisor)
    deep_researcher_builder.add_edge("research_supervisor", "final_report_generation")
    deep_researcher_builder.add_edge("final_report_generation", END)
    
    deep_researcher_builder.add_edge("await_user_clarification", END)

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