# core/agents/deep_researcher_config.py

import os
from enum import Enum
from typing import Any, List, Optional

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

class SearchAPI(Enum):
    """Enumeration of available search API providers."""
    
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    TAVILY = "tavily"
    NONE = "none"

class MCPConfig(BaseModel):
    """Configuration for Model Context Protocol (MCP) servers."""
    
    url: Optional[str] = Field(
        default=None,
        description="The URL of the MCP server"
    )
    tools: Optional[List[str]] = Field(
        default=None,
        description="The tools to make available to the LLM"
    )
    auth_required: Optional[bool] = Field(
        default=False,
        description="Whether the MCP server requires authentication"
    )

class Configuration(BaseModel):
    """Main configuration class for the Deep Research agent."""
    
    # General Configuration
    max_structured_output_retries: int = Field(default=3)
    allow_clarification: bool = Field(default=True)
    max_concurrent_research_units: int = Field(default=3)
    max_clarification_attempts: int = Field(default=3) # Added this line

    # Research Configuration
    search_api: SearchAPI = Field(default=SearchAPI.TAVILY)
    max_researcher_iterations: int = Field(default=10)
    max_react_tool_calls: int = Field(default=8)

    # Model Configuration
    # We can define different models for different tasks
    summarization_model: str = Field(default="gemini-2.5-flash")
    summarization_model_max_tokens: int = Field(default=8192)

    research_model: str = Field(default="gemini-2.5-flash")
    research_model_max_tokens: int = Field(default=8192)

    compression_model: str = Field(default="gemini-2.5-flash")
    compression_model_max_tokens: int = Field(default=8192)

    final_report_model: str = Field(default="gemini-2.5-flash")
    final_report_model_max_tokens: int = Field(default=8192)
    
    max_content_length: int = Field(default=10000)

    # Context window management
    max_input_tokens: int = Field(default=150000) # More conservative limit to prevent context overflow

    # MCP server configuration
    mcp_config: Optional[MCPConfig] = Field(default=None)
    mcp_prompt: Optional[str] = Field(default=None)

    # Retry Configuration for LLM calls to handle RateLimitError
    llm_retry_exponential_multiplier: int = Field(default=1000) # milliseconds

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config.get("configurable", {}) if config else {}
        field_names = list(cls.model_fields.keys())
        values: dict[str, Any] = {
            field_name: os.environ.get(field_name.upper(), configurable.get(field_name))
            for field_name in field_names
        }
        return cls(**{k: v for k, v in values.items() if v is not None})

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True