import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from api.main import app
from utils.security import create_access_token
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_delete_user_secret_with_slashes_in_key_name():
    """Verifica que /api/users/me/secrets/{key_name:path} permita eliminar secretos cuyos nombres contienen '/'.
    Prevé la falla de 404 (Route Not Found) al usar slashes en el key_name.
    """
    account_id = str(uuid.uuid4())
    token = create_access_token({"sub": account_id})
    headers = {"Authorization": f"Bearer {token}"}
    
    key_name_with_slashes = "FEDIVERSO_5b8d59b0-69b7-4aa8-9bb0-bf07511222a6_https://hidden.pics_CLIENT_SECRET"
    
    with patch("api.users.SecretRepository") as mock_repo_class:
        mock_repo_instance = AsyncMock()
        mock_repo_instance.delete_secret.return_value = True
        mock_repo_class.return_value = mock_repo_instance
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/api/users/me/secrets/{key_name_with_slashes}",
                headers=headers
            )
            
            assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
            data = response.json()
            assert "eliminado correctamente" in data["message"]
            mock_repo_instance.delete_secret.assert_called_once_with(uuid.UUID(account_id), key_name_with_slashes)
