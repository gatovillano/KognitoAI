import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_graph.neo4j_adapter import Neo4jAdapter
from knowledge_graph.embedded_slm_extractor import EmbeddedSLMExtractor
from knowledge_graph.knowledge_extraction_node import KnowledgeExtractionNode


def test_delete_entity_by_name():
    mock_db = MagicMock()
    mock_db.execute_query = AsyncMock(return_value=[{"deleted": 1}])
    
    adapter = Neo4jAdapter(graph_db=mock_db)
    
    deleted = asyncio.run(adapter.delete_entity_by_name("ObsoleteEntity", account_id="acc1"))
    assert deleted == 1
    assert mock_db.execute_query.called
    
    call_args = mock_db.execute_query.call_args[0]
    query_str = call_args[0]
    params = call_args[1]
    
    assert "DETACH DELETE n" in query_str
    assert params["name"] == "ObsoleteEntity"


def test_update_entity_by_name():
    mock_db = MagicMock()
    mock_db.execute_query = AsyncMock(return_value=[{"updated": 1}])
    
    adapter = Neo4jAdapter(graph_db=mock_db)
    
    success = asyncio.run(adapter.update_entity_by_name(
        name="ServerA",
        new_props={"status": "inactive"},
        account_id="acc1"
    ))
    assert success is True
    assert mock_db.execute_query.called
    
    call_args = mock_db.execute_query.call_args[0]
    query_str = call_args[0]
    params = call_args[1]
    
    assert "SET n += $new_props" in query_str
    assert params["name"] == "ServerA"
    assert params["new_props"] == {"status": "inactive"}


@patch("core.llm_manager.get_fast_llm")
def test_slm_reconcile_parsing(mock_get_fast_llm):
    mock_llm_resp = MagicMock()
    mock_llm_resp.content = '{"actions": [{"action": "DELETE", "target_name": "OldService", "reason": "deprecated"}]}'
    mock_fast_llm = MagicMock()
    mock_fast_llm.ainvoke = AsyncMock(return_value=mock_llm_resp)
    mock_get_fast_llm.return_value = mock_fast_llm

    extractor = EmbeddedSLMExtractor()
    extractor.fallback_mode = True

    res = asyncio.run(extractor.reconcile(
        new_msg="OldService ya no se utiliza en el workspace",
        existing_nodes=[{"name": "OldService", "type": "TOOL", "description": "Legacy service"}],
        workspace_name="test_ws"
    ))

    assert "actions" in res
    assert len(res["actions"]) == 1
    assert res["actions"][0]["action"] == "DELETE"
    assert res["actions"][0]["target_name"] == "OldService"


@patch("knowledge_graph.knowledge_extraction_node.get_fast_llm")
def test_knowledge_extraction_node_processes_actions(mock_get_fast_llm):
    mock_get_fast_llm.return_value = MagicMock()
    mock_db = MagicMock()
    
    node = KnowledgeExtractionNode(graph_db=mock_db)
    node.adapter.delete_entity_by_name = AsyncMock(return_value=1)
    node.adapter.update_entity_by_name = AsyncMock(return_value=True)
    node.adapter.add_cognee_results_to_graph = AsyncMock(return_value={})

    # Simular ejecución sobre un output con acciones DELETE / UPDATE
    parsed_output = {
        "actions": [
            {"action": "DELETE", "target_name": "LegacyTool"},
            {"action": "UPDATE", "target_name": "CurrentTool", "new_props": {"version": "v2"}}
        ],
        "entities": [],
        "relationships": [],
        "conceptual_insights": []
    }

    # Llamar formateo / guardado directo
    asyncio.run(node._persist_knowledge(parsed_output, {"account_id": "acc1", "workspace_id": "ws1"}))

    assert node.adapter.delete_entity_by_name.called
    assert node.adapter.update_entity_by_name.called
