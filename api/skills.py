import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from pydantic import BaseModel
from core.dependencies import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from utils.security import get_current_user
from core.skill_manager import SkillManager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/available", summary="Listar todas las habilidades disponibles")
async def list_available_skills(
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todas las habilidades (Skills) descubiertas por el SkillManager.
    Devuelve sus nombres y descripciones extraídas de los archivos .md.
    """
    try:
        skill_manager = SkillManager()
        skills_info = await skill_manager.get_skills_metadata()
        return {"skills": skills_info}
    except Exception as e:
        logger.error(f"Error listando habilidades disponibles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class ToolRunRequest(BaseModel):
    tool_name: str
    action: Optional[str] = None
    dataset_name: Optional[str] = None
    documents: Optional[List[Dict[str, Any]]] = None
    workspace_id: Optional[str] = None
    # Allow extra fields
    class Config:
        extra = "allow"

@router.post("/run", summary="Ejecutar una habilidad")
async def run_skill(
    background_tasks: BackgroundTasks,
    request: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint genérico para ejecutar habilidades (skills).
    """
    tool_name = request.get("tool_name")
    if not tool_name:
        raise HTTPException(status_code=400, detail="tool_name es requerido")

    logger.info(f"Solicitud de ejecución de habilidad: {tool_name} por usuario {current_user.get('user_id')}")

    try:
        skill_manager = SkillManager()
        
        # Cargar las habilidades disponibles para el contexto actual
        loaded_skills = await skill_manager.load_skills(
            account_id=current_user.get('account_id'),
            workspace_id=request.get("workspace_id")
        )
        
        # Encontrar la habilidad solicitada
        target_skill = next((skill for skill in loaded_skills if skill.name == tool_name), None)

        if not target_skill:
            raise HTTPException(status_code=404, detail=f"Habilidad '{tool_name}' no encontrada o no disponible.")

        # Preparar los argumentos para la habilidad
        args = request.copy()
        if "tool_name" in args:
            del args["tool_name"]
            
        # Añadir db_session si la habilidad lo requiere
        if hasattr(target_skill, 'db_session'):
             args['db_session'] = db

        # Lógica para ejecutar en segundo plano (ejemplo)
        # Una mejor aproximación sería tener un flag en la metadata de la skill
        if tool_name == "add_web_to_rag":
             background_tasks.add_task(target_skill._arun, **args)
             return {"status": "success", "message": f"La habilidad '{tool_name}' ha comenzado en segundo plano."}
        else:
            result = await target_skill._arun(**args)
            return {"result": result, "status": "success"}

    except Exception as e:
        logger.error(f"Error ejecutando la habilidad {tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno ejecutando la habilidad: {str(e)}")
