"""
Ethnograph Agent
=================

Agente especializado en procesamiento de materiales etnográficos.

Capacidades:
- Análisis del discurso (Fairclough, van Dijk)
- Teoría del Actor-Red (Latour, Callon)
- Etnografía de la práctica (Schatzki, Reckwitz)
- Análisis narrativo (Riessman)
- Codificación temática (Braun & Clarke)
- Detección de PII y enmascaramiento ético
"""

from .agent import EthnographAgent, EthnographState

__all__ = ["EthnographAgent", "EthnographState"]
__version__ = "1.0.0"
