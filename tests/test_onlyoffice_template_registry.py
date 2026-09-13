import pytest
import os
import tempfile
from skills.onlyoffice_skill.design.template_registry import (
    list_templates,
    get_template_info,
    create_from_template,
    TEMPLATES,
)

def test_list_templates():
    templates = list_templates()
    assert len(templates) >= 8
    ids = [t["id"] for t in templates]
    assert "executive_report" in ids
    assert "commercial_proposal" in ids
    assert "project_charter" in ids
    assert "financial_budget" in ids
    assert "sales_dashboard" in ids
    assert "project_tracker" in ids
    assert "pitch_deck" in ids
    assert "quarterly_review" in ids

def test_get_template_info():
    info = get_template_info("executive_report")
    assert info is not None
    assert info["doc_type"] == "word"
    assert info["id"] == "executive_report"

def test_create_from_template_word():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "reporte.docx")
        success = create_from_template(
            "executive_report",
            path,
            title="Informe de Desempeño Trimestral",
            subtitle="Resultados Q3 2026",
            theme_name="corporate_blue"
        )
        assert success is True
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

def test_create_from_template_excel():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "presupuesto.xlsx")
        success = create_from_template(
            "financial_budget",
            path,
            title="Presupuesto Operativo 2026",
            theme_name="emerald_green"
        )
        assert success is True
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

def test_create_from_template_powerpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "pitch.pptx")
        success = create_from_template(
            "pitch_deck",
            path,
            title="KAI Solutions - Pitch Deck",
            subtitle="Revolución en Productividad Corporativa",
            theme_name="dark_slate"
        )
        assert success is True
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
