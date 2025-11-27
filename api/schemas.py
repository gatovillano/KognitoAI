import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr

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
    theme: str
    notifications_email: bool
    notifications_push: bool
    language: str
    privacy_data_sharing: bool

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
    theme: Optional[str] = None
    notifications_email: Optional[bool] = None
    notifications_push: Optional[bool] = None
    language: Optional[str] = None
    privacy_data_sharing: Optional[bool] = None
