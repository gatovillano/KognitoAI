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
import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, List, AsyncIterator
import pytz
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY, TSVECTOR

# --- Importaciones de SQLAlchemy ---
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, BigInteger, Integer, Boolean,
    UniqueConstraint, select, text, Float, Index, Table
)
from sqlalchemy.orm import sessionmaker, relationship, selectinload
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
try:
    from sqlalchemy import inspect
except ImportError:
    from sqlalchemy.inspection import inspect # Para compatibilidad con versiones anteriores

# --- Importaciones de pgvector y del proyecto ---
from pgvector.sqlalchemy import Vector
from core.config import settings
from utils.db_session import DBSession

import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# ... (other imports)

# --- Configuración del Logger e Instancias de SQLAlchemy ---
logger = logging.getLogger(__name__)

# Motor de base de datos asíncrono
database_url = settings.database_url
if database_url is None:
    raise ValueError("DATABASE_URL no está configurado en las settings.")
engine = create_async_engine(
    database_url,
    echo=False,  # Poner en True para depurar las queries SQL
    pool_pre_ping=True,
    pool_recycle=3600,  # Recicla conexiones cada hora
    pool_size=10,       # Aumentar el número de conexiones persistentes
    max_overflow=20,    # Aumentar el número de conexiones adicionales
    pool_timeout=60,    # Aumentar el tiempo de espera para adquirir una conexión
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
    json_deserializer=json.loads
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


# Tabla de asociación para la relación muchos a muchos entre AgendaEvent y Account (para asistentes)
agenda_event_attendees_association = Table(
    "agenda_event_attendees_association",
    Base.metadata,
    Column("agenda_event_id", Integer, ForeignKey("agenda_events.id"), primary_key=True),
    Column("account_id", UUID(as_uuid=True), ForeignKey("accounts.id"), primary_key=True)
)


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
    custom_system_prompt = Column(Text, nullable=True, comment="Prompt de sistema específico para la IA de esta cuenta.")
    is_admin = Column(Boolean, default=False, nullable=False, comment="Indica si esta cuenta tiene privilegios de administrador.")
    is_active = Column(Boolean, default=True, nullable=False, comment="Indica si esta cuenta está activa y puede usar el sistema.")
    
    # Nuevos campos para configuración de usuario
    phone = Column(String(255), nullable=True, comment="Número de teléfono del usuario.")
    bio = Column(Text, nullable=True, comment="Biografía o descripción personal del usuario.")
    
    # Toggles para módulos
    profiles_enabled = Column(Boolean, default=False, nullable=False, comment="Indica si el módulo de perfiles está habilitado para la cuenta.")
    galleries_enabled = Column(Boolean, default=False, nullable=False, comment="Indica si el módulo de galerías está habilitado para la cuenta.")
    forms_enabled = Column(Boolean, default=False, nullable=False, comment="Indica si el módulo de formularios está habilitado para la cuenta.")

    # Configuraciones adicionales
    theme = Column(String(50), nullable=False, default="system", comment="Tema de la interfaz de usuario (e.g., 'light', 'dark', 'system').")
    notifications_email = Column(Boolean, default=True, nullable=False, comment="Indica si las notificaciones por correo electrónico están habilitadas.")
    notifications_push = Column(Boolean, default=True, nullable=False, comment="Indica si las notificaciones push están habilitadas.")
    language = Column(String(10), nullable=False, default="en", comment="Idioma preferido de la interfaz de usuario (e.g., 'en', 'es').")
    privacy_data_sharing = Column(Boolean, default=False, nullable=False, comment="Indica si el usuario permite compartir datos para mejoras del servicio.")

    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # --- Relaciones con otros modelos ---
    # Una cuenta puede tener múltiples identidades de plataforma.
    platform_identities = relationship("PlatformIdentity", back_populates="account", cascade="all, delete-orphan")
    
    # Cada cuenta tiene un único perfil.
    profile = relationship("Perfil", uselist=False, back_populates="account", cascade="all, delete-orphan")
    
    # Relación con perfiles de contacto
    contact_profiles = relationship("ContactProfile", back_populates="account", cascade="all, delete-orphan")
    
    # Relaciones uno a muchos con los datos del usuario.
    workspaces = relationship("Workspace", back_populates="account", cascade="all, delete-orphan")
    # ELIMINADO: La tabla 'Memory' se eliminará, por lo que esta relación ya no es necesaria.
    # memories = relationship("Memory", back_populates="account", cascade="all, delete-orphan")
    notas = relationship("Nota", back_populates="account", cascade="all, delete-orphan")
    recordatorios = relationship("Recordatorio", back_populates="account", cascade="all, delete-orphan")
    agenda_events = relationship("AgendaEvent", back_populates="account", cascade="all, delete-orphan")
    agenda_events_attended = relationship( # Nueva relación para eventos a los que asiste
        "AgendaEvent",
        secondary=agenda_event_attendees_association,
        back_populates="attendees"
    )
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
    tasks = relationship("Task", back_populates="account", cascade="all, delete-orphan")
    forms = relationship("Form", back_populates="account", cascade="all, delete-orphan")
    workspace_permissions = relationship("WorkspacePermission", back_populates="account", cascade="all, delete-orphan") # NUEVA RELACIÓN
    gap_development_analysis = relationship("GapDevelopmentAnalysis", back_populates="account", cascade="all, delete-orphan")

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


# --- Modelo de Espacio de Trabajo ---
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
    color = Column(String(7), nullable=True, default="#007bff", comment="Color asociado al workspace (ej. #RRGGBB).") # NEW COLUMN
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relaciones
    account = relationship("Account", back_populates="workspaces")
    chat_threads = relationship("ChatThread", back_populates="workspace", cascade="all, delete-orphan")
    # ELIMINADO: La relación 'collection_associations' ya no es necesaria.
    # collection_associations = relationship("WorkspaceCollectionAssociation", back_populates="workspace", cascade="all, delete-orphan")
    # AÑADIDO: Relación con la nueva tabla de temas/colecciones de documentos definidos para este workspace
    user_document_topics = relationship("UserDocumentTopic", back_populates="workspace", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="workspace", cascade="all, delete-orphan")
    agenda_events = relationship("AgendaEvent", back_populates="workspace", cascade="all, delete-orphan")
    permissions = relationship("WorkspacePermission", back_populates="workspace", cascade="all, delete-orphan") # NUEVA RELACIÓN

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}')>"


class WorkspacePermission(Base):
    """
    Gestiona los permisos de acceso de los usuarios a los workspaces.
    """
    __tablename__ = "workspace_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete='CASCADE'), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(50), nullable=False, comment="Nivel de permiso (owner, editor, viewer).")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relaciones
    workspace = relationship("Workspace", back_populates="permissions")
    account = relationship("Account", back_populates="workspace_permissions")

    __table_args__ = (
        UniqueConstraint('workspace_id', 'account_id', name='_workspace_account_permission_uc'),
        Index('ix_workspace_permission_workspace_id', workspace_id),
        Index('ix_workspace_permission_account_id', account_id),
    )

    def __repr__(self):
        return f"<WorkspacePermission(id={self.id}, workspace_id={self.workspace_id}, account_id={self.account_id}, role='{self.role}')>"


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
    telegram_id = Column(BigInteger, nullable=True, index=True) # ⭐ COLUMNA DIRECTA
    thread_id = Column(UUID(as_uuid=True), nullable=True, index=True) # ⭐ COLUMNA DIRECTA
    text_search_vector = Column(TSVECTOR, nullable=True) # ⭐ COLUMNA DIRECTA para FTS

    # Índices adicionales para las columnas directas
    __table_args__ = (
        Index('idx_langchain_pg_embedding_account_id', account_id),
        Index('idx_langchain_pg_embedding_workspace_id', workspace_id),
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

    name = Column(String(255), nullable=False, comment="El nombre del tema/colección (corresponde al 'topic' en cmetadata).")
    description = Column(Text, nullable=True, comment="Descripción opcional de la colección.")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relaciones
    account = relationship("Account", back_populates="user_document_topics")
    workspace = relationship("Workspace", back_populates="user_document_topics")

    contact_profiles = relationship(
        "ContactProfile",
        secondary="user_document_topic_contact_profiles_association",
        back_populates="user_document_topics"
    )

    # Restricciones para asegurar que un usuario/workspace no tenga dos colecciones con el mismo nombre
    __table_args__ = (
        Index('ix_account_workspace_topic', 'account_id', 'workspace_id', 'name', unique=True, postgresql_where=text("workspace_id IS NOT NULL")),
        Index('ix_account_personal_topic', 'account_id', 'name', unique=True, postgresql_where=text("workspace_id IS NULL")),
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
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete='CASCADE'), nullable=False, unique=True)
    
    nombre = Column(String(255), nullable=True)
    gustos = Column(String, nullable=True)
    intereses = Column(String, nullable=True)
    otros_datos = Column(String, nullable=True)
    
    # CORREGIDO: Añadimos la columna 'system_prompt' que faltaba.
    system_prompt = Column(String, nullable=True)

    account = relationship("Account", back_populates="profile")


class ContactProfile(Base):
    """
    Representa un perfil de contacto, vinculado a una cuenta de usuario.
    """
    __tablename__ = "contact_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=True, comment="Nombre del contacto.")
    email = Column(String(255), nullable=True, comment="Email del contacto.")
    phone = Column(String(255), nullable=True, comment="Número de teléfono del contacto.")
    tags = Column(ARRAY(String), nullable=True, comment="Etiquetas asociadas al contacto.")
    category = Column(String(255), nullable=True, comment="Categoría del contacto.")
    custom_fields = Column(JSONB, nullable=True, comment="Campos personalizados para el contacto.")
    
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relación con Account
    account = relationship("Account", back_populates="contact_profiles")

    notas = relationship(
        "Nota",
        secondary="note_contact_profiles_association",
        back_populates="contact_profiles"
    )

    user_document_topics = relationship(
        "UserDocumentTopic",
        secondary="user_document_topic_contact_profiles_association",
        back_populates="contact_profiles"
    )

    agenda_events = relationship(
        "AgendaEvent",
        secondary="agenda_event_contact_profiles_association",
        back_populates="contact_profiles"
    )

    tasks = relationship(
        "Task",
        secondary="task_contact_profiles_association",
        back_populates="contact_profiles"
    )

    albums = relationship("Album", secondary="contact_profile_album_association", back_populates="contact_profiles")
 
    forms = relationship(
        "Form",
        secondary="form_contact_profiles_association",
        back_populates="contact_profiles"
    )

    def __repr__(self):
        return f"<ContactProfile(id={self.id}, name='{self.name}', account_id={self.account_id})>"


class Form(Base):
    """
    Representa un formulario dinámico creado por el usuario.
    """
    __tablename__ = "forms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False, comment="Nombre del formulario.")
    description = Column(Text, nullable=True, comment="Descripción del formulario.")
    schema = Column(JSONB, nullable=False, comment="Esquema JSON del formulario.")
    is_public = Column(Boolean, default=False, nullable=False, comment="Indica si el formulario es accesible públicamente.")

    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relación con Account
    account = relationship("Account", back_populates="forms")

    contact_profiles = relationship(
        "ContactProfile",
        secondary="form_contact_profiles_association",
        back_populates="forms"
    )

    def __repr__(self):
        return f"<Form(id={self.id}, name='{self.name}', account_id={self.account_id})>"


class FormContactProfileAssociation(Base):
    """
    Tabla de asociación para la relación muchos a muchos entre Form y ContactProfile.
    """
    __tablename__ = "form_contact_profiles_association"

    form_id = Column(UUID(as_uuid=True), ForeignKey("forms.id"), primary_key=True, nullable=False)
    contact_profile_id = Column(UUID(as_uuid=True), ForeignKey("contact_profiles.id"), primary_key=True, nullable=False)

    def __repr__(self):
        return f"<FormContactProfileAssociation(form_id={self.form_id}, contact_profile_id={self.contact_profile_id})>"


class FormResponse(Base):
    """
    Representa una respuesta enviada a un formulario dinámico.
    """
    __tablename__ = "form_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_id = Column(UUID(as_uuid=True), ForeignKey("forms.id"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, index=True) # Quien envió la respuesta
    contact_profile_id = Column(UUID(as_uuid=True), ForeignKey("contact_profiles.id"), nullable=True, index=True) # Si la respuesta está asociada a un perfil de contacto

    answers = Column(JSONB, nullable=False, comment="Respuestas en formato JSONB (campo_id: valor).")

    submitted_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relaciones
    form = relationship("Form", backref="responses")
    account = relationship("Account", backref="form_responses")
    contact_profile = relationship("ContactProfile", backref="form_responses", uselist=False)

    def __repr__(self):
        return f"<FormResponse(id={self.id}, form_id={self.form_id}, account_id={self.account_id})>"


class Nota(Base):
    """Almacena las notas de un usuario o equipo."""
    __tablename__ = "notas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True)
    
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    category = Column(String, default="General")
    created_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    etag = Column(String, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    text_search_vector = Column(TSVECTOR, nullable=True)

    contact_profiles = relationship(
        "ContactProfile",
        secondary="note_contact_profiles_association",
        back_populates="notas"
    )

    account = relationship("Account", back_populates="notas")
    workspace = relationship("Workspace", backref="notas")

    __table_args__ = (
        Index('ix_notas_text_search_vector', text_search_vector, postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<Nota(id={self.id}, title='{self.title}', account_id={self.account_id})>"


# --- Modelos para Galerías y Fotos ---

class Album(Base):
    __tablename__ = 'albums'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    cover_photo_id = Column(UUID(as_uuid=True), ForeignKey('photos.id', use_alter=True, name='fk_album_cover_photo'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("Account")
    cover_photo = relationship("Photo", foreign_keys=[cover_photo_id], post_update=True)
    photos = relationship("Photo",
                          back_populates="album",
                          cascade="all, delete-orphan",
                          foreign_keys="[Photo.album_id]")
    contact_profiles = relationship("ContactProfile", secondary="contact_profile_album_association", back_populates="albums")
    contact_profiles = relationship("ContactProfile", secondary="contact_profile_album_association", back_populates="albums")


class Photo(Base):
    __tablename__ = 'photos'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey('albums.id'), nullable=False)
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True) # NEW COLUMN
    is_favorite = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    order = Column(Integer, nullable=False, default=0) # NUEVA COLUMNA PARA EL ORDEN

    album = relationship("Album", back_populates="photos", foreign_keys=[album_id])


# --- Model for Shared Album Links ---
class SharedAlbumLink(Base):
    __tablename__ = 'shared_album_links'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey('albums.id'), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)
    expiry_date = Column(DateTime, nullable=True) # NUEVA COLUMNA
    created_at = Column(DateTime, default=datetime.utcnow) # NUEVA COLUMNA
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    allow_download = Column(Boolean, default=True, nullable=False) # NUEVA COLUMNA

    album = relationship("Album")


contact_profile_album_association = Table('contact_profile_album_association', Base.metadata,
    Column('contact_profile_id', UUID(as_uuid=True), ForeignKey('contact_profiles.id'), primary_key=True),
    Column('album_id', UUID(as_uuid=True), ForeignKey('albums.id'), primary_key=True)
)


class AgendaEvent(Base):
    """Modelo para los eventos de la agenda del usuario o equipo."""
    __tablename__ = "agenda_events"

    id = Column(Integer, primary_key=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True)
    summary = Column(String, nullable=False, comment="Resumen conciso del evento.")
    description = Column(Text, nullable=True, comment="Descripción detallada del evento.")
    location = Column(String(255), nullable=True, comment="Ubicación del evento.")
    event_datetime_utc = Column(DateTime(timezone=True), nullable=False)
    external_attendees = Column(ARRAY(String), nullable=True, comment="Nombres de asistentes no registrados.")
    is_active = Column(Boolean, default=True, nullable=False)
    job_name = Column(String, nullable=True, unique=True) # Para poder cancelar los jobs de Telegram
    etag = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="Pendiente", comment="Estado del evento para tableros Kanban (ej. Pendiente, En Progreso, Completado).")
    end_date = Column(DateTime(timezone=True), nullable=True) # Nuevo campo para la fecha de finalización
    is_private = Column(Boolean, default=False, nullable=False, comment="Indica si el evento es privado (solo visible para el creador).")

    contact_profiles = relationship(
        "ContactProfile",
        secondary="agenda_event_contact_profiles_association",
        back_populates="agenda_events"
    )
    
    attendees = relationship(
        "Account",
        secondary=agenda_event_attendees_association,
        back_populates="agenda_events_attended"
    )

    account = relationship("Account", back_populates="agenda_events")
    workspace = relationship("Workspace", back_populates="agenda_events")

    def to_dict(self, timezone_str: str | None = "UTC") -> Dict[str, Any]:
        """Convierte el objeto a un diccionario para su uso en APIs."""
        user_tz = pytz.timezone(timezone_str) if timezone_str else pytz.utc
        local_datetime = self.event_datetime_utc.astimezone(user_tz)
        
        workspace_name = None
        workspace_color = None
        if self.workspace:
            workspace_name = self.workspace.name
            workspace_color = self.workspace.color

        creator_name = "Desconocido"
        if self.account:
            creator_name = self.account.name or self.account.email or "Usuario"

        return {
            "id": self.id,
            "account_id": str(self.account_id),
            "creator_name": creator_name, # Nuevo campo
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "workspace_name": workspace_name,
            "workspace_color": workspace_color,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "event_datetime_utc": self.event_datetime_utc.isoformat(),
            "event_datetime_local": local_datetime.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "user_timezone": str(user_tz),
            "is_active": self.is_active,
            "is_private": self.is_private, # Nuevo campo
            "attendees": [str(att.id) for att in self.attendees],
            "external_attendees": self.external_attendees if self.external_attendees else [],
            "duration_minutes": self.duration_minutes,
            "status": self.status,
            "etag": self.etag
        }


class NoteContactProfileAssociation(Base):
    """
    Tabla de asociación para la relación muchos a muchos entre Nota y ContactProfile.
    """
    __tablename__ = "note_contact_profiles_association"

    note_id = Column(Integer, ForeignKey("notas.id"), primary_key=True, nullable=False)
    contact_profile_id = Column(UUID(as_uuid=True), ForeignKey("contact_profiles.id"), primary_key=True, nullable=False)

    def __repr__(self):
        return f"<NoteContactProfileAssociation(note_id={self.note_id}, contact_profile_id={self.contact_profile_id})>"


class AgendaEventContactProfileAssociation(Base):
    """
    Tabla de asociación para la relación muchos a muchos entre AgendaEvent y ContactProfile.
    """
    __tablename__ = "agenda_event_contact_profiles_association"

    agenda_event_id = Column(Integer, ForeignKey("agenda_events.id"), primary_key=True, nullable=False)
    contact_profile_id = Column(UUID(as_uuid=True), ForeignKey("contact_profiles.id"), primary_key=True, nullable=False)

    def __repr__(self):
        return f"<AgendaEventContactProfileAssociation(agenda_event_id={self.agenda_event_id}, contact_profile_id={self.contact_profile_id})>"





class Recordatorio(Base):
    """Almacena recordatorios simples."""
    __tablename__ = "recordatorios"
    id = Column(Integer, primary_key=True, index=True)
    # Refactorizado: Se vincula a account_id
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    message = Column(Text, nullable=False)
    due_datetime = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    job_name = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

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
    persistent_rag_context = Column(JSONB, nullable=True, default=[])

    account = relationship("Account", back_populates="chat_threads")
    workspace = relationship("Workspace", back_populates="chat_threads")

class ProactiveInsight(Base):
    __tablename__ = "proactive_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    insight_message = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    action_suggestion = Column(Text, nullable=True)
    related_items = Column(JSONB, nullable=True)  # Se almacena la lista de ítems como JSON (incluye tool_used en metadata)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    account = relationship("Account", back_populates="proactive_insights")


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


class UserDocumentTopicContactProfileAssociation(Base):
    """
    Tabla de asociación para la relación muchos a muchos entre UserDocumentTopic y ContactProfile.
    """
    __tablename__ = "user_document_topic_contact_profiles_association"

    user_document_topic_id = Column(UUID(as_uuid=True), ForeignKey("user_document_topics.id"), primary_key=True, nullable=False)
    contact_profile_id = Column(UUID(as_uuid=True), ForeignKey("contact_profiles.id"), primary_key=True, nullable=False)

    def __repr__(self):
        return f"<UserDocumentTopicContactProfileAssociation(user_document_topic_id={self.user_document_topic_id}, contact_profile_id={self.contact_profile_id})>"


class TaskContactProfileAssociation(Base):
    """
    Tabla de asociación para la relación muchos a muchos entre Task y ContactProfile.
    """
    __tablename__ = "task_contact_profiles_association"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True, nullable=False)
    contact_profile_id = Column(UUID(as_uuid=True), ForeignKey("contact_profiles.id"), primary_key=True, nullable=False)

    def __repr__(self):
        return f"<TaskContactProfileAssociation(task_id={self.task_id}, contact_profile_id={self.contact_profile_id})>"


class Task(Base):
    """

    Representa una tarea en el sistema, que puede estar asociada a una cuenta,
    o un espacio de trabajo.
    """
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), index=True, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True, nullable=True)
    
    description = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True) # Nuevo campo para la fecha de inicio
    end_date = Column(DateTime(timezone=True), nullable=True) # Nuevo campo para la fecha de finalización
    status = Column(String(50), nullable=False, default="Pendiente", comment="Estado de la tarea para tableros Kanban (ej. Pendiente, En Progreso, Completado).")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relaciones
    account = relationship("Account", back_populates="tasks")
    workspace = relationship("Workspace", back_populates="tasks")

    contact_profiles = relationship(
        "ContactProfile",
        secondary="task_contact_profiles_association",
        back_populates="tasks"
    )

    def __repr__(self):
        return f"<Task(id={self.id}, description='{self.description[:50]}...', is_completed={self.is_completed})>"


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

    __table_args__ = (UniqueConstraint('repo_url', 'file_path', name='_github_repo_file_uc'), {'extend_existing': True})

    def __repr__(self):
        return f"<GitHubDocument(repo_url='{self.repo_url}', file_path='{self.file_path}')>"


class AnalyzedPair(Base):
    """
    Almacena pares de IDs de documentos que ya han sido analizados para evitar re-análisis redundantes.
    Los document_id_a y document_id_b se almacenan en orden lexicográfico para asegurar unicidad.
    """
    __tablename__ = "analyzed_pairs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    document_id_a = Column(String, nullable=False, index=True)
    document_id_b = Column(String, nullable=False, index=True)
    last_analyzed_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        UniqueConstraint('account_id', 'document_id_a', 'document_id_b', name='_account_document_pair_uc'), {'extend_existing': True}
    )

    def __repr__(self):
        return f"<AnalyzedPair(account_id={self.account_id}, doc_a={self.document_id_a}, doc_b={self.document_id_b})>"


class GapDevelopmentAnalysis(Base):
    """
    Almacena los resultados de las investigaciones profundas sobre brechas de conocimiento.
    """
    __tablename__ = "gap_development_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gap_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="ID de la brecha de conocimiento")
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    
    status = Column(String(50), nullable=False, default="pending", index=True,
                   comment="Estado de la investigación: pending, processing, completed, failed")
    
    report = Column(JSONB, nullable=True, comment="Informe estructurado con hallazgos, fuentes y recomendaciones")
    
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Relación con Account
    account = relationship("Account", back_populates="gap_development_analysis")

    def __repr__(self):
        return f"<GapDevelopmentAnalysis(id={self.id}, gap_id={self.gap_id}, status='{self.status}')>"


# ==============================================================================
# SECCIÓN 2: FUNCIONES AUXILIARES DE LA BASE DE DATOS
# ==============================================================================
from contextlib import asynccontextmanager
import logging


async def create_tables():
    """
    Crea la extensión pgvector y todas las tablas definidas en los modelos
    si no existen en la base de datos. Incluye reintentos para robustez.
    """
    max_retries = 5
    retry_delay = 5  # segundos
    for attempt in range(max_retries):
        try:
            logger.info(f"Verificando y creando tablas (intento {attempt + 1}/{max_retries})...")
            async with engine.begin() as conn:
                # Asegura que la extensión de pgvector esté habilitada
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                logger.info("Extensión pgvector verificada/creada.")
                
                # Crea todas las tablas que heredan de Base
                await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ Tablas de la base de datos verificadas/creadas exitosamente.")

                # Crear índices manualmente para AnalyzedPair con IF NOT EXISTS
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_analyzed_pairs_account_id ON analyzed_pairs (account_id)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_analyzed_pairs_document_ids ON analyzed_pairs (document_id_a, document_id_b)"))
                logger.info("✅ Índices de 'analyzed_pairs' verificados/creados exitosamente.")

                return  # Salir de la función si tiene éxito
        except Exception as e:
            logger.error(f"❌ Error al crear tablas en el intento {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Reintentando en {retry_delay} segundos...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("❌ ERROR CRÍTICO: No se pudieron crear las tablas de la base de datos después de varios reintentos.")
                raise

async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    Dependencia de FastAPI para obtener una sesión de base de datos asíncrona.
    Este es el patrón estándar para la inyección de dependencias de sesiones en FastAPI.
    """
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        logger.error(f"Error en la sesión de la base de datos: {e}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()
        await log_pool_status()



from sqlalchemy import delete

async def delete_accounts_by_ids(db_session: AsyncSession, account_ids: list[uuid.UUID]) -> int:
    """
    Elimina cuentas de la base de datos por sus IDs, asegurando que todas las
    dependencias se eliminen primero para evitar errores de ForeignKeyViolation.
    """
    try:
        logger.info(f"Iniciando eliminación completa de cuentas y dependencias para IDs: {account_ids}")

        # --- Fase 1: Eliminar dependencias complejas y de asociación ---
        
        # Eliminar de tablas de asociación
        await db_session.execute(delete(agenda_event_attendees_association).where(agenda_event_attendees_association.c.account_id.in_(account_ids)))
        
        # Eliminar WorkspacePermissions antes que Workspaces
        await db_session.execute(delete(WorkspacePermission).where(WorkspacePermission.account_id.in_(account_ids)))
        
        # La tabla TeamMember ha sido eliminada.
        # await db_session.execute(delete(TeamMember).where(TeamMember.account_id.in_(account_ids)))

        # Eliminar FormResponses (que pueden depender de la cuenta o del formulario)
        form_ids_stmt = select(Form.id).where(Form.account_id.in_(account_ids))
        form_ids_result = await db_session.execute(form_ids_stmt)
        form_ids = form_ids_result.scalars().all()
        if form_ids:
            await db_session.execute(delete(FormResponse).where(FormResponse.form_id.in_(form_ids)))
        await db_session.execute(delete(FormResponse).where(FormResponse.account_id.in_(account_ids)))
            
        # Eliminar Photos y SharedAlbumLinks antes que Albums
        album_ids_stmt = select(Album.id).where(Album.account_id.in_(account_ids))
        album_ids_result = await db_session.execute(album_ids_stmt)
        album_ids = album_ids_result.scalars().all()
        if album_ids:
            await db_session.execute(delete(SharedAlbumLink).where(SharedAlbumLink.album_id.in_(album_ids)))
            await db_session.execute(delete(Photo).where(Photo.album_id.in_(album_ids)))

        # --- Fase 2: Eliminar entidades que dependen directamente de Account ---
        
        direct_dependents = [
            PlatformIdentity, Perfil, ContactProfile, Form, Nota, Album,
            AgendaEvent, Recordatorio, ProactiveInsight, VerificationCode,
            AnalysisTask, MindmapTask, UploadTask, Task, GitHubDocument,
            UserDocumentTopic, ChatThread, LangchainPgEmbedding, Workspace,
            AnalyzedPair, GapDevelopmentAnalysis
        ]
        for model in direct_dependents:
            if hasattr(model, 'account_id'):
                await db_session.execute(delete(model).where(model.account_id.in_(account_ids)))


        # --- Fase 3: Eliminar la cuenta principal ---
        logger.info("Eliminando las cuentas principales...")
        delete_accounts_stmt = delete(Account).where(Account.id.in_(account_ids))
        result = await db_session.execute(delete_accounts_stmt)
        
        await db_session.commit()
        logger.info(f"✅ Eliminadas {result.rowcount} cuentas y todas sus dependencias con IDs: {account_ids}")
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

async def get_or_create_account_from_platform_id(
    platform: str,
    platform_user_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None
) -> Optional[Tuple[Account, bool]]:
    """
    Busca o crea una cuenta de usuario basada en una identidad de plataforma.

    Args:
        platform: Nombre de la plataforma (ej. 'telegram')
        platform_user_id: ID del usuario en esa plataforma
        first_name: Nombre del usuario (opcional)
        last_name: Apellido del usuario (opcional)
        username: Nombre de usuario (opcional)

    Returns:
        Tupla (Account, bool) donde bool indica si la cuenta fue creada (True) o ya existía (False),
        o None si hubo un error.
    """
    async with DBSession(SessionLocal) as db_session:
        try:
            # Buscar identidad existente
            stmt = select(PlatformIdentity).where(
                PlatformIdentity.platform == platform,
                PlatformIdentity.platform_user_id == platform_user_id
            ).options(selectinload(PlatformIdentity.account).selectinload(Account.profile))

            result = await db_session.execute(stmt)
            identity = result.scalars().first()

            if identity and identity.account:
                # Actualizar información si está vacía
                if identity.account.name is None and first_name:
                    identity.account.name = first_name
                if identity.account.username is None and username:
                    identity.account.username = username
                if first_name or username:
                    await db_session.commit()
                return (identity.account, False)

            # Crear nueva cuenta
            new_account = Account(name=first_name, username=username)
            db_session.add(new_account)
            await db_session.flush()

            # Crear identidad de plataforma
            new_identity = PlatformIdentity(
                account_id=new_account.id,
                platform=platform,
                platform_user_id=platform_user_id
            )
            db_session.add(new_identity)

            # Crear perfil vacío
            new_profile = Perfil(account_id=new_account.id)
            db_session.add(new_profile)

            await db_session.commit()
            return (new_account, True)

        except Exception as e:
            logger.error(f"Error en get_or_create_account_from_platform_id: {e}", exc_info=True)
            await db_session.rollback()
            return None

async def log_pool_status():
    """
    Registra el estado actual del pool de conexiones para monitorear su uso.
    """
    # NOTE: `engine.pool.status()` es un método síncrono, por lo que **no** debe usarse con `await`.
    # Mantener la función como async permite llamarla desde código async sin bloquear el bucle de eventos.
    try:
        pool_status = engine.pool.status()
        logger.debug(f"Estado del pool de conexiones: {pool_status}")
    except Exception as e:
        logger.error(f"Error al obtener el estado del pool: {e}", exc_info=True)
