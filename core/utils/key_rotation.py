import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import UserSecret
from core.repositories.secret_repository import SecretRepository
import logging

logger = logging.getLogger(__name__)

class KeyRotationManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SecretRepository(session)

    async def check_expiring_keys(self, days_threshold: int = 30) -> list[UserSecret]:
        """
        Identifica las claves que no han sido actualizadas en 'days_threshold' días.
        """
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        
        stmt = select(UserSecret).where(
            UserSecret.updated_at < threshold_date
        )
        
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def rotate_key(self, account_id: uuid.UUID, key_name: str, new_value: str) -> bool:
        """
        Rota una clave específica: actualiza su valor y la fecha de actualización.
        """
        try:
            logger.info(f"Rotating key '{key_name}' for account {account_id}")
            await self.repo.set_secret(account_id, key_name, new_value, description="Rotated automatically")
            return True
        except Exception as e:
            logger.error(f"Error rotating key '{key_name}' for account {account_id}: {e}")
            return False

    async def notify_expiring_keys(self, expiring_keys: list[UserSecret]):
        """
        (Simulado) Notifica a los usuarios sobre claves próximas a expirar o que requieren rotación.
        En una implementación real, esto enviaría correos electrónicos o notificaciones push.
        """
        for secret in expiring_keys:
            logger.warning(f"⚠️ Key '{secret.key_name}' for account {secret.account_id} is old (last updated: {secret.updated_at}). Consider rotating it.")
            # Aquí iría la lógica de notificación real
            # await send_notification(secret.account_id, f"Tu clave {secret.key_name} necesita rotación.")
