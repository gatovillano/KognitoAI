import logging
import os
import stat
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.security import get_current_account_id
from core.dependencies import get_db_session
from core.database import Account
from core.repositories.secret_repository import SecretRepository
from skills.developer_tools_skill.scripts.local_file_navigator import LocalFileNavigator

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/tree_flat")
async def get_local_tree_flat(
    query: Optional[str] = "",
    account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns a flat list of files for autocompletion, either local or via SSH.
    Fetches configuration directly from DB to ensure robustness.
    """
    navigator = LocalFileNavigator()
    try:
        # Fetch account configuration directly
        stmt = select(Account).where(Account.id == uuid.UUID(account_id))
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        
        ssh_config = None
        if account and account.ssh_host:
            logger.info(f"SSH Config detected for account {account_id}: host={account.ssh_host}")
            secret_repo = SecretRepository(db)
            password = await secret_repo.get_decrypted_secret(uuid.UUID(account_id), 'SSH_PASSWORD')
            private_key = await secret_repo.get_decrypted_secret(uuid.UUID(account_id), 'SSH_PRIVATE_KEY')

            # host.docker.internal only resolves from inside a Docker container.
            # When the API runs on the host (no /.dockerenv), translate it to localhost.
            ssh_host = account.ssh_host
            import os as _os
            if not _os.path.exists("/.dockerenv") and ssh_host in ("host.docker.internal",):
                logger.info(f"API running outside Docker: translating host.docker.internal → localhost for SSH")
                ssh_host = "localhost"

            ssh_config = {
                "host": ssh_host,
                "port": int(account.ssh_port or 22),
                "username": account.ssh_user,
                "base_path": account.local_base_path or ".", # Default to home if not specified
                "password": password,
                "private_key": private_key,
            }
        
        if ssh_config:
            # SSH Mode
            try:
                logger.info(f"Using SSH mode for autocomplete on {ssh_config['host']} starting at {ssh_config['base_path']}")
                client = navigator._get_ssh_client(ssh_config)
                base_path = ssh_config["base_path"]
                
                # Use find to get a flat list of files quickly
                # We filter by query if provided to reduce output
                exclude_cmd = "-not -path '*/.*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*'"
                
                # Aumentamos el maxdepth a 10 para que vea más archivos, pero evitamos que sea infinito
                # Si base_path es / (raíz), mantenemos un límite más estricto
                max_depth = 4 if base_path == "/" else 10
                
                if query:
                    # Usamos -iname para búsqueda insensible a mayúsculas/minúsculas
                    cmd = f"find '{base_path}' -maxdepth {max_depth} -type f -iname '*{query}*' {exclude_cmd} | head -n 100"
                else:
                    # Si no hay query, mostramos los archivos más recientes o simplemente los primeros encontrados
                    cmd = f"find '{base_path}' -maxdepth {max_depth} -type f {exclude_cmd} | head -n 100"
                    
                _, stdout, _ = client.exec_command(cmd)
                output = stdout.read().decode().strip()
                files = output.splitlines() if output else []
                
                # Strip base_path for cleaner display and ensure absolute paths are handled if needed
                clean_files = []
                for f in files:
                    if base_path != "." and f.startswith(base_path):
                        clean_f = f.replace(base_path, "").lstrip("/")
                    else:
                        clean_f = f.lstrip("./")
                    clean_files.append(clean_f)

                client.close()
                return {"options": clean_files}
            except Exception as ssh_err:
                logger.error(f"SSH Autocomplete error: {ssh_err}", exc_info=True)
                return {"options": []}
        else:
            # Local Mode (fallback to current project directory)
            try:
                logger.info(f"No SSH config found for {account_id}, falling back to container local path")
                base_path = Path.cwd()
                files = []
                count = 0
                
                # Search recursively but carefully
                for item in base_path.rglob("*"):
                    if item.is_file():
                        # Ignore common noise
                        if any(part.startswith('.') or part in ['node_modules', '__pycache__', 'venv', '.venv'] for part in item.parts):
                            continue
                            
                        rel_path = str(item.relative_to(base_path))
                        if not query or query.lower() in rel_path.lower():
                            files.append(rel_path)
                            count += 1
                    
                    if count >= 100:
                        break
                
                return {"options": files}
            except Exception as local_err:
                logger.error(f"Local Autocomplete error: {local_err}")
                return {"options": []}
            
    except Exception as e:
        logger.error(f"Error getting local tree for autocomplete: {e}", exc_info=True)
        return {"options": []}
