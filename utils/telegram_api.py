# utils/telegram_api.py
"""
Utility client to send requests to the Telegram gateway API.
Allows core tools to communicate with the running Telegram bot.
"""

import httpx
import logging
from typing import Any, Optional
from core.config import settings

logger = logging.getLogger(__name__)

async def store_telegram_user_data(telegram_id: int, key: str, data: Any) -> bool:
    """
    Sends data to the Telegram gateway to be stored in the user's context/session.
    """
    if not settings.telegram_bot_url:
        logger.warning("TELEGRAM_BOT_URL is not configured.")
        return False
        
    url = f"{settings.telegram_bot_url}/internal/store-user-data"
    payload = {
        "user_id": telegram_id,
        "key": key,
        "data": data
    }
    headers = {
        "X-Internal-API-Key": settings.internal_api_key_for_bot,
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully stored {key} for user {telegram_id} on Telegram gateway.")
            return True
    except Exception as e:
        logger.error(f"Error storing user data on Telegram gateway: {e}", exc_info=True)
        return False

async def send_telegram_message(telegram_id: int, text: str) -> bool:
    """
    Sends a message to a user via the Telegram gateway.
    """
    if not settings.telegram_bot_url:
        logger.warning("TELEGRAM_BOT_URL is not configured.")
        return False
        
    url = f"{settings.telegram_bot_url}/internal/send-message"
    payload = {
        "chat_id": telegram_id,
        "text": text
    }
    headers = {
        "X-Internal-API-Key": settings.internal_api_key_for_bot,
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent message to user {telegram_id} via Telegram gateway.")
            return True
    except Exception as e:
        logger.error(f"Error sending message via Telegram gateway: {e}", exc_info=True)
        return False
