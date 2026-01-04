
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from core.config import settings

print(f"API_SERVER_URL: {settings.api_server_url}")
print(f"TELEGRAM_BOT_TOKEN: {'*' * 5 if settings.telegram_bot_token else 'None'}")
