from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, Field
from datetime import datetime

from sqlalchemy import func

from core.database import get_db_session, ContactProfile, Account, Nota, AgendaEvent, Task, UserDocumentTopic, Album, Photo, FormResponse
from api.auth import get_current_account_id
from sqlalchemy.orm import selectinload

async def get_current_account(account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)) -> Account:
    account = await db.get(Account, uuid.UUID(account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    return account

router = APIRouter()

# Pydantic models for request and response
class ContactProfileBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    custom_fields: Optional[dict] = None

class ContactProfileResponse(ContactProfileBase):
    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Pydantic models for linked objects
class LinkedNoteResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    created_at: datetime
    class Config: from_attributes = True

class LinkedAgendaEventResponse(BaseModel):
    id: int
    summary: Optional[str] # Añadido para el título del evento
    description: Optional[str]
    event_datetime_utc: datetime
    event_datetime_local: Optional[datetime] = None
    class Config: from_attributes = True

class LinkedTaskResponse(BaseModel):
    id: uuid.UUID
    description: str
    is_completed: bool
    due_date: Optional[datetime] = None
    class Config: from_attributes = True

class LinkedUserDocumentTopicResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    class Config: from_attributes = True

# Redefined PhotoResponse to avoid circular imports, keeping it minimal for this context.
class PhotoResponseForContactProfile(BaseModel):
    id: uuid.UUID
    file_path: str
    thumbnail_path: Optional[str] = None
    class Config:
        from_attributes = True

class LinkedAlbumResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    cover_photo_id: Optional[uuid.UUID] = None
    created_at: datetime
    total_photos: int
    cover_photo: Optional[PhotoResponseForContactProfile] = None
    class Config: from_attributes = True

class LinkedFormResponse(BaseModel):
    id: uuid.UUID
    form_id: uuid.UUID
    submitted_at: datetime
    answers: List[Dict[str, Any]] # Cambiado de dict a List[Dict[str, Any]]
    class Config: from_attributes = True

class LinkedObjectsResponse(BaseModel):
    notes: List[LinkedNoteResponse]
    agenda_events: List[LinkedAgendaEventResponse]
    tasks: List[LinkedTaskResponse]
    user_document_topics: List[LinkedUserDocumentTopicResponse]
    albums: List[LinkedAlbumResponse]
    form_responses: List[LinkedFormResponse]

class LinkNoteToProfileRequest(BaseModel):
    note_id: int

class LinkAlbumToProfileRequest(BaseModel):
    album_id: uuid.UUID

class LinkFormResponseToProfileRequest(BaseModel):
    form_response_id: uuid.UUID

@router.post("/contact-profiles/{profile_id}/link-note")
async def link_note_to_profile(
    profile_id: uuid.UUID,
    request: LinkNoteToProfileRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Vincula una nota existente a un perfil de contacto.
    """
    profile_stmt = select(ContactProfile).where(
        ContactProfile.id == profile_id,
        ContactProfile.account_id == current_account.id
    ).options(selectinload(ContactProfile.notas))
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    note = await db.get(Nota, request.note_id)
    if not note or note.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no autorizada.")

    if note in profile.notas:
        return {"message": "La nota ya está vinculada a este perfil."}

    profile.notas.append(note)
    await db.commit()
    return {"message": "Nota vinculada exitosamente al perfil."}

@router.post("/contact-profiles/{profile_id}/link-album", summary="Vincular un álbum a un perfil")
async def link_album_to_profile(
    profile_id: uuid.UUID,
    request: LinkAlbumToProfileRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Vincula un álbum de fotos existente a un perfil de contacto.
    """
    profile_stmt = select(ContactProfile).where(
        ContactProfile.id == profile_id,
        ContactProfile.account_id == current_account.id
    ).options(selectinload(ContactProfile.albums))
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    album = await db.get(Album, request.album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    if album in profile.albums:
        return {"message": "El álbum ya está vinculado a este perfil."}

    profile.albums.append(album)
    await db.commit()
    return {"message": "Álbum vinculado exitosamente al perfil."}

@router.post("/contact-profiles/{profile_id}/link-form-response", summary="Vincular una respuesta de formulario a un perfil")
async def link_form_response_to_profile(
    profile_id: uuid.UUID,
    request: LinkFormResponseToProfileRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Vincula una respuesta de formulario existente a un perfil de contacto.
    """
    # 1. Verificar que el perfil de contacto existe y pertenece a la cuenta actual
    profile = await db.get(ContactProfile, profile_id)
    if not profile or profile.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    # 2. Verificar que la respuesta de formulario existe y pertenece a la cuenta actual
    form_response = await db.get(FormResponse, request.form_response_id)
    if not form_response or form_response.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Respuesta de formulario no encontrada o no autorizada.")

    # 3. Verificar si ya está vinculada
    if form_response.contact_profile_id == profile_id:
        return {"message": "La respuesta de formulario ya está vinculada a este perfil."}

    # 4. Vincular la respuesta de formulario al perfil de contacto
    form_response.contact_profile_id = profile_id
    await db.commit()
    await db.refresh(form_response) # Refrescar para obtener el contact_profile_id actualizado

    return {"message": "Respuesta de formulario vinculada exitosamente al perfil."}

@router.post("/contact-profiles/{profile_id}/unlink-form-response", summary="Desvincular una respuesta de formulario de un perfil")
async def unlink_form_response_from_profile(
    profile_id: uuid.UUID,
    request: LinkFormResponseToProfileRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Desvincula una respuesta de formulario de un perfil de contacto.
    """
    # 1. Verificar que el perfil de contacto existe y pertenece a la cuenta actual
    profile = await db.get(ContactProfile, profile_id)
    if not profile or profile.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    # 2. Verificar que la respuesta de formulario existe y pertenece a la cuenta actual
    form_response = await db.get(FormResponse, request.form_response_id)
    if not form_response or form_response.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Respuesta de formulario no encontrada o no autorizada.")

    # 3. Verificar si la respuesta de formulario está vinculada a este perfil
    if form_response.contact_profile_id != profile_id:
        return {"message": "La respuesta de formulario no está vinculada a este perfil."}

    # 4. Desvincular la respuesta de formulario del perfil de contacto
    form_response.contact_profile_id = None
    await db.commit()
    await db.refresh(form_response)

    return {"message": "Respuesta de formulario desvinculada exitosamente del perfil."}

@router.post("/contact-profiles/{profile_id}/unlink-album", summary="Desvincular un álbum de un perfil")
async def unlink_album_from_profile(
    profile_id: uuid.UUID,
    request: LinkAlbumToProfileRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Desvincula un álbum de fotos de un perfil de contacto.
    """
    profile_stmt = select(ContactProfile).where(
        ContactProfile.id == profile_id,
        ContactProfile.account_id == current_account.id
    ).options(selectinload(ContactProfile.albums))
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    album = await db.get(Album, request.album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    if album not in profile.albums:
        return {"message": "El álbum no está vinculado a este perfil."}

    profile.albums.remove(album)
    await db.commit()
    return {"message": "Álbum desvinculado exitosamente del perfil."}

@router.get("/contact-profiles", response_model=List[ContactProfileResponse])
async def get_all_contact_profiles(
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(
        select(ContactProfile)
        .where(ContactProfile.account_id == current_account.id)
        .order_by(ContactProfile.created_at.desc())
    )
    return result.scalars().all()

@router.post("/list-contact-profiles", response_model=List[ContactProfileResponse])
async def list_contact_profiles(
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(
        select(ContactProfile)
        .where(ContactProfile.account_id == current_account.id)
        .order_by(ContactProfile.created_at.desc())
    )
    return result.scalars().all()

@router.get("/contact-profiles/{profile_id}", response_model=ContactProfileResponse)
async def get_contact_profile(
    profile_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    profile = await db.get(ContactProfile, profile_id)
    if not profile or profile.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")
    return profile

@router.get("/contact-profiles/{profile_id}/linked-objects", response_model=LinkedObjectsResponse)
async def get_linked_objects(
    profile_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene todos los objetos vinculados a un perfil de contacto.
    """
    profile_stmt = (
        select(ContactProfile)
        .options(
            selectinload(ContactProfile.notas),
            selectinload(ContactProfile.agenda_events).selectinload(AgendaEvent.attendees), # Aquí cargamos los asistentes
            selectinload(ContactProfile.agenda_events).selectinload(AgendaEvent.workspace), # Y aquí cargamos el workspace para evitar el lazy loading
            selectinload(ContactProfile.tasks),
            selectinload(ContactProfile.user_document_topics),
            selectinload(ContactProfile.albums),
            selectinload(ContactProfile.form_responses) # Cargar las respuestas de formulario
        )
        .where(ContactProfile.id == profile_id, ContactProfile.account_id == current_account.id)
    )
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    # Enhance albums with total_photos and cover_photo
    enhanced_albums = []
    if profile.albums:
        for album in profile.albums:
            # Get total photo count for the album
            total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album.id)
            total_photos_result = await db.execute(total_photos_stmt)
            total_photos = total_photos_result.scalar_one()

            # Get the cover photo object if it exists
            cover_photo_obj = None
            if album.cover_photo_id:
                cover_photo_result = await db.execute(select(Photo).where(Photo.id == album.cover_photo_id))
                photo = cover_photo_result.scalars().first()
                if photo:
                    cover_photo_obj = PhotoResponseForContactProfile.model_validate(photo)

            enhanced_albums.append(
                LinkedAlbumResponse(
                    id=album.id,
                    name=album.name,
                    description=album.description,
                    cover_photo_id=album.cover_photo_id,
                    created_at=album.created_at,
                    total_photos=total_photos,
                    cover_photo=cover_photo_obj
                )
            )

    # Procesar eventos de agenda para incluir event_datetime_local calculado
    processed_agenda_events = []
    if profile.agenda_events:
        # Necesitamos la zona horaria del usuario para calcular event_datetime_local
        account = await db.get(Account, current_account.id)
        user_timezone = account.timezone if account and account.timezone else "UTC"

        for event in profile.agenda_events:
            event_dict = event.to_dict(user_timezone)
            processed_agenda_events.append(LinkedAgendaEventResponse(**event_dict))

    return LinkedObjectsResponse(
        notes=profile.notas,
        agenda_events=processed_agenda_events,
        tasks=profile.tasks,
        user_document_topics=profile.user_document_topics,
        albums=enhanced_albums,
        form_responses=profile.form_responses # Añadir las respuestas de formulario
    )

@router.post("/create-contact-profile", response_model=ContactProfileResponse)
async def create_contact_profile(
    profile_data: ContactProfileBase,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    new_profile = ContactProfile(**profile_data.model_dump(), account_id=current_account.id)
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    return new_profile

@router.post("/update-contact-profile/{profile_id}", response_model=ContactProfileResponse)
async def update_contact_profile(
    profile_id: uuid.UUID,
    profile_data: ContactProfileBase,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    profile = await db.get(ContactProfile, profile_id)
    if not profile or profile.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    
    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/delete-contact-profile")
async def delete_contact_profile(
    profile_id: uuid.UUID = Body(..., embed=True),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    profile = await db.get(ContactProfile, profile_id)
    if not profile or profile.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    await db.delete(profile)
    await db.commit()
    return {"message": "Perfil de contacto eliminado exitosamente."}