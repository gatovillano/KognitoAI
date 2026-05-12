# En api/collections.py

from fastapi import APIRouter, HTTPException, Depends, status, Query, Path
from typing import List, Optional
from pydantic import BaseModel
import uuid
import logging

from core.database import SessionLocal
from core.dependencies import get_db_session
from utils.security import get_current_account_id
from core.memory_manager import list_user_collections, create_empty_collection
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# --- Modelos Pydantic para Colecciones ---
class CollectionResponse(BaseModel):
    id: Optional[str] = None
    topic: Optional[str] = None
    name: Optional[str] = None
    parent_id: Optional[str] = None
    position: Optional[int] = None
    item_type: Optional[str] = None
    document_count: int = 0
    description: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_color: Optional[str] = None
    has_knowledge_graph: Optional[bool] = None
    subcollection_count: int = 0

class CollectionCreateRequest(BaseModel):
    topic: str
    description: Optional[str] = None
    workspaceId: Optional[str] = None
    parent_id: Optional[str] = None
    item_type: Optional[str] = None

from urllib.parse import unquote

def decoded_topic(topic: str = Path(..., description="El tema de la colección, codificado en la URL")) -> str:
    return unquote(topic)

@router.get("/collections/{topic}/details", summary="Obtener detalles de una colección por nombre")
async def get_collection_details_by_name(
    current_account_id: str = Depends(get_current_account_id),
    topic: str = Depends(decoded_topic),
    workspace_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene los detalles de una colección específica por su nombre, incluyendo los perfiles de contacto vinculados.
    """
    from utils.security import check_workspace_permission
    from core.memory_manager import get_user_document_topic_by_name

    # Verificar permisos de workspace si se proporciona
    if workspace_id:
        if not await check_workspace_permission(current_account_id, workspace_id, db, required_roles=["owner", "editor", "viewer"]):
            raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta colección.")

    collection_details = await get_user_document_topic_by_name(
        account_id=current_account_id,
        topic_name=topic,
        workspace_id=workspace_id,
    )
    if not collection_details:
        raise HTTPException(status_code=404, detail=f"Colección '{topic}' no encontrada o no autorizada.")
    return collection_details

# --- Endpoints para Colecciones ---
@router.get("/collections", response_model=List[CollectionResponse], summary="Listar colecciones del usuario")
async def list_collections(current_account_id: str = Depends(get_current_account_id), db: "AsyncSession" = Depends(get_db_session), workspace_id: Optional[str] = Query(None)):
    logger.info(f"API: list_collections - Listando colecciones para account_id: {current_account_id}, workspace_id recibido: {workspace_id}")
    try:
        collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
        logger.info(f"API: list_collections - Collections retrieved from memory_manager: {len(collections)} collections")
        return [CollectionResponse(
            id=c.get('id'),
            topic=c.get('topic') or c.get('name'),
            name=c.get('name') or c.get('topic') or "Sin nombre",
            parent_id=c.get('parent_id'),
            position=c.get('position'),
            item_type=c.get('item_type', 'collection'),
            document_count=c.get('document_count', 0),
            description=c.get('description'),
            workspace_id=c.get('workspace_id'),
            workspace_name=c.get('workspace_name'),
            workspace_color=c.get('workspace_color'),
            has_knowledge_graph=c.get('has_knowledge_graph', False),
            subcollection_count=c.get('subcollection_count', 0)
        ) for c in collections]
    except Exception as e:
        logger.error(f"API: list_collections - Error al listar colecciones para account_id: {current_account_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor al listar colecciones.")

@router.post("/collections", status_code=status.HTTP_201_CREATED, summary="Crear una nueva colección")
async def create_collection(request: CollectionCreateRequest, current_account_id: str = Depends(get_current_account_id), db: "AsyncSession" = Depends(get_db_session)):
    logger.info(f"API: create_collection - Petición para crear colección: {request.topic}, description: {request.description}, workspaceId: {request.workspaceId}, account: {current_account_id}")
    
    # Crear la colección usando create_empty_collection
    try:
        collection = await create_empty_collection(
            account_id=current_account_id,
            topic_name=request.topic,
            workspace_id=request.workspaceId,
            parent_id=request.parent_id,
            item_type=request.item_type
        )
        logger.info(f"API: create_collection - Colección '{request.topic}' creada y asociada al workspace {request.workspaceId if request.workspaceId else 'global'} con éxito.")
        return {"message": f"Colección '{request.topic}' creada y lista para ser usada en el workspace {request.workspaceId if request.workspaceId else 'global'}."}
    except Exception as e:
        logger.error(f"API: create_collection - Error al crear la colección '{request.topic}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"No se pudo crear la colección: {str(e)}")

# --- Modelo Pydantic para Actualizar Colección ---
class CollectionUpdateRequest(BaseModel):
    old_topic: str
    new_topic: Optional[str] = None
    new_description: Optional[str] = None
    workspace_id: Optional[str] = None
    parent_id: Optional[str] = None
    item_type: Optional[str] = None

@router.post("/update-collection", summary="Actualizar una colección existente")
async def update_collection_endpoint(
    request: CollectionUpdateRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza una colección existente (nombre, descripción, workspace_id).
    """
    logger.info(f"API: update_collection - Actualizando colección para account_id: {current_account_id}, old_topic: {request.old_topic}, new_topic: {request.new_topic}, new_description: {request.new_description}, workspace_id: {request.workspace_id}")
    
    try:
        # Importar la función de actualización
        from core.memory_manager import update_collection
        # Llamar a la función de actualización
        success = await update_collection(
            account_id=current_account_id,
            old_topic_name=request.old_topic,
            new_topic_name=request.new_topic,
            new_description=request.new_description,
            workspace_id=request.workspace_id,
            parent_id=request.parent_id,
            item_type=request.item_type
        )
        
        if not success:
            logger.error(f"API: update_collection - No se pudo actualizar la colección '{request.old_topic}' para el usuario {current_account_id}")
            raise HTTPException(status_code=400, detail="No se pudo actualizar la colección o no existe.")
        
        logger.info(f"API: update_collection - Colección '{request.old_topic}' actualizada exitosamente para el usuario {current_account_id}")
        return {"message": f"Colección '{request.old_topic}' actualizada exitosamente."}
        
    except HTTPException:
        # Re-lanzar las excepciones HTTP que ya están correctamente definidas
        raise
    except Exception as e:
        logger.error(f"API: update_collection - Error al actualizar la colección para account_id: {current_account_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor al actualizar la colección.")

class CollectionMoveRequest(BaseModel):
    topic: str
    new_parent_id: Optional[str] = None
    workspace_id: Optional[str] = None

@router.post("/collections/move", summary="Mover una colección a otro parent")
async def move_collection(request: CollectionMoveRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    from core.memory_manager import update_collection
    success = await update_collection(account_id=current_account_id, old_topic_name=request.topic, parent_id=request.new_parent_id, workspace_id=request.workspace_id)
    if not success:
        raise HTTPException(status_code=400, detail="No se pudo mover la colección.")
    return {"message":"Colección movida exitosamente."}

class CollectionRenameRequest(BaseModel):
    old_topic: str
    new_topic: str
    workspace_id: Optional[str] = None

@router.post("/collections/rename", summary="Renombrar una colección")
async def rename_collection(request: CollectionRenameRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)):
    from core.memory_manager import update_collection
    success = await update_collection(account_id=current_account_id, old_topic_name=request.old_topic, new_topic_name=request.new_topic, workspace_id=request.workspace_id)
    if not success:
        raise HTTPException(status_code=400, detail="No se pudo renombrar la colección.")
    return {"message":"Colección renombrada exitosamente."}

class CollectionShareRequest(BaseModel):
    workspace_id: str

@router.post("/collections/{topic}/share", summary="Compartir una colección con un workspace")
async def share_collection(
    request: CollectionShareRequest,
    topic: str = Depends(decoded_topic),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Permite compartir (asignar) una colección a un workspace específico.
    """
    logger.info(f"API: share_collection - Solicitud para compartir la colección '{topic}' con el workspace '{request.workspace_id}' por el usuario {current_account_id}")
    
    try:
        from core.memory_manager import update_collection
        
        success = await update_collection(
            account_id=current_account_id,
            old_topic_name=topic,
            workspace_id=request.workspace_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=f"No se pudo compartir la colección '{topic}'. Puede que no exista o que ya esté en el workspace.")
            
        return {"message": f"La colección '{topic}' ha sido compartida exitosamente con el workspace."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: share_collection - Error al compartir la colección '{topic}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor al compartir la colección.")


@router.delete("/collections/{topic}", summary="Eliminar una colección")
async def delete_collection_endpoint(
    topic: str = Depends(decoded_topic),
    current_account_id: str = Depends(get_current_account_id),
    workspace_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    from utils.security import check_workspace_permission
    from core.memory_manager import delete_collection

    # Verificar permisos si workspace especificado
    if workspace_id:
        if not await check_workspace_permission(current_account_id, workspace_id, db, required_roles=["owner", "editor"]):
            raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta colección en el workspace especificado.")

    try:
        success = await delete_collection(account_id=current_account_id, topic_name=topic, workspace_id=workspace_id)
        if not success:
            raise HTTPException(status_code=400, detail=f"No se pudo eliminar la colección '{topic}'.")
        return {"message": f"Colección '{topic}' eliminada correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: delete_collection - Error al eliminar la colección '{topic}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor al eliminar la colección.")


@router.get("/collections/children", response_model=List[CollectionResponse], summary="Listar subcolecciones de un parent")
async def list_collection_children(
    parent_id: Optional[str] = Query(None, description="ID del parent (omit para listar top-level)"),
    current_account_id: str = Depends(get_current_account_id),
    workspace_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    """Lista las subcolecciones directamente hijas de parent_id. Si parent_id es None, devuelve sólo los top-level."""
    try:
        collections = await list_user_collections(account_id=current_account_id, workspace_id=workspace_id)
        # Filtrar por parent_id (None => parent_id is None)
        if parent_id:
            filtered = [c for c in collections if c.get('parent_id') == parent_id]
        else:
            filtered = [c for c in collections if not c.get('parent_id')]

        return [CollectionResponse(
            id=c.get('id'),
            topic=c.get('topic') or c.get('name'),
            name=c.get('name') or c.get('topic'),
            parent_id=c.get('parent_id'),
            position=c.get('position'),
            item_type=c.get('item_type'),
            document_count=c.get('document_count'),
            description=c.get('description'),
            workspace_id=c.get('workspace_id'),
            workspace_name=c.get('workspace_name'),
            workspace_color=c.get('workspace_color'),
            has_knowledge_graph=c.get('has_knowledge_graph')
        ) for c in filtered]
    except Exception as e:
        logger.error(f"API: list_collection_children - Error al listar subcolecciones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor al listar subcolecciones.")
