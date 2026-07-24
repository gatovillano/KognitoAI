import httpx
from typing import Dict, Any

def get_google_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    return (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        "response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        "scope=https://mail.google.com/&"
        "access_type=offline&"
        "prompt=consent&"
        f"state={state}"
    )

async def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict[str, Any]:
    url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, data=data)
        if res.status_code != 200:
            raise ValueError(f"Failed to exchange code: {res.text}")
        return res.json()

async def refresh_google_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, data=data)
        if res.status_code != 200:
            raise ValueError(f"Failed to refresh token: {res.text}")
        return res.json().get("access_token")
