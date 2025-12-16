# core/agents/deep_researcher_state.py

import operator
from typing import Annotated, Optional, List, TypedDict

from langchain_core.messages import MessageLikeRepresentation
from pydantic import BaseModel, Field

# --- Structured Outputs ---

class ConductResearch(BaseModel):
    """Call this tool to conduct research on a specific topic."""
    research_topic: str = Field(
        description="The topic to research. Should be a single topic, and should be described in high detail (at least a paragraph).",
    )

class ResearchComplete(BaseModel):
    """Call this tool to indicate that the research is complete."""

class ClarifyWithUser(BaseModel):
    """Model for user clarification requests."""
    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarifying question.",
    )
    question: str = Field(
        description="A question to ask the user to clarify the report scope",
    )
    verification: str = Field(
        description="Verify message that we will start research after the user has provided the necessary information.",
    )

class ResearchQuestion(BaseModel):
    """Research question and brief for guiding research."""
    research_brief: str = Field(
        description="A research question that will be used to guide the research.",
    )

# --- State Definitions ---

def override_reducer(current_value, new_value):
    """Reducer function that allows overriding values in state."""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)

class AgentInputState(TypedDict):
    """Input state is only 'messages'."""
    messages: List[MessageLikeRepresentation]
    account_id: str

class AgentState(TypedDict):
    """Main agent state containing messages and research data."""
    messages: Annotated[List[MessageLikeRepresentation], operator.add]
    account_id: str
    supervisor_messages: Annotated[List[MessageLikeRepresentation], override_reducer]
    research_brief: Optional[str]
    raw_notes: Annotated[List[str], override_reducer]
    notes: Annotated[List[str], override_reducer]
    final_report: str

class SupervisorState(TypedDict):
    """State for the supervisor that manages research tasks."""
    account_id: str
    supervisor_messages: Annotated[List[MessageLikeRepresentation], override_reducer]
    research_brief: str
    notes: Annotated[List[str], override_reducer]
    research_iterations: int
    raw_notes: Annotated[List[str], override_reducer]

class ResearcherState(TypedDict):
    """State for individual researchers conducting research."""
    account_id: str
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    tool_call_iterations: int
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[List[str], override_reducer]

class ResearcherOutputState(BaseModel):
    """Output state from individual researchers."""
    compressed_research: str
    raw_notes: Annotated[List[str], override_reducer]