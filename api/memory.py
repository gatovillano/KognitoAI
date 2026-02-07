# api/memory.py

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from core.memory_manager import get_relevant_memories, add_memory_to_vector_db
from utils.security import get_current_account_id
from core.dependencies import get_db_session

import logging # Importar logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import datetime # Importar datetime

from core.memory_manager import get_relevant_memories, add_memory_to_vector_db, get_all_user_memories
from utils.security import get_current_account_id
from core.dependencies import get_db_session

router = APIRouter()
logger = logging.getLogger(__name__) # Inicializar logger

class MemoryResponse(BaseModel):
    id: str
    title: Optional[str]
    content: str
    type: str
    created_at: str
    updated_at: str
    user_id: str
    
class AddMemoryRequest(BaseModel):
    title: Optional[str] = None
    content: str
    type: str = "general_memory"
    
@router.get("/memories", response_model=List[MemoryResponse], summary="Obtener memorias vectoriales del usuario")
async def get_user_vector_memories(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Recupera las memorias vectoriales del usuario, filtradas por content_type
    'user_memory_proactive_llm' y 'user_memories'.
    """
    logger.info(f"Solicitud GET /api/memories recibida para el usuario: {current_account_id}") # Log para depuración
    
    # Llamar a get_all_user_memories en lugar de get_relevant_memories
    docs = await get_all_user_memories(
        account_id=current_account_id,
        content_types=["user_memory_proactive_llm", "user_memories", "general_memory", "user_memory"],
        limit=100
    )
    
    memories: List[MemoryResponse] = []
    for doc in docs:
        # Extraer información relevante de los metadatos de LCDocument
        # Asumiendo que el 'id' puede venir de 'document_id' o generarse si no existe
        memory_id = doc.metadata.get("document_id") or str(uuid.uuid4())
        
        # El 'title' podría estar en cmetadata->>'title' o file_name
        title = doc.metadata.get("title") or doc.metadata.get("file_name", f"Memoria {memory_id[:8]}")
        
        memories.append(
            MemoryResponse(
                id=memory_id,
                title=title,
                content=doc.page_content,
                type=doc.metadata.get("type", "general_memory"),
                created_at=doc.metadata.get("created_at", datetime.datetime.now().isoformat()),
                updated_at=doc.metadata.get("updated_at", datetime.datetime.now().isoformat()),
                user_id=current_account_id,
            )
        )
    logger.info(f"Devolviendo {len(memories)} memorias para el usuario: {current_account_id}") # Log para depuración
    return memories

@router.post("/memories", summary="Añadir una nueva memoria vectorial")
async def add_user_vector_memory(
    request: AddMemoryRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Añade una nueva memoria vectorial a la base de datos para el usuario actual.
    """
    logger.info(f"Solicitud POST /api/memories recibida para el usuario: {current_account_id}, título: {request.title}") # Log para depuración
    try:
        await add_memory_to_vector_db(
            account_id=current_account_id,
            content=request.content,
            type=request.type,
            topic=request.title # Usamos el título como topic para fácil referencia
        )
        logger.info(f"Memoria añadida exitosamente para el usuario: {current_account_id}") # Log para depuración
        return {"message": "Memoria añadida exitosamente."}
    except Exception as e:
        logger.error(f"Error al añadir memoria para el usuario {current_account_id}: {e}", exc_info=True) # Log de error
        raise HTTPException(status_code=500, detail=f"Error al añadir memoria: {str(e)}")
