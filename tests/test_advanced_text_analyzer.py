import os
import sys
import asyncio
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import settings
from utils.advanced_text_analyzer import CollectionAnalysis, SingleTextAnalysis, text_analyzer


def test_single_text_analysis_accepts_partial_payload_with_defaults():
    payload = {
        "executive_summary": "Resumen breve",
        "general_analysis": "Analisis suficiente",
        "key_themes": [],
        "central_concepts": ["Concepto: definicion"],
        "discipline": ["Derecho"],
        "authorial_tone": "Formal",
    }

    result = SingleTextAnalysis.model_validate(payload)

    assert result.knowledge_gaps == []
    assert result.exploration_questions == []
    assert result.problematic_areas == []
    assert result.final_reflections == []
    assert result.kai_synthesis == ""


def test_analyze_single_text_short_input_returns_complete_shape():
    result = asyncio.run(text_analyzer.analyze_single_text("Texto demasiado corto para analizar."))

    assert result.executive_summary == "Texto demasiado corto para analizar."
    assert result.general_analysis == "Texto insuficiente para análisis detallado"
    assert result.knowledge_gaps == []
    assert result.exploration_questions == []
    assert result.problematic_areas == []
    assert result.final_reflections == []
    assert result.kai_synthesis == "Texto insuficiente para generar una síntesis."


def test_analyze_collection_uses_extended_llm_timeout(monkeypatch):
    captured = {}

    async def fake_run_analysis_with_parser(prompt, output_parser, pydantic_object, account_id=None, timeout_seconds=None):
        captured["timeout_seconds"] = timeout_seconds
        return CollectionAnalysis(
            collection_summary="Resumen",
            general_analysis="Analisis",
            authorial_tone="Formal",
            cross_cutting_themes=[],
            central_concepts=[],
            concept_relationships=[],
            identified_connections=[],
            emergent_knowledge_gaps=[],
            exploration_questions=[],
            problematic_areas=[],
            final_reflections=[],
            collection_insights=[],
            methodological_notes=[],
            kai_synthesis="",
        )

    monkeypatch.setattr(text_analyzer, "_run_analysis_with_parser", fake_run_analysis_with_parser)

    result = asyncio.run(
        text_analyzer.analyze_collection([
            {"title": "Doc 1", "content": "Este es un documento de prueba con suficiente longitud para pasar por el flujo."}
        ])
    )

    assert isinstance(result, CollectionAnalysis)
    assert captured["timeout_seconds"] == max(float(settings.llm_request_timeout), 180.0)
