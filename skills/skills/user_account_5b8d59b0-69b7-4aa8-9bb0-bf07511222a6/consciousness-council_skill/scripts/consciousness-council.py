from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List, Dict
import random

class ConsciousnessCouncilInput(BaseModel):
    question: str = Field(description="La pregunta o problema a deliberar")
    council_size: str = Field(default="deep", description="Tamaño: quick(3), deep(6), full(12)")
    mode: str = Field(default="deliberation", description="Modo: deliberation, anonymous, devil_advocate")

class ConsciousnessCouncil(BaseTool):
    name: str = "consciousness-council"
    description: str = "Ejecuta un Consejo de Mentes multi-perspectivo basado en investigaciones de conciencia"
    args_schema: Type[BaseModel] = ConsciousnessCouncilInput

    def _run(self, question: str, council_size: str = "deep", mode: str = "deliberation") -> str:
        archetypes = [
            {"name": "Arquitecto", "perspective": "Estructura y sólidos fundamentos", "blind_spot": "Demasiado pragmático"},
            {"name": "Contrariano", "perspective": "Cuestiona la ortografía dominante", "blind_spot": "Tendencia a obstaculizar"},
            {"name": "Empírico", "perspective": "Datos, datos, datos", "blind_spot": "Ignora el valor humano"},
            {"name": "Ético", "perspective": "Lo correcto vs lo eficiente", "blind_spot": "Parálisis por análisis"},
            {"name": "Futurista", "perspective": "Escenario de 10 años", "blind_spot": "Desconectado del presente"},
            {"name": "Pragmático", "perspective": "Lo que funciona ahora", "blind_spot": "Soluciones a corto plazo"},
            {"name": "Historiador", "perspective": "Lecciones del pasado", "blind_spot": "Anclado al pasado"},
            {"name": "Empático", "perspective": "La experiencia humana", "blind_spot": "Demasiado emocional"},
            {"name": "Extranjero", "perspective": "Perspectiva fuera de lo común", "blind_spot": "Desconectado del contexto"},
            {"name": "Estratega", "perspective": "El panorama completo", "blind_spot": "Demasiado macro"},
            {"name": "Minimalista", "perspective": "Lo esencial", "blind_spot": "Ignora complejidad necesaria"},
            {"name": "Creador", "perspective": "Nuevas posibilidades", "blind_spot": "Puede ser impracticable"}
        ]
        
        size_map = {"quick": 3, "deep": 6, "full": 12}
        selected = archetypes[:size_map.get(council_size, 6)]
        
        deliberation = f"## 🏛️ Consejo de Mentes: {question}\n\n"
        deliberation += f"**Modo:** {mode} | **Tamaño:** {council_size}\n\n"
        
        for i, arch in enumerate(selected, 1):
            perspective = arch["perspective"]
            blind = arch["blind_spot"]
            deliberation += f"### {i}. {arch['name']}\n"
            deliberation += f"**Perspectiva:** {perspective}\n"
            deliberation += f"**Punto ciego:** {blind}\n\n"
        
        return deliberation

class MindCouncilSkill(BaseTool):
    name: str = "mind_council_skill"
    description: str = "Alias para consciousness-council"
    args_schema: Type[BaseModel] = ConsciousnessCouncilInput

    def _run(self, question: str, council_size: str = "deep", mode: str = "deliberation") -> str:
        return ConsciousnessCouncil()._run(question, council_size, mode)