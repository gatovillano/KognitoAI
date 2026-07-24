import logging
import os
import sys
import uuid
import subprocess
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_db_session
from utils.security import get_current_account_id
from core.database import Base, Account, engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/extensions", tags=["extensions"])

# Lista estática de extensiones disponibles con sus metadatos
AVAILABLE_EXTENSIONS = [
    {
        "id": "gallery_selection_panel",
        "name": "KogniPhotos",
        "category": "UI / Media",
        "description": "Panel de selección colaborativa de fotos al estilo Google Photos.",
        "icon": "ImageIcon",
        "requires_db": True
    },
    {
        "id": "email_management",
        "name": "KogniMail",
        "category": "AI / Productivity",
        "description": "Gestión inteligente de correos con IA, resúmenes de hilos y redacción asistida.",
        "icon": "Mail",
        "requires_db": True
    },
    {
        "id": "jitsi_meet",
        "name": "Jitsi Meet",
        "category": "Integration",
        "description": "Videoconferencias integradas, gestión de salas y enlaces de reunión.",
        "icon": "Video",
        "requires_db": True
    },
    {
        "id": "fediverso",
        "name": "Fediverso",
        "category": "Social / AI",
        "description": "Cliente Mastodon y Fediverse con asistente de IA para redacción y lectura de feeds.",
        "icon": "Globe",
        "requires_db": True
    },
    {
        "id": "kai_ethno",
        "name": "KAI Ethno",
        "category": "Research / AI",
        "description": "Ecosistema de investigación etnográfica y antropológica aumentada para análisis cualitativo.",
        "icon": "Brain",
        "requires_db": False,
        "requires_pip": True
    }
]

class ExtensionInstallRequest(BaseModel):
    extension_id: str

@router.get("/available", summary="Listar extensiones disponibles y su estado")
async def list_available_extensions(
    account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        account = await db.get(Account, uuid.UUID(account_id))
        if not account:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")

        installed = account.installed_extensions or []
        
        result = []
        for ext in AVAILABLE_EXTENSIONS:
            result.append({
                **ext,
                "is_installed": ext["id"] in installed,
                "is_active": ext["id"] in installed # En esta arquitectura simplificada, instalada = activa
            })
        return {"extensions": result}
    except Exception as e:
        logger.error(f"Error listando extensiones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/install", summary="Instalar una extensión")
async def install_extension(
    request: ExtensionInstallRequest,
    account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    ext_id = request.extension_id
    ext_meta = next((ext for ext in AVAILABLE_EXTENSIONS if ext["id"] == ext_id), None)
    if not ext_meta:
        raise HTTPException(status_code=404, detail="Extensión no encontrada en la tienda")

    account = await db.get(Account, uuid.UUID(account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    installed = list(account.installed_extensions or [])
    if ext_id in installed:
        return {"status": "success", "message": f"La extensión '{ext_meta['name']}' ya está instalada."}

    try:
        # 1. Configuración de base de datos específica
        if ext_id == "gallery_selection_panel":
            # Importar los modelos para registrarlos en la metadata de Base
            try:
                import extensions.gallery_selection_panel.backend.models # noqa: F401
            except ImportError:
                # Fallback si se movió a api/
                try:
                    import api.gallery_selection_panel.models # noqa: F401
                except ImportError:
                    logger.warning("No se pudo importar el modelo de gallery_selection_panel")
            
            async with engine.begin() as conn:
                # Ejecutar alteración de tabla si existe
                try:
                    await conn.execute(text("ALTER TABLE albums ADD COLUMN IF NOT EXISTS workspace_id UUID;"))
                except Exception as db_err:
                    logger.warning(f"Error al alterar tabla albums: {db_err}")
                await conn.run_sync(Base.metadata.create_all)

        elif ext_id == "email_management":
            try:
                import extensions.email_management.backend.models # noqa: F401
            except ImportError:
                try:
                    import api.email_management.models # noqa: F401
                except ImportError:
                    logger.warning("No se pudo importar el modelo de email_management")
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        elif ext_id == "jitsi_meet":
            try:
                import extensions.jitsi_meet.backend.models # noqa: F401
            except ImportError:
                logger.warning("No se pudo importar el modelo de jitsi_meet")
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                try:
                    await conn.execute(text("ALTER TABLE jitsi_rooms ALTER COLUMN album_id DROP NOT NULL;"))
                except Exception as db_err:
                    logger.warning(f"Error al alterar tabla jitsi_rooms: {db_err}")

        elif ext_id == "fediverso":
            try:
                import extensions.fediverso.backend.models # noqa: F401
            except ImportError:
                logger.warning("No se pudo importar el modelo de fediverso")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        elif ext_id == "kai_ethno":
            # Ejecutar instalación de pip en segundo plano/proceso
            api_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(api_dir)
            python_bin = os.path.join(project_root, "venv_host", "bin", "python")
            req_file = os.path.join(project_root, "skills", "kai_ethno_skill", "requirements.txt")
            
            if os.path.exists(req_file) and os.path.exists(python_bin):
                cmd = [python_bin, "-m", "pip", "install", "-r", req_file]
                logger.info(f"Instalando dependencias de KAI Ethno: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
            else:
                logger.warning(f"No se encontró venv o requirements.txt para KAI Ethno. python_bin: {python_bin}, req_file: {req_file}")

        # 2. Registrar como instalada en la cuenta
        installed.append(ext_id)
        account.installed_extensions = installed
        db.add(account)
        await db.commit()
        await db.refresh(account)

        return {
            "status": "success",
            "message": f"Extensión '{ext_meta['name']}' instalada correctamente y activa inmediatamente.",
            "installed_extensions": account.installed_extensions
        }
    except Exception as e:
        logger.error(f"Error instalando extensión {ext_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error durante la instalación: {str(e)}")

@router.post("/uninstall", summary="Desinstalar una extensión")
async def uninstall_extension(
    request: ExtensionInstallRequest,
    account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    ext_id = request.extension_id
    ext_meta = next((ext for ext in AVAILABLE_EXTENSIONS if ext["id"] == ext_id), None)
    if not ext_meta:
        raise HTTPException(status_code=404, detail="Extensión no encontrada")

    account = await db.get(Account, uuid.UUID(account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    installed = list(account.installed_extensions or [])
    if ext_id not in installed:
        return {"status": "success", "message": f"La extensión '{ext_meta['name']}' no estaba instalada."}

    try:
        installed.remove(ext_id)
        account.installed_extensions = installed
        db.add(account)
        await db.commit()
        await db.refresh(account)

        return {
            "status": "success",
            "message": f"Extensión '{ext_meta['name']}' desinstalada correctamente.",
            "installed_extensions": account.installed_extensions
        }
    except Exception as e:
        logger.error(f"Error desinstalando extensión {ext_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
