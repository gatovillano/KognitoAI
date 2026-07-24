import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from api.galleries import PhotoResponse, AlbumResponse

class SelectionShareLinkCreate(BaseModel):
    password: Optional[str] = Field(None, min_length=4, description="Contraseña opcional para proteger el panel.")
    expiry_days: Optional[int] = Field(None, gt=0, description="Días hasta caducidad.")
    allow_comments: bool = Field(True, description="Permitir comentarios en fotos y selección general.")
    max_selections: Optional[int] = Field(None, gt=0, description="Límite máximo de fotos seleccionables.")

class SelectionShareLinkResponse(BaseModel):
    id: uuid.UUID
    album_id: uuid.UUID
    token: str
    has_password: bool
    expiry_date: Optional[datetime]
    allow_comments: bool
    max_selections: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class SelectionSubmitItem(BaseModel):
    photo_id: uuid.UUID
    comment: Optional[str] = None

class SelectionSubmitRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=255, description="Nombre del cliente o destinatario.")
    client_email: Optional[str] = Field(None, description="Email opcional del destinatario.")
    general_comment: Optional[str] = Field(None, description="Comentario general para la selección.")
    items: List[SelectionSubmitItem] = Field(..., min_items=1, description="Lista de fotos seleccionadas.")

class SelectionItemResponse(BaseModel):
    id: uuid.UUID
    photo_id: uuid.UUID
    comment: Optional[str] = None
    photo: Optional[PhotoResponse] = None

    class Config:
        from_attributes = True

class SelectionSubmissionResponse(BaseModel):
    id: uuid.UUID
    share_link_id: uuid.UUID
    album_id: uuid.UUID
    client_name: str
    client_email: Optional[str] = None
    general_comment: Optional[str] = None
    created_at: datetime
    items: List[SelectionItemResponse] = []

    class Config:
        from_attributes = True

class PublicSelectionPanelResponse(BaseModel):
    album: AlbumResponse
    allow_comments: bool
    max_selections: Optional[int]
    token: str
