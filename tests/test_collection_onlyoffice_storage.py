import pytest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import core.tasks as tasks
import api.documents as api_docs
from core.database import DocumentFolder, Document

class FakeSession:
    def __init__(self):
        self.added = []
        self.executed = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        class ExecRes:
            def scalars(self):
                class Scalars:
                    def first(self):
                        return None
                return Scalars()
        return ExecRes()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        pass

@pytest.mark.asyncio
async def test_get_or_create_onlyoffice_folder_creates_new():
    session = FakeSession()
    account_id = str(uuid.uuid4())
    topic = "Colección de Prueba"
    workspace_id = str(uuid.uuid4())

    folder_id = await tasks.get_or_create_onlyoffice_folder(
        session, account_id, topic, workspace_id
    )

    assert isinstance(folder_id, uuid.UUID)
    assert len(session.added) == 1
    added_folder = session.added[0]
    assert isinstance(added_folder, DocumentFolder)
    assert added_folder.name == topic
    assert added_folder.account_id == uuid.UUID(account_id)
    assert added_folder.workspace_id == uuid.UUID(workspace_id)

@pytest.mark.asyncio
async def test_process_upload_task_saves_in_collection_subfolder(monkeypatch, tmp_path):
    docs_root = tmp_path / "onlyoffice_docs"
    monkeypatch.setattr(tasks.settings, "onlyoffice_docs_root", str(docs_root))
    monkeypatch.setattr(tasks, "ONLYOFFICE_DOCS_ROOT", docs_root)

    account_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    topic = "Mi_Colección/Con_Sub/Slaves"
    clean_topic = topic.replace("/", "_").replace("\\", "_")

    file_data = {
        "filename": "test.docx",
        "content": b"dummy docx content"
    }

    session = FakeSession()
    class FakeDBCtx:
        async def __aenter__(self):
            return session
        async def __aexit__(self, exc_type, exc, tb):
            pass
    monkeypatch.setattr(tasks, "DBSession", lambda _: FakeDBCtx())

    async def mock_extract(*args, **kwargs):
        return ("dummy text", {"some": "metadata"})
    monkeypatch.setattr(tasks, "extract_text_and_metadata_from_document", mock_extract)

    async def mock_send_personal(*args, **kwargs):
        pass
    monkeypatch.setattr(tasks, "send_personal_message", mock_send_personal)

    async def mock_process_rag(*args, **kwargs):
        return 1
    monkeypatch.setattr(tasks, "process_multiple_documents_for_rag", mock_process_rag)

    async def mock_extract_titles(*args, **kwargs):
        pass
    monkeypatch.setattr(tasks, "extract_titles_and_update_metadata", mock_extract_titles)

    async def mock_process_graph(*args, **kwargs):
        pass
    monkeypatch.setattr(tasks, "process_knowledge_graph", mock_process_graph)

    await tasks.process_upload_task(
        task_id=task_id,
        account_id=account_id,
        file_data_list=[file_data],
        topic=topic
    )

    collection_dir = docs_root / account_id / clean_topic
    assert collection_dir.exists()
    assert collection_dir.is_dir()

    saved_files = list(collection_dir.glob("*.docx"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"dummy docx content"

    assert len(session.added) > 0
    doc_entries = [obj for obj in session.added if isinstance(obj, Document)]
    assert len(doc_entries) == 1
    doc = doc_entries[0]
    assert doc.filename == "test.docx"
    assert doc.file_path == f"{account_id}/{clean_topic}/{saved_files[0].name}"
