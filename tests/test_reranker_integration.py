import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from core.reranker import Reranker, CloudReranker, LocalReranker, SYSTEM_ACCOUNT_ID
from core.database import Account

@pytest.mark.asyncio
async def test_reranker_uses_local_by_default():
    # Test that if no account or settings exist, it defaults to settings.reranker_provider
    reranker = Reranker()
    
    mock_local = MagicMock()
    mock_local.rerank = AsyncMock(return_value=["doc1", "doc2"])
    
    with patch.object(reranker, 'get_local_reranker', return_value=mock_local) as mock_get_local:
        docs = await reranker.rerank("query", ["doc1", "doc2"])
        assert docs == ["doc1", "doc2"]
        mock_get_local.assert_called_once()

@pytest.mark.asyncio
async def test_reranker_resolves_user_cloud_settings_and_api_key():
    reranker = Reranker()
    user_id = uuid.uuid4()
    
    mock_account = Account(
        id=user_id,
        reranker_provider="openrouter",
        reranker_model="nvidia/llama-nemotron-rerank-vl-1b-v2:free",
        reranker_api_base="https://openrouter.ai/api/v1"
    )
    
    # Mock database session to return the mock account
    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=mock_account)
    
    # Mock SecretRepository
    mock_secret_repo = MagicMock()
    mock_secret_repo.get_decrypted_secret = AsyncMock(return_value="fake-api-key")
    
    # Mock CloudReranker instance
    mock_cloud_reranker = MagicMock()
    mock_cloud_reranker.rerank = AsyncMock(return_value=["doc_reranked_1"])
    
    with patch("core.reranker.SessionLocal") as mock_session_local, \
         patch("core.reranker.SecretRepository", return_value=mock_secret_repo), \
         patch("core.reranker.CloudReranker", return_value=mock_cloud_reranker) as mock_cloud_class:
        
        # Setup context manager mock for DBSession
        mock_db_context = MagicMock()
        mock_db_context.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("core.reranker.DBSession", return_value=mock_db_context):
            result = await reranker.rerank(
                query="test query",
                documents=["doc1", "doc2"],
                account_id=str(user_id)
            )
            
            assert result == ["doc_reranked_1"]
            mock_cloud_class.assert_called_once_with(
                provider="openrouter",
                model="nvidia/llama-nemotron-rerank-vl-1b-v2:free",
                api_base="https://openrouter.ai/api/v1",
                api_key="fake-api-key"
            )

@pytest.mark.asyncio
async def test_reranker_falls_back_to_local_on_cloud_failure():
    reranker = Reranker()
    user_id = uuid.uuid4()
    
    mock_account = Account(
        id=user_id,
        reranker_provider="openrouter",
        reranker_model="nvidia/llama-nemotron-rerank-vl-1b-v2:free",
        reranker_api_base="https://openrouter.ai/api/v1"
    )
    
    # Mock database session to return the mock account
    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=mock_account)
    
    # Mock SecretRepository
    mock_secret_repo = MagicMock()
    mock_secret_repo.get_decrypted_secret = AsyncMock(return_value="fake-api-key")
    
    # Mock CloudReranker to raise exception
    mock_cloud_reranker = MagicMock()
    mock_cloud_reranker.rerank = AsyncMock(side_effect=Exception("API limit reached"))
    
    # Mock LocalReranker fallback
    mock_local_reranker = MagicMock()
    mock_local_reranker.rerank = AsyncMock(return_value=["doc_local_fallback"])
    
    with patch("core.reranker.SessionLocal") as mock_session_local, \
         patch("core.reranker.SecretRepository", return_value=mock_secret_repo), \
         patch("core.reranker.CloudReranker", return_value=mock_cloud_reranker), \
         patch.object(reranker, "get_local_reranker", return_value=mock_local_reranker) as mock_get_local:
        
        # Setup context manager mock for DBSession
        mock_db_context = MagicMock()
        mock_db_context.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("core.reranker.DBSession", return_value=mock_db_context):
            result = await reranker.rerank(
                query="test query",
                documents=["doc1", "doc2"],
                account_id=str(user_id)
            )
            
            # Should have returned from local reranker fallback
            assert result == ["doc_local_fallback"]
            mock_get_local.assert_called()
