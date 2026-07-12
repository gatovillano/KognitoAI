# core/api_key_model.py

"""
Modelo para la gestión de API Keys públicas.

Este modelo permite a los usuarios crear API keys para usar la API de KAI
desde aplicaciones externas, con compatibilidad OpenAI.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Integer, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from core.database import Base

class ApiKey(Base):
    """
    Representa una API Key para acceso a la API pública de KAI.
    
    Las API Keys son compatibles con el formato de OpenAI, permitiendo
    usar el header Authorization: Bearer <api_key> o el header
    Authorization: Bearer sk-... (formato OpenAI).
    """
    __tablename__ = 'api_keys'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    hashed_key = Column(Text, nullable=False, unique=True)
    account_id = Column(PG_UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    description = Column(Text, nullable=True, comment='Descripción opcional de la API Key')
    is_active = Column(Boolean, default=True, nullable=False, comment='Si la key está activa')
    is_revoked = Column(Boolean, default=False, nullable=False, comment='Si la key fue revocada')
    rate_limit_per_minute = Column(Integer, default=60, comment='Límite de requests por minuto')
    rate_limit_per_hour = Column(Integer, default=1000, comment='Límite de requests por hora')
    created_at = Column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    expires_at = Column(DateTime(timezone=True), nullable=True, comment='Fecha de expiración opcional')
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment='Última vez que se usó')

    account = relationship('Account', back_populates='api_keys')

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name='{self.name}', account_id={self.account_id})>"
