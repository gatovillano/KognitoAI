from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List, Dict
import random

class WhatIfOracleInput(BaseModel):
    scenario: str = Field(description="La pregunta especulativa o escenario a analizar")

class WhatIfOracle(BaseTool):
    name: str = "what-if-oracle"
    description: str = "Análisis estructurado de escenarios con exploración de espacio de posibilidades"
    args_schema: Type[BaseModel] = WhatIfOracleInput

    def _run(self, scenario: str) -> str:
        branches = {
            "Mejor caso": {"probability": 0.3, "assumptions": "Condiciones ideales", "consecuencias": "Resultado óptimo"},
            "Peor caso": {"probability": 0.2, "assumptions": "Fallos críticos", "consecuencias": "Daños significativos"},
            "Caso probable": {"probability": 0.5, "assumptions": "Condiciones normales", "consecuencias": "Resultado esperado"},
            "Caso inesperado": {"probability": 0.1, "assumptions": "Giro inesperado", "consecuencias": "Resultado sorprendente"}
        }
        
        analysis = f"## 🔮 What-If Oracle - Exploración de Posibilidades\n\n"
        analysis += f"**Escenario:** {scenario}\n\n"
        analysis += "### Espacio de Posibilidades\n\n"
        
        for branch, details in branches.items():
            analysis += f"#### {branch} ({details['probability']*100}%)\n"
            analysis += f"- **Asumpciones:** {details['assumptions']}\n"
            analysis += f"- **Consecuencias:** {details['consecuencias']}\n\n"
        
        return analysis

class WhatIfStatement(BaseTool):
    name: str = "what-if-statement"
    description: str = "Alias para what-if-oracle"
    args_schema: Type[BaseModel] = WhatIfOracleInput

    def _run(self, scenario: str) -> str:
        return WhatIfOracle()._run(scenario)