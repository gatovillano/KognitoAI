# core/agents/deep_researcher_utils.py

import asyncio
import logging
import os
import time
import warnings
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional, Sequence, cast

import aiohttp
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage, # Import BaseMessage
    HumanMessage,
    MessageLikeRepresentation,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig, Runnable
from langchain_core.tools import (
    BaseTool,
    InjectedToolArg,
    StructuredTool,
    ToolException,
    tool,
)
from tavily import AsyncTavilyClient

from core.agents.deep_researcher_config import Configuration, SearchAPI
from core.agents.deep_researcher_prompts import summarize_webpage_prompt
from core.agents.deep_researcher_state import ResearchComplete, Summary
from core.llm_manager import get_fast_llm, get_main_llm
from core.utils.llm_utils import is_token_limit_exceeded, remove_up_to_last_ai_message # Removed get_model_token_limit
from core.utils.tool_utils import get_tool_by_name as get_langchain_tool_by_name

logger = logging.getLogger(__name__)

def time_function(func):
    """Decorator to measure the execution time of an async function."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        logging.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper

# Tavily Search Tool Utils

TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)
@tool
async def tavily_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: Optional[RunnableConfig] = None # Changed to Optional
) -> str:
    """A search engine optimized for comprehensive, accurate, and trusted results. 
    Useful for when you need to answer questions about current events.
    
    Fetch and summarize search results from Tavily search API.
    
    Note: The Tavily search operation itself (via AsyncTavilyClient) does not
    directly use a local LLM. The 'fast LLM' (get_fast_llm()) is specifically
    utilized for the summarization of web page content, ensuring that any
    LLM-dependent processing within this tool leverages the designated fast model.
    """
    search_results = await tavily_search_async(
        queries,
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
        config=config
    )
    
    unique_results = {}
    for response in search_results:
        for result in response.get('results', []):
            url = result.get('url')
            if url and url not in unique_results:
                unique_results[url] = {**result, "query": response.get('query')}
    
    cfg = Configuration.from_runnable_config(config)
    max_char_to_include = cfg.max_content_length
    
    summarization_llm = get_fast_llm() # pylint: disable=undefined-variable
    if not summarization_llm:
        raise ValueError("Main LLM not initialized for summarization.")

    summarization_model = cast(Runnable[Sequence[BaseMessage], Summary],
                               summarization_llm.with_structured_output(Summary).with_retry(
                                   stop_after_attempt=cfg.max_structured_output_retries
                               ))
    
    async def noop():
        return None
    
    summarization_tasks = [
        noop() if not result.get("raw_content") 
        else summarize_webpage(
            summarization_model, 
            result['raw_content'][:max_char_to_include]
        )
        for result in unique_results.values()
    ]
    
    summaries = await asyncio.gather(*summarization_tasks)
    
    # Pair results with summaries, handling potential None summaries
    summarized_data = []
    for url, result, summary in zip(unique_results.keys(), unique_results.values(), summaries):
        # Determine the content to use:
        # 1. If summary is a Summary object, use its summary and key_excerpts.
        # 2. If summary is None (failed summarization or noop), use the original result content.
        # 3. Otherwise (e.g., if summary is a string from a previous error handling), use it directly.
        content_to_use = result['content']
        if isinstance(summary, Summary):
            content_to_use = summary.summary + "\n" + summary.key_excerpts
        elif summary is not None: # This covers cases where summary might be a string from older error handling
            content_to_use = str(summary)

        summarized_data.append({
            'url': url,
            'title': result['title'],
            'content': content_to_use
        })

    if not summarized_data:
        return "No valid search results found. Please try different search queries or use a different search API."
    
    formatted_output = "Search results: \n\n"
    current_char_count = len(formatted_output)
    
    # Use research_model_max_tokens as a guide, with a buffer for other prompt elements
    # Assuming ~4 chars per token, and leaving 4000 chars (approx 1000 tokens) for other prompt parts.
    max_aggregated_output_chars = (cfg.research_model_max_tokens - 1000) * 4
    if max_aggregated_output_chars < 0: # Ensure it's not negative
        max_aggregated_output_chars = 10000 # Fallback to a safe minimum


    for i, data in enumerate(summarized_data):
        single_result_str = (
            f"\n\n--- SOURCE {i+1}: {data['title']} ---\n"
            f"URL: {data['url']}\n\n"
            f"SUMMARY:\n{data['content']}\n\n"
            f"\n\n" + "-" * 80 + "\n"
        )
        
        if current_char_count + len(single_result_str) > max_aggregated_output_chars:
            formatted_output += f"\n\n--- Additional results omitted due to character limit ({max_aggregated_output_chars} chars). ---\n"
            break
        
        formatted_output += single_result_str
        current_char_count += len(single_result_str)
    
    return formatted_output

@time_function
async def tavily_search_async(
    search_queries,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
    config: Optional[RunnableConfig] = None # Changed to Optional
):
    """Execute multiple Tavily search queries asynchronously."""
    tavily_api_key = get_tavily_api_key(config)
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables or configuration.")
    
    tavily_client = AsyncTavilyClient(api_key=tavily_api_key)
    
    search_tasks = [
        tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            search_depth="advanced"
        )
        for query in search_queries[:3]
    ]
    
    search_results = await asyncio.gather(*search_tasks)
    return search_results

@time_function
async def summarize_webpage(model: Runnable[Sequence[BaseMessage], Summary], webpage_content: str) -> Optional[Summary]:
    """Summarize webpage content using AI model with timeout protection."""
    try:
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content,
            date=get_today_str()
        )
        
        summary: Summary = await model.ainvoke([HumanMessage(content=prompt_content)])
        return summary
        
    except asyncio.TimeoutError:
        logger.warning("Summarization timed out after 60 seconds, returning None")
        return None
    except Exception as e:
        logger.warning(f"Summarization failed with error: {str(e)}, returning None")
        return None

# Reflection Tool Utils

@tool
def deep_research_think_tool(reflection: str) -> str:
    """Strategic reflection tool for research planning. Use this ONLY to plan your next ConductResearch calls or to assess findings. 
    DO NOT use this tool as a substitute for actual research delegation.

    Tool for strategic reflection on research progress and decision-making.
    This tool records your thoughts but does not perform any research.
    """
    return f"Reflection recorded: {reflection}"

# Tool Utils

async def get_search_tool(search_api: SearchAPI, config: Optional[RunnableConfig]): # Changed to Optional
    """Configure and return search tools based on the specified API provider."""
    if search_api == SearchAPI.TAVILY:
        tavily_api_key = get_tavily_api_key(config)
        if not tavily_api_key:
            logger.warning("Tavily API key not found. Tavily search will be unavailable.")
            return []
        search_tool = tavily_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "tavily_search"
        }
        return [search_tool]
    return []

async def get_all_tools(config: Optional[RunnableConfig]): # Changed to Optional
    """Assemble complete toolkit including research and search tools."""
    from tools.web_scraper_tool import WebScraperTool
    from tools.knowledge_search_tool import KnowledgeSearchTool
    from tools.knowledge_graph_tool import KnowledgeGraphTool
    from tools.graph_cypher_generator_tool import GraphCypherGeneratorTool
    from tools.comprehensive_web_analysis_tool import ComprehensiveWebAnalysisTool

    # Extract account_id and workspace_id from config
    configurable = config.get("configurable", {}) if config else {}
    account_id = configurable.get("account_id")
    workspace_id = configurable.get("workspace_id")

    # Initialize tools without account_id first
    web_scraper = WebScraperTool()
    knowledge_graph = KnowledgeGraphTool()
    graph_cypher = GraphCypherGeneratorTool()
    knowledge_search = KnowledgeSearchTool()
    comprehensive_analyzer = ComprehensiveWebAnalysisTool()

    # Inject dependencies if account_id is available
    if account_id:
        graph_cypher.account_id = account_id
        knowledge_search.account_id = account_id
        knowledge_search.workspace_id = workspace_id
    else:
        logger.warning("⚠️ account_id no encontrado en la configuración del runnable. Las herramientas que lo requieran fallarán.")

    tools = [
        deep_research_think_tool,
        web_scraper,
        knowledge_search,
        knowledge_graph,
        graph_cypher,
        comprehensive_analyzer,
    ]
    
    cfg = Configuration.from_runnable_config(config)
    search_api = SearchAPI(get_config_value(cfg.search_api))
    search_tools = await get_search_tool(search_api, config)
    tools.extend(search_tools)
    
    return tools

def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    """Extracts notes from tool calls, especially from 'think_tool'."""
    notes = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "deep_research_think_tool":
                    reflection_note = tool_call["args"].get("reflection")
                    if reflection_note:
                        notes.append(reflection_note)
    # Also extract content from regular tool messages
    notes.extend([tool_msg.content for tool_msg in filter_messages(messages, include_types="tool")])
    return notes
    
# Misc Utils

def get_today_str() -> str:
    """Get current date formatted for display in prompts and outputs."""
    return datetime.now().strftime("%a %b %-d, %Y")

def get_config_value(value):
    """Extract value from configuration, handling enums and None values."""
    if value is None:
        return None
    if isinstance(value, str) or isinstance(value, dict):
        return value
    else:
        return value.value

def get_tavily_api_key(config: Optional[RunnableConfig]): # Changed to Optional
    """Get Tavily API key from environment or config."""
    configurable = config.get("configurable", {}) if config else {}
    api_key = configurable.get("tavily_api_key")
    if api_key:
        return api_key
    return os.getenv("TAVILY_API_KEY")

async def execute_tool_safely(tool, args, config: Optional[RunnableConfig]): # Changed to Optional
    """Safely execute a tool with error handling."""
    try:
        return await tool.ainvoke(args, config)
    except Exception as e:
        logger.error(f"Error executing tool {tool.name}: {e}", exc_info=True)
        return f"Error executing tool: {str(e)}"