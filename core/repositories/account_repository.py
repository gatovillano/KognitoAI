# core/repositories/account_repository.py

import uuid
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import Account, PlatformIdentity, Perfil
from utils.db_session import DBSession

class AccountRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_or_create_account_from_platform_id(
        self,
        platform: str,
        platform_user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> Tuple[Account, bool]:
        stmt = select(PlatformIdentity).where(
            PlatformIdentity.platform == platform,
            PlatformIdentity.platform_user_id == platform_user_id
        ).options(selectinload(PlatformIdentity.account).selectinload(Account.profile))
        
        result = await self.db_session.execute(stmt)
        identity = result.scalars().first()
        
        if identity and identity.account:
            if identity.account.name is None and first_name:
                identity.account.name = first_name
            if identity.account.username is None and username:
                identity.account.username = username
            if first_name or username:
                await self.db_session.commit()
            return (identity.account, False)

        new_account = Account(name=first_name, username=username)
        self.db_session.add(new_account)
        await self.db_session.flush()
        
        new_identity = PlatformIdentity(
            account_id=new_account.id,
            platform=platform,
            platform_user_id=platform_user_id
        )
        self.db_session.add(new_identity)
        
        new_profile = Perfil(account_id=new_account.id)
        self.db_session.add(new_profile)
        
        await self.db_session.commit()
        return (new_account, True)

    async def get_account_by_telegram_id(self, telegram_id: int) -> Optional[Account]:
        stmt = (
            select(Account)
            .join(PlatformIdentity)
            .where(
                PlatformIdentity.platform == 'telegram',
                PlatformIdentity.platform_user_id == str(telegram_id)
            )
        )
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def find_telegram_identity(self, identifier: str) -> Optional[PlatformIdentity]:
        """
        Busca una identidad de Telegram por alias (username) o por ID de plataforma.
        """
        # Intentar buscar por username en la tabla Account
        stmt = select(PlatformIdentity).join(Account).where(
            PlatformIdentity.platform == 'telegram',
            Account.username == identifier
        )
        result = await self.db_session.execute(stmt)
        identity = result.scalars().first()
        
        if not identity:
            # Si no se encuentra por username, intentar buscar por platform_user_id
            stmt = select(PlatformIdentity).where(
                PlatformIdentity.platform == 'telegram',
                PlatformIdentity.platform_user_id == identifier
            )
            result = await self.db_session.execute(stmt)
            identity = result.scalars().first()
            
        return identity