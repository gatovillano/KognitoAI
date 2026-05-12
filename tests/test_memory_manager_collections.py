import pytest
import uuid
from unittest.mock import MagicMock

import core.memory_manager as mm

class FakeSession:
    def __init__(self, scalar_return=None, get_return=None, rowcount=1):
        self._scalar_return = scalar_return
        self._get_return = get_return
        self.rowcount = rowcount
        self.added = []
    async def scalar(self, *args, **kwargs):
        return self._scalar_return
    async def execute(self, *args, **kwargs):
        # Return a simple object with .scalars().first() or .rowcount
        class ExecRes:
            def __init__(self, first_val=None, rowcount=0):
                self._first = first_val
                self.rowcount = rowcount
            def scalars(self):
                return self
            def all(self):
                return self._first or []
            def first(self):
                return self._first
        # For convenience, if _scalar_return is a list, return it via all()
        return ExecRes(first_val=self._scalar_return, rowcount=getattr(self, 'rowcount', 0))
    async def commit(self):
        return None
    async def refresh(self, obj):
        try:
            obj.id = uuid.uuid4()
        except Exception:
            pass
    async def close(self):
        return None
    async def rollback(self):
        return None
    def add(self, obj):
        self.added.append(obj)
    async def get(self, model, id):
        return self._get_return

class FakeDBCtx:
    def __init__(self, session):
        self._session = session
    async def __aenter__(self):
        return self._session
    async def __aexit__(self, exc_type, exc, tb):
        return False

@pytest.mark.asyncio
async def test_create_empty_collection_creates_when_not_exists(monkeypatch):
    fake_session = FakeSession(scalar_return=None)
    monkeypatch.setattr(mm, 'DBSession', lambda session_local: FakeDBCtx(fake_session))

    result = await mm.create_empty_collection(account_id=str(uuid.uuid4()), topic_name='test_topic', description='desc')
    assert result is True

@pytest.mark.asyncio
async def test_create_empty_collection_returns_true_when_exists(monkeypatch):
    # Simulate existing collection by making scalar() return a truthy value
    fake_session = FakeSession(scalar_return=object())
    monkeypatch.setattr(mm, 'DBSession', lambda session_local: FakeDBCtx(fake_session))

    result = await mm.create_empty_collection(account_id=str(uuid.uuid4()), topic_name='existing_topic', description=None)
    assert result is True

@pytest.mark.asyncio
async def test_update_collection_returns_false_when_not_found(monkeypatch):
    # Simulate execute returning scalars().first() == None
    fake_session = FakeSession(scalar_return=None)
    # execute will return ExecRes with first_val=None which triggers not found
    monkeypatch.setattr(mm, 'DBSession', lambda session_local: FakeDBCtx(fake_session))

    res = await mm.update_collection(account_id=str(uuid.uuid4()), old_topic_name='nope')
    assert res is False

@pytest.mark.asyncio
async def test_delete_collection_success(monkeypatch):
    # Patch get_user_document_topic_by_name to return a collection dict
    monkeypatch.setattr(mm, 'get_user_document_topic_by_name', lambda account_id, topic_name, workspace_id=None: {'id': str(uuid.uuid4()), 'workspace_id': None})
    # Patch delete_document_chunks to return 0
    monkeypatch.setattr(mm, 'delete_document_chunks', lambda account_id, topic, workspace_id=None: 0)

    # Make DBSession return a session whose execute returns rowcount=1
    fake_session = FakeSession(scalar_return=None, rowcount=1)
    # Override execute to return an object with rowcount
    async def exec_override(*args, **kwargs):
        class ExecRes:
            def __init__(self):
                self.rowcount = 1
        return ExecRes()
    fake_session.execute = exec_override

    monkeypatch.setattr(mm, 'DBSession', lambda session_local: FakeDBCtx(fake_session))

    res = await mm.delete_collection(account_id=str(uuid.uuid4()), topic_name='todelete')
    assert res is True
