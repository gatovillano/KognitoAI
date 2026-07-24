"""
KAI-Ethno: Investigación Antropológica Aumentada
Sistema multi-agente para investigación etnográfica y bibliográfica
"""

__version__ = "1.0.0"
__author__ = "KognitoAI"

from .agents.bibliomancer import BibliomancerAgent, BibliomancerState
from .agents.ethnograph import EthnographAgent, EthnographState
from .agents.pattern_finder import PatternFinderAgent, PatternFinderState
from .agents.synthesizer import SynthesizerAgent, SynthesizerState
from .agents.visualizer import VisualizerAgent, VisualizerState
from .agents.scribe import ScribeAgent, ScribeState
from .agents.archivist import ArchivistAgent, ArchivistState

__all__ = [
    "BibliomancerAgent",
    "BibliomancerState",
    "EthnographAgent",
    "EthnographState",
    "PatternFinderAgent",
    "PatternFinderState",
    "SynthesizerAgent",
    "SynthesizerState",
    "VisualizerAgent",
    "VisualizerState",
    "ScribeAgent",
    "ScribeState",
    "ArchivistAgent",
    "ArchivistState",
]
