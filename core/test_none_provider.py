import asyncio
from unittest.mock import MagicMock
from core.llm_manager import get_llm_for_user
from core.database import SessionLocal, Account
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        # Find user Gato
        result = await db.execute(select(Account).where(Account.name == "Gato"))
        gato = result.scalar_one()
        gato_id = str(gato.id)
        
        # Save original values
        orig_model = gato.llm_model
        orig_provider = gato.llm_provider
        
        try:
            # Set provider to None, model to gemini
            gato.llm_model = "gemini/gemini-1.5-flash"
            gato.llm_provider = None
            await db.commit()
            
            print("Running get_llm_for_user with provider=None and model=gemini/gemini-1.5-flash...")
            llm = await get_llm_for_user(gato_id, purpose="main")
            print(f"Success! Model: {getattr(llm, 'model_name', None)}")
        except Exception as e:
            print("ERROR CAUGHT:")
            import traceback
            traceback.print_exc()
        finally:
            # Restore original values
            gato.llm_model = orig_model
            gato.llm_provider = orig_provider
            await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
