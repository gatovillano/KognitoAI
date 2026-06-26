from pathlib import Path
from types import SimpleNamespace
import asyncio
import uuid
import sys
import types

import pytest

passlib_module = types.ModuleType("passlib")
passlib_context_module = types.ModuleType("passlib.context")


class _FakeCryptContext:
    def __init__(self, *args, **kwargs):
        pass

    def verify(self, *args, **kwargs):
        return True

    def hash(self, value):
        return str(value)


passlib_context_module.CryptContext = _FakeCryptContext
passlib_module.context = passlib_context_module
sys.modules.setdefault("passlib", passlib_module)
sys.modules.setdefault("passlib.context", passlib_context_module)

multipart_module = types.ModuleType("multipart")
multipart_submodule = types.ModuleType("multipart.multipart")


def _fake_parse_options_header(value):
    return value, {}


multipart_submodule.parse_options_header = _fake_parse_options_header
multipart_module.multipart = multipart_submodule
sys.modules.setdefault("multipart", multipart_module)
sys.modules.setdefault("multipart.multipart", multipart_submodule)

fitz_module = types.ModuleType("fitz")
sys.modules.setdefault("fitz", fitz_module)

import core.onlyoffice_storage as storage
import skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool as read_tool_module
import skills.onlyoffice_rag_pipeline.scripts.process_document as process_tool_module
from skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool import ReadOnlyOfficeDocumentTool
from skills.onlyoffice_rag_pipeline.scripts.process_document import ProcessOnlyOfficeDocumentTool


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


def test_read_onlyoffice_tool_resolves_relative_storage_path(monkeypatch, tmp_path):
    account_id = str(uuid.uuid4())
    document_id = uuid.uuid4()
    physical_file = tmp_path / account_id / "nota.txt"
    physical_file.parent.mkdir(parents=True, exist_ok=True)
    physical_file.write_text("contenido original", encoding="utf-8")

    doc = SimpleNamespace(
        id=document_id,
        account_id=uuid.UUID(account_id),
        filename="nota.txt",
        extension="txt",
        file_path=f"{account_id}/nota.txt",
    )

    monkeypatch.setattr(read_tool_module, "SessionLocal", lambda: _FakeSession(doc))

    async def fake_extract(filename, file_bytes):
        return ("contenido parseado", {})

    monkeypatch.setattr(read_tool_module, "extract_text_and_metadata_from_document", fake_extract)
    monkeypatch.setattr(read_tool_module, "resolve_onlyoffice_file_path", lambda _: physical_file)

    tool = ReadOnlyOfficeDocumentTool(account_id=account_id)

    result = asyncio.run(tool._arun(str(document_id)))

    assert "contenido parseado" in result
    assert "nota.txt" in result


def test_process_onlyoffice_tool_extracts_text_from_relative_path(monkeypatch, tmp_path):
    physical_file = tmp_path / "user" / "archivo.txt"
    physical_file.parent.mkdir(parents=True, exist_ok=True)
    physical_file.write_text("hola desde onlyoffice", encoding="utf-8")

    doc = SimpleNamespace(
        filename="archivo.txt",
        file_path="user/archivo.txt",
    )

    monkeypatch.setattr(process_tool_module, "resolve_onlyoffice_file_path", lambda _: physical_file)

    tool = ProcessOnlyOfficeDocumentTool(account_id=str(uuid.uuid4()))

    result = asyncio.run(tool._extract_text(doc))

    assert result == "hola desde onlyoffice"


def test_onlyoffice_storage_rejects_paths_outside_root(monkeypatch, tmp_path):
    docs_root = tmp_path / "onlyoffice"
    docs_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(storage, "ONLYOFFICE_DOCS_ROOT", docs_root.resolve())

    with pytest.raises(ValueError):
        storage.resolve_onlyoffice_file_path("../escape.txt")


def test_onlyoffice_storage_resolves_across_multiple_roots(monkeypatch, tmp_path):
    docs_root = tmp_path / "onlyoffice"
    docs_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(storage, "ONLYOFFICE_DOCS_ROOT", docs_root.resolve())
    
    media_root = tmp_path / "media_root"
    media_docs_root = media_root / "documents"
    media_docs_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(storage.settings, "media_root", str(media_root.resolve()))

    file_onlyoffice = docs_root / "user1" / "file1.docx"
    file_onlyoffice.parent.mkdir(parents=True, exist_ok=True)
    file_onlyoffice.write_text("onlyoffice content", encoding="utf-8")

    file_media = media_docs_root / "user1" / "file2.docx"
    file_media.parent.mkdir(parents=True, exist_ok=True)
    file_media.write_text("media content", encoding="utf-8")

    res1 = storage.resolve_onlyoffice_file_path("user1/file1.docx")
    assert res1 == file_onlyoffice.resolve()

    res2 = storage.resolve_onlyoffice_file_path("user1/file2.docx")
    assert res2 == file_media.resolve()

    res3 = storage.resolve_onlyoffice_file_path("user1/file3.docx")
    assert res3 == (docs_root / "user1" / "file3.docx").resolve()

