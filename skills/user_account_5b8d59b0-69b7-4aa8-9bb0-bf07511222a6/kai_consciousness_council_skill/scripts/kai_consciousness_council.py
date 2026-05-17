from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional

class InputSchema(BaseModel):
    question: str = Field(description="The question or challenge to deliberate on")
    council_size: str = Field(default="deep", description="Size: quick(3), deep(6), full(12)")
    mode: str = Field(default="deliberation", description="Mode: deliberation, anonymous, devil_advocate")

class KaiConsciousnessCouncil(BaseTool):
    name: str = "kai_consciousness_council"
    description: str = """Run a multi-perspective Mind Council deliberation on any question, decision, or creative challenge. Use this skill whenever the user wants diverse viewpoints, needs help making a tough decision, asks for a council/panel/board discussion, wants to explore a problem from multiple angles, requests devil's advocate analysis, or says things like "what would different experts think about this", "help me think through this from all sides", "council mode", "mind council", or "deliberate on this". Also trigger when the user faces a dilemma, trade-off, or complex choice with no obvious answer."""
    args_schema: Type[BaseModel] = InputSchema

    def _run(self, question: str, council_size: str = "deep", mode: str = "deliberation") -> str:
        # Implementation would invoke the actual council deliberation
        return f"Running {council_size} council in {mode} mode for: {question}"