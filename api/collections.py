# En api/collections.py

from fastapi import APIRouter, HTTPException, Depends, status, Query, Path
from typing import List, Optional
from pydantic import BaseModel
import uuid
import logging

from core.database import SessionLocal, get_db_session
from utils.security import get_current_account_id
from core.memory_manager import list_user_collections, create_empty_collection
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# --- Modelos Pydantic para Colecciones ---
class CollectionResponse(BaseModel):
    topic: str
    document_count: int
    description: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_color: Optional[str] = None
    has_knowledge_graph: Optional[bool] = None

class CollectionCreateRequest(BaseModel):
    topic: str
    description: Optional[str] = None
    workspaceId: Optional[str] = None

from urllib.parse import unquote

def decoded_topic(topic: str = Path(..., description="El tema de la colección, codificado en la URL")) -> str:
    return unquote(topic)

@router.get("/collections/{topic}/details", summary="Obtener detalles de una colección por nombre")
async def get_collection_details_by_name(
    current_account_id: str = Depends(get_current_account_id),
    topic: str = Depends(decoded_topic),
    workspace_id: Optional[str] = Query(None),
):
    """
    Obtiene los detalles de una colección específica por su nombre, incluyendo los perfiles de contacto vinculados.
    """
    from utils.security import check_workspace_permission
    from core.database import SessionLocal
    from utils.db_session import DBSession
    from core.memory_manager import get_user_document_topic_by_name

    # Verificar permisos de workspace si se proporciona
    if workspace_id:
        async with DBSession(SessionLocal) as db_session:
            if not await check_workspace_permission(current_account_id, workspace_id, db_session, required_roles=["owner", "editor", "viewer"]):
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
            topic=c['topic'],
            document_count=c['document_count'],
            description=c.get('description'),
            workspace_id=c.get('workspace_id'),
            workspace_name=c.get('workspace_name'),
            workspace_color=c.get('workspace_color'),
            has_knowledge_graph=c.get('has_knowledge_graph')
        ) for c in collections]
    except Exception as e:
        logger.error(f"API: list_collections - Error al listar colecciones para account_id: {current_account_id}, error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor al listar colecciones.")

@router.post("/collections", status_code=status.HTTP_201_CREATED, summary="Crear una nueva colección")
async def create_collection(request: CollectionCreateRequest, current_account_id: str = Depends(get_current_account_id), db: "AsyncSession" = Depends(get_db_session)):
    logger.info(f"API: create_collection - Petición para crear colección: {request.topic}, description: {request.description}, workspaceId: {request.workspaceId}, account: {current_account_id}")
    success = await create_empty_collection(
        account_id=current_account_id,
        topic_name=request.topic,
        description=request.description,
        workspace_id=request.workspaceId
    )
    if not success:
        logger.error(f"API: create_collection - No se pudo crear la colección o ya existe: {request.topic}")
        raise HTTPException(status_code=400, detail="No se pudo crear la colección o ya existe.")
    logger.info(f"API: create_collection - Colección '{request.topic}' creada y asociada al workspace {request.workspaceId if request.workspaceId else 'global'} con éxito.")
    return {"message": f"Colección '{request.topic}' creada y lista para ser usada en el workspace {request.workspaceId if request.workspaceId else 'global'}."}
