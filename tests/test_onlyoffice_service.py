# tests/test_onlyoffice_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.onlyoffice_service import OnlyOfficeService
import io

@pytest.mark.asyncio
async def test_get_editor_config_note_not_found():
    # Setup
    db = AsyncMock()
    service = OnlyOfficeService(db)
    service.notes_manager.get_note_by_id = AsyncMock(return_value=None)
    
    # Execute
    config = await service.get_editor_config(1, "account_123")
    
    # Assert
    assert config is None
    service.notes_manager.get_note_by_id.assert_called_once_with("account_123", 1)

@pytest.mark.asyncio
async def test_extract_text_from_docx_error_handling():
    # Setup
    db = AsyncMock()
    service = OnlyOfficeService(db)
    
    # Execute
    # Pasamos bytes inválidos que no son un docx real
    text = service._extract_text_from_docx(b"not a docx")
    
    # Assert
    assert text == ""

@pytest.mark.asyncio
async def test_handle_callback_status_unknown():
    # Setup
    db = AsyncMock()
    service = OnlyOfficeService(db)
    
    # Execute
    result = await service.handle_callback(1, "acc_1", {"status": 100})
    
    # Assert
    assert result == {"error": 0} # Status desconocido suele ser ignorado sin error

@pytest.mark.asyncio
async def test_handle_callback_no_status():
    # Setup
    db = AsyncMock()
    service = OnlyOfficeService(db)
    
    # Execute
    result = await service.handle_callback(1, "acc_1", {}, remote_ip="1.2.3.4")
    
    # Assert
    assert result["error"] == 1
    assert "Invalid status" in result["message"]
