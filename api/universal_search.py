import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession # Importar AsyncSession
from core.database import get_db_session # Cambiado de get_db a get_db_session
from core.notes_manager import NotesManager # Importar NotesManager
from core.agenda_manager import get_events_as_dicts # Importar get_events_as_dicts
from api.chat import get_threads, search_chat_messages # Importar get_threads y la nueva función search_chat_messages
from core.memory_manager import _run_fts_search # Importar para búsqueda de conocimientos

router = APIRouter()

@router.get("/universal_search")
async def universal_search(
    query: str,
    user_id: str = Query(..., description="ID del usuario para filtrar los resultados"),
    workspace_id: Optional[str] = Query(None, description="ID del espacio de trabajo para filtrar los resultados. Puede ser 'None' o una cadena vacía para buscar sin filtro de espacio de trabajo."),
    search_types: Optional[List[str]] = Query(None, description="Tipos de contenido a buscar (e.g., chat, note, knowledge, agenda)"),
    db: AsyncSession = Depends(get_db_session)
):
    parsed_user_id: uuid.UUID
    parsed_workspace_id: Optional[uuid.UUID] = None

    try:
        parsed_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"El ID de usuario '{user_id}' no es un UUID válido.")

    # Manejar workspace_id: si es 'None' (cadena), una cadena vacía, o un UUID válido
    if workspace_id is not None and workspace_id.lower() != 'none' and workspace_id != '':
        try:
            parsed_workspace_id = uuid.UUID(workspace_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"El ID de workspace '{workspace_id}' no es un UUID válido.")
    # Si workspace_id es None, 'none' (cadena) o una cadena vacía, parsed_workspace_id permanece None, lo cual es el comportamiento deseado.

    results = []
    
    try:
        # Búsqueda en Notas
        if not search_types or "note" in search_types:
            try:
                notes_manager = NotesManager(db)
                _, notes_data = await notes_manager.get_notes_as_dicts(
                    account_id=str(parsed_user_id), 
                    workspace_id=str(parsed_workspace_id) if parsed_workspace_id else None, 
                    search_query=query
                )
                for note in notes_data:
                    results.append({
                        "type": "note",
                        "id": str(note["id"]),
                        "title": note["title"],
                        "content": note["content"],
                        "created_at": note["created_at"]
                    })
            except HTTPException as e:
                print(f"Error en búsqueda de Notas: {e.detail}")
            except Exception as e:
                print(f"Error inesperado en búsqueda de Notas: {e}")

        # Búsqueda en Agenda
        if not search_types or "agenda" in search_types:
            try:
                events_data = await get_events_as_dicts(account_id=str(parsed_user_id), include_past=True)
                for event in events_data:
                    if query.lower() in event["summary"].lower() or (event["description"] and query.lower() in event["description"].lower()):
                        results.append({
                            "type": "agenda",
                            "id": str(event["id"]),
                            "title": event["summary"],
                            "description": event["description"],
                            "start_time": event["event_datetime_local"],
                        })
            except HTTPException as e:
                print(f"Error en búsqueda de Agenda: {e.detail}")
            except Exception as e:
                print(f"Error inesperado en búsqueda de Agenda: {e}")

        # Búsqueda en Chats
        if not search_types or "chat" in search_types:
            try:
                chat_results = await search_chat_messages(
                    query=query,
                    account_id=str(parsed_user_id),
                    db=db,
                    workspace_id=str(parsed_workspace_id) if parsed_workspace_id else None
                )
                for result in chat_results:
                    # El tipo ya viene en el resultado de la función
                    results.append(result)
            except HTTPException as e:
                print(f"Error en búsqueda de Chats: {e.detail}")
            except Exception as e:
                print(f"Error inesperado en búsqueda de Chats: {e}")

        # Búsqueda en Conocimientos
        if not search_types or "knowledge" in search_types:
            try:
                docs = await _run_fts_search(query=query, account_id=str(parsed_user_id), k=10, content_types=["user_documents"])
                for doc in docs:
                    results.append({
                        "type": "knowledge",
                        "id": doc.metadata.get("document_id"),
                        "title": doc.metadata.get("title", doc.metadata.get("file_name")),
                        "content": doc.page_content,
                        "topic": doc.metadata.get("topic"),
                        "file_name": doc.metadata.get("file_name"),
                    })
            except HTTPException as e:
                print(f"Error en búsqueda de Conocimientos: {e.detail}")
            except Exception as e:
                print(f"Error inesperado en búsqueda de Conocimientos: {e}")
        return results

    except HTTPException as http_exc:
        # Re-lanzar la excepción HTTP para que FastAPI la maneje
        raise http_exc
    except Exception as e:
        # Loggear el error y devolver una respuesta genérica
        # Considera usar un logger más robusto en producción
        print(f"Error inesperado en la búsqueda universal: {e}")
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado durante la búsqueda.")
