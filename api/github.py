from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from core.database import get_db_session # Asumiendo que get_db_session existe o se puede crear
from tools.github_repo_tool import GitHubRepoTool
# from api.auth import get_current_active_user # Descomentar si se usa autenticación

router = APIRouter()

class GitHubCollectionRequest(BaseModel):
    repo_url: str
    action: str # "add_as_knowledge_collection" o "update_knowledge_collection"
    collection_topic: Optional[str] = None
    account_id: Optional[str] = None # Se obtendría del usuario autenticado si no se proporciona
    github_token: Optional[str] = None

@router.post("/collections")
async def manage_github_collection(
    request: GitHubCollectionRequest,
    db: AsyncSession = Depends(get_db_session),
    # current_user: Account = Depends(get_current_active_user) # Descomentar y ajustar si se usa autenticación
):
    # Si no se proporciona collection_topic ni account_id, se considera un error.
    if not request.collection_topic and not request.account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes proporcionar un 'collection_topic' o un 'account_id'."
        )

    # Si se usa autenticación, se podría obtener el account_id del usuario actual
    # account_id_to_use = request.account_id
    # if not account_id_to_use and current_user:
    #     account_id_to_use = str(current_user.id)

    github_tool = GitHubRepoTool()
    
    # Pasar la sesión de la base de datos a la herramienta si es necesario,
    # aunque la herramienta ya crea su propia SessionLocal.
    # Para operaciones de escritura, es mejor usar la sesión de la dependencia.
    # Sin embargo, GitHubRepoTool ya maneja su propia sesión, así que la pasamos como None
    # y dejamos que la herramienta la gestione internamente.
    
    try:
        result = await github_tool._arun(
            repo_url=request.repo_url,
            action=request.action,
            collection_topic=request.collection_topic,
            account_id=request.account_id, # Usar el account_id proporcionado o el del usuario autenticado
            github_token=request.github_token
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al gestionar la colección de GitHub: {e}"
        )
