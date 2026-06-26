# telegram_gateway/api_client.py
"""
Cliente HTTP para comunicarse con el Core API.
Todas las llamadas a la lógica de negocio pasan por aquí, nunca por imports directos.
"""

import httpx
import logging
import hashlib
import hmac
import time
from typing import Optional, Dict, Any, Tuple

from telegram_gateway.config import config

logger = logging.getLogger(__name__)

# Timeout largo para el chat (el agente puede tardar)
_CHAT_TIMEOUT = httpx.Timeout(None)  # Sin límite
_DEFAULT_TIMEOUT = httpx.Timeout(15.0)


def _calculate_telegram_login_hash(user_id: int, first_name: str, last_name: Optional[str],
                                   username: Optional[str], auth_date: int, bot_token: str) -> str:
    """Calcula el hash HMAC para la autenticación de Telegram Login."""
    data_parts = [f"id={user_id}", f"first_name={first_name}"]
    if last_name:
        data_parts.append(f"last_name={last_name}")
    if username:
        data_parts.append(f"username={username}")
    data_parts.append(f"auth_date={auth_date}")
    data_check_string = "\n".join(sorted(data_parts))
    secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
    return hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()


async def get_or_create_account(platform_user_id: str, first_name: str,
                                last_name: Optional[str] = None,
                                username: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Obtiene o crea una cuenta via /api/auth/telegram/callback.
    Retorna dict con access_token y account_id (extraído del JWT), o None si falla.
    """
    auth_date = int(time.time())
    hash_val = _calculate_telegram_login_hash(
        user_id=int(platform_user_id),
        first_name=first_name,
        last_name=last_name,
        username=username,
        auth_date=auth_date,
        bot_token=config.telegram_bot_token
    )
    payload = {
        "id": int(platform_user_id),
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "auth_date": auth_date,
        "hash": hash_val
    }
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(f"{config.core_api_url}/api/auth/telegram/callback", json=payload)
            resp.raise_for_status()
            data = resp.json()  # {"access_token": "...", "token_type": "bearer"}

            access_token = data.get("access_token")
            if not access_token:
                logger.error("La respuesta de auth no contiene access_token")
                return None

            # El account_id está en el claim "sub" del JWT (no se verifica la firma,
            # solo se decodifica — la verificación ya la hizo el servidor).
            import base64 as _b64, json as _json
            try:
                payload_part = access_token.split(".")[1]
                # Añadir padding si falta
                payload_part += "=" * (-len(payload_part) % 4)
                decoded = _json.loads(_b64.urlsafe_b64decode(payload_part))
                account_id = decoded.get("sub")
            except Exception as decode_err:
                logger.error(f"No se pudo decodificar el JWT para obtener account_id: {decode_err}")
                account_id = None

            return {"access_token": access_token, "account_id": account_id}
    except Exception as e:
        logger.error(f"Error en get_or_create_account para {platform_user_id}: {e}", exc_info=True)
        return None


async def create_thread(account_id: str, chat_id: int, workspace_id: Optional[str] = None) -> Optional[str]:
    """
    Crea un nuevo hilo de conversación via /internal/bot-create-thread.
    Retorna el thread_id o None si falla.
    """
    headers = {"X-Internal-API-Key": config.internal_api_key_for_bot, "Content-Type": "application/json"}
    payload = {"account_id": account_id, "chat_id": chat_id}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(f"{config.core_api_url}/internal/bot-create-thread", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("id") or data.get("thread_id")
    except Exception as e:
        logger.error(f"Error en create_thread para account {account_id}: {e}", exc_info=True)
        return None


async def send_chat_message(jwt_token: str, account_id: str, thread_id: str,
                            user_message: str, image_base64: Optional[str] = None,
                            workspace_id: Optional[str] = None,
                            telegram_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Envía un mensaje al agente via POST /api/chat.
    Retorna el dict con taskId y thread_id, o None si falla.
    """
    payload: Dict[str, Any] = {
        "account_id": account_id,
        "user_message": user_message,
        "thread_id": thread_id,
    }
    if image_base64:
        payload["image_base64"] = image_base64
    if workspace_id:
        payload["workspace_id"] = workspace_id
    if telegram_id is not None:
        payload["telegram_id"] = telegram_id

    headers = {"Authorization": f"Bearer {jwt_token}"}
    try:
        async with httpx.AsyncClient(timeout=_CHAT_TIMEOUT) as client:
            resp = await client.post(f"{config.core_api_url}/api/chat", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Error en send_chat_message para thread {thread_id}: {e}", exc_info=True)
        return None


async def upload_document(jwt_token: str, file_name: str, file_bytes: bytes,
                          topic: str = "General") -> bool:
    """
    Sube un documento al core via POST /api/upload-document (multipart).
    Retorna True si se procesó correctamente.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            resp = await client.post(
                f"{config.core_api_url}/api/upload-document",
                headers=headers,
                files={"file": (file_name, file_bytes, "application/octet-stream")},
                data={"topic": topic}
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Error en upload_document '{file_name}': {e}", exc_info=True)
        return False


async def get_workspaces(jwt_token: str) -> list:
    """
    Obtiene la lista de workspaces del usuario via GET /api/workspaces.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(f"{config.core_api_url}/api/workspaces", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("workspaces", [])
            return data  # Fallback si por alguna razón ya es lista
    except Exception as e:
        logger.error(f"Error en get_workspaces: {e}", exc_info=True)
        return []


async def set_default_prompt(new_prompt: str) -> Tuple[bool, str]:
    """
    Actualiza el prompt del sistema via POST /api/admin/set-default-prompt.
    Retorna (success, message).
    """
    headers = {"X-Admin-Secret": config.admin_secret}
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{config.core_api_url}/api/admin/set-default-prompt",
                json={"default_prompt": new_prompt},
                headers=headers
            )
            resp.raise_for_status()
            msg = resp.json().get("message", "Prompt actualizado.")
            return True, msg
    except Exception as e:
        logger.error(f"Error en set_default_prompt: {e}", exc_info=True)
        return False, str(e)
