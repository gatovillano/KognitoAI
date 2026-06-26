# tests/test_knowledge_search_input_validation.py
import pytest
from skills.knowledge_and_memory_skill.scripts.knowledge_search_tool import KnowledgeSearchInput
from skills.knowledge_and_memory_skill.scripts.internal_knowledge_search_tool import InternalKnowledgeSearchInput

def test_knowledge_search_input_mapping():
    # Test that providing 'query' works normally
    inp1 = KnowledgeSearchInput(query="hello")
    assert inp1.query == "hello"

    # Test that providing 'question' gets mapped to 'query'
    inp2 = KnowledgeSearchInput(question="What are the risks?")
    assert inp2.query == "What are the risks?"

    # Test other aliases
    for alias in ["search", "text", "search_query", "content", "prompt", "input"]:
        kwargs = {alias: f"test {alias}"}
        inp = KnowledgeSearchInput(**kwargs)
        assert inp.query == f"test {alias}"

def test_internal_knowledge_search_input_mapping():
    # Test that providing 'query' works normally
    inp1 = InternalKnowledgeSearchInput(query="hello")
    assert inp1.query == "hello"

    # Test that providing 'question' gets mapped to 'query'
    inp2 = InternalKnowledgeSearchInput(question="What are the risks?")
    assert inp2.query == "What are the risks?"

    # Test other aliases
    for alias in ["search", "text", "search_query", "content", "prompt", "input"]:
        kwargs = {alias: f"test {alias}"}
        inp = InternalKnowledgeSearchInput(**kwargs)
        assert inp.query == f"test {alias}"
