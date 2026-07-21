import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_graph.neo4j_adapter import Neo4jAdapter
from knowledge_graph.graph_reasoning_node import GraphReasoningNode


def test_add_relationships_with_bitemporal_fields():
    mock_db = MagicMock()
    mock_db._driver = MagicMock()
    mock_db._driver.closed = False
    mock_db.execute_query = AsyncMock(return_value=[{"created": 1}])
    mock_db._relationship_exists_in_db = AsyncMock(return_value=False)
    
    adapter = Neo4jAdapter(graph_db=mock_db)
    adapter._relationship_exists_in_db = AsyncMock(return_value=False)
    
    relationships = [
        {
            "source_id": "n1",
            "target_id": "n2",
            "type": "WORKS_AT",
            "confidence": 0.9,
            "source_document": "doc1.pdf"
        }
    ]
    
    added_count = asyncio.run(adapter._add_relationships_to_neo4j(
        relationships=relationships,
        workspace_id="ws1",
        account_id="acc1"
    ))
    
    assert added_count == 1
    assert mock_db.execute_query.called
    
    call_args = mock_db.execute_query.call_args[0]
    query_str = call_args[0]
    params = call_args[1]
    
    assert "r.is_current = rel.is_current" in query_str
    assert "r.valid_from = rel.valid_from" in query_str
    assert "r.valid_to = rel.valid_to" in query_str
    assert params["relationships"][0]["is_current"] is True


def test_invalidate_relationship():
    mock_db = MagicMock()
    mock_db.execute_query = AsyncMock(return_value=[{"invalidated": 1}])
    
    adapter = Neo4jAdapter(graph_db=mock_db)
    
    invalidated = asyncio.run(adapter.invalidate_relationship("nodeA", "nodeB", "WORKS_AT", account_id="acc1"))
    assert invalidated == 1
    assert mock_db.execute_query.called
    
    call_args = mock_db.execute_query.call_args[0]
    query_str = call_args[0]
    params = call_args[1]
    
    assert "r.is_current = false" in query_str
    assert "r.valid_to =" in query_str
    assert params["source_id"] == "nodeA"
    assert params["target_id"] == "nodeB"


def test_update_temporal_fact():
    mock_db = MagicMock()
    mock_db._driver = MagicMock()
    mock_db._driver.closed = False
    mock_db.execute_query = AsyncMock(return_value=[{"invalidated": 1}, {"created": 1}])
    
    adapter = Neo4jAdapter(graph_db=mock_db)
    adapter._relationship_exists_in_db = AsyncMock(return_value=False)
    adapter.invalidate_relationship = AsyncMock(return_value=1)
    adapter._add_relationships_to_neo4j = AsyncMock(return_value=1)
    
    success = asyncio.run(adapter.update_temporal_fact(
        source_id="user1",
        target_id="companyB",
        rel_type="WORKS_AT",
        new_rel_data={"confidence": 0.95},
        account_id="acc1"
    ))
    
    assert success is True
    assert adapter.invalidate_relationship.called
    assert adapter._add_relationships_to_neo4j.called


@patch("knowledge_graph.graph_reasoning_node.get_fast_llm")
def test_graph_reasoning_node_cypher_includes_is_current(mock_get_fast_llm):
    mock_get_fast_llm.return_value = MagicMock()
    mock_db = MagicMock()
    mock_db.execute_query = AsyncMock(return_value=[])
    
    node = GraphReasoningNode(graph_db=mock_db)
    
    asyncio.run(node._perform_neural_thinking(
        user_query="¿Dónde trabaja el usuario?",
        account_id="acc1"
    ))
    
    assert mock_db.execute_query.called
    for call in mock_db.execute_query.call_args_list:
        query_str = call[0][0]
        assert "rel.is_current IS NULL OR rel.is_current = true" in query_str
