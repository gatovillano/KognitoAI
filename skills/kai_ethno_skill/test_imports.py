#!/usr/bin/env python3
"""
Script de prueba de importaciones para KAI-Ethno
Verifica que todos los módulos y clases se importan correctamente
"""

import sys
import os
from pathlib import Path

# Agregar el directorio padre al sys.path para importar kai_ethno_skill
skill_dir = Path(__file__).parent.resolve()
if str(skill_dir) not in sys.path:
    sys.path.insert(0, str(skill_dir))

parent_dir = skill_dir.parent.resolve()
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


print("=" * 60)
print("KAI-Ethno: Prueba de Importaciones")
print("=" * 60)

# Test 1: Importar el paquete principal
print("\n[1/5] Importando paquete o módulos principales...")
try:
    try:
        import kai_ethno_skill as pkg
        version = getattr(pkg, '__version__', '1.0.0')
    except ImportError:
        from agents.bibliomancer import BibliomancerAgent
        version = "1.0.0 (local modules)"
    print(f"   ✓ Paquete/Módulos KAI-Ethno versión {version}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)


# Test 2: Importar todas las clases de agentes y estados
print("\n[2/5] Importando agentes y estados...")
try:
    try:
        from kai_ethno_skill import (
            BibliomancerAgent, BibliomancerState,
            EthnographAgent, EthnographState,
            PatternFinderAgent, PatternFinderState,
            SynthesizerAgent, SynthesizerState,
            VisualizerAgent, VisualizerState,
            ScribeAgent, ScribeState,
            ArchivistAgent, ArchivistState,
        )
    except ImportError:
        from agents.bibliomancer import BibliomancerAgent, BibliomancerState
        from agents.ethnograph import EthnographAgent, EthnographState
        from agents.pattern_finder import PatternFinderAgent, PatternFinderState
        from agents.synthesizer import SynthesizerAgent, SynthesizerState
        from agents.visualizer import VisualizerAgent, VisualizerState
        from agents.scribe import ScribeAgent, ScribeState
        from agents.archivist import ArchivistAgent, ArchivistState

    print("   ✓ Todos los agentes importados correctamente")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 3: Importar módulos core
print("\n[3/5] Importando módulos core...")
try:
    try:
        from kai_ethno_skill.core.ethics_council import EthicsCouncil, EthicsVerdict
        from kai_ethno_skill.core.message_bus import MessageBus, MessageType
        from kai_ethno_skill.core.llm_service import LLMService
    except ImportError:
        from core.ethics_council import EthicsCouncil, EthicsVerdict
        from core.message_bus import MessageBus, MessageType
        from core.llm_service import LLMService

    print("   ✓ Módulos core (incluyendo LLMService) importados correctamente")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)


# Test 4: Instanciar agentes
print("\n[4/5] Instanciando agentes...")
try:
    agents = {
        "Bibliomancer": BibliomancerAgent(),
        "Ethnograph": EthnographAgent(),
        "PatternFinder": PatternFinderAgent(),
        "Synthesizer": SynthesizerAgent(),
        "Visualizer": VisualizerAgent(),
        "Scribe": ScribeAgent(),
        "Archivist": ArchivistAgent(),
    }
    for name, agent in agents.items():
        print(f"   ✓ {name}: {type(agent).__name__}")
except Exception as e:
    print(f"   ✗ Error al instanciar agentes: {e}")
    sys.exit(1)

# Test 5: Instanciar componentes core
print("\n[5/5] Instanciando componentes core...")
try:
    message_bus = MessageBus()
    ethics_council = EthicsCouncil()
    print("   ✓ MessageBus instanciado")
    print("   ✓ EthicsCouncil instanciado")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ TODAS LAS PRUEBAS DE IMPORTACIÓN PASARON")
print("=" * 60)
