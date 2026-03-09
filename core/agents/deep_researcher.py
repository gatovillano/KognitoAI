# core/agents/deep_researcher.py

import asyncio
import uuid
import json
import logging
import os
import re
from typing import Any, Literal, Sequence, cast

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
    generate_stable_id,
)
from core.utils.llm_utils import (
    is_token_limit_exceeded, 
    remove_up_to_last_ai_message, 
    prune_messages_to_fit_token_limit,
    invoke_structured_output
)


# --- Helpers ---


logger = logging.getLogger(__name__)

# --- Main Graph Nodes ---

async def clarify_with_user(state: AgentState, config: RunnableConfig) -> dict:
    logger.debug("--- [DeepResearcher] Node: clarify_with_user ---")
    # Explicitly convert to list to ensure it's iterable and not a problematic generator
    messages_from_state_list = list(state.get("messages", []))
    current_messages: list[BaseMessage] = [cast(BaseMessage, msg) for msg in messages_from_state_list]
    
    logger.debug(f"🔍 [DeepResearcher] clarify_with_user - Current messages count: {len(current_messages)}")
    
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100) # Default to 100 if not set
    
    # Get and increment clarification attempts
    account_id = state.get("account_id")
    from core.llm_manager import get_llm_for_user
    
    if account_id:
        fast_llm = await get_llm_for_user(account_id, purpose="fast")
        main_llm = await get_llm_for_user(account_id, purpose="main")
    else:
        fast_llm = get_fast_llm()
        main_llm = get_main_llm()

    if not fast_llm:
        raise ValueError("Fast LLM not initialized.")
    if not main_llm:
        raise ValueError("Main LLM not initialized.")

    clarification_attempts = state.get("clarification_attempts", 0) + 1
    logger.debug(f"🔄 [DeepResearcher] Clarification attempt: {clarification_attempts}")

    # Send initial progress update
    if progress_callback:
        progress = int(base_progress + max_sub_progress * 0.05)
        logger.debug(f"Calling progress_callback in clarify_with_user: {progress}%")
        await progress_callback(progress, "Verificando claridad de la consulta...", "clarify_with_user")
    
    # Proactively prune messages to fit within the token limit
    pruned_messages_for_clarification = await prune_messages_to_fit_token_limit(
        current_messages, fast_llm, cfg.max_input_tokens
    )
    
    if not pruned_messages_for_clarification:
        logger.error("❌ [DeepResearcher] clarify_with_user - Pruned messages list is empty. Cannot invoke LLM.")
        return {"messages": [AIMessage(content="Error interno: La solicitud para clarificación está vacía.")], "final_report": "PROCEED", "clarification_attempts": clarification_attempts}

    prompt = clarify_with_user_instructions.format(messages=get_buffer_string(pruned_messages_for_clarification), date=get_today_str())
    logger.debug(f"📝 [DeepResearcher] clarify_with_user - Prompt generated.")

    if not prompt:
        logger.error("❌ [DeepResearcher] clarify_with_user - Prompt is empty. Cannot invoke LLM.")
        return {"messages": [AIMessage(content="Error interno: La solicitud para clarificación está vacía.")], "final_report": "PROCEED", "clarification_attempts": clarification_attempts}

    # Try with fast LLM first
    retry_cfg = {"stop_after_attempt": cfg.max_structured_output_retries}
    
    response = None
    try:
        response = await invoke_structured_output(fast_llm, ClarifyWithUser, prompt, retry_cfg)
    except Exception as e:
        error_str = str(e)
        if "tool_choice" in error_str and "Openrouter" in error_str:
            logger.warning(f"⚠️ [DeepResearcher] clarify_with_user - OpenRouter tool_choice error. Retrying with json_mode.")
            try:
                # Forcing json_mode for providers that support it but fail with tool_choice
                model_with_json = fast_llm.with_structured_output(ClarifyWithUser, method="json_mode")
                response = await model_with_json.ainvoke([HumanMessage(content=prompt)])
            except Exception as e2:
                logger.warning(f"⚠️ [DeepResearcher] clarify_with_user - Retry with json_mode failed: {e2}. Falling back to Main LLM.")
                response = None
        else:
            logger.warning(f"⚠️ [DeepResearcher] clarify_with_user - Fast LLM failed: {e}. Falling back to Main LLM.")
            response = None

    # Fallback to main LLM
    if response is None:
        logger.warning("⚠️ [DeepResearcher] clarify_with_user - Trying Main LLM.")
        try:
            response = await invoke_structured_output(main_llm, ClarifyWithUser, prompt, retry_cfg)
        except Exception as e:
            logger.error(f"❌ [DeepResearcher] clarify_with_user - Main LLM also failed: {e}")
            response = None

    # If still None and error was context length related, try fallback LLM
    if response is None and 'e' in locals() and is_token_limit_exceeded(e):
        logger.warning("⚠️ [DeepResearcher] clarify_with_user - Context length exceeded. Trying fallback LLM.")
        fallback_llm = get_fallback_llm()
        if fallback_llm:
            try:
                clarification_model_fallback = cast(Runnable[Sequence[BaseMessage], ClarifyWithUser],
                                                   fallback_llm.with_structured_output(
                                                       ClarifyWithUser
                                                   ).with_retry(
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
    logger.debug("--- [DeepResearcher] Node: write_research_brief ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)

    if progress_callback:
        # This node takes 5% of the total range (from 5% to 10%)
        progress = int(base_progress + max_sub_progress * 0.10)
        logger.debug(f"Calling progress_callback in write_research_brief: {progress}%")
        await progress_callback(progress, "Generando el resumen de investigación...", "write_research_brief")
    
    account_id = state.get("account_id")
    from core.llm_manager import get_llm_for_user

    if account_id:
        fast_llm = await get_llm_for_user(account_id, purpose="fast")
        main_llm = await get_llm_for_user(account_id, purpose="main")
    else:
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
    retry_cfg = {"stop_after_attempt": cfg.max_structured_output_retries}
    
    try:
        response = await invoke_structured_output(fast_llm, ResearchQuestion, prompt_content, retry_cfg)
    except Exception as e:
        error_str = str(e)
        if "tool_choice" in error_str and "Openrouter" in error_str:
            logger.warning(f"⚠️ [DeepResearcher] write_research_brief - OpenRouter tool_choice error. Retrying with json_mode.")
            try:
                model_with_json = fast_llm.with_structured_output(ResearchQuestion, method="json_mode")
                response = await model_with_json.ainvoke([HumanMessage(content=prompt_content)])
            except Exception as e2:
                logger.warning(f"⚠️ [DeepResearcher] write_research_brief - Retry with json_mode failed: {e2}. Falling back to Main LLM.")
                response = None
        else:
            logger.warning(f"⚠️ [DeepResearcher] write_research_brief - Fast LLM failed: {e}. Falling back to Main LLM.")
            response = None

    # Fallback to main LLM if fast LLM fails or returns None
    if response is None or not response.research_brief:
        logger.warning("⚠️ [DeepResearcher] write_research_brief - Trying Main LLM.")
        try:
            response = await invoke_structured_output(main_llm, ResearchQuestion, prompt_content, retry_cfg)
        except Exception as e:
            logger.error(f"❌ [DeepResearcher] write_research_brief - Main LLM also failed: {e}")
            response = None

    logger.debug(f"📝 [DeepResearcher] write_research_brief - LLM Response received.")
    
    if response is None or not getattr(response, 'research_brief', None):
        logger.error(f"[DeepResearcher] write_research_brief - Both LLMs returned None or invalid response for ResearchQuestion. Response: {response}")
        return {"research_brief": "Error: LLM failed to generate a research brief."}
    
    # Send progress update after successful brief generation
    if progress_callback:
        progress = int(base_progress + max_sub_progress * 0.12)
        logger.debug(f"Calling progress_callback after research brief: {progress}%")
        await progress_callback(progress, "Resumen de investigación generado. Iniciando investigación...", "write_research_brief_complete")
    
    return {"research_brief": response.research_brief}


async def final_report_generation(state: AgentState, config: RunnableConfig) -> dict:
    """Generates the final comprehensive research report divided into sections."""
    logger.debug("--- [DeepResearcher] Node: final_report_generation ---")
    cfg = Configuration.from_runnable_config(config)
    progress_callback = config.get("configurable", {}).get("progress_callback")
    base_progress = config.get("configurable", {}).get("base_progress", 0)
    max_sub_progress = config.get("configurable", {}).get("max_sub_progress", 100)

    if progress_callback:
        # This node takes the final 10% of the main graph's progress (from 90% to 100%)
        # So, its base_progress will be 90% of the main range.
        current_global_progress = int(base_progress + max_sub_progress * 0.90)
        logger.debug(f"Calling progress_callback in final_report_generation: {current_global_progress}%")
        await progress_callback(current_global_progress, "Generando el informe final...", "final_report_generation")

    account_id = state.get("account_id")
    from core.llm_manager import get_llm_for_user
    
    if account_id:
        writer_model = await get_llm_for_user(account_id, purpose="main")
    else:
        writer_model = get_main_llm()

    if not writer_model:
        raise ValueError("Main LLM not initialized.")

    current_messages_list: list[BaseMessage] = [cast(BaseMessage, msg) for msg in state.get("messages", [])]

    # Proactively prune messages to fit within the token limit
    pruned_messages_for_report = await prune_messages_to_fit_token_limit(
        current_messages_list, writer_model, cfg.max_input_tokens, keep_ratio=0.3
    )

    # Retrieve findings from the state
    findings = "\n\n".join(state.get("notes", []))

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
    final_report_prompt += "\n\nIMPORTANTE: Al citar fuentes, cada número de fuente debe estar entre sus propios corchetes. Por ejemplo, en lugar de [1, 2, 3], formatee como [1][2][3]."
    
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
    
    logger.debug(f"📄 [DeepResearcher] Sources received in final_report_generation: {len(sources)}")
    for i, s in enumerate(sources):
        logger.debug(f"📄 [DeepResearcher] Source {i+1}: {s.get('title', 'No title')} - {s.get('url', 'No URL')[:50]}...")
    
    # Deduplicate sources based on URL while merging metadata from duplicates
    unique_sources = []
    seen_urls: Dict[str, dict] = {}
    for source in sources:
        url = source.get('url')
        if not url:
            # Keep sources without URL as-is
            unique_sources.append(source)
            continue
        
        if url not in seen_urls:
            # First occurrence: add as-is
            unique_sources.append(source)
            seen_urls[url] = source
        else:
            # Duplicate: ensure same ID and merge metadata, then add duplicate
            existing = seen_urls[url]
            # Ensure the duplicate uses the same ID as the first (stable ID)
            source['id'] = existing['id']
            
            # Merge metadata
            if 'metadata' not in existing:
                existing['metadata'] = {}
            if 'metadata' not in source:
                source['metadata'] = {}
            
            # Merge tool_names (combine without duplicates)
            existing_tools = set(existing['metadata'].get('tool_names', []))
            new_tools = set(source['metadata'].get('tool_names', []))
            merged_tools = list(existing_tools | new_tools)
            existing['metadata']['tool_names'] = merged_tools

            # Add the duplicate to the list (with merged metadata)

            unique_sources.append(source)
    
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
    
    # Parse the final report into sections
    report_content = final_report.content
    # Mark which sources are cited in the report text
    citation_numbers = set()
    for match in re.findall(r'\[(\d+)\]', report_content):
        try:
            num = int(match)
            citation_numbers.add(num)
        except ValueError:
            continue
    
    for idx, source in enumerate(sources):
        source['is_cited'] = (idx + 1) in citation_numbers
    summary = ""
    findings = ""
    recommendations_section = ""

    # Extract Summary (Resumen Ejecutivo)
    summary_match = re.search(r"Resumen Ejecutivo.*?(?=Introducción|Introducción, Metodología y Marco Teórico|$)", report_content, re.DOTALL | re.IGNORECASE)
    if summary_match:
        summary = summary_match.group(0).strip()
        # Remove the section title to clean it up
        summary = re.sub(r"^.*?Resumen Ejecutivo", "", summary, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # Extract Findings (Introducción, Metodología, Análisis Temático, Integración, Conclusión)
    findings_match = re.search(r"(Introducción|Introducción, Metodología y Marco Teórico).*?(?=Implicaciones Estratégicas|Recomendaciones|Bibliografía|$)", report_content, re.DOTALL | re.IGNORECASE)
    if findings_match:
        findings = findings_match.group(0).strip()
    
    # Extract Recommendations (Implicaciones Estratégicas, Proyecciones y Recomendaciones)
    recommendations_match = re.search(r"(Implicaciones Estratégicas|Recomendaciones).*?(?=Conclusión|Bibliografía|$)", report_content, re.DOTALL | re.IGNORECASE)
    if recommendations_match:
        recommendations_section = recommendations_match.group(0).strip()
    
    # Extract Visual Schema
    visual_schema = ""
    schema_match = re.search(r"<visual_schema>(.*?)</visual_schema>", report_content, re.DOTALL | re.IGNORECASE)
    if schema_match:
        visual_schema = schema_match.group(1).strip()
        # Clean up the report content by removing the schema tag
        report_content = re.sub(r"<visual_schema>.*?</visual_schema>", "", report_content, flags=re.DOTALL | re.IGNORECASE).strip()

    logger.info(f"📄 [DeepResearcher] Final report generated with sections: Summary ({len(summary)} chars), Findings ({len(findings)} chars), Recommendations ({len(recommendations_section)} chars), Visual Schema ({len(visual_schema)} chars), {len(sources)} sources, {len(recommendations)} think-tool recommendations")
    
    return {
        "final_report": report_content,  # Keep full report for backward compatibility
        "summary": summary if summary else report_content[:1000] + "...",  # Fallback if no summary section
        "findings": findings if findings else report_content,  # Fallback if no findings section
        "recommendations": recommendations if recommendations else ([recommendations_section] if recommendations_section else []),  # Fallback to extracted recommendations
        "messages": [final_report],
        "sources": sources,
        "visual_schema": visual_schema if visual_schema else None,
    }

# --- Supervisor Sub-Graph Nodes ---

async def supervisor(state: SupervisorState, config: RunnableConfig) -> dict:
    """Plans research strategy and delegates to researchers."""
    logger.debug("--- [DeepResearcher] Node: supervisor ---")
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
        
        logger.debug(f"Calling progress_callback in supervisor: {current_global_progress}%")
        await progress_callback(current_global_progress, f"Supervisor: Planificando iteración de investigación {current_iteration + 1}/{total_iterations}", "supervisor")

    account_id = state.get("account_id")
    from core.llm_manager import get_llm_for_user
    
    if account_id:
        llm = await get_llm_for_user(account_id, purpose="fast")
    else:
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

    try:
        research_model = cast(Runnable[Sequence[BaseMessage], AIMessage],
                              chat_llm.bind_tools(
                                  lead_researcher_tools
                              ).with_retry(
                                  stop_after_attempt=cfg.max_structured_output_retries
                              ))
    except Exception as e:
        logger.warning(f"⚠️ [Supervisor] Error binding tools: {e}. Trying simple bind.")
        research_model = cast(Runnable[Sequence[BaseMessage], AIMessage], chat_llm.bind_tools(lead_researcher_tools))

    messages: list[BaseMessage] = [SystemMessage(content=supervisor_system_prompt)]
    initial_human_message_content = f"Plan research for: {state.get('research_brief', '')}"

    if not state.get("supervisor_messages"):
        logger.debug("First supervisor run. Planning initial research.")
        messages.append(HumanMessage(content=initial_human_message_content))
    else:
        logger.debug(f"Supervisor continuing with {len(state['supervisor_messages'])} previous messages.")
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

    logger.debug(f"🔍 [DeepResearcher] supervisor - Pruned messages for supervisor count: {len(pruned_messages_for_supervisor)}")
    if not pruned_messages_for_supervisor:
        logger.error("❌ [DeepResearcher] supervisor - Pruned messages list is empty. Cannot invoke LLM.")
        return {"supervisor_messages": state.get("supervisor_messages", []) + [AIMessage(content="Error interno: La lista de mensajes para el supervisor está vacía.")], "research_iterations": state.get("research_iterations", 0) + 1}

    try:
        response: AIMessage = await research_model.ainvoke(pruned_messages_for_supervisor)
    except Exception as e:
        error_str = str(e)
        if "tool_choice" in error_str or "404" in error_str and "Openrouter" in error_str:
            logger.warning(f"⚠️ [Supervisor] OpenRouter tool_choice error detected: {e}. Retrying without strict tool binding...")
            # Try once more with a simpler bind or without tools if necessary, 
            # but for supervisor tools are essential. Let's try to bind without extras.
            simple_model = chat_llm.bind_tools(lead_researcher_tools)
            response = await simple_model.ainvoke(pruned_messages_for_supervisor)
        elif is_token_limit_exceeded(e):
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
            logger.debug(f"📋 [Supervisor] LLM decided to call tool: {tool_call['name']}")
    else:
        logger.warning("[Supervisor] LLM did not generate any tool calls.")

    return {
        "supervisor_messages": [response],
        "research_iterations": state.get("research_iterations", 0) + 1,
    }

async def supervisor_tools(state: SupervisorState, config: RunnableConfig, researcher_subgraph: Pregel) -> dict:
    """Executes tools called by the supervisor."""
    logger.debug("--- [DeepResearcher] Node: supervisor_tools ---")
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
        logger.debug(f"Calling progress_callback in supervisor_tools: {current_global_progress}%")
        await progress_callback(current_global_progress, "Supervisor: Preparando herramientas de investigación...", "supervisor_tools")

    if not most_recent_message.tool_calls:
        logger.warning("[Supervisor Tools] No tool calls in the last message. Checking iteration count.")
        if state["research_iterations"] > cfg.max_researcher_iterations:
            logger.debug("[Supervisor Tools] Max iterations reached. Ending research.")
            return {"notes": get_notes_from_tool_calls(state["supervisor_messages"])}
        else:
            logger.debug("[Supervisor Tools] Not at max iterations. Returning to supervisor.")
            return {"supervisor_messages": state["supervisor_messages"]}

    all_tool_messages = []
    update_payload = {}

    all_tool_messages = []
    update_payload = {}

    tool_calls = most_recent_message.tool_calls
    logger.debug(f"[Supervisor Tools] Processing {len(tool_calls)} tool calls in exact order.")

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
            
            # Ensure tool_call_id is never None
            tool_call_id = tc.get("id")
            if tool_call_id is None:
                tool_call_id = str(uuid.uuid4()) # Generate a UUID if ID is missing
                logger.warning(f"⚠️ [Supervisor Tools] Missing tool_call_id for tool '{tc['name']}'. Generated UUID: {tool_call_id}")

            tool_results_map[i] = ToolMessage(
                content=content,
                name=tc["name"],
                tool_call_id=tool_call_id
            )

    # 2. Execute parallel research tasks if any
    if conduct_research_tasks:
        logger.debug(f"🚀 [Supervisor Tools] Starting {len(conduct_research_tasks)} parallel research tasks.")
        parallel_results = await asyncio.gather(*conduct_research_tasks)
        logger.debug("✅ [Supervisor Tools] All parallel research tasks completed.")
        
        # Store parallel results in the map
        for idx, result in zip(conduct_research_indices, parallel_results):
            compressed_result = result.get("compressed_research", "Error: No compressed research found.")
            
            # Ensure tool_call_id is never None
            tool_call_id = tool_calls[idx].get("id")
            if tool_call_id is None:
                tool_call_id = str(uuid.uuid4()) # Generate a UUID if ID is missing
                logger.warning(f"⚠️ [Supervisor Tools] Missing tool_call_id for tool '{tool_calls[idx]['name']}'. Generated UUID: {tool_call_id}")

            tool_results_map[idx] = ToolMessage(
                content=compressed_result,
                name=tool_calls[idx]["name"],
                tool_call_id=tool_call_id,
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
            # Ensure tool_call_id is never None
            tool_call_id = tool_calls[i].get("id")
            if tool_call_id is None:
                tool_call_id = str(uuid.uuid4()) # Generate a UUID if ID is missing
                logger.warning(f"⚠️ [Supervisor Tools] Missing tool_call_id for tool '{tool_calls[i]['name']}'. Generated UUID: {tool_call_id}")

            all_tool_messages.append(ToolMessage(
                content=tool_results_map[i].content, # Use content from the map
                name=tool_calls[i]["name"],
                tool_call_id=tool_call_id
            ))

    update_payload["supervisor_messages"] = all_tool_messages
    
    # Ensure sources are included in the return payload
    if "sources" not in update_payload:
        update_payload["sources"] = []
    
    logger.debug(f"🎨 [Supervisor Tools] Total sources being returned: {len(update_payload['sources'])}")
    return update_payload

# --- Researcher Sub-Graph Nodes ---

async def researcher(state: ResearcherState, config: RunnableConfig) -> dict:
    """Conducts focused research on a specific topic."""
    logger.debug(f"--- [DeepResearcher] Node: researcher ---")
    logger.debug(f"🔍 [Researcher] Researching topic: '{state['research_topic']}'")
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
        
        logger.debug(f"Calling progress_callback in researcher: {current_global_progress}% for topic {state['research_topic']}")
        await progress_callback(current_global_progress, f"Investigando: {state['research_topic']} (Paso {current_tool_iteration + 1}/{total_tool_calls})", f"researcher_{state['research_topic']}")
    
    tools = await get_all_tools(config)
    if not tools:
        logger.error("[Researcher] No tools found for research. Aborting.")
        raise ValueError("No tools found for research.")

    account_id = state.get("account_id")
    from core.llm_manager import get_llm_for_user
    
    if account_id:
        llm_instance = await get_llm_for_user(account_id, purpose="main")
    else:
        llm_instance = get_main_llm()

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

    logger.info(f"PRUNED MESSAGES FOR RESEARCHER: {len(pruned_messages_for_researcher)} messages")

    try:
        response: AIMessage = await research_model.ainvoke(pruned_messages_for_researcher)
    except Exception as e:
        error_str = str(e)
        if "tool_choice" in error_str or "404" in error_str and "Openrouter" in error_str:
            logger.warning(f"⚠️ [Researcher] OpenRouter tool_choice error detected: {e}. Retrying with simpler binding...")
            # Try again with a simpler bind
            simple_research_model = chat_llm.bind_tools(tools)
            response = await simple_research_model.ainvoke(pruned_messages_for_researcher)
        elif is_token_limit_exceeded(e):
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
            logger.info(f"🛠️ [Researcher] LLM decided to call tool: {tool_call['name']}")
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

    # --- REAL-TIME FINDINGS REPORTING ---
    if progress_callback:
        found_sources = []
        for obs in observations:
            try:
                # 1. Check for structured ToolOutputWithSources format
                if hasattr(obs, 'sources') or (isinstance(obs, dict) and "sources" in obs):
                    obs_sources = obs.sources if hasattr(obs, 'sources') else obs["sources"]
                    if isinstance(obs_sources, list):
                        for s in obs_sources:
                            s_dict = s.model_dump() if hasattr(s, 'model_dump') else (s if isinstance(s, dict) else {})
                            if s_dict.get("url"):
                                found_sources.append({
                                    "title": s_dict.get("title", s_dict.get("url")),
                                    "url": s_dict.get("url"),
                                    "snippet": str(s_dict.get("snippet", "")),
                                    "type": s_dict.get("type", "web")
                                })
                # 2. Extract from raw content via Regex if no structured sources found
                else:
                    content_str = str(obs)
                    # Pattern: Markdown style [Title](URL)
                    md_matches = list(re.finditer(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", content_str))
                    for match in md_matches:
                        found_sources.append({
                            "title": match.group(1).strip(),
                            "url": match.group(2).strip(),
                            "snippet": "",
                            "type": "web"
                        })
            except Exception as e:
                logger.error(f"⚠️ [Researcher Tools] Error extracting real-time sources: {e}")

        if found_sources:
            # Deduplicate by URL
            unique_found = []
            seen_urls = set()
            for s in found_sources:
                if s["url"] not in seen_urls:
                    unique_found.append(s)
                    seen_urls.add(s["url"])
            
            logger.info(f"📡 [Researcher Tools] Reporting {len(unique_found)} real-time findings for topic: {state['research_topic']}")
            
            # Formatear hallazgos como Markdown para el stream de chat
            findings_md = f"\n\n#### ✨ Descubrimientos para: {state['research_topic']}\n"
            for s in unique_found:
                title = s.get("title", s.get("url", "Fuente")).strip()
                url = s.get("url")
                snippet = s.get("snippet", "").strip()
                
                # Crear link Markdown con snippet opcional
                findings_md += f"- **[{title}]({url})**"
                if snippet:
                    # Limpiar snippet de saltos de línea excesivos y truncarlo si es muy largo
                    clean_snippet = " ".join(snippet.split())
                    if len(clean_snippet) > 200:
                        clean_snippet = clean_snippet[:197] + "..."
                    findings_md += f": _{clean_snippet}_"
                findings_md += "\n"
            
            await progress_callback(
                int(progress_at_end_of_tools), 
                f"Hallazgos para: {state['research_topic']}", 
                data={"stream_chunk": findings_md}
            )
    # --- END REAL-TIME FINDINGS REPORTING ---

    if progress_callback:
        logger.info(f"Calling progress_callback in researcher_tools: {int(progress_at_end_of_tools)}% for topic {state['research_topic']}")
        await progress_callback(int(progress_at_end_of_tools), f"Herramientas ejecutadas para: {state['research_topic']}", f"researcher_tools_end_{state['research_topic']}")

    tool_outputs = []
    for obs, tc in zip(observations, most_recent_message.tool_calls):
        logger.info(f"🔧 [Researcher Tools] Result for '{tc['name']}' received.")
        
        # Check if the observation is a ToolOutputWithSources object or dict
        is_tool_output = False
        if hasattr(obs, 'context_for_llm') and hasattr(obs, 'sources'):
            is_tool_output = True
        elif isinstance(obs, dict) and "context_for_llm" in obs and "sources" in obs:
            is_tool_output = True
            
        if is_tool_output:
            # It's a ToolOutputWithSources object or dict
            logger.info(f"✅ [Researcher Tools] Tool '{tc['name']}' returned ToolOutputWithSources format.")
            
            # Extract attributes safely whether it's object or dict
            if isinstance(obs, dict):
                obs_sources = obs.get("sources", [])
                obs_context = obs.get("context_for_llm", "")
                obs_summary = obs.get("summary")
            else:
                obs_sources = obs.sources
                obs_context = obs.context_for_llm
                obs_summary = getattr(obs, "summary", None)
            
            logger.info(f"✅ [Researcher Tools] Extracted {len(obs_sources)} sources.")

            # Convert Source objects to dicts for JSON serialization
            sources_dicts = []
            for source in obs_sources:
                if hasattr(source, 'model_dump'):
                    sources_dicts.append(source.model_dump())
                elif isinstance(source, dict):
                    sources_dicts.append(source)
                else:
                    logger.warning(f"⚠️ [Researcher Tools] Unexpected source type: {type(source)}")
            
            # Create a structured content that includes both context and sources
            structured_content = {
                "context_for_llm": obs_context,
                "sources": sources_dicts,
                "summary": obs_summary
            }
            
            # Serialize to JSON string for ToolMessage
            import json
            # Ensure we produce valid JSON string
            content_str = json.dumps(structured_content, ensure_ascii=False)
            tool_outputs.append(ToolMessage(content=content_str, name=tc["name"], tool_call_id=tc["id"]))
        else:
            # Regular tool output, convert to string
            # IMPORTANT: If it's a dict/list, use json.dumps to ensure it's valid JSON for subsequent parsing
            if isinstance(obs, (dict, list)):
                try:
                    content_str = json.dumps(obs, ensure_ascii=False)
                except Exception:
                    content_str = str(obs)
            else:
                content_str = str(obs)
                
            tool_outputs.append(ToolMessage(content=content_str, name=tc["name"], tool_call_id=tc["id"]))

    return {"researcher_messages": tool_outputs}



    def _normalize_source_dict(source_dict: dict, tool_name: str, tool_call_id: str | None, message_index: int) -> dict:
        """Normaliza un dict de fuente: asegura id, metadata y tipo."""
        # Asegurar que el dict tenga los campos mínimos
        if "url" not in source_dict or not source_dict["url"]:
            # Fallback: generar ID único sin URL
            source_id = generate_stable_id("", prefix="unknown")
        else:
            url = source_dict["url"]
            source_type = source_dict.get("type", "web").lower()
            source_id = generate_stable_id(url, prefix=source_type)
        
        # Inicializar metadata si no existe
        metadata = source_dict.get("metadata", {})
        # Añadir información del origen
        if "tool_names" not in metadata:
            metadata["tool_names"] = []
        if tool_name and tool_name not in metadata["tool_names"]:
            metadata["tool_names"].append(tool_name)
        if tool_call_id and "tool_call_id" not in metadata:
            metadata["tool_call_id"] = tool_call_id
        if "message_index" not in metadata:
            metadata["message_index"] = message_index
        
        # Construir dict normalizado
        normalized = {
            "title": source_dict.get("title", ""),
            "url": source_dict.get("url", ""),
            "snippet": source_dict.get("snippet", ""),
            "type": source_dict.get("type", "web").lower(),
            "id": source_id,
            "metadata": metadata
        }
        return normalized

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

    account_id = state.get("account_id")
    from core.llm_manager import get_llm_for_user
    
    if account_id:
        synthesizer_model = await get_llm_for_user(account_id, purpose="fast")
    else:
        synthesizer_model = get_fast_llm()

    if not synthesizer_model:
        raise ValueError("Main LLM not initialized.")


    researcher_messages = [cast(BaseMessage, msg) for msg in state["researcher_messages"]] + [HumanMessage(content=compress_research_simple_human_message)]
    
    compression_prompt = compress_research_system_prompt.format(date=get_today_str())
    compression_prompt += "\n\nIMPORTANTE: Al citar fuentes, cada número de fuente debe estar entre sus propios corchetes. Por ejemplo, en lugar de [1, 2, 3], formatee como [1][2][3]."
    messages = [SystemMessage(content=compression_prompt)] + researcher_messages

    logger.info(f"📚 [Compress Research] Compressing {len(researcher_messages)} messages.")
    response = await synthesizer_model.ainvoke(messages)

    raw_notes_content = "\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])

    logger.info(f"📦 [Compress Research] Compressed research output received.")
    logger.info(f"🔍 [Compress Research] Researcher messages count: {len(researcher_messages)}")
    logger.info(f"🔍 [Compress Research] Raw notes content length: {len(raw_notes_content)}")
    
    # Extract sources from researcher messages
    sources = []
    
    # Lista de herramientas que pueden devolver fuentes ( расширенная lista)
    search_tool_names = [
        "tavily_search_tool",
        "web_search",
        "ddg_search_tool",
        "multi_query_search",
        "tavily_search",
        "brave_search_tool",
        "brave_search",
        "google_search",
        "google_search_tool",
        "bing_search",
        "arxiv_search",
        "knowledge_graph_search",
        "comprehensive_web_analyzer",
        # Nuevas herramientas añadidas
        "knowledge_graph",
        "knowledge_graph_tool",
        "KnowledgeGraphTool",
        "knowledge_search",
        "KnowledgeSearchTool",
        "web_scraper",
        "WebScraperTool",
        "graph_cypher",
        "GraphCypherGeneratorTool",
        "rag_search",
        "rag_tool",
        "document_search",
    ]
    
    # Debug: Mostrar todos los nombres de herramientas encontrados
    tool_names_found = set()
    for msg_idx, msg in enumerate(researcher_messages):
        if isinstance(msg, ToolMessage):
            tool_names_found.add(msg.name)
            logger.debug(f"🔍 [Compress Research] Found ToolMessage: name={msg.name}")
    logger.info(f"🔍 [Compress Research] Tool names found in messages: {tool_names_found}")
    
    for msg_idx, msg in enumerate(researcher_messages):
        if isinstance(msg, ToolMessage):
            # Intentar extraer fuentes de cualquier herramienta que devuelva un formato estructurado
            # No limitamos solo a herramientas de búsqueda conocidas
            is_search_tool = msg.name in search_tool_names
            try:
                # The content of the ToolMessage is often a string representation of a list of dicts
                # or sometimes it's already a list of dicts.
                content = msg.content
                
                # 1. If content is a string, try to parse it as JSON
                if isinstance(content, str):
                    try:
                        # It might be a JSON string, so let's parse it.
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        # FALLBACK: If it's not JSON, try to extract sources via Regex
                        logger.info(f"🔍 [Compress Research] Content is not JSON for tool '{msg.name}'. Attempting regex extraction...")
                        
                        # Pattern 1: Tavily / Generic (--- SOURCE 1: Title --- URL: ...)
                        tavily_matches = list(re.finditer(r"--- SOURCE \d+: (.*?) ---\s+URL: (https?://\S+)", str(msg.content)))
                        for match in tavily_matches:
                            title = match.group(1).strip()
                            url = match.group(2).strip()
                            if not any(s['url'] == url for s in sources):
                                source_raw = {
                                    "title": title,
                                    "url": url,
                                    "snippet": "",
                                    "type": "web"
                                }
                                sources.append(_normalize_source_dict(source_raw, msg.name, msg.tool_call_id, msg_idx))
                                logger.info(f"✅ [Compress Research] Added source via Regex (Format 1): {title} - {url[:50]}...")
                        
                        # Pattern 2: Markdown style [Title](URL)
                        md_matches = list(re.finditer(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", str(msg.content)))
                        for match in md_matches:
                            title = match.group(1).strip()
                            url = match.group(2).strip()
                            if not any(s['url'] == url for s in sources):
                                source_raw = {
                                    "title": title,
                                    "url": url,
                                    "snippet": "",
                                    "type": "web"
                                }
                                sources.append(_normalize_source_dict(source_raw, msg.name, msg.tool_call_id, msg_idx))
                                logger.info(f"✅ [Compress Research] Added source via Regex (Format 2): {title} - {url[:50]}...")

                        if not tavily_matches and not md_matches:
                            logger.debug(f"⚠️ [Compress Research] No sources found via regex in non-JSON content for '{msg.name}'.")
                        
                        continue # Done with this message

                # 2. PRIORITY: Check if it's our new structured format with context_for_llm and sources
                # Este formato viene de tavily_search y otras herramientas que usan ToolOutputWithSources
                if isinstance(content, dict) and "context_for_llm" in content and "sources" in content:
                    logger.info(f"✅ [Compress Research] Found structured ToolOutputWithSources format from '{msg.name}'")
                    sources_list = content["sources"]
                    if isinstance(sources_list, list):
                        for source_dict in sources_list:
                            if isinstance(source_dict, dict):
                                url = source_dict.get("url")
                                title = source_dict.get("title")
                                snippet = source_dict.get("snippet", "")
                                source_type = source_dict.get("type", "web")
                                
                                if url and title:
                                    source_raw = {
                                        "title": title,
                                        "url": url,
                                        "snippet": str(snippet),
                                        "type": source_type
                                    }
                                    sources.append(_normalize_source_dict(source_raw, msg.name, msg.tool_call_id, msg_idx))
                                    logger.info(f"✅ [Compress Research] Added source from structured format: {title} - {url[:50]}...")
                    continue  # Skip to next message after processing structured format

                # 3. Si el contenido es un dict que tiene una clave 'sources' (común en nuestras herramientas personalizadas)
                if isinstance(content, dict) and "sources" in content:
                    content = content["sources"]


                # 2. Now, content should be a list of dictionaries or a list of strings (URLs).
                # Extraer fuentes de cualquier herramienta que devuelva un formato estructurado
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            url = item.get("url") or item.get("link") or item.get("href") or item.get("source") or item.get("uri")
                            title = item.get("title") or item.get("name") or item.get("header") or item.get("text")
                            snippet = item.get("snippet") or item.get("summary") or item.get("content") or item.get("description") or item.get("text", "")
                            
                            # Detectar tipo de fuente
                            source_type = "web"
                            if url:
                                if url.startswith("graph://") or url.startswith("analysis://"):
                                    source_type = "graph"
                                elif url.startswith("memory://"):
                                    source_type = "memory"
                                elif url.startswith("note://"):
                                    source_type = "note"
                                elif "github.com" in url:
                                    source_type = "github"
                            
                            # Si tiene URL y título, o si es una herramienta de búsqueda y tiene URL
                            if url and (title or is_search_tool):
                                # Normalizar título si falta pero tenemos URL
                                if not title:
                                    title = url.split('/')[-1] or url
                                
                                source_raw = {
                                    "title": title,
                                    "url": url,
                                    "snippet": str(snippet),
                                    "type": source_type
                                }
                                sources.append(_normalize_source_dict(source_raw, msg.name, msg.tool_call_id, msg_idx))
                                logger.info(f"✅ [Compress Research] Added source: {title} - {url[:50]}...")
                        elif isinstance(item, str) and (item.startswith("http") or item.startswith("analysis://")):
                            # Caso especial: lista de strings (URLs), común en comprehensive_web_analyzer
                            url = item
                            title = url.split('/')[-1] or url
                            source_raw = {
                                "title": title,
                                "url": url,
                                "snippet": "",
                                "type": "web"
                            }
                            sources.append(_normalize_source_dict(source_raw, msg.name, msg.tool_call_id, msg_idx))
                            logger.info(f"✅ [Compress Research] Added string source: {url[:50]}...")
                elif isinstance(content, dict) and is_search_tool:
                    # Algunos resultados pueden venir como un dict único (ej: respuesta de una API de búsqueda)
                    # Intentar extraer fuentes de cualquier dict que tenga URLs
                    url = content.get("url") or content.get("link") or content.get("source") or content.get("href")
                    title = content.get("title") or content.get("name") or content.get("header")
                    if url and title:
                        # Detectar tipo de fuente
                        source_type = "web"
                        if url.startswith("graph://") or url.startswith("analysis://"):
                            source_type = "graph"
                        elif url.startswith("memory://"):
                            source_type = "memory"
                        elif url.startswith("note://"):
                            source_type = "note"
                        
                        source_raw = {
                            "title": title,
                            "url": url,
                            "snippet": str(content.get("snippet", "") or content.get("summary", "") or content.get("description", "")),
                            "type": source_type
                        }
                        sources.append(_normalize_source_dict(source_raw, msg.name, msg.tool_call_id, msg_idx))
                        logger.info(f"✅ [Compress Research] Added source from dict: {title} - {url[:50]}...")
                else:
                    # También intentar extraer URLs de cualquier contenido que parezca tener enlaces
                    if not is_search_tool and content:
                        # Intentar encontrar URLs en el contenido
                        url_matches = re.findall(r'https?://[^\s\]">]+', str(content))
                        for url in url_matches[:5]:  # Limitar a 5 URLs por mensaje
                            if not any(s['url'] == url for s in sources):
                                source_raw = {
                                    "title": url.split('/')[-1] or url,
                                    "url": url,
                                    "snippet": "",
                                    "type": "web"
                                }
                                sources.append(_normalize_source_dict(source_raw, msg.name, msg.tool_call_id, msg_idx))
                                logger.info(f"✅ [Compress Research] Added source from regex: {url[:50]}...")
                    elif is_search_tool:
                        logger.warning(f"⚠️ [Compress Research] ToolMessage content for '{msg.name}' was not a list/dict after parsing. Type: {type(content)}")

            except Exception as e:
                logger.error(f"❌ [Compress Research] Error processing sources from tool {msg.name}: {e}")

    # Deduplicate sources at researcher level (fusion metadata on duplicates)
    unique_researcher_sources = []
    seen_urls: Dict[str, dict] = {}
    for s in sources:
        url = s["url"]
        if url not in seen_urls:
            unique_researcher_sources.append(s)
            seen_urls[url] = s
        else:
            # Fusionar metadatos: mantener primer ID, combinar tool_names
            existing = seen_urls[url]
            # Mantener el ID del primer origen encontrado
            s["id"] = existing["id"]
            # Fusionar tool_names (si existen)
            if "metadata" in existing and "tool_names" in existing["metadata"]:
                if "metadata" not in s:
                    s["metadata"] = {}
                if "tool_names" not in s["metadata"]:
                    s["metadata"]["tool_names"] = []
                # Agregar tool_names que no existan
                for tool in existing["metadata"]["tool_names"]:
                    if tool not in s["metadata"]["tool_names"]:
                        s["metadata"]["tool_names"].append(tool)
            # Usar la versión fusionada
            unique_researcher_sources.append(s)

    return {
        "compressed_research": str(response.content),
        "raw_notes": [raw_notes_content],
        "sources": unique_researcher_sources
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
    
    deep_researcher_builder.add_edge("await_user_clarification", "clarify_with_user")

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