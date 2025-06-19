# telegram_bot/database.py

"""
Módulo de Base de Datos y Modelos ORM.

Este módulo define la estructura de la base de datos de la aplicación utilizando
SQLAlchemy. Es el núcleo de la persistencia de datos.

La arquitectura de la base de datos ha sido rediseñada para soportar una
identidad de usuario universal, desacoplada de cualquier plataforma específica.

Arquitectura de Identidad:
-   **Account:** La tabla central que representa a un usuario único en el sistema.
    Utiliza un UUID como clave primaria (`account_id`) para garantizar un
    identificador universal.
-   **PlatformIdentity:** Una tabla de enlace que conecta una `Account` con sus
    diferentes identidades en las plataformas (ej. un ID de Telegram, un número
    de WhatsApp, una sesión web).
-   **Modelos de Datos (Nota, Perfil, etc.):** Todas las tablas que almacenan
    datos del usuario (notas, perfil, eventos) ahora se relacionan directamente
    con la tabla `Account` a través del `account_id`.

Este diseño permite que un usuario sea reconocido y que sus datos sean accesibles
de manera consistente, sin importar si interactúa con el asistente a través de
Telegram, una aplicación web u otra futura integración.
"""

import logging
import asyncio
import uuid
from datetime import datetime
from typing import Optional

# --- Importaciones de SQLAlchemy ---
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, BigInteger, Integer, Boolean,
    UniqueConstraint, select, text
)
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# Importar el tipo UUID de la extensión de PostgreSQL
from sqlalchemy.dialects.postgresql import UUID

# --- Importaciones de pgvector y del proyecto ---
from pgvector.sqlalchemy import Vector
from telegram_bot.config import settings
from utils.db_session import DBSession

# --- Configuración del Logger e Instancias de SQLAlchemy ---
logger = logging.getLogger(__name__)

# Motor de base de datos asíncrono
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Poner en True para depurar las queries SQL
    pool_pre_ping=True
)

# Fábrica de sesiones asíncronas
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base declarativa para los modelos ORM
Base = declarative_base()


# ==============================================================================
# SECCIÓN 1: MODELOS DE DATOS (ORM)
# ==============================================================================

# --- Nuevos Modelos de Identidad Universal ---

class Account(Base):
    """
    Representa una cuenta de usuario universal en el sistema.
    Esta es la tabla principal a la que se vinculan todos los datos del usuario.
    """
    __tablename__ = "accounts"

    # Clave primaria universal, no depende de ninguna plataforma.
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(255), nullable=True, comment="Nombre principal de la cuenta, puede ser establecido por el usuario.")
    email = Column(String(255), unique=True, nullable=True, index=True, comment="Email opcional para inicio de sesión o notificaciones.")
    timezone = Column(String(255), nullable=True, default="UTC", comment="Zona horaria preferida de la cuenta.")
    custom_system_prompt = Column(Text, nullable=True, comment="Prompt de sistema personalizado para la IA de esta cuenta.")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Relaciones con otros modelos ---
    # Una cuenta puede tener múltiples identidades de plataforma.
    platform_identities = relationship("PlatformIdentity", back_populates="account", cascade="all, delete-orphan")
    
    # Cada cuenta tiene un único perfil.
    profile = relationship("Perfil", uselist=False, back_populates="account", cascade="all, delete-orphan")
    
    # Relaciones uno a muchos con los datos del usuario.
    memories = relationship("Memory", back_populates="account", cascade="all, delete-orphan")
    notas = relationship("Nota", back_populates="account", cascade="all, delete-orphan")
    recordatorios = relationship("Recordatorio", back_populates="account", cascade="all, delete-orphan")
    agenda_events = relationship("AgendaEvent", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}')>"


class PlatformIdentity(Base):
    """
    Representa la identidad de un usuario en una plataforma específica (Telegram, web, etc.)
    y la enlaza a una cuenta universal.
    """
    __tablename__ = "platform_identities"

    id = Column(Integer, primary_key=True)
    # Clave foránea que enlaza esta identidad a una cuenta universal.
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    platform = Column(String(50), nullable=False, comment="Nombre de la plataforma, ej: 'telegram', 'whatsapp', 'web'.")
    platform_user_id = Column(String(255), nullable=False, index=True, comment="ID del usuario en esa plataforma, ej: el ID numérico de Telegram.")
    
    # Relación inversa para navegar desde una identidad a su cuenta principal.
    account = relationship("Account", back_populates="platform_identities")

    # Restricción para asegurar que no se puede enlazar el mismo ID de plataforma dos veces.
    __table_args__ = (UniqueConstraint('platform', 'platform_user_id', name='_platform_user_id_uc'),)

    def __repr__(self):
        return f"<PlatformIdentity(platform='{self.platform}', platform_user_id='{self.platform_user_id}')>"


# --- Modelos de Datos Refactorizados (ahora vinculados a Account) ---

class Perfil(Base):
    """Almacena el perfil estructurado de un usuario."""
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, unique=True)
    
    nombre = Column(String(255), nullable=True)
    gustos = Column(Text, nullable=True)
    intereses = Column(Text, nullable=True)
    otros_datos = Column(Text, nullable=True)

    account = relationship("Account", back_populates="profile")


class Memory(Base):
    """Almacena memorias vectoriales para RAG."""
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, index=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True) # Ajustado a la dimensión de text-embedding-004 de Google
    type = Column(String(50), default="general_memory")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", back_populates="memories")


class Nota(Base):
    """Almacena las notas de un usuario."""
    __tablename__ = "notas"
    id = Column(Integer, primary_key=True, index=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("Account", back_populates="notas")


class AgendaEvent(Base):
    """Almacena los eventos de la agenda de un usuario."""
    __tablename__ = "agenda_events"
    id = Column(Integer, primary_key=True, index=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    description = Column(Text, nullable=False)
    event_datetime_utc = Column(DateTime(timezone=True), nullable=False)
    user_timezone = Column(String(255), nullable=False)
    reminder_sent = Column(Boolean, default=False)
    job_name = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", back_populates="agenda_events")


class Recordatorio(Base):
    """Almacena recordatorios simples."""
    __tablename__ = "recordatorios"
    id = Column(Integer, primary_key=True, index=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    text = Column(Text, nullable=False)
    due_datetime = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    job_name = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", back_populates="recordatorios")


# ==============================================================================
# SECCIÓN 2: FUNCIONES AUXILIARES DE LA BASE DE DATOS
# ==============================================================================

async def create_tables():
    """
    Crea la extensión pgvector y todas las tablas definidas en los modelos
    si no existen en la base de datos.
    """
    logger.info("Verificando y creando tablas de la base de datos asincrónicamente...")
    try:
        async with engine.begin() as conn:
            # Asegura que la extensión de pgvector esté habilitada
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("Extensión pgvector verificada/creada.")
            
            # Crea todas las tablas que heredan de Base
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tablas de la base de datos verificadas/creadas.")
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO al crear tablas de la base de datos: {e}", exc_info=True)
        raise


async def get_or_create_account_from_platform_id(
    platform: str,
    platform_user_id: str,
    platform_user_name: Optional[str] = None
) -> Optional[Account]:
    """
    Obtiene una cuenta universal a partir de un ID de plataforma, o la crea si no existe.

    Esta es la función de enlace clave entre una plataforma externa (como Telegram)
    y nuestro sistema de cuentas interno.

    Args:
        platform: El nombre de la plataforma (ej. "telegram").
        platform_user_id: El ID del usuario en esa plataforma.
        platform_user_name: El nombre del usuario en esa plataforma (para crear la cuenta).

    Returns:
        El objeto `Account` correspondiente, o `None` si ocurre un error.
    """
    async with DBSession(SessionLocal) as db:
        try:
            # 1. Buscar si ya existe una identidad para esta plataforma y ID
            stmt = select(PlatformIdentity).where(
                PlatformIdentity.platform == platform,
                PlatformIdentity.platform_user_id == str(platform_user_id)
            )
            result = await db.execute(stmt)
            identity = result.scalars().first()

            if identity:
                # Si la identidad existe, devolvemos la cuenta asociada
                logger.debug(f"Identidad de plataforma encontrada para {platform}:{platform_user_id}. Devolviendo cuenta existente.")
                return identity.account
            else:
                # 2. Si no existe, creamos una nueva cuenta y una nueva identidad
                logger.info(f"No se encontró identidad para {platform}:{platform_user_id}. Creando nueva cuenta...")
                
                # Crear la cuenta universal
                new_account = Account(name=platform_user_name)
                db.add(new_account)
                
                # Crear la identidad de la plataforma y vincularla a la nueva cuenta
                new_identity = PlatformIdentity(
                    platform=platform,
                    platform_user_id=str(platform_user_id),
                    account=new_account  # Vincula directamente el objeto
                )
                db.add(new_identity)

                # Crear un perfil vacío para la nueva cuenta
                new_profile = Perfil(account=new_account)
                db.add(new_profile)

                await db.commit()
                await db.refresh(new_account) # Refrescar para obtener el ID generado y otras relaciones
                
                logger.info(f"✅ Nueva cuenta e identidad creadas para {platform}:{platform_user_id}. Account ID: {new_account.id}")
                return new_account

        except Exception as e:
            logger.error(f"❌ Error al obtener o crear cuenta para {platform}:{platform_user_id}: {e}", exc_info=True)
            await db.rollback()
            return None