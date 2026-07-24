"""
PatternFinder Agent
====================

Agente especializado en minería de patrones y modelado de tópicos.

Capacidades:
- Redes semánticas y co-ocurrencia de términos
- Clustering temático (LDA, BERTopic)
- Análisis de evolución histórica de conceptos
- Detección de comunidades en redes de citación
- Análisis de sentimiento y polaridad
"""

from .agent import PatternFinderAgent, PatternFinderState

__all__ = ["PatternFinderAgent", "PatternFinderState"]
__version__ = "1.0.0"
