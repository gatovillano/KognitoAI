# core/agents/deep_researcher_config.py

from typing import Any, List, Optional

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

class Configuration(BaseModel):
    """Main configuration class for the Deep Research agent."""
    
    # General Configuration
    max_structured_output_retries: int = Field(default=3)
    allow_clarification: bool = Field(default=True)
    max_concurrent_research_units: int = Field(default=3)

    # Research Configuration
    max_researcher_iterations: int = Field(default=3)
    max_react_tool_calls: int = Field(default=5)

    # Model Configuration
    # We can define different models for different tasks
    research_model: str = Field(default="main_llm")
    compression_model: str = Field(default="main_llm")
    final_report_model: str = Field(default="main_llm")
    
    research_model_max_tokens: int = Field(default=8192)
    compression_model_max_tokens: int = Field(default=4096)
    final_report_model_max_tokens: int = Field(default=8192)

    # Retry Configuration for LLM calls to handle RateLimitError
    llm_retry_exponential_multiplier: int = Field(default=1000) # milliseconds

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config.get("configurable", {}) if config else {}
        # Simple implementation: we can expand this to read from env vars or other sources
        return cls(**configurable)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True