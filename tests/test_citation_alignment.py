import hashlib
from typing import Dict, Any, List
from langchain_core.messages import ToolMessage, AIMessage
from core.citation_models import Source

# We duplicate the get_source_identifier logic here to test it under various conditions
def get_source_identifier(s: Dict[str, Any]) -> str:
    s_type = s.get('type', 'web')
    if hasattr(s_type, 'value'):
        s_type = s_type.value
    s_type = str(s_type)
    
    s_url = s.get('url') or s.get('id') or ''
    s_url = str(s_url)
    
    s_snippet = s.get('snippet', '')
    # Use MD5 hash of the snippet to allow multiple chunks from the same document
    snippet_hash = hashlib.md5(s_snippet.strip().encode()).hexdigest()[:8] if s_snippet.strip() else "empty"
    return f"{s_type}:{s_url}:{snippet_hash}"


def test_source_identifier_distinguishes_different_snippets():
    # Same URL, different snippets (like two chunks from the same RAG doc)
    s1 = {"type": "document", "url": "doc_123", "snippet": "First paragraph content.", "title": "Doc 123"}
    s2 = {"type": "document", "url": "doc_123", "snippet": "Second paragraph content.", "title": "Doc 123"}
    
    assert get_source_identifier(s1) != get_source_identifier(s2)


def test_source_identifier_deduplicates_identical_snippets():
    s1 = {"type": "document", "url": "doc_123", "snippet": "First paragraph content.", "title": "Doc 123"}
    s2 = {"type": "document", "url": "doc_123", "snippet": "First paragraph content.", "title": "Doc 123"}
    
    assert get_source_identifier(s1) == get_source_identifier(s2)


def test_citation_alignment_in_messages():
    # Simulate the consolidation and re-indexing logic of call_model_node
    # Let's say the state has accumulated these sources:
    state_sources = [
        {"type": "document", "url": "doc_1", "snippet": "Snippet A", "id": 1, "title": "Doc 1"},
        {"type": "web", "url": "http://example.com", "snippet": "Snippet B", "id": 2, "title": "Web 2"},
        {"type": "document", "url": "doc_1", "snippet": "Snippet C", "id": 1, "title": "Doc 1"}, # another chunk from doc_1
    ]
    
    # We create raw_sources by deduplicating them
    raw_sources = []
    seen_source_identifiers = set()
    for s in state_sources:
        ident = get_source_identifier(s)
        if ident not in seen_source_identifiers:
            raw_sources.append(s)
            seen_source_identifiers.add(ident)
            
    # At this point, we should have 3 unique raw sources (Snippet A, B, and C)
    assert len(raw_sources) == 3
    
    # Let's perform sequential re-indexing (1 to N)
    all_sources_for_llm: List[Source] = []
    final_sources_for_state = []
    for i, s_dict in enumerate(raw_sources, start=1):
        s_dict_copy = s_dict.copy()
        s_dict_copy['id'] = i
        source_obj = Source(**s_dict_copy)
        all_sources_for_llm.append(source_obj)
        final_sources_for_state.append(s_dict_copy)
        
    assert all_sources_for_llm[0].id == 1
    assert all_sources_for_llm[1].id == 2
    assert all_sources_for_llm[2].id == 3
    
    # Now build a search map by identifier
    consolidated_source_by_ident = {}
    for source_obj in all_sources_for_llm:
        s_dict = source_obj.dict() if hasattr(source_obj, 'dict') else source_obj.model_dump()
        ident = get_source_identifier(s_dict)
        consolidated_source_by_ident[ident] = source_obj
        
    # Simulate a ToolMessage from a tool that returned "Snippet C" with a local ID of 1
    # inside its text content "Contexto [1]" and as metadata
    tool_sources_meta = [
        {"type": "document", "url": "doc_1", "snippet": "Snippet C", "id": 1, "title": "Doc 1"}
    ]
    
    tool_msg = ToolMessage(
        content="This is the search result: Contexto [1] details the second chunk.",
        tool_call_id="call_abc",
        additional_kwargs={"sources": tool_sources_meta}
    )
    
    # Update ToolMessage to use consolidated IDs (as in call_model_node)
    tool_sources = tool_msg.additional_kwargs.get("sources")
    if tool_sources and isinstance(tool_sources, list):
        updated_tool_sources = []
        id_replacement_map = {}
        
        for ts in tool_sources:
            ts_dict = ts.dict() if hasattr(ts, 'dict') else (ts.model_dump() if hasattr(ts, 'model_dump') else ts)
            ident = get_source_identifier(ts_dict)
            local_id = ts_dict.get('id')
            
            if ident in consolidated_source_by_ident:
                new_source_obj = consolidated_source_by_ident[ident]
                updated_tool_sources.append(new_source_obj)
                if local_id is not None:
                    id_replacement_map[local_id] = new_source_obj.id
            else:
                try:
                    updated_tool_sources.append(Source(**ts_dict))
                except Exception:
                    updated_tool_sources.append(ts)
                    
        # Update additional_kwargs['sources']
        tool_msg.additional_kwargs["sources"] = [
            s.dict() if hasattr(s, 'dict') else s.model_dump()
            for s in updated_tool_sources
        ]
        
        # Rewrite ToolMessage content with updated citation IDs
        content_str = tool_msg.content
        if isinstance(content_str, str) and id_replacement_map:
            sorted_old_ids = sorted(id_replacement_map.keys(), key=lambda x: int(x) if str(x).isdigit() else 0, reverse=True)
            for old_id in sorted_old_ids:
                new_id = id_replacement_map[old_id]
                content_str = content_str.replace(f"[{old_id}]", f"[{new_id}]")
                content_str = content_str.replace(f"Contexto [{old_id}]", f"Contexto [{new_id}]")
            tool_msg.content = content_str
            
    # Verify that:
    # 1. The source ID in the metadata has been updated to 3 (since Snippet C is the third consolidated source)
    assert tool_msg.additional_kwargs["sources"][0]["id"] == 3
    # 2. The text content has been rewritten to "Contexto [3]" instead of "Contexto [1]"
    assert "Contexto [3]" in tool_msg.content
    assert "Contexto [1]" not in tool_msg.content
