# tools/contact_profile_tool.py

import logging
import asyncio
import uuid
from typing import Type, Any, Optional, List, Dict, Union

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select, update # Added update
from sqlalchemy.orm import selectinload

from core.database import SessionLocal, ContactProfile, Nota, AgendaEvent, Task # Added Note, Event, Task
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

# --- Schemas de Entrada para acciones específicas (internos) ---

class _GetContactProfileInput(BaseModel):
    name: str = Field(description="El nombre completo del perfil de contacto a buscar.")

class _ListContactProfilesInput(BaseModel):
    query: Optional[str] = Field(None, description="Una consulta de búsqueda para filtrar perfiles por nombre, email o teléfono.")
    tags: Optional[List[str]] = Field(None, description="Una lista de etiquetas para filtrar perfiles.")
    category: Optional[str] = Field(None, description="Una categoría para filtrar perfiles.")

class _CreateContactProfileInput(BaseModel):
    name: str = Field(description="El nombre del nuevo perfil de contacto.")
    email: Optional[str] = Field(None, description="El email del contacto.")
    phone: Optional[str] = Field(None, description="El número de teléfono del contacto.")
    tags: Optional[List[str]] = Field(None, description="Una lista de etiquetas para el contacto.")
    category: Optional[str] = Field(None, description="Una categoría para el contacto.")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Campos personalizados para el contacto en formato JSON.")

# --- Esquema de Entrada Unificado para la Herramienta ---

class ContactProfileToolInput(BaseModel):
    action: str = Field(description="La acción a realizar: 'get_profile', 'list_profiles', 'create_profile', 'update_profile', 'link_to_note', o 'link_to_event_or_task'.")
    # Parámetros opcionales para cada acción
    name: Optional[str] = Field(None, description="Nombre del perfil (para get_profile, create_profile, update_profile, link_to_note, link_to_event_or_task).")
    query: Optional[str] = Field(None, description="Consulta de búsqueda (para list_profiles).")
    tags: Optional[List[str]] = Field(None, description="Lista de etiquetas (para list_profiles, create_profile, update_profile).")
    category: Optional[str] = Field(None, description="Categoría (para list_profiles, create_profile, update_profile).")
    email: Optional[str] = Field(None, description="Email del contacto (para create_profile, update_profile).")
    phone: Optional[str] = Field(None, description="Teléfono del contacto (para create_profile, update_profile).")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Campos personalizados para el contacto en formato JSON (para create_profile, update_profile).")
    
    # Nuevos parámetros para vinculación
    note_id: Optional[int] = Field(None, description="ID de la nota a vincular (para link_to_note).")
    event_id: Optional[str] = Field(None, description="ID del evento a vincular (para link_to_event_or_task).")
    task_id: Optional[str] = Field(None, description="ID de la tarea a vincular (para link_to_event_or_task).")

# --- Clase de Herramienta ---

class ContactProfileTool(BaseTool):
    name: str = "contact_profile_manager"
    description: str = (
        "Herramienta para gestionar perfiles de contacto. Permite ver perfiles individuales por nombre, "
        "listar todos los perfiles (con filtros opcionales), crear nuevos perfiles, "
        "actualizar perfiles existentes, vincular perfiles a notas, y vincular perfiles a eventos o tareas. "
        "Usa el parámetro 'action' para especificar la operación (get_profile, list_profiles, create_profile, update_profile, link_to_note, link_to_event_or_task) "
        "y proporciona los parámetros relevantes para cada acción."
    )
    args_schema: Type[BaseModel] = ContactProfileToolInput # Usamos el esquema unificado
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")
    telegram_id: Optional[str] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación, inyectado automáticamente.")

    async def _arun(self, action: str, **kwargs: Any) -> str:
        """
        Ejecuta la acción especificada para la gestión de perfiles de contacto.
        """
        if not self.account_id:
            return "Error: Se requiere el ID de la cuenta para gestionar perfiles de contacto."

        async with DBSession(SessionLocal) as db:
            if action == "get_profile":
                name = kwargs.get("name")
                if not name:
                    return "Error: Se requiere el nombre del perfil para buscar."
                
                profile = await db.execute(
                    select(ContactProfile).where(
                        ContactProfile.account_id == uuid.UUID(self.account_id),
                        ContactProfile.name == name
                    )
                )
                profile = profile.scalars().first()
                
                if profile:
                    return f"Perfil encontrado: Nombre: {profile.name}, Email: {profile.email}, Teléfono: {profile.phone}, Categoría: {profile.category}, Etiquetas: {profile.tags}, Campos Personalizados: {profile.custom_fields}"
                else:
                    return f"No se encontró ningún perfil con el nombre '{name}'."

            elif action == "list_profiles":
                query = kwargs.get("query")
                tags = kwargs.get("tags")
                category = kwargs.get("category")

                stmt = select(ContactProfile).where(
                    ContactProfile.account_id == uuid.UUID(self.account_id)
                )
                if query:
                    stmt = stmt.where(
                        (ContactProfile.name.ilike(f"%{query}%")) |
                        (ContactProfile.email.ilike(f"%{query}%")) |
                        (ContactProfile.phone.ilike(f"%{query}%"))
                    )
                if tags:
                    # Asumiendo que tags es un ARRAY(String) en PostgreSQL
                    stmt = stmt.where(ContactProfile.tags.overlap(tags))
                if category:
                    stmt = stmt.where(ContactProfile.category == category)
                
                profiles = await db.execute(stmt)
                profiles = profiles.scalars().all()

                if profiles:
                    response = "Perfiles encontrados:\n"
                    for profile in profiles:
                        response += f'- Nombre: {profile.name}, Email: {profile.email}, Teléfono: {profile.phone}, Categoría: {profile.category}, Etiquetas: {profile.tags}\n'
                    return response
                else:
                    return "No se encontraron perfiles que coincidan con los criterios de búsqueda."

            elif action == "create_profile":
                name = kwargs.get("name")
                email = kwargs.get("email")
                phone = kwargs.get("phone")
                tags = kwargs.get("tags")
                category = kwargs.get("category")
                custom_fields = kwargs.get("custom_fields")

                if not name:
                    return "Error: Se requiere el nombre para crear un perfil."
                
                new_profile = ContactProfile(
                    id=uuid.uuid4(),
                    account_id=uuid.UUID(self.account_id),
                    name=name,
                    email=email,
                    phone=phone,
                    tags=tags,
                    category=category,
                    custom_fields=custom_fields
                )
                db.add(new_profile)
                await db.commit()
                await db.refresh(new_profile)
                return f"Perfil '{new_profile.name}' creado exitosamente con ID: {new_profile.id}"

            elif action == "update_profile":
                name = kwargs.get("name")
                if not name:
                    return "Error: Se requiere el nombre del perfil para actualizar."

                profile = await db.scalar(
                    select(ContactProfile).where(
                        ContactProfile.account_id == uuid.UUID(self.account_id),
                        ContactProfile.name == name
                    )
                )
                if not profile:
                    return f"No se encontró ningún perfil con el nombre '{name}' para actualizar."

                update_data = {k: v for k, v in kwargs.items() if k not in ["action", "name"] and v is not None}
                if not update_data:
                    return "No se proporcionaron datos para actualizar el perfil."

                for key, value in update_data.items():
                    setattr(profile, key, value)
                
                await db.commit()
                await db.refresh(profile)
                return f"Perfil '{profile.name}' actualizado exitosamente."

            elif action == "link_to_note":
                name = kwargs.get("name")
                note_id = kwargs.get("note_id")
                if not name or not note_id:
                    return "Error: Se requiere el nombre del perfil y el ID de la nota para vincular."

                profile = await db.scalar(
                    select(ContactProfile).where(
                        ContactProfile.account_id == uuid.UUID(self.account_id),
                        ContactProfile.name == name
                    )
                )
                if not profile:
                    return f"No se encontró ningún perfil con el nombre '{name}'."

                note = await db.scalar(
                    select(Nota).options(selectinload(Nota.contact_profiles)).where(
                        Nota.id == note_id,
                        Nota.account_id == uuid.UUID(self.account_id)
                    )
                )
                if not note:
                    return f"No se encontró ninguna nota con el ID '{note_id}'."
                
                # Asumiendo que Nota tiene una relación many-to-many con ContactProfile
                # o un campo contact_profile_id si es one-to-many
                if profile not in note.contact_profiles:
                    note.contact_profiles.append(profile)
                    await db.commit()
                    return f"Perfil '{name}' vinculado exitosamente a la nota '{note_id}'."
                else:
                    return f"El perfil '{name}' ya está vinculado a la nota '{note_id}'."

            elif action == "link_to_event_or_task":
                name = kwargs.get("name")
                event_id = kwargs.get("event_id")
                task_id = kwargs.get("task_id")

                if not name:
                    return "Error: Se requiere el nombre del perfil para vincular a un evento o tarea."
                if not event_id and not task_id:
                    return "Error: Se requiere el ID del evento o el ID de la tarea para vincular."
                if event_id and task_id:
                    return "Error: Solo se puede vincular a un evento O a una tarea, no a ambos."

                profile = await db.scalar(
                    select(ContactProfile).where(
                        ContactProfile.account_id == uuid.UUID(self.account_id),
                        ContactProfile.name == name
                    )
                )
                if not profile:
                    return f"No se encontró ningún perfil con el nombre '{name}'."

                if event_id:
                    try:
                        event_id_int = int(event_id)
                    except ValueError:
                        return f"Error: El ID del evento '{event_id}' no es un número válido."

                    event = await db.scalar(
                        select(AgendaEvent).options(selectinload(AgendaEvent.contact_profiles)).where(
                            AgendaEvent.id == event_id_int,
                            AgendaEvent.account_id == uuid.UUID(self.account_id)
                        )
                    )
                    if not event:
                        return f"No se encontró ningún evento con el ID '{event_id}'."
                    
                    if profile not in event.contact_profiles:
                        event.contact_profiles.append(profile)
                        await db.commit()
                        return f"Perfil '{name}' vinculado exitosamente al evento '{event_id}'."
                    else:
                        return f"El perfil '{name}' ya está vinculado al evento '{event_id}'."

                elif task_id:
                    task = await db.scalar(
                        select(Task).options(selectinload(Task.contact_profiles)).where(
                            Task.id == uuid.UUID(task_id),
                            Task.account_id == uuid.UUID(self.account_id)
                        )
                    )
                    if not task:
                        return f"No se encontró ninguna tarea con el ID '{task_id}'."
                    
                    if profile not in task.contact_profiles:
                        task.contact_profiles.append(profile)
                        await db.commit()
                        return f"Perfil '{name}' vinculado exitosamente a la tarea '{task_id}'."
                    else:
                        return f"El perfil '{name}' ya está vinculado a la tarea '{task_id}'."

            else:
                return "Error: Acción no válida. Las acciones soportadas son 'get_profile', 'list_profiles', 'create_profile', 'update_profile', 'link_to_note', 'link_to_event_or_task'."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("contact_profile_manager no soporta ejecución síncrona.")