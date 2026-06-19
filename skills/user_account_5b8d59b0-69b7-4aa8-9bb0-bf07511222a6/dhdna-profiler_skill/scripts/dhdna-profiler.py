from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict
import re

class DHDNAProfilerInput(BaseModel):
    text: str = Field(description="El texto a analizar para extraer patrones cognitivos")

class DHDNAProfiler(BaseTool):
    name: str = "dhdna-profiler"
    description: str = "Extrae patrones cognitivos de cualquier texto basado en el marco DHDNA"
    args_schema: Type[BaseModel] = DHDNAProfilerInput

    def _run(self, text: str) -> str:
        dimensions = {
            "Decisión": "analítico" if "debemos" in text.lower() or "consideremos" in text.lower() else "intuitivo",
            "Valores": "énfasis en datos" if len(re.findall(r'\d+', text)) > 3 else "énfasis en principios",
            "Incertidumbre": "exploración" if "?" in text or "quizás" in text.lower() else "certeza",
            "Estructura": "jerárquico" if text.count('\n') > 10 else "fluido"
        }
        
        profile = f"## 🧬 DHDNA Profiler - Huella Cognitiva\n\n"
        for dim, score in dimensions.items():
            profile += f"- **{dim}:** {score}\n"
        
        return profile

class CognitiveProfiler(BaseTool):
    name: str = "cognitive-profiler"
    description: str = "Alias para dhdna-profiler"
    args_schema: Type[BaseModel] = DHDNAProfilerInput

    def _run(self, text: str) -> str:
        return DHDNAProfiler()._run(text)