import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.analysis_progress import build_analysis_progress_payload


def test_build_analysis_progress_payload_creates_progress_block():
    payload = build_analysis_progress_payload(
        phase="analyzing",
        message="Analizando documento...",
        progress_percent=42,
        analysis_type="document",
        file_name="archivo.pdf",
    )

    assert payload["analysis_progress"]["phase"] == "analyzing"
    assert payload["analysis_progress"]["progress_percent"] == 42
    assert payload["analysis_progress"]["file_name"] == "archivo.pdf"
    assert payload["analysis_metadata"]["analysis_type"] == "document"
    assert payload["analysis_metadata"]["file_name"] == "archivo.pdf"


def test_build_analysis_progress_payload_preserves_existing_metadata():
    payload = build_analysis_progress_payload(
        {
            "analysis_metadata": {
                "tool_used": "advanced_text_analyzer.py",
            }
        },
        phase="saving_to_neo4j",
        message="Guardando...",
        progress_percent=94,
        analysis_type="document_summary",
        file_name="resumen.md",
        topic="repositorio",
    )

    assert payload["analysis_metadata"]["tool_used"] == "advanced_text_analyzer.py"
    assert payload["analysis_metadata"]["analysis_type"] == "document_summary"
    assert payload["analysis_metadata"]["topic"] == "repositorio"
    assert payload["analysis_progress"]["message"] == "Guardando..."
