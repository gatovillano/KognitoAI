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
from typing import Any, Dict, Optional, Tuple
import pytz
from sqlalchemy.dialects.postgresql import JSONB, UUID

# --- Importaciones de SQLAlchemy ---
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, BigInteger, Integer, Boolean,
    UniqueConstraint, select, text, Float, Index
)
from sqlalchemy.orm import sessionmaker, relationship, selectinload
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# --- Importaciones de pgvector y del proyecto ---
from pgvector.sqlalchemy import Vector
from core.config import settings
from utils.db_session import DBSession

# --- Configuración del Logger e Instancias de SQLAlchemy ---
logger = logging.getLogger(__name__)

# Motor de base de datos asíncrono
database_url = settings.database_url
if database_url is None:
    raise ValueError("DATABASE_URL no está configurado en las settings.")
engine = create_async_engine(
    database_url,
    echo=False,  # Poner en True para depurar las queries SQL
    pool_pre_ping=True
)

# Fábrica de sesiones asíncronas
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,  # type: ignore
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
    hashed_password = Column(String(255), nullable=True)
    username = Column(String(255), unique=True, nullable=True, index=True) 
    timezone = Column(String(255), nullable=True, default="UTC", comment="Zona horaria preferida de la cuenta.")
    custom_system_prompt = Column(Text, nullable=True, comment="Prompt de sistema personalizado para la IA de esta cuenta.")
    is_admin = Column(Boolean, default=False, nullable=False, comment="Indica si esta cuenta tiene privilegios de administrador.")
    is_active = Column(Boolean, default=True, nullable=False, comment="Indica si esta cuenta está activa y puede usar el sistema.")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # --- Relaciones con otros modelos ---
    # Una cuenta puede tener múltiples identidades de plataforma.
    platform_identities = relationship("PlatformIdentity", back_populates="account", cascade="all, delete-orphan")
    
    # Cada cuenta tiene un único perfil.
    profile = relationship("Perfil", uselist=False, back_populates="account", cascade="all, delete-orphan")
    
    # Relaciones uno a muchos con los datos del usuario.
    workspaces = relationship("Workspace", back_populates="account", cascade="all, delete-orphan")
    # ELIMINADO: La tabla 'Memory' se eliminará, por lo que esta relación ya no es necesaria.
    # memories = relationship("Memory", back_populates="account", cascade="all, delete-orphan")
    notas = relationship("Nota", back_populates="account", cascade="all, delete-orphan")
    recordatorios = relationship("Recordatorio", back_populates="account", cascade="all, delete-orphan")
    agenda_events = relationship("AgendaEvent", back_populates="account", cascade="all, delete-orphan")
    chat_threads = relationship("ChatThread", back_populates="account", cascade="all, delete-orphan")
    proactive_insights = relationship(
        "ProactiveInsight",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    # AÑADIDO: Relación con la nueva tabla de temas/colecciones de documentos definidos por el usuario
    user_document_topics = relationship("UserDocumentTopic", back_populates="account", cascade="all, delete-orphan")

    # NUEVO: Relaciones con las tablas de análisis y tareas
    analysis_tasks = relationship("AnalysisTask", back_populates="account", cascade="all, delete-orphan")
    mindmap_tasks = relationship("MindmapTask", back_populates="account", cascade="all, delete-orphan")
    upload_tasks = relationship("UploadTask", back_populates="account", cascade="all, delete-orphan")

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


# --- Modelos de Identidad de Equipos ---
class Team(Base):
    """
    Representa un equipo en el sistema, permitiendo la memoria colectiva y la colaboración entre usuarios.
    """
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, comment="Nombre del equipo.")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    admin_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, comment="ID del administrador del equipo.")

    # Relaciones
    admin = relationship("Account", backref="administered_teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    notas = relationship("Nota", back_populates="team", cascade="all, delete-orphan")
    agenda_events = relationship("AgendaEvent", back_populates="team", cascade="all, delete-orphan")
    # ELIMINADO: La tabla 'Memory' se eliminará, por lo que esta relación ya no es necesaria.
    # memories = relationship("Memory", back_populates="team", cascade="all, delete-orphan")
    proactive_insights = relationship("ProactiveInsight", back_populates="team", cascade="all, delete-orphan")
    # AÑADIDO: Relación con la nueva tabla de temas/colecciones de documentos definidos por el equipo
    user_document_topics = relationship("UserDocumentTopic", back_populates="team", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"


class TeamMember(Base):
    """
    Tabla de relación que vincula a los usuarios (accounts) con los equipos (teams).
    """
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relaciones
    team = relationship("Team", back_populates="members")
    account = relationship("Account", backref="team_memberships")

    __table_args__ = (UniqueConstraint('team_id', 'account_id', name='_team_account_uc'),)

    def __repr__(self):
        return f"<TeamMember(team_id={self.team_id}, account_id={self.account_id})>"


class Workspace(Base):
    """
    Representa un espacio de trabajo para separar proyectos y lógicas.
    Cada espacio de trabajo puede tener su propio prompt de sistema.
    """
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    system_prompt = Column(Text, nullable=True, comment="Prompt de sistema específico para este espacio de trabajo.")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relaciones
    account = relationship("Account", back_populates="workspaces")
    chat_threads = relationship("ChatThread", back_populates="workspace", cascade="all, delete-orphan")
    # ELIMINADO: La relación 'collection_associations' ya no es necesaria.
    # collection_associations = relationship("WorkspaceCollectionAssociation", back_populates="workspace", cascade="all, delete-orphan")
    # AÑADIDO: Relación con la nueva tabla de temas/colecciones de documentos definidos para este workspace
    user_document_topics = relationship("UserDocumentTopic", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}')>"

class LangchainPgCollection(Base):
    """
    Mapea la tabla 'langchain_pg_collection' de LangChain para poder consultarla.
    Esta tabla almacena macrocolecciones que permiten mapear a que usuario pertenecen, que elementos de la tabla langchain_pg_embedding
    """
    __tablename__ = "langchain_pg_collection"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Cambiado 'id' a 'uuid'
    name = Column(String(255), unique=True, nullable=False)
    cmetadata = Column(JSONB, nullable=True) # Metadatos de la colección, si los hay
    
    # ELIMINADO: La relación 'workspace_associations' ya no es necesaria.
    # workspace_associations = relationship("WorkspaceCollectionAssociation", back_populates="langchain_collection", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LangchainPgCollection(uuid={self.uuid}, name='{self.name}')>"


class LangchainPgEmbedding(Base):
    """
    Mapea la tabla 'langchain_pg_embedding' de LangChain.
    Esta tabla almacena todos los embeddings vectoriales con columnas optimizadas para búsquedas directas.
    """
    __tablename__ = "langchain_pg_embedding"

    id = Column(String, primary_key=True)
    collection_id = Column(UUID(as_uuid=True), nullable=True)
    embedding = Column(Vector(), nullable=True) # El tamaño del vector se infiere o se especifica en la configuración
    document = Column(String, nullable=True)
    cmetadata = Column(JSONB, nullable=True)
    custom_id = Column(String, nullable=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=True)
    account_id = Column(UUID(as_uuid=True), nullable=True, index=True) # ⭐ COLUMNA DIRECTA
    content_type = Column(String(50), nullable=True) # ⭐ COLUMNA DIRECTA
    workspace_id = Column(UUID(as_uuid=True), nullable=True, index=True) # ⭐ COLUMNA DIRECTA
    topic = Column(String(100), nullable=True) # ⭐ COLUMNA DIRECTA
    category = Column(String(50), nullable=True) # ⭐ COLUMNA DIRECTA
    team_id = Column(UUID(as_uuid=True), nullable=True, index=True) # ⭐ COLUMNA DIRECTA
    visibility_teams = Column(JSONB, nullable=True) # ⭐ COLUMNA DIRECTA

    # Índices adicionales para las columnas directas
    __table_args__ = (
        Index('idx_langchain_pg_embedding_account_id', account_id),
        Index('idx_langchain_pg_embedding_workspace_id', workspace_id),
        Index('idx_langchain_pg_embedding_team_id', team_id),
        Index('ix_cmetadata_gin', cmetadata, postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<LangchainPgEmbedding(id={self.id}, account_id={self.account_id}, topic='{self.topic}')>"

# ELIMINADO: La clase 'WorkspaceCollectionAssociation' ya no es necesaria y se elimina por completo.
# class WorkspaceCollectionAssociation(Base):
#     """
#     Tabla de unión para asociar colecciones de LangChain (topics) con Workspaces.
#     Permite que una colección (topic) esté en múltiples workspaces.
#     """
#     __tablename__ = "workspace_collection_associations"
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete='CASCADE'), nullable=False, index=True)
#     langchain_collection_id = Column(UUID(as_uuid=True), ForeignKey("langchain_pg_collection.uuid", ondelete='CASCADE'), nullable=False, index=True)
#     created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
#     workspace = relationship("Workspace", back_populates="collection_associations")
#     langchain_collection = relationship("LangchainPgCollection", back_populates="workspace_associations")
#     __table_args__ = (UniqueConstraint('workspace_id', 'langchain_collection_id', name='_workspace_langchain_collection_uc'),)
#     def __repr__(self):
#         return f"<WorkspaceCollectionAssociation(workspace_id={self.workspace_id}, langchain_collection_id={self.langchain_collection_id})>"


# --- AÑADIDO: NUEVA TABLA para almacenar las colecciones/temas definidas por el usuario ---
class UserDocumentTopic(Base):
    """
    Representa una colección o tema de documentos definido por el usuario.
    Permite crear colecciones "vacías" antes de que se les asignen documentos.
    """
    __tablename__ = "user_document_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete='CASCADE'), nullable=True, index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete='CASCADE'), nullable=True, index=True) # Opcional: si las colecciones pueden ser de equipo

    name = Column(String(255), nullable=False, comment="El nombre del tema/colección (corresponde al 'topic' en cmetadata).")
    description = Column(Text, nullable=True, comment="Descripción opcional de la colección.")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relaciones
    account = relationship("Account", back_populates="user_document_topics")
    workspace = relationship("Workspace", back_populates="user_document_topics")
    team = relationship("Team", back_populates="user_document_topics") # Si se añade team_id

    # Restricciones para asegurar que un usuario/workspace/equipo no tenga dos colecciones con el mismo nombre
    __table_args__ = (
        Index('ix_account_workspace_topic', 'account_id', 'workspace_id', 'name', unique=True, postgresql_where=text("workspace_id IS NOT NULL")),
        Index('ix_account_team_topic', 'account_id', 'team_id', 'name', unique=True, postgresql_where=text("team_id IS NOT NULL")),
        Index('ix_account_personal_topic', 'account_id', 'name', unique=True, postgresql_where=text("workspace_id IS NULL AND team_id IS NULL")),
    )

    def __repr__(self):
        return f"<UserDocumentTopic(id={self.id}, name='{self.name}', account_id={self.account_id})>"


# --- ELIMINADO: La clase 'Memory' ya no es necesaria si todo va a langchain_pg_embedding ---
# class Memory(Base):
#     """Almacena memorias vectoriales para RAG."""
#     __tablename__ = "memories"
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
#     team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
#     content = Column(Text, nullable=False)
#     embedding = Column(Vector(384), nullable=False)
#     type = Column(String, default="general_memory")
#     created_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"))
#     account = relationship("Account", back_populates="memories")
#     team = relationship("Team", back_populates="memories")
#     def __repr__(self):
#         return f"<Memory(id={self.id}, type='{self.type}', content='{self.content[:50]}...')>"


# --- Modelos de Datos Refactorizados (ahora vinculados a Account y opcionalmente a Team) ---

class Perfil(Base):
    """Modelo para el perfil estructurado del usuario."""
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, unique=True)
    
    nombre = Column(String(255), nullable=True)
    gustos = Column(String, nullable=True)
    intereses = Column(String, nullable=True)
    otros_datos = Column(String, nullable=True)
    
    # CORREGIDO: Añadimos la columna 'system_prompt' que faltaba.
    system_prompt = Column(String, nullable=True)

    account = relationship("Account", back_populates="profile")


class Nota(Base):
    """Almacena las notas de un usuario o equipo."""
    __tablename__ = "notas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    category = Column(String, default="General")
    created_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    embedding = Column(Vector(384), nullable=True)

    account = relationship("Account", back_populates="notas")
    team = relationship("Team", back_populates="notas")

    def __repr__(self):
        return f"<Nota(id={self.id}, title='{self.title}', account_id={self.account_id})>"


class AgendaEvent(Base):
    """Modelo para los eventos de la agenda del usuario o equipo."""
    __tablename__ = "agenda_events"

    id = Column(Integer, primary_key=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    description = Column(String, nullable=False)
    event_datetime_utc = Column(DateTime(timezone=True), nullable=False)
    
    # CORREGIDO: Añadimos la columna 'is_active' que faltaba.
    is_active = Column(Boolean, default=True, nullable=False)
    
    job_name = Column(String, nullable=True, unique=True) # Para poder cancelar los jobs de Telegram

    account = relationship("Account", back_populates="agenda_events")
    team = relationship("Team", back_populates="agenda_events")

    def to_dict(self, timezone_str: str | None = "UTC") -> Dict[str, Any]:
        """Convierte el objeto a un diccionario para su uso en APIs."""
        user_tz = pytz.timezone(timezone_str) if timezone_str else pytz.utc
        local_datetime = self.event_datetime_utc.astimezone(user_tz)
        
        return {
            "id": self.id,
            "account_id": str(self.account_id),
            "team_id": str(self.team_id) if self.team_id else None, # type: ignore
            "description": self.description,
            "event_datetime_utc": self.event_datetime_utc.isoformat(),
            "event_datetime_local": local_datetime.isoformat(),
            "user_timezone": str(user_tz),
            "is_active": self.is_active
        }


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

class ChatThread(Base):
    __tablename__ = "chat_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True)

    title = Column(String, default="Nuevo Chat")
    platform = Column(String, default="web", nullable=False, comment="Plataforma de origen: 'web', 'telegram'")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    is_pinned = Column(Boolean, default=False, nullable=False)
    # Usamos JSONB para almacenar una lista flexible de etiquetas.
    tags = Column(JSONB, nullable=True)

    account = relationship("Account", back_populates="chat_threads")
    workspace = relationship("Workspace", back_populates="chat_threads")

class ProactiveInsight(Base):
    __tablename__ = "proactive_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    type = Column(String(50), nullable=False)
    insight_message = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    action_suggestion = Column(Text, nullable=True)
    related_items = Column(JSONB, nullable=True)  # Se almacena la lista de ítems como JSON (incluye tool_used en metadata)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    account = relationship("Account", back_populates="proactive_insights")
    team = relationship("Team", back_populates="proactive_insights")


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True)
    # Usamos el account_id para vincular el código a una cuenta
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    account = relationship("Account")


class AnalysisTask(Base):
    """Guarda el estado y resultado de las tareas de análisis de documentos."""
    __tablename__ = "analysis_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)

    file_name = Column(String, nullable=False) # Guardamos el nombre del archivo analizado
    analysis_type = Column(String, nullable=False, default="document", index=True) # NUEVO: Tipo de análisis (document, collection, semantic, code, etc.)
    status = Column(String, default="pending", index=True, nullable=False) # pending, processing, completed, failed

    result_payload = Column(JSONB, nullable=True) # Aquí guardamos el JSON completo del análisis (incluye tool_used en metadata)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relación con Account
    account = relationship("Account", back_populates="analysis_tasks")


class MindmapTask(Base):
    """Guarda el estado y resultado de las tareas de generación de mapas mentales."""
    __tablename__ = "mindmap_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)

    topic = Column(String, nullable=False) # Tema central del mapa mental
    ideas_input = Column(Text, nullable=True) # Ideas iniciales proporcionadas por el usuario
    document_name = Column(String, nullable=True) # Nombre del documento del cual extraer conceptos
    concept_query = Column(String, nullable=True) # Tipo de información a extraer del documento
    status = Column(String, default="pending", index=True, nullable=False) # pending, processing, completed, failed

    result_payload = Column(JSONB, nullable=True) # Aquí guardamos el resultado del mapa mental (incluye tool_used en metadata)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relación con Account
    account = relationship("Account", back_populates="mindmap_tasks")


class UploadTask(Base):
    """Guarda el estado y resultado de las tareas de subida de documentos."""
    __tablename__ = "upload_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)

    file_names = Column(JSONB, nullable=False)  # Lista de nombres de archivos
    topic = Column(String, nullable=False)  # Colección de destino
    workspace_id = Column(String, nullable=True)  # ID del workspace si aplica
    status = Column(String, default="pending", index=True, nullable=False)  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # Progreso en porcentaje (0-100)

    result_payload = Column(JSONB, nullable=True)  # Resultado de la subida
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relación con Account
    account = relationship("Account", back_populates="upload_tasks")


class GitHubDocument(Base):
    """
    Representa un documento individual de un repositorio de GitHub almacenado como conocimiento.
    Permite rastrear el path y el SHA para actualizaciones.
    """
    __tablename__ = "github_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_url = Column(String, nullable=False, index=True, comment="URL del repositorio de GitHub.")
    file_path = Column(String, nullable=False, comment="Ruta del archivo dentro del repositorio.")
    sha = Column(String, nullable=False, comment="SHA del contenido del archivo para detección de cambios.")
    content = Column(Text, nullable=False, comment="Contenido del archivo.")
    
    # Opcional: vincular a un workspace o a una cuenta general
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete='CASCADE'), nullable=True, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, index=True)
    topic = Column(String, nullable=True, comment="Tema o categoría asociada al documento para colecciones RAG.")
    
    # Columna de embedding para búsquedas semánticas o análisis
    embedding = Column(Vector(384), nullable=True, comment="Embedding vectorial del contenido del documento para búsquedas semánticas.")
    
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relaciones (opcionales, dependiendo de cómo se use)
    workspace = relationship("Workspace", backref="github_documents")
    account = relationship("Account", backref="github_documents")

    __table_args__ = (UniqueConstraint('repo_url', 'file_path', name='_github_repo_file_uc'),)

    def __repr__(self):
        return f"<GitHubDocument(repo_url='{self.repo_url}', file_path='{self.file_path}')>"


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
            
            # La lógica de añadir columnas personalizadas a langchain_pg_embedding ya no es necesaria aquí,
            # porque ahora se define como un modelo ORM completo y sus columnas e índices se crean
            # automáticamente con Base.metadata.create_all.
            # Se puede eliminar el bloque try-except anterior que manejaba esto.
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO al crear tablas de la base de datos: {e}", exc_info=True)
        raise

async def get_db_session():
    """
    Dependencia de FastAPI para obtener una sesión de base de datos asíncrona.
    """
    async with DBSession(SessionLocal) as session:
        yield session

async def get_or_create_account_from_platform_id(
    platform: str, 
    platform_user_id: str,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None
) -> Tuple[Account, bool] | None:
    async with DBSession(SessionLocal) as db:
        try:
            stmt = select(PlatformIdentity).where(
                PlatformIdentity.platform == platform,
                PlatformIdentity.platform_user_id == platform_user_id
            ).options(selectinload(PlatformIdentity.account).selectinload(Account.profile))
            
            result = await db.execute(stmt)
            identity = result.scalars().first()
            
            if identity is not None and identity.account is not None:
                # Si la cuenta existe pero no tiene nombre, la actualizamos.
                if identity.account.name is None and first_name:  # type: ignore
                    identity.account.name = first_name
                if identity.account.username is None and username:  # type: ignore
                    identity.account.username = username
                if first_name or username:
                    await db.commit()
                return (identity.account, False)

            # Si no existe, crear todo desde cero.
            logger.info(f"Creando nueva cuenta para {platform}:{platform_user_id}...")
            new_account = Account(
                name=first_name,
                username=username
            )
            db.add(new_account)
            await db.flush()
            
            new_identity = PlatformIdentity(
                account_id=new_account.id,
                platform=platform,
                platform_user_id=platform_user_id
            )
            db.add(new_identity)
            
            new_profile = Perfil(account_id=new_account.id)
            db.add(new_profile)
            
            await db.commit()
            
            logger.info(f"✅ Nueva cuenta e identidad creadas para {platform}:{platform_user_id}. Account ID: {new_account.id}")
            return (new_account, True)

        except Exception as e:
            logger.error(f"Error en get_or_create_account_from_platform_id para {platform}:{platform_user_id}: {e}", exc_info=True)
            await db.rollback()
            return None
        
# En core/database.py, al final del archivo

async def get_account_by_telegram_id(db_session, telegram_id: int) -> Optional[Account]:
    """
    Busca una cuenta de usuario universal utilizando su ID de plataforma de Telegram.
    Esta es una función de solo lectura; no crea una cuenta si no existe.
    """
    stmt = (
        select(Account)
        .join(PlatformIdentity)
        .where(
            PlatformIdentity.platform == 'telegram',
            PlatformIdentity.platform_user_id == str(telegram_id)
        )
    )
    result = await db_session.execute(stmt)
    return result.scalars().first()


from sqlalchemy import delete

async def delete_accounts_by_ids(db_session: AsyncSession, account_ids: list[uuid.UUID]) -> int:
    """
    Elimina cuentas de la base de datos por sus IDs.
    Retorna el número de filas eliminadas.
    """
    try:
        # Eliminar las identidades de plataforma asociadas primero
        # Aunque cascade="all, delete-orphan" debería manejar esto,
        # una eliminación explícita puede ser útil para claridad o si hay problemas de cascada.
        delete_platform_identities_stmt = (
            delete(PlatformIdentity)
            .where(PlatformIdentity.account_id.in_(account_ids))
        )
        await db_session.execute(delete_platform_identities_stmt)
        
        # Eliminar las cuentas
        delete_accounts_stmt = (
            delete(Account)
            .where(Account.id.in_(account_ids))
        )
        result = await db_session.execute(delete_accounts_stmt)
        
        await db_session.commit()
        logger.info(f"✅ Eliminadas {result.rowcount} cuentas con IDs: {account_ids}")
        return result.rowcount
    except Exception as e:
        logger.error(f"❌ Error al eliminar cuentas con IDs {account_ids}: {e}", exc_info=True)
        await db_session.rollback()
        raise


# Al final de core/database.py

async def find_telegram_identity(db_session, identifier: str) -> Optional[PlatformIdentity]:
    """
    Busca una identidad de Telegram por su ID numérico o su nombre de usuario.
    """
    # Intentar buscar por ID numérico primero
    if identifier.isdigit():
        stmt = select(PlatformIdentity).where(
            PlatformIdentity.platform == 'telegram',
            PlatformIdentity.platform_user_id == identifier
        )
    else:
        # Si no es un número, buscar por nombre de usuario (ignorando mayúsculas/minúsculas)
        # Necesitamos unir con la tabla Account para obtener el username.
        stmt = select(PlatformIdentity).join(Account).where(
            PlatformIdentity.platform == 'telegram',
            Account.username.ilike(identifier) # ilike es case-insensitive
        )
    
    result = await db_session.execute(stmt)
    return result.scalars().first()
