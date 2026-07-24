"""
KAI-Ethno Agents Module
========================

Arquitectura multi-agente para investigación antropológica aumentada.

Agentes disponibles:
- Bibliomancer: Búsqueda y recolección bibliográfica
- Ethnograph: Procesamiento y análisis etnográfico
- PatternFinder: Minería de patrones y modelado de tópicos
- Synthesizer: Síntesis analítica y triangulación
- Visualizer: Generación de visualizaciones académicas
- Scribe: Redacción de documentos académicos
- Archivist: Gestión de memoria y conocimiento
- KAI Core: Orquestador central del sistema
"""

from .bibliomancer.agent import BibliomancerAgent
from .ethnograph.agent import EthnographAgent
from .pattern_finder.agent import PatternFinderAgent
from .synthesizer.agent import SynthesizerAgent
from .visualizer.agent import VisualizerAgent
from .scribe.agent import ScribeAgent
from .archivist.agent import ArchivistAgent
from .kai_core.agent import KAIOrchestrator

__all__ = [
    "BibliomancerAgent",
    "EthnographAgent",
    "PatternFinderAgent",
    "SynthesizerAgent",
    "VisualizerAgent",
    "ScribeAgent",
    "ArchivistAgent",
    "KAIOrchestrator",
]

__version__ = "1.0.0"
__author__ = "KognitoAI"
__description__ = "Agentes especializados para investigación antropológica aumentada"
