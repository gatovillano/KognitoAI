# core/utils/date_utils.py

from datetime import datetime

def get_today_str() -> str:
    """Returns the current date as a string in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")