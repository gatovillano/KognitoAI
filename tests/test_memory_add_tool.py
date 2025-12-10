# tests/test_memory_add_tool.py

import pytest
from unittest.mock import AsyncMock, patch

from tools.memory_add_tool import MemoryAddTool

@pytest.fixture
def mock_dependencies():
    """Fixture para mockear las dependencias de la herramienta."""
    with patch('tools.memory_add_tool.add_memory_to_vector_db', new_callable=AsyncMock) as mock_add, \
         patch('tools.memory_add_tool.proactive_knowledge_linker_trigger', new_callable=AsyncMock) as mock_linker, \
         patch('tools.memory_add_tool.schedule_memory_graph_processing', new_callable=AsyncMock) as mock_scheduler:
        yield {
            "add": mock_add,
            "linker": mock_linker,
            "scheduler": mock_scheduler
        }

@pytest.mark.asyncio
async def test_memory_add_tool_successful_call(mock_dependencies):
    """
    Verifica que una llamada exitosa a la herramienta invoca todas las dependencias correctas.
    """
    # Arrange
    tool = MemoryAddTool(account_id="test_account_id", workspace_id="test_workspace")
    content = "El usuario prefiere el té verde."
    mem_type = "user_memory"
    category = "preference"

    # Act
    result = await tool._arun(content=content, type=mem_type, category=category)

    # Assert
    # 1. Verificar que se guardó en la DB vectorial
    mock_dependencies["add"].assert_called_once()
    add_args = mock_dependencies["add"].call_args.kwargs
    assert add_args["account_id"] == "test_account_id"
    assert add_args["content"] == content
    assert add_args["type"] == mem_type
    assert add_args["workspace_id"] == "test_workspace"

    # 2. Verificar que se disparó el linker proactivo
    mock_dependencies["linker"].assert_called_once()

    # 3. Verificar que se programó el procesamiento del grafo (¡NUEVO!)
    mock_dependencies["scheduler"].assert_called_once_with(account_id="test_account_id")

    # 4. Verificar el mensaje de retorno
    assert "información ha sido añadida" in result
    assert "procesando para enriquecer tu grafo" in result

@pytest.mark.asyncio
async def test_memory_add_tool_handles_empty_content(mock_dependencies):
    """
    Verifica que la herramienta no hace nada si el contenido está vacío.
    """
    # Arrange
    tool = MemoryAddTool(account_id="test_account_id")
    
    # Act
    result = await tool._arun(content="  ") # Contenido vacío o solo espacios

    # Assert
    assert result == "No se puede guardar contenido vacío en la memoria."
    mock_dependencies["add"].assert_not_called()
    mock_dependencies["linker"].assert_not_called()
    mock_dependencies["scheduler"].assert_not_called()

@pytest.mark.asyncio
async def test_memory_add_tool_handles_db_error(mock_dependencies):
    """
    Verifica que la herramienta maneja errores de la base de datos y no dispara
    los procesos siguientes.
    """
    # Arrange
    mock_dependencies["add"].side_effect = Exception("DB connection error")
    tool = MemoryAddTool(account_id="test_account_id")
    content = "Contenido que fallará."

    # Act
    result = await tool._arun(content=content)

    # Assert
    assert "Ocurrió un error" in result
    assert "DB connection error" in result
    mock_dependencies["add"].assert_called_once()
    mock_dependencies["linker"].assert_not_called()
    mock_dependencies["scheduler"].assert_not_called()
