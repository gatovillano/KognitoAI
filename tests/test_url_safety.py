import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from core.llm_manager import UnsafeLlmApiBaseError, _user_api_base
from utils.security import create_access_token
from utils.url_safety import SSRFValidationError, validate_llm_api_base


class TestValidateLlmApiBase:
    def test_allows_localhost_for_ollama(self):
        assert (
            validate_llm_api_base("http://127.0.0.1:11434", "ollama")
            == "http://127.0.0.1:11434"
        )

    def test_allows_private_network_for_openai_compatible(self):
        assert (
            validate_llm_api_base("http://192.168.1.50:8000/v1", "openai-compatible")
            == "http://192.168.1.50:8000/v1"
        )

    def test_blocks_private_network_for_openai(self):
        with pytest.raises(SSRFValidationError):
            validate_llm_api_base("http://10.0.0.5:11434", "openai")

    def test_blocks_link_local_metadata_for_ollama(self):
        with pytest.raises(SSRFValidationError):
            validate_llm_api_base("http://169.254.169.254/latest/meta-data/", "ollama")

    def test_blocks_metadata_hostname(self):
        with pytest.raises(SSRFValidationError):
            validate_llm_api_base("http://metadata.google.internal/", "openai")

    def test_blocks_non_http_scheme(self):
        with pytest.raises(SSRFValidationError):
            validate_llm_api_base("file:///etc/passwd", "ollama")

    def test_blocks_embedded_credentials(self):
        with pytest.raises(SSRFValidationError):
            validate_llm_api_base("http://user:pass@example.com", "openai")

    def test_blocks_internal_hostnames(self):
        with pytest.raises(SSRFValidationError):
            validate_llm_api_base("http://service.cluster.local", "openai")


@pytest.mark.asyncio
async def test_get_provider_models_rejects_ssrf_api_base_query_param():
    account_id = str(uuid.uuid4())
    token = create_access_token({"sub": account_id})
    headers = {"Authorization": f"Bearer {token}"}

    with patch("api.llm.get_user_api_key", new=AsyncMock(return_value="test-key")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/llm/models/openai",
                params={"api_base": "http://169.254.169.254/"},
                headers=headers,
            )

    assert response.status_code == 400
    assert "no permitida" in response.json()["detail"].lower() or "permitido" in response.json()["detail"].lower()


class TestLlmManagerApiBaseValidation:
    def test_user_api_base_rejects_metadata_for_openai(self):
        with pytest.raises(UnsafeLlmApiBaseError):
            _user_api_base("http://169.254.169.254/", "openai")

    def test_user_api_base_allows_local_ollama(self):
        assert _user_api_base("http://127.0.0.1:11434", "ollama") == "http://127.0.0.1:11434"
