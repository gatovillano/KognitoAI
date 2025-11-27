import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy.orm import configure_mappers
from core.database import Base

try:
    print("Configuring mappers...")
    configure_mappers()
    print("Mappers configured successfully!")
except Exception as e:
    print(f"Error configuring mappers: {e}")
    sys.exit(1)
