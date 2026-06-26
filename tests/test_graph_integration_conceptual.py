import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch


def _register_stub_module(name, **attrs):
    module = types.ModuleType(name)
    for attr_name, value in attrs.items():
        setattr(module, attr_name, value)
    sys.modules[name] = module
    return module


class _DummyHybridGraphProcessor:
    def __init__(self, llm=None, fast_llm=None):
        self.llm = llm
        self.fast_llm = fast_llm


class _DummyNeo4jAdapter:
    def __init__(self, graph_db):
        self.graph_db = graph_db

    async def add_cognee_results_to_graph(self, *args, **kwargs):
        return {}


_register_stub_module("core.config", settings=types.SimpleNamespace())
_register_stub_module("core.database", SessionLocal=object())
_register_stub_module("utils.db_session", DBSession=object())
_register_stub_module("knowledge_graph.graph_database", GraphDB=object)
_register_stub_module(
    "core.llm_manager",
    get_main_llm=lambda: None,
    get_fast_llm=lambda: None,
    get_llm_for_user=AsyncMock(return_value=object()),
)
_register_stub_module("utils.embeddings", get_embedding_model=lambda: None)
_register_stub_module(
    "core.memory_manager",
    get_full_document_content=AsyncMock(return_value=None),
)
_register_stub_module(
    "knowledge_graph.hybrid_graph_processor",
    HybridGraphProcessor=_DummyHybridGraphProcessor,
)
_register_stub_module(
    "knowledge_graph.neo4j_adapter",
    Neo4jAdapter=_DummyNeo4jAdapter,
)

from knowledge_graph.graph_integration import GraphIntegration


def test_conceptual_processing_persists_idea_profiles():
    graph_db = MagicMock()
    graph_integration = GraphIntegration(graph_db)
    graph_integration._ensure_llms = AsyncMock()
    graph_integration._create_fulltext_indexes = AsyncMock()
    graph_integration._reconstruct_document_content = AsyncMock(
        return_value=[
            {
                "content": "Documento reconstruido",
                "metadata": {"workspace_id": "ws-123"},
            }
        ]
    )
    graph_integration.hybrid_adapter.add_cognee_results_to_graph = AsyncMock(
        return_value={"entities_added": 3, "relationships_added": 2}
    )

    tracker = MagicMock()
    tracker.task_id = "task-123"

    conceptual_result = {
        "conceptual_nodes": [
            {
                "id": "quote-1",
                "text": "La plasticidad cerebral sostiene el aprendizaje.",
                "importance": "alta",
                "category": "neurociencia",
                "confidence": 0.95,
                "source_document": "doc-1",
                "extraction_method": "llm",
                "concept": "plasticidad cerebral",
            },
            {
                "id": "quote-2",
                "text": "Las sinapsis cambian con la experiencia.",
                "importance": "alta",
                "category": "neurociencia",
                "confidence": 0.92,
                "source_document": "doc-1",
                "extraction_method": "llm",
                "concept": "cambio sinaptico",
            },
        ],
        "thematic_relationships": [
            {
                "id": "rel-1",
                "source_id": "quote-1",
                "target_id": "quote-2",
                "type": "THEMATIC_RELATIONSHIP",
                "description": "Ambas ideas describen mecanismos de aprendizaje.",
                "confidence": 0.88,
                "extraction_method": "semantic_similarity",
            }
        ],
        "idea_profiles": [
            {
                "id": "profile-1",
                "central_concept": "Plasticidad cerebral y aprendizaje",
                "description": "Integra ideas sobre cambios neuronales asociados al aprendizaje.",
                "quote_ids": ["quote-1", "quote-2"],
                "quotes_count": 2,
                "categories": ["neurociencia"],
                "importance_score": 0.94,
                "coherence_score": 0.9,
                "documents_span": ["doc-1"],
            }
        ],
        "metadata": {"dataset_name": "dataset-prueba"},
    }

    conceptual_processor = MagicMock()
    conceptual_processor.process_documents_conceptually = AsyncMock(
        return_value=conceptual_result
    )

    with patch(
        "knowledge_graph.progress_tracker.create_progress_tracker",
        return_value=tracker,
    ), patch(
        "knowledge_graph.conceptual_graph_processor.ConceptualGraphProcessor",
        return_value=conceptual_processor,
    ):
        result = asyncio.run(
            graph_integration.process_documents(
                db_session=None,
                documents=[{"content": "doc"}],
                dataset_name="dataset-prueba",
                account_id="acc-123",
                processing_mode="conceptual",
                workspace_id="ws-123",
            )
        )

    add_call = graph_integration.hybrid_adapter.add_cognee_results_to_graph.call_args
    persisted_entities = add_call.args[0]
    persisted_relationships = add_call.args[1]

    assert any(
        entity["type"] == "IDEA_PROFILE"
        and entity["properties"]["cognee_id"] == "profile-1"
        for entity in persisted_entities
    )
    assert any(
        relationship["type"] == "CONTAINS_IDEA"
        and relationship["source_entity"] == "profile-1"
        and relationship["target_entity"] == "quote-1"
        for relationship in persisted_relationships
    )
    assert result["idea_profiles"] == 1
    assert result["neo4j_stats"] == {"entities_added": 3, "relationships_added": 2}
