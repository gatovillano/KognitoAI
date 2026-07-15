import pytest
import uuid
import os
from pathlib import Path
from fastapi import HTTPException, UploadFile
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

# Import the Document database model
from core.database import Document, DocumentFolder

@pytest.mark.asyncio
async def test_put_onlyoffice_document_not_found(monkeypatch):
    # Mock db session to return None when getting document
    db_session = AsyncMock()
    db_session.get.return_value = None

    from api.onlyoffice import update_document_content

    # Call the endpoint directly
    with pytest.raises(HTTPException) as exc_info:
        await update_document_content(
            document_id=uuid.uuid4(),
            file=MagicMock(spec=UploadFile),
            current_account_id=str(uuid.uuid4()),
            db=db_session
        )
    
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Documento no encontrado"

@pytest.mark.asyncio
async def test_put_onlyoffice_document_success(monkeypatch, tmp_path):
    # Mocking filesystem path
    temp_file = tmp_path / "test.docx"
    temp_file.write_text("old content")

    account_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_doc = Document(
        id=doc_id,
        account_id=account_id,
        filename="test.docx",
        extension="docx",
        file_path=f"{account_id}/test.docx",
        workspace_id=None,
        folder_id=None
    )

    # Mock db session
    db_session = AsyncMock()
    db_session.get.side_effect = lambda model, oid: mock_doc if oid == doc_id else None
    db_session.commit = AsyncMock()

    # Mock dependencies/functions inside api/onlyoffice.py
    monkeypatch.setattr("api.onlyoffice._can_access_document", AsyncMock(return_value=True))
    monkeypatch.setattr("api.onlyoffice.resolve_onlyoffice_file_path", lambda path: temp_file)

    # Mock parser and memory manager functions
    extracted_text_mock = AsyncMock(return_value=("new text content", {"author": "test"}))
    monkeypatch.setattr("api.onlyoffice.extract_text_and_metadata_from_document", extracted_text_mock)
    
    delete_chunks_mock = AsyncMock()
    monkeypatch.setattr("api.onlyoffice.delete_document_chunks", delete_chunks_mock)

    process_rag_mock = AsyncMock(return_value=1)
    monkeypatch.setattr("api.onlyoffice.process_document_for_rag", process_rag_mock)

    # Mock file upload
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=b"new binary content")
    mock_file.filename = "test.docx"

    from api.onlyoffice import update_document_content

    response = await update_document_content(
        document_id=doc_id,
        file=mock_file,
        current_account_id=str(account_id),
        db=db_session
    )

    assert response["document_id"] == str(doc_id)
    assert response["message"] == "Documento actualizado con éxito"
    
    # Check if file content was updated physically
    assert temp_file.read_text() == "new binary content"
    
    # Verify mock calls
    extracted_text_mock.assert_called_once_with("test.docx", b"new binary content")
    delete_chunks_mock.assert_called_once_with(
        account_id=str(account_id),
        file_name="test.docx",
        workspace_id=None
    )
    process_rag_mock.assert_called_once()
