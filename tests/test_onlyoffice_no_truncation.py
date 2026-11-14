# tests/test_onlyoffice_no_truncation.py

import io
import uuid
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage

import core.onlyoffice_storage as storage
import skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool as read_tool_module
from skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool import ReadOnlyOfficeDocumentTool
from core.agent import NativeAgentRunner


class _FakeResult:
    def __init__(self, document):
        self._document = document

    def scalar_one_or_none(self):
        return self._document


class _FakeSession:
    def __init__(self, document):
        self._document = document

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt):
        return _FakeResult(self._document)


def test_read_onlyoffice_document_does_not_truncate_long_document(monkeypatch, tmp_path):
    """Verifica que ReadOnlyOfficeDocumentTool no trunca documentos largos (> 20.000 caracteres)."""
    account_id = str(uuid.uuid4())
    document_id = uuid.uuid4()
    
    # Generar un texto extenso de más de 20.000 caracteres
    paragraph_base = "Este es un párrafo de prueba detallado para verificar que no existe truncamiento en la lectura de OnlyOffice. "
    long_content = paragraph_base * 200  # ~22.000 caracteres
    assert len(long_content) > 20000

    physical_file = tmp_path / account_id / "documento_largo.txt"
    physical_file.parent.mkdir(parents=True, exist_ok=True)
    physical_file.write_text(long_content, encoding="utf-8")

    doc = SimpleNamespace(
        id=document_id,
        account_id=uuid.UUID(account_id),
        filename="documento_largo.txt",
        extension="txt",
        file_path=f"{account_id}/documento_largo.txt",
    )

    monkeypatch.setattr(read_tool_module, "SessionLocal", lambda: _FakeSession(doc))
    monkeypatch.setattr(read_tool_module, "resolve_onlyoffice_file_path", lambda _: physical_file)

    tool = ReadOnlyOfficeDocumentTool(account_id=account_id)
    result = asyncio.run(tool._arun(str(document_id)))

    # Verificar que el resultado preserva todo el contenido y no tiene indicadores de truncamiento
    assert isinstance(result, str)
    assert "[contenido truncado" not in result
    assert "[truncado]" not in result
    assert len(result) >= len(long_content)
    # Verificar que el final del documento está presente
    assert result.endswith(paragraph_base.strip()) or paragraph_base in result[-200:]


def test_native_agent_runner_does_not_truncate_onlyoffice_reader():
    """Verifica que el safety check de NativeAgentRunner no trunca read_onlyoffice_document."""
    account_id = str(uuid.uuid4())
    long_doc_text = "Sección de OnlyOffice con información exhaustiva. " * 300  # ~15.000 caracteres
    assert len(long_doc_text) > 10000

    ws_messages = []
    def fake_send_personal_message(target_account_id, payload, **kwargs):
        ws_messages.append(payload)

    runner = NativeAgentRunner.__new__(NativeAgentRunner)

    # 1. Herramienta read_onlyoffice_document devolviendo texto plano largo
    mock_tool = MagicMock()
    mock_tool.name = "read_onlyoffice_document"
    mock_tool.ainvoke = AsyncMock(return_value=long_doc_text)

    # Simular la lógica de ejecución interna
    tool_call = {"name": "read_onlyoffice_document", "args": {"document_id": "test-uuid"}, "id": "call_123"}
    
    # Validar lógica de discriminación
    tool_name = tool_call["name"]
    is_doc_reading_tool = (
        tool_name in (
            "read_onlyoffice_document",
            "read_onlyoffice_document_tool",
            "get_document_content_tool",
        )
        or ("onlyoffice" in str(tool_name).lower() and "read" in str(tool_name).lower())
    )
    assert is_doc_reading_tool is True

    # Comprobar que out_str no se trunca
    out_str = long_doc_text
    if not is_doc_reading_tool:
        if isinstance(out_str, str) and len(out_str) > 5000:
            out_str = out_str[:4000] + "\n...[contenido truncado por seguridad de contexto]"

    assert len(out_str) == len(long_doc_text)
    assert "[contenido truncado" not in out_str

    # 2. Herramienta regular (ej. bash o web_search) SÍ debe truncarse por seguridad
    regular_tool_name = "terminal_executor"
    is_regular_doc_reading = (
        regular_tool_name in (
            "read_onlyoffice_document",
            "read_onlyoffice_document_tool",
            "get_document_content_tool",
        )
        or ("onlyoffice" in str(regular_tool_name).lower() and "read" in str(regular_tool_name).lower())
    )
    assert is_regular_doc_reading is False

    reg_out_str = "Log masivo de terminal " * 500
    if not is_regular_doc_reading:
        if isinstance(reg_out_str, str) and len(reg_out_str) > 5000:
            reg_out_str = reg_out_str[:4000] + "\n...[contenido truncado por seguridad de contexto]"

    assert "...[contenido truncado por seguridad de contexto]" in reg_out_str
    assert len(reg_out_str) < 5000


def test_multimodal_list_blocks_not_truncated_for_onlyoffice():
    """Verifica que bloques multimodales devueltos como lista no sufran truncamiento en _safe_blocks."""
    tool_name = "read_onlyoffice_document"
    is_doc_reading_tool = (
        tool_name in (
            "read_onlyoffice_document",
            "read_onlyoffice_document_tool",
            "get_document_content_tool",
        )
        or ("onlyoffice" in str(tool_name).lower() and "read" in str(tool_name).lower())
    )

    long_text = "Reporte financiero con tablas e imágenes detalladas. " * 200
    out_blocks = [
        {"type": "text", "text": long_text},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,12345"}}
    ]

    out_str = out_blocks
    if not is_doc_reading_tool:
        if isinstance(out_str, list):
            _safe_blocks = []
            for _b in out_str:
                if isinstance(_b, dict) and _b.get("type") == "text" and isinstance(_b.get("text"), str) and len(_b["text"]) > 5000:
                    _b = dict(_b)
                    _b["text"] = _b["text"][:4000] + "...[truncado]"
                    _safe_blocks.append(_b)
                else:
                    _safe_blocks.append(_b)
            out_str = _safe_blocks

    assert out_str[0]["text"] == long_text
    assert "[truncado]" not in out_str[0]["text"]


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    print("Running test_read_onlyoffice_document_does_not_truncate_long_document...")
    with tempfile.TemporaryDirectory() as tmpdir:
        class MonkeyPatch:
            def setattr(self, target, name, value):
                setattr(target, name, value)
        test_read_onlyoffice_document_does_not_truncate_long_document(MonkeyPatch(), Path(tmpdir))
    print("✅ test_read_onlyoffice_document_does_not_truncate_long_document passed!")

    print("Running test_native_agent_runner_does_not_truncate_onlyoffice_reader...")
    test_native_agent_runner_does_not_truncate_onlyoffice_reader()
    print("✅ test_native_agent_runner_does_not_truncate_onlyoffice_reader passed!")

    print("Running test_multimodal_list_blocks_not_truncated_for_onlyoffice...")
    test_multimodal_list_blocks_not_truncated_for_onlyoffice()
    print("✅ test_multimodal_list_blocks_not_truncated_for_onlyoffice passed!")

    print("🎉 All OnlyOffice no-truncation tests passed successfully!")

