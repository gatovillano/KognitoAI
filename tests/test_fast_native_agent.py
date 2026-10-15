import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from core.agent import (
    get_langgraph_agent,
    get_native_agent,
    NativeAgentRunner,
    AgentState,
    _TOOL_SCHEMA_CACHE,
    sanitize_json_content,
    extract_text_content,
    is_multimodal_model,
)

@tool
def sample_calculator(a: int, b: int) -> int:
    """Suma dos enteros."""
    return a + b

@tool
def failing_tool(msg: str) -> str:
    """Herramienta que lanza error."""
    raise ValueError("Fallo simulado en la herramienta")


def test_singleton_and_helpers():
    agent1 = get_langgraph_agent()
    agent2 = get_native_agent()
    assert agent1 is agent2
    assert isinstance(agent1, NativeAgentRunner)

    assert is_multimodal_model("gpt-4o") is True
    assert is_multimodal_model("gemini-2.0-flash") is True
    assert is_multimodal_model("llama-3-8b") is False

    assert extract_text_content([{"type": "text", "text": "Hola"}, {"type": "text", "text": "Mundo"}]) == "Hola\nMundo"
    assert sanitize_json_content({"key": "val\x00\x01\x1f"}) == {"key": "val"}


@pytest.mark.asyncio
async def test_fast_tool_execution_flow():
    agent = NativeAgentRunner()

    # Pre-cargar schema cache para sample_calculator
    assert sample_calculator.name == "sample_calculator"

    # Mock LLM stream chunks:
    # 1. First iteration: model streams tool call to sample_calculator
    chunk_call = AIMessage(
        content="",
        tool_call_chunks=[
            {"name": "sample_calculator", "args": '{"a": 5', "id": "call_1", "index": 0},
            {"name": "sample_calculator", "args": ', "b": 10}', "id": "call_1", "index": 0},
        ],
    )
    # 2. Second iteration: model returns final synthesis
    chunk_final = AIMessage(content="El resultado es 15.")

    # Simular LLM con astream iterando
    class MockLLM:
        def __init__(self):
            self.turn = 0

        def bind(self, tools, **kwargs):
            return self

        async def astream(self, messages):
            if self.turn == 0:
                self.turn += 1
                yield chunk_call
            else:
                yield chunk_final

    mock_llm = MockLLM()

    with patch("core.agent.get_llm_for_user", new=AsyncMock(return_value=mock_llm)), \
         patch("core.agent.get_all_langchain_tools", new=AsyncMock(return_value=[sample_calculator, failing_tool])), \
         patch("core.agent.get_user_profile", new=AsyncMock(return_value=None)), \
         patch("core.agent.fetch_relevant_procedural_skills", new=AsyncMock(return_value=[])), \
         patch("core.agent.get_relevant_memories", new=AsyncMock(return_value=None)):

        state: AgentState = {
            "messages": [HumanMessage(content="¿Cuánto es 5 + 10?")],
            "account_id": "test-account",
            "thread_id": "thread-123",
            "task_id": "task-456",
        }

        chunks = []
        async for chunk in agent.astream(state):
            chunks.append(chunk)

        # Debe generar el resultado final compatible con api/chat.py
        assert len(chunks) == 1
        gen_resp = chunks[0]["generateResponse"]
        assert gen_resp["account_id"] == "test-account"
        assert gen_resp["thread_id"] == "thread-123"
        messages = gen_resp["messages"]
        
        # HumanMessage, AIMessage(tool_call), ToolMessage(res=15), AIMessage(final)
        assert len(messages) == 4
        assert isinstance(messages[1], AIMessage)
        assert messages[1].tool_calls[0]["name"] == "sample_calculator"
        assert isinstance(messages[2], ToolMessage)
        assert "15" in messages[2].content
        assert isinstance(messages[3], AIMessage)
        assert "El resultado es 15." in messages[3].content

        # Verificar que el schema fue cacheado
        assert "sample_calculator" in _TOOL_SCHEMA_CACHE


@pytest.mark.asyncio
async def test_failing_tool_graceful_recovery():
    agent = NativeAgentRunner()

    chunk_call = AIMessage(
        content="",
        tool_call_chunks=[
            {"name": "failing_tool", "args": '{"msg": "test"}', "id": "call_fail", "index": 0},
        ],
    )
    chunk_final = AIMessage(content="Detecté el error en la herramienta.")

    class MockLLM:
        def __init__(self):
            self.turn = 0

        def bind(self, tools, **kwargs):
            return self

        async def astream(self, messages):
            if self.turn == 0:
                self.turn += 1
                yield chunk_call
            else:
                yield chunk_final

    mock_llm = MockLLM()

    with patch("core.agent.get_llm_for_user", new=AsyncMock(return_value=mock_llm)), \
         patch("core.agent.get_all_langchain_tools", new=AsyncMock(return_value=[failing_tool])), \
         patch("core.agent.get_user_profile", new=AsyncMock(return_value=None)), \
         patch("core.agent.fetch_relevant_procedural_skills", new=AsyncMock(return_value=[])), \
         patch("core.agent.get_relevant_memories", new=AsyncMock(return_value=None)):

        state: AgentState = {
            "messages": [HumanMessage(content="Ejecuta falla")],
            "account_id": "test-account",
        }

        result = await agent.ainvoke(state)
        messages = result["generateResponse"]["messages"]
        assert len(messages) == 4
        # El ToolMessage debe contener el mensaje de error capturado sin lanzar excepción fatal
        tool_msg = messages[2]
        assert isinstance(tool_msg, ToolMessage)
        assert "Error ejecutando 'failing_tool'" in tool_msg.content


@pytest.mark.asyncio
async def test_sources_propagation_from_rag_and_tools():
    from core.citation_models import Source, ToolOutputWithSources

    agent = NativeAgentRunner()

    rag_source = Source(
        id=1,
        title="Documento Fundacional",
        url="doc-123",
        snippet="Snippet de RAG inicial",
        type="document",
    )
    mock_rag_output = ToolOutputWithSources(
        context_for_llm="Contexto [1] - Documento Fundacional:\nSnippet de RAG inicial\n",
        sources=[rag_source],
    )

    chunk_final = AIMessage(content="Respuesta basada en la fuente [1].")

    class MockLLM:
        def bind(self, tools, **kwargs):
            return self

        async def astream(self, messages):
            yield chunk_final

    mock_llm = MockLLM()

    with patch("core.agent.get_llm_for_user", new=AsyncMock(return_value=mock_llm)), \
         patch("core.agent.get_all_langchain_tools", new=AsyncMock(return_value=[])), \
         patch("core.agent.get_user_profile", new=AsyncMock(return_value=None)), \
         patch("core.agent.fetch_relevant_procedural_skills", new=AsyncMock(return_value=[])), \
         patch("core.agent.get_relevant_memories", new=AsyncMock(return_value=mock_rag_output)):

        state: AgentState = {
            "messages": [HumanMessage(content="Consulta con RAG")],
            "account_id": "test-account",
        }

        result = await agent.ainvoke(state)
        gen_resp = result["generateResponse"]
        
        # 1. generateResponse debe contener las fuentes
        assert len(gen_resp["sources"]) == 1
        assert gen_resp["sources"][0]["title"] == "Documento Fundacional"
        assert gen_resp["sources"][0]["id"] == 1

        # 2. El último AIMessage debe contener las fuentes en additional_kwargs para persistencia en BD
        messages = gen_resp["messages"]
        final_ai = messages[-1]
        assert isinstance(final_ai, AIMessage)
        assert "sources" in final_ai.additional_kwargs
        assert len(final_ai.additional_kwargs["sources"]) == 1
        assert final_ai.additional_kwargs["sources"][0]["id"] == 1

