
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field
from datetime import datetime # Importar datetime

from core.database import get_db_session, ContactProfile, Account, Nota, AgendaEvent, Task, UserDocumentTopic
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
    created_at: datetime # Cambiado a datetime
    updated_at: datetime # Cambiado a datetime

    class Config:
        from_attributes = True

# Pydantic models para los objetos vinculados (simplificados para este endpoint)
class LinkedNoteResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class LinkedAgendaEventResponse(BaseModel):
    id: int
    description: str
    event_datetime_utc: datetime

    class Config:
        from_attributes = True

class LinkedTaskResponse(BaseModel):
    id: uuid.UUID
    description: str
    is_completed: bool
    due_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class LinkedUserDocumentTopicResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class LinkedObjectsResponse(BaseModel):
    notes: List[LinkedNoteResponse]
    agenda_events: List[LinkedAgendaEventResponse]
    tasks: List[LinkedTaskResponse]
    user_document_topics: List[LinkedUserDocumentTopicResponse]

@router.get("/contact-profiles", response_model=List[ContactProfileResponse])
async def get_all_contact_profiles(
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todos los perfiles de contacto asociados a la cuenta del usuario actual.
    """
    try:
        result = await db.execute(
            select(ContactProfile)
            .where(ContactProfile.account_id == current_account.id)
            .order_by(ContactProfile.created_at.desc())
        )
        contact_profiles = result.scalars().all()
        return contact_profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar perfiles de contacto: {e}")

@router.post("/list-contact-profiles", response_model=List[ContactProfileResponse])
async def list_contact_profiles(
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todos los perfiles de contacto asociados a la cuenta del usuario actual.
    """
    try:
        result = await db.execute(
            select(ContactProfile)
            .where(ContactProfile.account_id == current_account.id)
            .order_by(ContactProfile.created_at.desc())
        )
        contact_profiles = result.scalars().all()
        return contact_profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar perfiles de contacto: {e}")

@router.get("/contact-profiles/{profile_id}", response_model=ContactProfileResponse)
async def get_contact_profile(
    profile_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene los detalles de un perfil de contacto específico.
    """
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
    Obtiene todas las notas, eventos, tareas y colecciones de documentos vinculadas a un perfil de contacto.
    """
    profile = await db.execute(
        select(ContactProfile)
        .options(
            selectinload(ContactProfile.notas),
            selectinload(ContactProfile.agenda_events),
            selectinload(ContactProfile.tasks),
            selectinload(ContactProfile.user_document_topics)
        )
        .where(ContactProfile.id == profile_id, ContactProfile.account_id == current_account.id)
    )
    profile = profile.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    return LinkedObjectsResponse(
        notes=profile.notas,
        agenda_events=profile.agenda_events,
        tasks=profile.tasks,
        user_document_topics=profile.user_document_topics
    )

@router.post("/create-contact-profile", response_model=ContactProfileResponse)
async def create_contact_profile(
    profile_data: ContactProfileBase,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Crea un nuevo perfil de contacto para la cuenta del usuario actual.
    """
    try:
        print(f"DEBUG: Datos recibidos para crear perfil: {profile_data.model_dump_json()}")
        new_profile = ContactProfile(
            account_id=current_account.id,
            name=profile_data.name,
            email=profile_data.email,
            phone=profile_data.phone,
            tags=profile_data.tags, # Añadir tags
            category=profile_data.category, # Añadir category
            custom_fields=profile_data.custom_fields
        )
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return new_profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear perfil de contacto: {e}")

@router.post("/update-contact-profile/{profile_id}", response_model=ContactProfileResponse)
async def update_contact_profile(
    profile_id: uuid.UUID,
    profile_data: ContactProfileBase,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza un perfil de contacto existente para la cuenta del usuario actual.
    """
    print("DEBUG: Función update_contact_profile invocada.") # <-- NUEVO PRINT
    try:
        profile = await db.get(ContactProfile, profile_id)

        if not profile or profile.account_id != current_account.id:
            raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

        print(f"DEBUG: profile_data recibida: {profile_data.model_dump_json()}")
        print(f"DEBUG: profile_data para actualizar (exclude_unset): {profile_data.model_dump(exclude_unset=True)}")

        # Actualizar campos individualmente para depuración
        if profile_data.name is not None: profile.name = profile_data.name
        if profile_data.email is not None: profile.email = profile_data.email
        if profile_data.phone is not None: profile.phone = profile_data.phone
        if profile_data.tags is not None: profile.tags = profile_data.tags
        if profile_data.category is not None: profile.category = profile_data.category
        if profile_data.custom_fields is not None: profile.custom_fields = profile_data.custom_fields

        # for field, value in profile_data.model_dump(exclude_unset=True).items():
        #     print(f"DEBUG: Intentando actualizar campo '{field}' con valor '{value}' (tipo: {type(value)})")
        #     setattr(profile, field, value)
        
        await db.commit()
        await db.refresh(profile)
        return profile
    except HTTPException as http_exc:
        print(f"ERROR: HTTPException capturada: {http_exc.detail}") # Loguear el detalle de HTTPException
        raise http_exc
    except Exception as e:
        print(f"ERROR: Excepción inesperada al actualizar perfil: {e}")
        import traceback
        traceback.print_exc() # Esto imprimirá el stack trace completo
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al actualizar perfil: {e}")

@router.post("/delete-contact-profile")
async def delete_contact_profile(
    profile_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina un perfil de contacto existente para la cuenta del usuario actual.
    """
    try:
        profile = await db.get(ContactProfile, profile_id)

        if not profile or profile.account_id != current_account.id:
            raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

        await db.delete(profile)
        await db.commit()
        return {"message": "Perfil de contacto eliminado exitosamente."}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar perfil de contacto: {e}")
