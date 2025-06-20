# telegram_bot/notes_manager.py

"""
Gestor de Lógica de Negocio para las Notas.

Este módulo encapsula toda la lógica para interactuar con la tabla `notas` en la
base de datos. Proporciona funciones asíncronas para realizar operaciones CRUD
(Crear, Leer, Actualizar, Eliminar) sobre las notas de un usuario.

En línea con la nueva arquitectura universal, todas las funciones aquí han sido
refactorizadas para operar utilizando el `account_id` (UUID) como el identificador
principal del usuario. Esto asegura que la gestión de notas sea consistente
a través de cualquier plataforma desde la que el usuario interactúe.

Las funciones de este módulo son llamadas directamente por las herramientas de
LangChain (`add_note_tool`, `get_notes_tool`, etc.), que a su vez son invocadas
por el agente de IA.
"""

import logging
from typing import Optional, List, Dict, Tuple
import uuid

from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

# Importaciones de la nueva estructura de la base de datos y sesión
from core.database import SessionLocal, Nota, Account
from utils.db_session import DBSession

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


async def add_note(account_id: str, content: str, title: Optional[str] = None, category: Optional[str] = None) -> str:
    """
    Añade una nueva nota a la base de datos para una cuenta de usuario específica.

    Args:
        account_id: El ID universal (UUID en formato string) de la cuenta del usuario.
        content: El contenido principal de la nota.
        title: Un título opcional para la nota.
        category: Una categoría opcional para la nota.

    Returns:
        Un mensaje de confirmación para el usuario.
    """
    logger.info(f"Añadiendo nota para la cuenta {account_id} con título: '{title or 'Sin título'}'.")
    async with DBSession(SessionLocal) as db:
        new_note = Nota(
            account_id=uuid.UUID(account_id),  # Convierte el string del account_id a un objeto UUID
            title=title,
            content=content,
            category=category or "General"  # Asigna una categoría por defecto si no se proporciona
        )
        db.add(new_note)
        await db.commit()
        await db.refresh(new_note)
        logger.info(f"Nota {new_note.id} creada exitosamente para la cuenta {account_id}.")
        return f"¡Nota guardada! (ID: {new_note.id}, Título: {title or 'Sin título'}, Categoría: {new_note.category})"


async def get_notes(account_id: str, category: Optional[str] = None, search_query: Optional[str] = None) -> str:
    """
    Obtiene una lista de notas para una cuenta de usuario, con filtros opcionales.

    Args:
        account_id: El ID universal (UUID en formato string) de la cuenta del usuario.
        category: Filtra las notas por una categoría específica.
        search_query: Busca un texto en el título o contenido de las notas.

    Returns:
        Una cadena de texto formateada con la lista de notas o un mensaje indicando que no se encontraron.
    """
    logger.info(f"Consultando notas para la cuenta {account_id} (Categoría: {category}, Búsqueda: {search_query}).")
    async with DBSession(SessionLocal) as db:
        # Construye la consulta base, ordenando por fecha de creación descendente.
        stmt = select(Nota).where(Nota.account_id == uuid.UUID(account_id)).order_by(Nota.created_at.desc())
        
        filter_descriptions = []
        if category:
            stmt = stmt.where(Nota.category.ilike(f"%{category}%"))
            filter_descriptions.append(f"categoría '{category}'")
        if search_query:
            # Busca tanto en el título como en el contenido, insensible a mayúsculas/minúsculas.
            stmt = stmt.where(Nota.title.ilike(f"%{search_query}%") | Nota.content.ilike(f"%{search_query}%"))
            filter_descriptions.append(f"búsqueda '{search_query}'")

        result = await db.execute(stmt)
        notes = result.scalars().all()

        if not notes:
            if filter_descriptions:
                return f"No encontré ninguna nota que coincida con tu filtro ({' y '.join(filter_descriptions)})."
            return "No tienes ninguna nota guardada todavía."

        # Formatear la respuesta para el usuario.
        response_lines = ["Aquí están tus notas:"]
        for note in notes:
            title = f"<b>{note.title}</b>" if note.title else "Nota sin título"
            response_lines.append(f"\n- <b>ID: {note.id}</b> | {title} (Categoría: {note.category})\n  <i>{note.content[:100]}...</i>")
        
        return "\n".join(response_lines)


async def update_note(account_id: str, note_id: int, new_content: Optional[str] = None, new_title: Optional[str] = None, new_category: Optional[str] = None) -> str:
    """
    Actualiza una nota existente para una cuenta de usuario.

    Args:
        account_id: El ID universal de la cuenta.
        note_id: El ID de la nota a actualizar.
        new_content: El nuevo contenido (opcional).
        new_title: El nuevo título (opcional).
        new_category: La nueva categoría (opcional).

    Returns:
        Un mensaje de confirmación o de error.
    """
    if not any([new_content, new_title, new_category]):
        return "Debes proporcionar al menos un campo para actualizar (contenido, título o categoría)."

    logger.info(f"Actualizando nota {note_id} para la cuenta {account_id}.")
    async with DBSession(SessionLocal) as db:
        # Busca la nota asegurándose de que pertenezca a la cuenta correcta.
        stmt = select(Nota).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        result = await db.execute(stmt)
        note_to_update = result.scalars().first()

        if not note_to_update:
            return f"No encontré ninguna nota con el ID {note_id} que te pertenezca."
        
        # Actualiza solo los campos que se proporcionaron.
        if new_content is not None: note_to_update.content = new_content
        if new_title is not None: note_to_update.title = new_title
        if new_category is not None: note_to_update.category = new_category
        
        await db.commit()
        logger.info(f"Nota {note_id} actualizada exitosamente para la cuenta {account_id}.")
        return f"¡Nota con ID {note_id} actualizada correctamente!"


async def delete_note(account_id: str, note_id: int) -> str:
    """
    Elimina una nota existente de una cuenta de usuario.

    Args:
        account_id: El ID universal de la cuenta.
        note_id: El ID de la nota a eliminar.

    Returns:
        Un mensaje de confirmación o de error.
    """
    logger.info(f"Intentando eliminar la nota {note_id} para la cuenta {account_id}.")
    async with DBSession(SessionLocal) as db:
        # Busca la nota asegurándose de que pertenezca a la cuenta correcta antes de eliminarla.
        stmt = select(Nota).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        result = await db.execute(stmt)
        note_to_delete = result.scalars().first()
        
        if not note_to_delete:
            return f"No encontré ninguna nota con el ID {note_id} que te pertenezca para eliminar."
            
        await db.delete(note_to_delete)
        await db.commit()
        logger.info(f"Nota {note_id} eliminada exitosamente para la cuenta {account_id}.")
        return f"¡Nota con ID {note_id} eliminada!"
