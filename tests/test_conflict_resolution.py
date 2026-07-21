import asyncio
import pytest
from unittest.mock import MagicMock
from core.enhanced_memory_manager import EnhancedMemoryManager


def test_detect_and_resolve_conflicts():
    emm = EnhancedMemoryManager()
    
    traditional_context = {
        "memories": [
            {"content": "El servidor PostgreSQL está alojado en AWS US-East-1"},
            {"content": "El sistema utiliza Redis para caching local"}
        ]
    }

    graph_context = {
        "entities": [
            {
                "name": "PostgreSQL",
                "type": "TECHNOLOGY",
                "trust_score": 0.9,
                "description": "Base de datos alojada en Google Cloud Platform"
            },
            {
                "name": "Redis",
                "type": "TECHNOLOGY",
                "trust_score": 0.4,
                "description": "Cache en memoria"
            }
        ]
    }

    conflicts = asyncio.run(emm._detect_and_resolve_conflicts(
        traditional_context=traditional_context,
        graph_context=graph_context,
        user_query="¿Dónde está la base de datos?"
    ))

    # Debería resolver el conflicto para PostgreSQL (trust 0.9 >= 0.7)
    assert len(conflicts) == 1
    assert conflicts[0]["entity"] == "PostgreSQL"
    assert conflicts[0]["prevailed_source"] == "knowledge_graph"
    assert conflicts[0]["trust_score"] == 0.9
