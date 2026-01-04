
import os
import sys
import asyncio
from core.config import settings
from core.llm_manager import initialize_llms, get_main_llm
from langchain_core.messages import HumanMessage

# Mock settings if needed, but we rely on loaded env
# settings.llm_model = "openrouter/mistralai/devstral-2512:free"

async def test_llm():
    print("Initializing LLMs...")
    await initialize_llms()
    
    llm = get_main_llm()
    if not llm:
        print("Failed to initialize LLM")
        return

    print(f"LLM Config: {llm.model_name}, Provider: {llm.model_kwargs.get('provider')}")
    print(f"Extra Headers: {llm.model_kwargs.get('extra_headers')}")
    
    try:
        print("Invoking LLM...")
        response = await llm.ainvoke([HumanMessage(content="Hello, are you working?")])
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error invoking LLM: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
