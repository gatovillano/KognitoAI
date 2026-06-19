"""
cli/core/api_client.py
Cliente HTTP + WebSocket para comunicarse con el backend de KognitoAI.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx


class KognitoAPIClient:
    """Cliente para la API REST de KognitoAI con soporte SSE/streaming."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── Auth ─────────────────────────────────────────────────────────────────

    @classmethod
    async def login(cls, base_url: str, email: str, password: str) -> "KognitoAPIClient":
        """Autenticar y devolver cliente inicializado."""
        async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
            resp = await client.post(
                "/api/auth/login",
                json={"email": email, "password": password},
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("access_token")
            if not token:
                raise ValueError(f"Login fallido: {data}")
            return cls(base_url, token)

    async def get_me(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=15) as client:
            resp = await client.get("/api/users/me")
            resp.raise_for_status()
            return resp.json()

    # ── Threads ───────────────────────────────────────────────────────────────

    async def list_threads(
        self,
        skip: int = 0,
        limit: int = 20,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"skip": skip, "limit": limit}
        if workspace_id:
            params["workspace_id"] = workspace_id
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=15) as client:
            resp = await client.get("/api/threads", params=params)
            resp.raise_for_status()
            return resp.json()

    async def create_thread(self, title: str = "Nuevo Chat", workspace_id: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": title, "platform": "cli"}
        if workspace_id:
            payload["workspace_id"] = workspace_id
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=15) as client:
            resp = await client.post("/api/threads", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def delete_thread(self, thread_id: str) -> None:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=15) as client:
            resp = await client.delete(f"/api/threads/{thread_id}")
            resp.raise_for_status()

    async def get_thread_messages(
        self, thread_id: str, skip: int = 0, limit: int = 50
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=15) as client:
            resp = await client.get(
                f"/api/threads/{thread_id}/messages",
                params={"skip": skip, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    # ── Chat streaming ────────────────────────────────────────────────────────

    async def send_message_stream(
        self,
        thread_id: str,
        account_id: str,
        message: str,
        workspace_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Envía un mensaje e inicia la escucha de chunks vía WebSocket."""
        import websockets

        payload: Dict[str, Any] = {
            "thread_id": thread_id,
            "account_id": account_id,
            "user_message": message,
        }
        if workspace_id:
            payload["workspace_id"] = workspace_id

        # 1. Resolver URL de WebSocket
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://") + f"/ws/{account_id}?token={self.token}"

        # 2. Conectar al WebSocket
        async with websockets.connect(ws_url) as ws:
            # 3. Iniciar el procesamiento en background llamando a /api/chat
            async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30) as client:
                resp = await client.post("/api/chat", json=payload)
                resp.raise_for_status()

            # 4. Escuchar del WebSocket filtrando por thread_id
            async for raw_msg in ws:
                try:
                    data = json.loads(raw_msg)
                except Exception:
                    continue

                if data.get("thread_id") == thread_id:
                    msg_type = data.get("type")
                    if msg_type == "stream_chunk":
                        chunk = data.get("chunk") or data.get("token") or data.get("text") or ""
                        if chunk:
                            yield chunk
                    elif msg_type in ("stream_end", "error"):
                        break

    async def send_message(
        self,
        thread_id: str,
        account_id: str,
        message: str,
        workspace_id: Optional[str] = None,
    ) -> str:
        """Collect full streaming response into a single string."""
        parts: List[str] = []
        async for chunk in self.send_message_stream(thread_id, account_id, message, workspace_id):
            parts.append(chunk)
        return "".join(parts)

    # ── Workspaces ────────────────────────────────────────────────────────────

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=15) as client:
            resp = await client.get("/api/workspaces")
            resp.raise_for_status()
            return resp.json()

    # ── Documents ─────────────────────────────────────────────────────────────

    async def upload_document(self, file_path: str, topic: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Sube un documento al sistema RAG."""
        with open(file_path, "rb") as f:
            file_content = f.read()
        filename = os.path.basename(file_path)
        files = {"file": (filename, file_content, "application/octet-stream")}
        data: Dict[str, Any] = {"topic": topic}
        if workspace_id:
            data["workspace_id"] = workspace_id
        upload_headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(base_url=self.base_url, headers=upload_headers, timeout=60) as client:
            resp = await client.post("/api/documents/upload", files=files, data=data)
            resp.raise_for_status()
            return resp.json()
