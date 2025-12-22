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
from core.llm_manager import get_main_llm
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
@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 20,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: Optional[RunnableConfig] = None # Changed to Optional
) -> str:
    """Fetch and summarize search results from Tavily search API."""
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
    
    summarization_llm = get_main_llm()
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
    
    summarized_results = {
        url: {
            'title': result['title'], 
            'content': result['content'] if summary is None else summary
        }
        for url, result, summary in zip(
            unique_results.keys(), 
            unique_results.values(), 
            summaries
        )
    }
    
    if not summarized_results:
        return "No valid search results found. Please try different search queries or use a different search API."
    
    formatted_output = "Search results: \n\n"
    for i, (url, result) in enumerate(summarized_results.items()):
        formatted_output += f"\n\n--- SOURCE {i+1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"
    
    return formatted_output

@time_function
async def tavily_search_async(
    search_queries,
    max_results: int = 20,
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
        for query in search_queries
    ]
    
    search_results = await asyncio.gather(*search_tasks)
    return search_results

@time_function
async def summarize_webpage(model: Runnable[Sequence[BaseMessage], Summary], webpage_content: str) -> str:
    """Summarize webpage content using AI model with timeout protection."""
    try:
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content,
            date=get_today_str()
        )
        
        summary: Summary = await model.ainvoke([HumanMessage(content=prompt_content)])
        
        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )
        
        return formatted_summary
        
    except asyncio.TimeoutError:
        logger.warning("Summarization timed out after 60 seconds, returning original content")
        return webpage_content
    except Exception as e:
        logger.warning(f"Summarization failed with error: {str(e)}, returning original content")
        return webpage_content

# Reflection Tool Utils

@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making."""
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
    tools = [think_tool]
    
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
                if tool_call["name"] == "think_tool":
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