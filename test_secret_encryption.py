import asyncio
import uuid
import logging
from sqlalchemy import select, text
from core.database import SessionLocal, UserSecret, Account
from core.repositories.secret_repository import SecretRepository
from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_encryption():
    logger.info("Starting encryption test...")
    
    async with SessionLocal() as session:
        # 1. Create a dummy account
        dummy_email = f"test_secret_{uuid.uuid4().hex[:8]}@example.com"
        account = Account(email=dummy_email, name="Test Secret User")
        session.add(account)
        await session.commit()
        await session.refresh(account)
        logger.info(f"Created dummy account: {account.id}")

        try:
            repo = SecretRepository(session)
            secret_key = "OPENAI_API_KEY"
            secret_value = "sk-test-1234567890abcdef"
            
            # 2. Store a secret
            logger.info(f"Storing secret '{secret_key}'...")
            stored_secret = await repo.set_secret(account.id, secret_key, secret_value, "Test API Key")
            logger.info(f"Secret stored with ID: {stored_secret.id}")

            # 3. Verify raw data in DB is encrypted (not plain text)
            stmt = select(UserSecret.encrypted_value).where(UserSecret.id == stored_secret.id)
            result = await session.execute(stmt)
            raw_value = result.scalar()
            
            logger.info(f"Raw encrypted value in DB: {raw_value[:50]}...")
            
            if secret_value in raw_value:
                logger.error("❌ FAILURE: Raw value contains plain text secret!")
            else:
                logger.info("✅ SUCCESS: Raw value does not contain plain text secret.")

            if "-----BEGIN PGP MESSAGE-----" in raw_value:
                 logger.info("✅ SUCCESS: Raw value appears to be PGP armored.")
            else:
                 logger.error("❌ FAILURE: Raw value does not appear to be PGP armored.")

            # 4. Retrieve and decrypt
            logger.info("Retrieving decrypted secret...")
            decrypted_value = await repo.get_decrypted_secret(account.id, secret_key)
            
            if decrypted_value == secret_value:
                logger.info(f"✅ SUCCESS: Decrypted value matches original: {decrypted_value}")
            else:
                logger.error(f"❌ FAILURE: Decrypted value '{decrypted_value}' does not match original '{secret_value}'")

            # 5. Update secret
            new_value = "sk-updated-987654321"
            logger.info("Updating secret...")
            await repo.set_secret(account.id, secret_key, new_value)
            
            updated_decrypted = await repo.get_decrypted_secret(account.id, secret_key)
            if updated_decrypted == new_value:
                logger.info(f"✅ SUCCESS: Updated value retrieved correctly: {updated_decrypted}")
            else:
                logger.error(f"❌ FAILURE: Updated value mismatch.")

            # 6. Delete secret
            logger.info("Deleting secret...")
            deleted = await repo.delete_secret(account.id, secret_key)
            if deleted:
                logger.info("✅ SUCCESS: Secret deleted.")
            else:
                logger.error("❌ FAILURE: Secret deletion failed.")
                
            # Verify deletion
            check_val = await repo.get_decrypted_secret(account.id, secret_key)
            if check_val is None:
                 logger.info("✅ SUCCESS: Secret no longer retrievable.")
            else:
                 logger.error("❌ FAILURE: Secret still exists.")

        except Exception as e:
            logger.error(f"❌ ERROR during test: {e}", exc_info=True)
        finally:
            # Cleanup
            logger.info("Cleaning up...")
            await session.delete(account)
            await session.commit()
            logger.info("Test account deleted.")

if __name__ == "__main__":
    asyncio.run(test_encryption())