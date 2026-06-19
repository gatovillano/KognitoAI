import asyncio
from core.llm_manager import get_llm_for_user

async def main():
    user_id = "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6"
    print("=== Testing get_llm_for_user ===")
    
    # 1. Main LLM
    llm = await get_llm_for_user(user_id, purpose="main")
    if llm:
        print("\n[MAIN LLM]")
        print(f"Type: {type(llm)}")
        print(f"Model Name: {getattr(llm, 'model_name', None)}")
        print(f"Model: {getattr(llm, 'model', None)}")
        print(f"Custom LLM Provider: {getattr(llm, 'custom_llm_provider', None)}")
        print(f"API Base: {getattr(llm, 'api_base', None)}")
        
        # Check API key presence and length
        api_key = getattr(llm, 'api_key', None)
        if api_key:
            print(f"API Key present: length={len(api_key)}, first/last={api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
        else:
            print("API Key: None")
            
        # Check custom_llm_provider or provider logic
        print(f"Instance dict: {llm.__dict__}")

if __name__ == "__main__":
    asyncio.run(main())
