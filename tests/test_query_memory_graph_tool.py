# tests/test_query_memory_graph_tool.py

import pytest
from unittest.mock import AsyncMock, patch

from skills.knowledge_and_memory_skill.scripts.query_memory_graph_tool import QueryMemoryGraphTool

@pytest.fixture
def mock_graph_integration():
    """Fixture para mockear la integración con el grafo."""
    with patch('skills.knowledge_and_memory_skill.scripts.query_memory_graph_tool.GraphIntegration', autospec=True) as mock_graph:
        mock_instance = mock_graph.return_value
        mock_instance.search_knowledge_graph = AsyncMock()
        yield mock_instance

@pytest.mark.asyncio
async def test_query_memory_graph_tool_successful_call(mock_graph_integration):
    """
    Verifica que la herramienta construye el dataset_name correcto y llama
    a la búsqueda en el grafo.
    """
    # Arrange
    tool = QueryMemoryGraphTool(account_id="test_account_id")
    tool._graph_integration = mock_graph_integration # Inyectar el mock
    query = "Mis preferencias de café"
    
    mock_graph_integration.search_knowledge_graph.return_value = {
        "results": "Recuerdo que te gusta el café con leche por las mañanas."
    }

    # Act
    result = await tool._arun(query=query)

    # Assert
    # 1. Verificar que se llamó a la búsqueda del grafo con los parámetros correctos
    mock_graph_integration.search_knowledge_graph.assert_called_once()
    call_args = mock_graph_integration.search_knowledge_graph.call_args.kwargs
    assert call_args["query"] == query
    assert call_args["dataset_name"] == "agent_memories_test_account_id"
    assert call_args["return_type"] == "summary"

    # 2. Verificar que el resultado está formateado correctamente
    assert "Resultados de la consulta a mi grafo de memorias" in result
    assert "Recuerdo que te gusta el café con leche" in result

@pytest.mark.asyncio
async def test_query_memory_graph_tool_no_results(mock_graph_integration):
    """
    Verifica que la herramienta devuelve un mensaje amigable si no se encuentran
    resultados en el grafo.
    """
    # Arrange
    tool = QueryMemoryGraphTool(account_id="test_account_id")
    tool._graph_integration = mock_graph_integration
    query = "Inversiones en la bolsa"

    mock_graph_integration.search_knowledge_graph.return_value = {"results": None}

    # Act
    result = await tool._arun(query=query)

    # Assert
    mock_graph_integration.search_knowledge_graph.assert_called_once_with(
        query=query,
        dataset_name="agent_memories_test_account_id",
        return_type="summary"
    )
    assert "No encontré información relevante" in result

@pytest.mark.asyncio
async def test_query_memory_graph_tool_handles_exception(mock_graph_integration):
    """
    Verifica que la herramienta maneja excepciones de la integración del grafo.
    """
    # Arrange
    tool = QueryMemoryGraphTool(account_id="test_account_id")
    tool._graph_integration = mock_graph_integration
    query = "Algo que cause un error"

    mock_graph_integration.search_knowledge_graph.side_effect = Exception("Neo4j connection failed")

    # Act
    result = await tool._arun(query=query)

    # Assert
    assert "Ocurrió un error técnico" in result
    assert "Neo4j connection failed" in result
