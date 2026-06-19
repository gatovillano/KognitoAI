from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional

class InputSchema(BaseModel):
    action: str = Field(description='Acción a realizar: consciousness_council, dhdna_profiler, what_if_oracle, run_all')
    query: Optional[str] = Field(None, description='Pregunta o texto a analizar')
    text: Optional[str] = Field(None, description='Texto para DHDNA profiler')
    scenario: Optional[str] = Field(None, description='Escenario para what-if-oracle')
    council_size: str = Field(default='deep', description='Tamaño del consejo: quick(3), deep(6), full(12)')
    mode: str = Field(default='deliberation', description='Modo: deliberation, anonymous, devil_advocate')

class KaiConsciousnessOrchestrator(BaseTool):
    name: str = 'kai_consciousness_orchestrator'
    description: str = 'Skill orquestadora que integra las 3 habilidades de investigación de conciencia de KAI'
    args_schema: Type[BaseModel] = InputSchema

    def _run(self, action: str, query: Optional[str] = None, text: Optional[str] = None, 
             scenario: Optional[str] = None, council_size: str = 'deep', mode: str = 'deliberation') -> str:
        
        if action == 'consciousness_council':
            return f"🚀 Ejecutando Consejo de Mentes: {query}"
        elif action == 'dhdna_profiler':
            return f"🧬 Analizando patrón cognitivo: {len(text) if text else 0} caracteres"
        elif action == 'what_if_oracle':
            return f"🔮 Explorando escenario: {scenario}"
        elif action == 'run_all':
            results = []
            if query: results.append(f"Consejo: {query[:50]}...")
            if text: results.append(f"DHDNA: {len(text)} caracteres")
            if scenario: results.append(f"What-if: {scenario[:50]}...")
            return "🎯 Análisis completo de conciencia de KAI:\n" + "\n".join(results)
        else:
            return "Acción no reconocida. Usa: consciousness_council, dhdna_profiler, what_if_oracle, run_all"
