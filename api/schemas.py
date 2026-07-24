import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class ProfileLinkRequest(BaseModel):
    profile_id: uuid.UUID


class UserSettingsResponse(BaseModel):
    """Define la estructura de datos para la respuesta de la configuración de usuario."""
    name: Optional[str]
    email: Optional[EmailStr]
    phone: Optional[str]
    bio: Optional[str]
    profiles_enabled: bool
    galleries_enabled: bool
    forms_enabled: bool
    skills_enabled: bool
    heartbeat_enabled: bool
    theme: str
    notifications_email: bool
    notifications_push: bool
    language: str
    privacy_data_sharing: bool
    # Campos de LLM
    llm_provider: Optional[str]
    llm_model: Optional[str]
    llm_temperature: Optional[float]
    llm_api_base: Optional[str]
    fast_llm_model: Optional[str]
    fast_llm_provider: Optional[str]
    vision_llm_model: Optional[str]
    vision_llm_provider: Optional[str]
    use_prompt_tooling: bool
    # Campos de TTS
    tts_provider: Optional[str]
    tts_model: Optional[str]
    tts_voice: Optional[str]
    tts_speed: Optional[float]
    tts_region: Optional[str]
    tts_api_base: Optional[str]
    # Campos de Embeddings
    embedding_provider: Optional[str]
    embedding_model: Optional[str]
    embedding_api_key_name: Optional[str]
    embedding_api_base: Optional[str]
    # Campos de Reranker
    reranker_provider: Optional[str] = None
    reranker_model: Optional[str] = None
    reranker_api_base: Optional[str] = None
    disabled_skills: Optional[list] = []
    installed_extensions: Optional[list] = []
    # Campos de SSH
    ssh_host: Optional[str] = None
    ssh_port: Optional[str] = "22"
    ssh_user: Optional[str] = None
    local_base_path: Optional[str] = None
    cloud_storage_path: Optional[str] = None
    # Campos de Correo IMAP/SMTP
    email_provider: Optional[str] = None
    email_imap_host: Optional[str] = None
    email_imap_port: Optional[str] = "993"
    email_smtp_host: Optional[str] = None
    email_smtp_port: Optional[str] = "465"
    email_use_ssl: Optional[bool] = True
    email_username: Optional[str] = None
    email_password_secret: Optional[str] = None
    # Campos de Heartbeat
    custom_heartbeat_instructions: Optional[str] = None
    custom_heartbeat_interval_minutes: Optional[int] = 60
    custom_heartbeat_allowed_tools: Optional[list] = []

    class Config:
        from_attributes = True

class UserSettingsUpdateRequest(BaseModel):
    """Define la estructura de datos para la actualización de la configuración de usuario."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    profiles_enabled: Optional[bool] = None
    galleries_enabled: Optional[bool] = None
    forms_enabled: Optional[bool] = None
    skills_enabled: Optional[bool] = None
    heartbeat_enabled: Optional[bool] = None
    theme: Optional[str] = None
    notifications_email: Optional[bool] = None
    notifications_push: Optional[bool] = None
    language: Optional[str] = None
    privacy_data_sharing: Optional[bool] = None
    # Campos de LLM
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_api_base: Optional[str] = None
    fast_llm_model: Optional[str] = None
    fast_llm_provider: Optional[str] = None
    vision_llm_model: Optional[str] = None
    vision_llm_provider: Optional[str] = None
    use_prompt_tooling: Optional[bool] = None
    # Campos de TTS
    tts_provider: Optional[str] = None
    tts_model: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_speed: Optional[float] = None
    tts_region: Optional[str] = None
    tts_api_base: Optional[str] = None
    # Campos de Embeddings
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_api_key_name: Optional[str] = None
    embedding_api_base: Optional[str] = None
    # Campos de Reranker
    reranker_provider: Optional[str] = None
    reranker_model: Optional[str] = None
    reranker_api_base: Optional[str] = None
    disabled_skills: Optional[list] = None
    installed_extensions: Optional[list] = None
    # Campos de SSH
    ssh_host: Optional[str] = None
    ssh_port: Optional[str] = None
    ssh_user: Optional[str] = None
    local_base_path: Optional[str] = None
    cloud_storage_path: Optional[str] = None
    # Campos de Email
    email_provider: Optional[str] = None
    email_imap_host: Optional[str] = None
    email_imap_port: Optional[str] = None
    email_smtp_host: Optional[str] = None
    email_smtp_port: Optional[str] = None
    email_use_ssl: Optional[bool] = None
    email_username: Optional[str] = None
    email_password_secret: Optional[str] = None
    custom_heartbeat_instructions: Optional[str] = None
    custom_heartbeat_interval_minutes: Optional[int] = None
    custom_heartbeat_allowed_tools: Optional[list] = None

class UserPasswordUpdateRequest(BaseModel):
    """Define la estructura de datos para actualizar la contraseña."""
    current_password: Optional[str] = None
    new_password: str = Field(..., min_length=8)

class UserSecretRequest(BaseModel):
    """Estructura para crear o actualizar un secreto."""
    key_name: str = Field(..., pattern=r"^[A-Z0-9_]+$")
    value: str
    description: Optional[str] = None

class UserSecretResponse(BaseModel):
    """Estructura para la respuesta de un secreto (sin mostrar el valor completo)."""
    key_name: str
    description: Optional[str]
    masked_value: str # e.g. "sk-proj...h3k8"
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

