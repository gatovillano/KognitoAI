import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_graph.neo4j_adapter import Neo4jAdapter
from knowledge_graph.graph_reasoning_node import GraphReasoningNode


def test_compute_trust_base():
    adapter = Neo4jAdapter(graph_db=MagicMock())
    
    # Base case
    score = adapter._compute_trust(confidence=0.8, source="general", method="hybrid")
    assert score == 0.8


def test_compute_trust_slm_penalty():
    adapter = Neo4jAdapter(graph_db=MagicMock())
    
    # Penalty for low confidence slm_extractor (0.5 * 0.7 = 0.35)
    score = adapter._compute_trust(confidence=0.5, source="general", method="slm_extractor")
    assert score == 0.35


def test_compute_trust_verified_document_bonus():
    adapter = Neo4jAdapter(graph_db=MagicMock())
    
    # Bonus for source_document (0.8 + 0.1 = 0.9)
    score = adapter._compute_trust(confidence=0.8, source="source_document", method="parser")
    assert score == 0.9


def test_add_entities_with_provenance_and_trust():
    mock_db = MagicMock()
    mock_db._driver = MagicMock()
    mock_db._driver.closed = False
    mock_db.execute_query = AsyncMock(return_value=[{"created": 1}])
    
    adapter = Neo4jAdapter(graph_db=mock_db)
    
    entities = [
        {
            "id": "e1",
            "name": "Concept A",
            "type": "Concept",
            "confidence": 0.8,
            "source_document": "doc1.pdf",
            "extraction_method": "slm_extractor"
        }
    ]
    
    added_count = asyncio.run(adapter._add_entities_to_neo4j(
        entities=entities,
        workspace_id="ws1",
        account_id="acc1"
    ))
    
    assert added_count == 1
    assert mock_db.execute_query.called
    
    # Verify execute_query was called with entities containing provenance and trust attributes
    call_args = mock_db.execute_query.call_args[0]
    query_str = call_args[0]
    params = call_args[1]
    
    assert "provenance_source" in query_str
    assert "trust_score" in query_str
    assert "extraction_model" in query_str
    assert params["entities"][0]["trust_score"] == 0.9  # 0.8 base + 0.1 doc bonus


@patch("knowledge_graph.graph_reasoning_node.get_fast_llm")
def test_graph_reasoning_node_min_trust_init(mock_get_fast_llm):
    mock_get_fast_llm.return_value = MagicMock()
    mock_db = MagicMock()
    node = GraphReasoningNode(graph_db=mock_db, min_trust=0.7)
    assert node.min_trust == 0.7
