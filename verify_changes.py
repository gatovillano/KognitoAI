
import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

async def verify_imports():
    print("Verifying imports...")
    try:
        print("Importing core.tools...")
        import core.tools
        print("✅ core.tools imported successfully")

        print("Importing core.agent...")
        import core.agent
        print("✅ core.agent imported successfully")

        print("Importing core.memory_manager...")
        import core.memory_manager
        print("✅ core.memory_manager imported successfully")

        print("Importing api.chat...")
        import api.chat
        print("✅ api.chat imported successfully")
        
        print("All modules imported successfully. Syntax check passed.")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify_imports())
