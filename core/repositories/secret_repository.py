from sqlalchemy import select, update, delete, func, text, insert
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import UserSecret
from core.config import settings
import uuid
import logging

logger = logging.getLogger(__name__)

class SecretRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_secret(self, account_id: uuid.UUID, key_name: str, value: str, description: str = None) -> UserSecret:
        """
        Encrypts and stores a secret.
        Uses PGP Armor to store the encrypted binary data as text.
        """
        # Check if secret exists
        stmt = select(UserSecret).where(
            UserSecret.account_id == account_id,
            UserSecret.key_name == key_name
        )
        result = await self.session.execute(stmt)
        existing_secret = result.scalars().first()

        encryption_key = settings.db_encryption_key

        # Expression to encrypt: armor(pgp_sym_encrypt(value, key))
        encrypted_expr = func.armor(func.pgp_sym_encrypt(value, encryption_key))

        if existing_secret:
            stmt = update(UserSecret).where(
                UserSecret.id == existing_secret.id
            ).values(
                encrypted_value=encrypted_expr,
                description=description if description is not None else UserSecret.description,
                updated_at=func.now()
            )
            await self.session.execute(stmt)
            await self.session.commit()
            # Re-fetch to return
            return await self.get_secret_entry(account_id, key_name)
        else:
            stmt = insert(UserSecret).values(
                account_id=account_id,
                key_name=key_name,
                encrypted_value=encrypted_expr,
                description=description
            ).returning(UserSecret)
            
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.scalars().first()

    async def get_decrypted_secret(self, account_id: uuid.UUID, key_name: str) -> str | None:
        """
        Retrieves and decrypts a secret.
        """
        try:
            encryption_key = settings.db_encryption_key
            
            # Expression to decrypt: pgp_sym_decrypt(dearmor(encrypted_value), key)
            
            stmt = select(
                func.pgp_sym_decrypt(
                    func.dearmor(UserSecret.encrypted_value), 
                    encryption_key
                )
            ).where(
                UserSecret.account_id == account_id,
                UserSecret.key_name == key_name
            )
            
            result = await self.session.execute(stmt)
            return result.scalar()
        except Exception as e:
            logger.warning(
                f"No se pudo desencriptar el secreto '{key_name}' para el usuario {account_id}. "
                f"Esto puede deberse a que el secreto fue encriptado con una clave anterior o corrupta. Error: {e}"
            )
            try:
                await self.session.rollback()
            except Exception as rb_err:
                logger.error(f"Error al realizar rollback tras fallo de desencriptación: {rb_err}")
            return None

    async def get_secret_entry(self, account_id: uuid.UUID, key_name: str) -> UserSecret | None:
        stmt = select(UserSecret).where(
            UserSecret.account_id == account_id,
            UserSecret.key_name == key_name
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def delete_secret(self, account_id: uuid.UUID, key_name: str) -> bool:
        stmt = delete(UserSecret).where(
            UserSecret.account_id == account_id,
            UserSecret.key_name == key_name
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0