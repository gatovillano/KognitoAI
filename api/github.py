import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from core.database import GitHubDocument # Asumiendo que get_db_session existe o se puede crear
from core.dependencies import get_db_session
from utils.db_session import DBSession
from skills.developer_tools_skill.scripts.github_repo_tool import GitHubRepoTool
from utils.security import get_current_account_id
from core.database import Account

router = APIRouter()

class GitHubCollectionRequest(BaseModel):
    repo_url: str
    action: str # "add_as_knowledge_collection" o "update_knowledge_collection"
    collection_topic: Optional[str] = None
    workspace_id: Optional[str] = None  # Para asociar el repositorio a un workspace específico
    account_id: Optional[str] = None # Se obtendría del usuario autenticado si no se proporciona
    github_token: Optional[str] = None
    vectorize: Optional[bool] = True

@router.post("/collections")
async def manage_github_collection(
    request: GitHubCollectionRequest,
    db: AsyncSession = Depends(get_db_session),
    account_id: str = Depends(get_current_account_id)
):
    # No se requiere collection_topic ni account_id específicamente para repositorios de GitHub
    # ya que se guardarán en una colección conjunta sin tema específico.

    # Si se usa autenticación, se podría obtener el account_id del usuario actual
    account_id_to_use = request.account_id if request.account_id else account_id

    github_tool = GitHubRepoTool(
        account_id=account_id_to_use,
        workspace_id=request.workspace_id
    )
    
    # Pasar la sesión de la base de datos a la herramienta si es necesario,
    # aunque la herramienta ya crea su propia SessionLocal.
    # Para operaciones de escritura, es mejor usar la sesión de la dependencia.
    # Sin embargo, GitHubRepoTool ya maneja su propia sesión, así que la pasamos como None
    # y dejamos que la herramienta la gestione internamente.
    
    if not account_id_to_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo determinar el 'account_id'. Asegúrate de estar autenticado o proporciona un 'account_id'."
        )
    
    logger.info(f"Gestionando colección de GitHub para account_id: {account_id_to_use}, repo_url: {request.repo_url}, action: {request.action}")
    
    try:
        # Import and invoke create_empty_collection to ensure the repository is visible in the frontend list
        from core.memory_manager import create_empty_collection
        topic_to_create = request.collection_topic if request.collection_topic else "repositorio"
        await create_empty_collection(
            account_id=account_id_to_use,
            topic_name=topic_to_create,
            workspace_id=request.workspace_id
        )

        result = await github_tool._arun(
            repo_url=request.repo_url,
            action=request.action,
            collection_topic=request.collection_topic,
            github_token=request.github_token,
            vectorize=request.vectorize
        )
        logger.info(f"Resultado de la operación: {result}")
        
        # La vectorización ya se maneja dentro de github_tool._arun(), no necesitamos duplicarla aquí
        return {"message": f"{result}"}
    except Exception as e:
        logger.error(f"Error al gestionar la colección de GitHub para account_id: {account_id_to_use}, repo_url: {request.repo_url}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al gestionar la colección de GitHub: {str(e)}"
        )

@router.post("/list-github-documents")
async def list_github_documents(
    db: AsyncSession = Depends(get_db_session),
    account_id: str = Depends(get_current_account_id)
):
    """
    List all GitHub documents for the current user.
    """
    try:
        query = select(GitHubDocument).where(GitHubDocument.account_id == account_id)
        result = await db.execute(query)
        docs = result.scalars().all()
        logger.info(f"Listando {len(docs)} documentos de GitHub para account_id: {account_id}. Detalle: {[doc.file_path for doc in docs][:10]}...")
        return [
            {
                "file_name": doc.file_path,
                "repo_url": doc.repo_url,
                "topic": "Repositories",
                "title": doc.file_path.split('/')[-1],
                "author": None,
                "document_id": f"github_{doc.id}",
                "workspace_id": str(doc.workspace_id) if doc.workspace_id else None
            }
            for doc in docs
        ]
    except Exception as e:
        logger.error(f"Error al listar documentos de GitHub para account_id: {account_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar documentos de GitHub: {str(e)}"
        )

@router.post("/list-github-repositories")
async def list_github_repositories(
    db: AsyncSession = Depends(get_db_session),
    account_id: str = Depends(get_current_account_id)
):
    """
    List all unique GitHub repositories for the current user.
    """
    try:
        query = select(GitHubDocument.repo_url).where(GitHubDocument.account_id == account_id).distinct()
        result = await db.execute(query)
        repos = result.scalars().all()
        logger.info(f"Listando {len(repos)} repositorios de GitHub para account_id: {account_id}.")
        return [
            {
                "repo_url": repo,
                "repo_name": repo.split('/')[-1]
            }
            for repo in repos
        ]
    except Exception as e:
        logger.error(f"Error al listar repositorios de GitHub para account_id: {account_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar repositorios de GitHub: {str(e)}"
        )

class GitHubVectorizationRequest(BaseModel):
    repo_name: str

class GitHubUpdateRequest(BaseModel):
    repo_url: str
    collection_topic: Optional[str] = "repositorio"
    vectorize: Optional[bool] = True # Añadido para controlar la vectorización

@router.post("/start-vectorization", status_code=status.HTTP_202_ACCEPTED)
async def start_vectorization_endpoint(
    req: GitHubVectorizationRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Inicia el proceso de vectorización para un repositorio de GitHub específico.
    """
    account_id = current_account_id
    repo_name = req.repo_name

    try:
        # Verificar si el repositorio existe para este usuario
        query = select(GitHubDocument).where(
            GitHubDocument.account_id == account_id,
            GitHubDocument.repo_url.endswith(f"/{repo_name}")
        ).limit(1)
        result = await db.execute(query)
        repo_doc = result.scalars().first()

        if not repo_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El repositorio {repo_name} no se encuentra registrado para este usuario."
            )

        # Crear una tarea de análisis en la base de datos (similar a AnalysisTask en api/analysis.py)
        from core.database import AnalysisTask
        new_task = AnalysisTask(
            account_id=account_id,
            file_name=f"Vectorization: {repo_name}",
            status="pending"
        )
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)

        # Iniciar la tarea en segundo plano
        background_tasks.add_task(
            vectorize_repository_task,
            str(new_task.id),
            account_id,
            repo_name
        )

        return {"task_id": str(new_task.id), "message": f"Vectorización del repositorio {repo_name} iniciada en segundo plano."}
    except Exception as e:
        logger.error(f"Error al iniciar vectorización para account_id: {account_id}, repo_name: {repo_name}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al iniciar vectorización: {str(e)}"
        )

@router.post("/update-repository", status_code=status.HTTP_202_ACCEPTED)
async def update_repository_endpoint(
    req: GitHubUpdateRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Inicia el proceso de actualización de un repositorio de GitHub en segundo plano.
    """
    from core.database import AnalysisTask
    import uuid

    try:
        # Crear una nueva tarea de análisis para trackear el progreso
        new_task = AnalysisTask(
            account_id=uuid.UUID(current_account_id),
            file_name=f"Actualización: {req.repo_url}",
            status="pending",
            analysis_type="repository_update" # Añadido para categorizar la tarea
        )
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)

        # Iniciar la tarea en segundo plano
        background_tasks.add_task(
            update_repository_task,
            str(new_task.id),
            current_account_id,
            req.repo_url,
            req.collection_topic or "repositorio",
            req.vectorize # Pasar el parámetro vectorize
        )

        return {"task_id": str(new_task.id), "message": f"Actualización del repositorio iniciada en segundo plano."}
    except Exception as e:
        logger.error(f"Error al iniciar actualización para account_id: {current_account_id}, repo_url: {req.repo_url}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al iniciar actualización: {str(e)}"
        )

async def update_repository_task(task_id: str, account_id: str, repo_url: str, collection_topic: str, vectorize: bool):
    """
    Tarea en segundo plano para actualizar un repositorio de GitHub.
    """
    from core.database import SessionLocal, AnalysisTask
    from sqlalchemy import update
    import uuid

    async with DBSession(SessionLocal) as db: # type: ignore
        try:
            # Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db.execute(stmt_processing)
            await db.commit()

            logger.info(f"Iniciando actualización de repositorio para tarea {task_id}...")

            # Usar el GitHubRepoTool para actualizar el repositorio
            github_tool = GitHubRepoTool(account_id=account_id)
            result = await github_tool._update_repository_documents(
                repo_url=repo_url,
                account_id=account_id,
                collection_topic=collection_topic, # Pasar el collection_topic
                vectorize=vectorize # Pasar el parámetro vectorize
            )

            # Marcar la tarea como completada con el resultado
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed",
                result_payload={"message": result, "repo_url": repo_url}
            )
            await db.execute(stmt_completed)
            await db.commit()

            logger.info(f"Actualización de repositorio completada para tarea {task_id}")

        except Exception as e:
            logger.error(f"Error en actualización de repositorio para tarea {task_id}: {e}", exc_info=True)
            # Marcar la tarea como fallida
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed",
                error_message=str(e)
            )
            await db.execute(stmt_failed)
            await db.commit()

@router.get("/get-repository-update-result/{task_id}")
async def get_repository_update_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Consulta el estado y el resultado de una tarea de actualización de repositorio.
    """
    from core.database import AnalysisTask
    try:
        task = await db.get(AnalysisTask, uuid.UUID(task_id))
        if not task or str(task.account_id) != current_account_id or task.analysis_type != "repository_update":
            raise HTTPException(status_code=404, detail="Tarea de actualización de repositorio no encontrada o no pertenece al usuario.")
        return {"status": task.status, "result": task.result_payload, "error": task.error_message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener resultado de actualización de repositorio para task_id: {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resultado de actualización de repositorio: {str(e)}"
        )

@router.get("/get-vectorization-result/{task_id}")
async def get_vectorization_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Consulta el estado y el resultado de una tarea de vectorización.
    """
    from core.database import AnalysisTask
    try:
        task = await db.get(AnalysisTask, uuid.UUID(task_id))
        if not task or str(task.account_id) != current_account_id:
            raise HTTPException(status_code=404, detail="Tarea no encontrada o no pertenece al usuario.")
        return {"status": task.status, "result": task.result_payload, "error": task.error_message}
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Error al obtener resultado de vectorización para task_id: {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resultado de vectorización: {str(e)}"
        )

async def vectorize_repository_task(task_id: str, account_id: str, repo_name: str):
    """
    Tarea en segundo plano para vectorizar los documentos de un repositorio de GitHub.
    """
    from core.database import SessionLocal, AnalysisTask
    from core.memory_manager import process_document_for_rag
    from sqlalchemy import select, update
    async with DBSession(SessionLocal) as db:
        try:
            # Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db.execute(stmt_processing)
            await db.commit()

            logger.info(f"Iniciando vectorización para tarea {task_id} del repositorio {repo_name}...")

            # Obtener todos los documentos del repositorio
            query = select(GitHubDocument).where(
                GitHubDocument.account_id == account_id,
                GitHubDocument.repo_url.endswith(f"/{repo_name}")
            )
            result = await db.execute(query)
            docs = result.scalars().all()

            if not docs:
                raise ValueError(f"No se encontraron documentos para el repositorio {repo_name}.")

            processed_count = 0
            for doc in docs:
                try:
                    chunks_count = await process_document_for_rag(
                        account_id=account_id,
                        file_name=doc.file_path,
                        extracted_text=doc.content,
                        topic="Repositories",
                        metadata={"repo_url": doc.repo_url, "type": "code"}
                    )
                    if chunks_count > 0:
                        logger.info(f"Documento {doc.file_path} procesado con {chunks_count} fragmentos.")
                        processed_count += 1
                    else:
                        logger.warning(f"No se generaron fragmentos para el documento {doc.file_path}.")
                except Exception as e:
                    logger.error(f"Error al procesar el documento {doc.file_path}: {e}", exc_info=True)

            # Guardar el resultado y marcar como 'completed'
            result_payload = {"processed_documents": processed_count, "total_documents": len(docs)}
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=result_payload)
            await db.execute(stmt_completed)
            await db.commit()
            logger.info(f"Vectorización para tarea {task_id} completada con {processed_count} documentos procesados de {len(docs)}.")
        except Exception as e:
            logger.error(f"Fallo en tarea de vectorización {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db.execute(stmt_failed)
            await db.commit()
