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

import asyncio
import logging
from typing import Any, Optional, List, Dict, Tuple
import uuid

from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

# Importaciones de la nueva estructura de la base de datos y sesión
from core.database import SessionLocal, Nota, Account
from utils.db_session import DBSession
from utils.embeddings import initialize_embeddings

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


async def add_note(account_id: str, title: Optional[str], content: str, category: Optional[str] = None, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Añade una nueva nota a la base de datos para una cuenta de usuario específica o un equipo. Añade los embedding de la nota

    Args:
        account_id: El ID universal (UUID en formato string) de la cuenta del usuario.
        content: El contenido principal de la nota.
        title: Un título opcional para la nota.
        category: Una categoría opcional para la nota.
        team_id: El ID del equipo (UUID en formato string) al que se asocia la nota, si aplica.

    Returns:
        Un diccionario con los datos de la nota.
    """
    logger.info(f"Añadiendo nueva nota para la cuenta {account_id} con título '{title}'")
    
    # Asignamos un valor por defecto si la categoría es None o vacía
    effective_category = category if category and category.strip() else "General"

    async with DBSession(SessionLocal) as db:
        # Generar el embedding de la nota
        embeddings_model = await initialize_embeddings()
        note_embedding = None
        if embeddings_model:
            try:
                note_embedding = await embeddings_model.aembed_query(content)
            except Exception as e:
                logger.error(f"Error generando embedding para la nota: {e}", exc_info=True)

        new_note = Nota(
            account_id=uuid.UUID(account_id),
            team_id=uuid.UUID(team_id) if team_id else None,
            title=title,
            content=content,
            category=effective_category, # Usamos el valor efectivo
            embedding=note_embedding # Guardar el embedding
        )
        db.add(new_note)
        await db.commit()
        await db.refresh(new_note)
        logger.info(f"Nota '{title}' añadida exitosamente con ID {new_note.id}.")
        
        note_dict = {
            "id": new_note.id,
            "title": new_note.title,
            "content": new_note.content,
            "category": new_note.category,
            "created_at": new_note.created_at.isoformat(),
            "team_id": str(new_note.team_id) if new_note.team_id else None,
            # No devolvemos el embedding, es muy grande
        }
        # Trigger the proactive knowledge linker in the background
        # Asegúrate de que proactive_knowledge_linker_trigger esté importado
        from tools.proactive_knowledge_linker_tool import proactive_knowledge_linker_trigger
        asyncio.create_task(proactive_knowledge_linker_trigger({
            'id': str(new_note.id),
            'account_id': account_id,
            'content': new_note.content,
            'title': new_note.title,
            'type': 'note',
            'category': new_note.category,
            'timestamp': new_note.created_at,
            'embedding': note_embedding # Pasa el embedding si ya lo tienes
        }))

        return note_dict


async def get_notes(account_id: str, category: Optional[str] = None, search_query: Optional[str] = None, team_id: Optional[str] = None) -> str:
    """
    Obtiene una lista de notas para una cuenta de usuario o un equipo, con filtros opcionales.

    Args:
        account_id: El ID universal (UUID en formato string) de la cuenta del usuario.
        category: Filtra las notas por una categoría específica.
        search_query: Busca un texto en el título o contenido de las notas.
        team_id: El ID del equipo (UUID en formato string) para filtrar notas del equipo, si aplica.

    Returns:
        Una cadena de texto formateada con la lista de notas o un mensaje indicando que no se encontraron.
    """
    logger.info(f"Consultando notas para la cuenta {account_id} (Categoría: {category}, Búsqueda: {search_query}).")
    async with DBSession(SessionLocal) as db:
        # Construye la consulta base, ordenando por fecha de creación descendente.
        stmt = select(Nota).where(Nota.account_id == uuid.UUID(account_id))
        if team_id:
            stmt = stmt.where(Nota.team_id == uuid.UUID(team_id))
            filter_descriptions = [f"equipo ID {team_id}"]
        else:
            stmt = stmt.where(Nota.team_id.is_(None))
            filter_descriptions = []
        stmt = stmt.order_by(Nota.created_at.desc())
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


async def update_note(account_id: str, note_id: int, new_title: Optional[str] = None, new_content: Optional[str] = None, new_category: Optional[str] = None, team_id: Optional[str] = None) -> str:
    """
    Actualiza una nota existente para una cuenta de usuario o equipo. Regenera el embedding si el contenido cambia.

    Args:
        account_id: El ID universal de la cuenta.
        note_id: El ID de la nota a actualizar.
        new_content: El nuevo contenido (opcional).
        new_title: El nuevo título (opcional).
        new_category: La nueva categoría (opcional).
        team_id: El ID del equipo (UUID en formato string) para verificar la pertenencia, si aplica.

    Returns:
        Un mensaje de confirmación o de error.
    """
    logger.info(f"Intentando actualizar la nota {note_id} para la cuenta {account_id}.")
    async with DBSession(SessionLocal) as db:
        stmt = select(Nota).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        if team_id:
            stmt = stmt.where(Nota.team_id == uuid.UUID(team_id))
        else:
            stmt = stmt.where(Nota.team_id.is_(None))
        result = await db.execute(stmt)
        note_to_update = result.scalars().first()

        if not note_to_update:
            return f"No encontré ninguna nota con el ID {note_id} que te pertenezca para actualizar."

        content_changed = False
        if new_title is not None:
            note_to_update.title = new_title
        if new_content is not None:
            if note_to_update.content != new_content: # Check if content actually changed
                note_to_update.content = new_content
                content_changed = True
        if new_category is not None:
            note_to_update.category = new_category

        # Regenerar embedding si el contenido ha cambiado
        if content_changed:
            embeddings_model = await initialize_embeddings()
            if embeddings_model:
                try:
                    note_to_update.embedding = await embeddings_model.aembed_query(note_to_update.content)
                except Exception as e:
                    # Añadimos un log más específico para depurar
                    logger.error(f"Error al actualizar embedding para la nota {note_id} de la cuenta {account_id}: {e}", exc_info=True)
                    # Re-lanzamos la excepción para que FastAPI la capture como un 500 claro
                    raise

        await db.commit()
        logger.info(f"Nota {note_id} actualizada exitosamente para la cuenta {account_id}.")
        return f"¡Nota con ID {note_id} actualizada correctamente!"


async def delete_note(account_id: str, note_id: int, team_id: Optional[str] = None) -> str:
    """
    Elimina una nota existente de una cuenta de usuario o equipo.

    Args:
        account_id: El ID universal de la cuenta.
        note_id: El ID de la nota a eliminar.
        team_id: El ID del equipo (UUID en formato string) para verificar la pertenencia, si aplica.

    Returns:
        Un mensaje de confirmación o de error.
    """
    logger.info(f"Intentando eliminar la nota {note_id} para la cuenta {account_id}.")
    async with DBSession(SessionLocal) as db:
        # Busca la nota asegurándose de que pertenezca a la cuenta correcta y al equipo (si aplica) antes de eliminarla.
        stmt = select(Nota).where(Nota.id == note_id, Nota.account_id == uuid.UUID(account_id))
        if team_id:
            stmt = stmt.where(Nota.team_id == uuid.UUID(team_id))
        else:
            stmt = stmt.where(Nota.team_id.is_(None))
        result = await db.execute(stmt)
        note_to_delete = result.scalars().first()
        
        if not note_to_delete:
            return f"No encontré ninguna nota con el ID {note_id} que te pertenezca para eliminar."
            
        await db.delete(note_to_delete)
        await db.commit()
        logger.info(f"Nota {note_id} eliminada exitosamente para la cuenta {account_id}.")
        return f"¡Nota con ID {note_id} eliminada!"

async def get_notes_as_dicts(account_id: str, search_query: Optional[str] = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Recupera todas las notas de un usuario y las devuelve como una lista de diccionarios.
    Diseñada para ser usada por endpoints de API para interfaces web.
    Incluye notas compartidas con equipos.
    """
    logger.info(f"Obteniendo notas como diccionarios para la cuenta {account_id} (Búsqueda: {search_query}).")
    async with DBSession(SessionLocal) as db:
        stmt = select(Nota).where(Nota.account_id == uuid.UUID(account_id))
        if team_id:
            stmt = stmt.where(Nota.team_id == uuid.UUID(team_id))
        stmt = stmt.order_by(Nota.created_at.desc())
        
        if search_query:
            stmt = stmt.where(Nota.title.ilike(f"%{search_query}%") | Nota.content.ilike(f"%{search_query}%"))

        result = await db.execute(stmt)
        notes = result.scalars().all()
        
        # Convertimos cada objeto Nota a un diccionario
        return [
            {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "category": note.category,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
                "team_id": str(note.team_id) if note.team_id else None,
                "team_shared": bool(note.team_id)
            }
            for note in notes
        ]
