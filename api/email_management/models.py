import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base

class UserEmailConfig(Base):
    __tablename__ = "user_email_configs"

    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    provider = Column(String(50), nullable=False, default="custom")
    imap_server = Column(String(255), nullable=True)
    imap_port = Column(Integer, nullable=True, default=993)
    imap_ssl = Column(Boolean, nullable=False, default=True)
    imap_user = Column(String(255), nullable=True)
    smtp_server = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True, default=465)
    smtp_ssl = Column(Boolean, nullable=False, default=True)
    smtp_user = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
