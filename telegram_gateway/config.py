# telegram_gateway/config.py
"""
Configuración minimalista para el gateway de Telegram.
Solo lee las variables estrictamente necesarias, sin importar nada del core.
"""

import os
import logging
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class GatewayConfig:
    def __init__(self):
        # Telegram
        self.telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot_username: Optional[str] = os.getenv("BOT_USERNAME")
        self.webapp_url: Optional[str] = os.getenv("TELEGRAM_WEBAPP_URL")
        admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
        self.admin_telegram_ids: List[int] = [
            int(i.strip()) for i in admin_ids_str.split(',') if i.strip().isdigit()
        ]

        # Core API - URL base HTTP (ej: http://localhost:8000 o https://api.prod.com)
        self.core_api_url: str = os.getenv("CORE_API_URL", os.getenv("INTERNAL_API_SERVER_URL", "http://localhost:8889"))

        # Core WebSocket URL (ej: ws://localhost:8000 o ws://172.19.0.1:8000)
        _http = self.core_api_url
        _ws_default = _http.replace("https://", "wss://").replace("http://", "ws://")
        self.core_ws_url: str = os.getenv("CORE_WS_URL", _ws_default)

        # Seguridad
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "supersecretkey")
        self.jwt_expiry_days: int = int(os.getenv("JWT_EXPIRY_DAYS", 7))
        self.internal_api_key_for_bot: str = os.getenv("INTERNAL_API_KEY_FOR_BOT", "super-secret-internal-key")
        self.admin_secret: str = os.getenv("ADMIN_SECRET", "default-admin-secret")

        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

        # Validaciones críticas
        if not self.telegram_bot_token:
            logger.warning("⚠️ TELEGRAM_BOT_TOKEN no está configurado. El bot de Telegram no iniciará.")

config = GatewayConfig()
