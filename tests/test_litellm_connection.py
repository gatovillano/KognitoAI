import asyncio
import os
import sys

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config import settings
from core.llm_manager import initialize_llms, get_main_llm, get_fast_llm
from langchain_core.messages import HumanMessage

async def test_litellm():
    print("--- Testing LiteLLM Integration ---")
    
    # Print configuration
    print(f"LLM Model: {settings.llm_model}")
    print(f"Fast LLM Model: {settings.fast_llm_model}")
    print(f"API Base: {settings.llm_api_base}")
    
    # Initialize LLMs
    print("\nInitializing LLMs...")
    try:
        await initialize_llms()
    except Exception as e:
        print(f"FAILED to initialize LLMs: {e}")
        return

    # Test Main LLM
    print("\nTesting Main LLM...")
    main_llm = get_main_llm()
    if main_llm:
        try:
            response = await main_llm.ainvoke([HumanMessage(content="Hello, are you working via LiteLLM?")])
            print(f"Main LLM Response: {response.content}")
        except Exception as e:
            print(f"Main LLM Failed: {e}")
    else:
        print("Main LLM is None")

    # Test Fast LLM
    print("\nTesting Fast LLM...")
    fast_llm = get_fast_llm()
    if fast_llm:
        try:
            response = await fast_llm.ainvoke([HumanMessage(content="Quick check: 2+2?")])
            print(f"Fast LLM Response: {response.content}")
        except Exception as e:
            print(f"Fast LLM Failed: {e}")
    else:
        print("Fast LLM is None")

if __name__ == "__main__":
    asyncio.run(test_litellm())
