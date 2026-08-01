import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from skills.profile_and_tasks_skill.scripts.manage_tasks_tool import ManageTasksInput, ManageTasksTool


def test_manage_tasks_input_accepts_list_action():
    payload = ManageTasksInput(action="list", status="Pendiente")
    assert payload.action == "list"
    assert payload.status == "Pendiente"


@pytest.mark.asyncio
async def test_manage_tasks_tool_arun_list_no_tasks():
    tool = ManageTasksTool(account_id=str(uuid.uuid4()))
    
    mock_manager = AsyncMock()
    mock_manager.list_tasks.return_value = []
    
    mock_db = AsyncMock()
    mock_db.get.return_value = None

    with patch("skills.profile_and_tasks_skill.scripts.manage_tasks_tool.DBSession") as mock_db_session_cls, \
         patch("skills.profile_and_tasks_skill.scripts.manage_tasks_tool.TasksManager", return_value=mock_manager):
        
        mock_db_session_cls.return_value.__aenter__.return_value = mock_db
        
        res = await tool._arun(action="list")
        assert "No se encontraron tareas" in res


@pytest.mark.asyncio
async def test_manage_tasks_tool_arun_list_with_tasks():
    account_id = str(uuid.uuid4())
    tool = ManageTasksTool(account_id=account_id)
    
    task_id_1 = str(uuid.uuid4())
    task_id_2 = str(uuid.uuid4())
    
    sample_tasks = [
        {
            "id": task_id_1,
            "description": "Comprar insumos",
            "is_completed": False,
            "status": "Pendiente",
            "start_date": "2026-08-01T10:00:00+00:00",
            "end_date": "2026-08-01T18:00:00+00:00",
            "due_date": None,
        },
        {
            "id": task_id_2,
            "description": "Revisar correo",
            "is_completed": True,
            "status": "Hecho",
            "start_date": None,
            "end_date": None,
            "due_date": "2026-08-02T12:00:00+00:00",
        }
    ]
    
    mock_manager = AsyncMock()
    mock_manager.list_tasks.return_value = sample_tasks
    
    mock_db = AsyncMock()
    mock_db.get.return_value = None

    with patch("skills.profile_and_tasks_skill.scripts.manage_tasks_tool.DBSession") as mock_db_session_cls, \
         patch("skills.profile_and_tasks_skill.scripts.manage_tasks_tool.TasksManager", return_value=mock_manager):
        
        mock_db_session_cls.return_value.__aenter__.return_value = mock_db
        
        res = await tool._arun(action="list")
        
        # Verify output includes IDs, descriptions, statuses, and dates
        assert task_id_1 in res
        assert "Comprar insumos" in res
        assert task_id_2 in res
        assert "Revisar correo" in res
        assert "2026-08-01" in res
        assert "2026-08-02" in res
