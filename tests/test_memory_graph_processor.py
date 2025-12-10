# tests/test_memory_graph_processor.py

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from knowledge_graph.memory_graph_processor import (
    schedule_memory_graph_processing,
    process_memory_batches,
    MEMORY_PROCESSING_THRESHOLD,
)

@pytest.fixture
def mock_db_functions():
    """Fixture para mockear las funciones de base de datos."""
    with patch('knowledge_graph.memory_graph_processor.get_unprocessed_memories_count', new_callable=AsyncMock) as mock_count, \
         patch('knowledge_graph.memory_graph_processor.get_unprocessed_memories', new_callable=AsyncMock) as mock_get, \
         patch('knowledge_graph.memory_graph_processor.mark_memories_as_processed', new_callable=AsyncMock) as mock_mark:
        yield {
            "count": mock_count,
            "get": mock_get,
            "mark": mock_mark
        }

@pytest.fixture
def mock_graph_integration():
    """Fixture para mockear la integración con el grafo."""
    with patch('knowledge_graph.memory_graph_processor.GraphIntegration', autospec=True) as mock_graph:
        mock_instance = mock_graph.return_value
        mock_instance.process_documents = AsyncMock()
        yield mock_instance

@pytest.mark.asyncio
async def test_schedule_does_not_trigger_if_below_threshold(mock_db_functions):
    """
    Verifica que el procesamiento no se dispara si el número de memorias
    pendientes es menor que el umbral.
    """
    mock_db_functions["count"].return_value = MEMORY_PROCESSING_THRESHOLD - 1
    
    with patch('asyncio.create_task') as mock_create_task:
        await schedule_memory_graph_processing(account_id="test_account")
        
        mock_db_functions["count"].assert_called_once_with("test_account")
        mock_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_schedule_triggers_if_at_or_above_threshold(mock_db_functions):
    """
    Verifica que el procesamiento SÍ se dispara si el número de memorias
    es igual o mayor que el umbral.
    """
    mock_db_functions["count"].return_value = MEMORY_PROCESSING_THRESHOLD
    
    with patch('asyncio.create_task') as mock_create_task:
        await schedule_memory_graph_processing(account_id="test_account")
        
        mock_db_functions["count"].assert_called_once_with("test_account")
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_process_memory_batches_full_flow(mock_db_functions, mock_graph_integration):
    """
    Prueba el flujo completo del procesamiento de lotes:
    1. Obtiene memorias no procesadas.
    2. Llama al procesador de grafos con los datos correctos.
    3. Marca las memorias como procesadas.
    """
    account_id = "test_account_full_flow"
    mock_memories = [
        {"uuid": "uuid-1", "document": "memory content 1", "cmetadata": {"type": "user_memory", "created_at": "2023-01-01"}},
        {"uuid": "uuid-2", "document": "memory content 2", "cmetadata": {"type": "chat_summary", "created_at": "2023-01-02"}},
    ]
    mock_db_functions["get"].return_value = mock_memories

    await process_memory_batches(account_id=account_id)

    # 1. Verificar que se obtuvieron las memorias
    mock_db_functions["get"].assert_called_once_with(account_id, limit=100)

    # 2. Verificar que se llamó a process_documents del grafo
    mock_graph_integration.process_documents.assert_called_once()
    call_args = mock_graph_integration.process_documents.call_args
    assert call_args.kwargs['dataset_name'] == f"agent_memories_{account_id.replace('-', '_')}"
    assert call_args.kwargs['processing_mode'] == "hybrid"
    assert len(call_args.kwargs['documents']) == 2
    assert call_args.kwargs['documents'][0]['content'] == "memory content 1"

    # 3. Verificar que las memorias se marcaron como procesadas
    expected_ids_to_mark = ["uuid-1", "uuid-2"]
    mock_db_functions["mark"].assert_called_once()
    assert set(mock_db_functions["mark"].call_args[0][0]) == set(expected_ids_to_mark)

@pytest.mark.asyncio
async def test_process_memory_batches_does_nothing_if_no_memories(mock_db_functions, mock_graph_integration):
    """
    Verifica que no se hace nada si no hay memorias para procesar.
    """
    account_id = "test_account_no_memories"
    mock_db_functions["get"].return_value = []

    await process_memory_batches(account_id=account_id)

    mock_db_functions["get"].assert_called_once_with(account_id, limit=100)
    mock_graph_integration.process_documents.assert_not_called()
    mock_db_functions["mark"].assert_not_called()
