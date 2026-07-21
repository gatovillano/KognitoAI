import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from core.enhanced_memory_manager import EnhancedMemoryManager


@patch("core.embedding_manager.KognitoInternalEmbeddingService.aembed_query")
def test_add_episodic_memory(mock_aembed_query):
    mock_aembed_query.return_value = [0.1] * 768
    
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session_class = MagicMock()
    mock_session_class.return_value.__aenter__.return_value = mock_session
    
    user_id = str(uuid.uuid4())
    workspace_id = str(uuid.uuid4())
    
    with patch("core.database.SessionLocal", mock_session_class):
        emm = EnhancedMemoryManager()
        success = asyncio.run(emm.add_episodic_memory(
            event_text="El usuario prefiere respuestas concisas en español",
            user_id=user_id,
            workspace_id=workspace_id,
            episode_type="chat"
        ))
        
        assert success is True
        assert mock_session.add.called
        assert mock_session.commit.called


@patch("core.embedding_manager.KognitoInternalEmbeddingService.aembed_query")
def test_get_episodic_context(mock_aembed_query):
    mock_aembed_query.return_value = [0.1] * 768
    
    user_id = uuid.uuid4()
    rec1 = MagicMock()
    rec1.id = uuid.uuid4()
    rec1.event_text = "Recuerdo recencia alta"
    rec1.embedding = [0.1] * 768
    rec1.occurred_at = datetime.now() - timedelta(hours=2)
    rec1.episode_type = "chat"

    rec2 = MagicMock()
    rec2.id = uuid.uuid4()
    rec2.event_text = "Recuerdo antiguo"
    rec2.embedding = [0.1] * 768
    rec2.occurred_at = datetime.now() - timedelta(days=20)
    rec2.episode_type = "task"

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [rec1, rec2]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_res)

    mock_session_class = MagicMock()
    mock_session_class.return_value.__aenter__.return_value = mock_session

    with patch("core.database.SessionLocal", mock_session_class):
        emm = EnhancedMemoryManager()
        results = asyncio.run(emm.get_episodic_context(
            query="respuestas concisas",
            user_id=str(user_id),
            limit=2,
            recency_weight=0.3
        ))

        assert len(results) == 2
        # El recuerdo reciente debe obtener mayor puntaje debido al factor de recencia
        assert results[0]["event_text"] == "Recuerdo recencia alta"
        assert results[0]["score"] >= results[1]["score"]
