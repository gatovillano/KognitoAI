import logging
import os
import uuid
import asyncio
import io
import concurrent.futures
from typing import Type, Optional, Dict, Any
import paramiko
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.database import SessionLocal, Account
from core.repositories.secret_repository import SecretRepository

logger = logging.getLogger(__name__)

class InputSchema(BaseModel):
    command: str = Field(description="El comando de terminal a ejecutar en el host. Puede ser cualquier comando válido de Linux/Unix.")
    timeout: int = Field(default=30, description="Timeout en segundos para la ejecución del comando (por defecto 30).")

class HostTerminalTool(BaseTool):
    name: str = "host_terminal_skill"
    description: str = (
        "Permite ejecutar comandos de sistema directamente en la máquina host a través de SSH. "
        "Utiliza la configuración SSH guardada en la cuenta del usuario (host, usuario, llaves/contraseñas)."
    )
    args_schema: Type[BaseModel] = InputSchema
    
    # ✅ ESTE CAMPO ES OBLIGATORIO PARA TODAS LAS SKILLS DE USUARIO
    account_id: str = Field(..., description="ID de cuenta, inyectado automáticamente por el SkillManager")

    async def _fetch_ssh_config(self) -> Optional[dict]:
        """Obtiene la configuración SSH desde la base de datos del usuario."""
        if not self.account_id:
            return None
        try:
            async with SessionLocal() as db:
                account = await db.get(Account, uuid.UUID(self.account_id))
                if not account or not account.ssh_host:
                    return None

                repo = SecretRepository(db)
                password = await repo.get_decrypted_secret(uuid.UUID(self.account_id), 'SSH_PASSWORD')
                private_key = await repo.get_decrypted_secret(uuid.UUID(self.account_id), 'SSH_PRIVATE_KEY')

                return {
                    "hostname": account.ssh_host,
                    "port": int(account.ssh_port or 22),
                    "username": account.ssh_user,
                    "password": password,
                    "private_key": private_key,
                }
        except Exception as e:
            logger.error(f"Error al obtener configuración SSH para {self.account_id}: {e}")
            return None

    def _get_ssh_client(self, config: dict):
        """Crea y retorna un cliente SSH paramiko conectado."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": config["hostname"],
            "port": config["port"],
            "username": config["username"],
            "timeout": 15,
        }

        if config.get("private_key"):
            # Intentar cargar como RSA primero, luego Ed25519
            try:
                key_obj = paramiko.RSAKey.from_private_key(io.StringIO(config["private_key"]))
                connect_kwargs["pkey"] = key_obj
            except Exception:
                try:
                    key_obj = paramiko.Ed25519Key.from_private_key(io.StringIO(config["private_key"]))
                    connect_kwargs["pkey"] = key_obj
                except Exception:
                    logger.warning("No se pudo cargar la llave privada SSH (RSA o Ed25519)")

        if config.get("password") and "pkey" not in connect_kwargs:
            connect_kwargs["password"] = config["password"]

        # Si no hay llave ni contraseña en la DB, intentar con la llave por defecto en /tmp si existe
        if "pkey" not in connect_kwargs and "password" not in connect_kwargs:
            default_key = "/tmp/kai_id_ed25519"
            if os.path.exists(default_key):
                connect_kwargs["key_filename"] = default_key

        client.connect(**connect_kwargs)
        return client

    async def _arun(self, command: str, timeout: int = 30) -> str:
        """Ejecución asíncrona (envuelta en thread pool para paramiko)."""
        logger.info(f"🚀 Ejecutando comando SSH: {command}")
        
        config = await self._fetch_ssh_config()
        if not config:
            # Fallback a variables de entorno si no hay config en DB
            config = {
                "hostname": os.environ.get("SSH_HOST", "127.0.0.1"),
                "port": int(os.environ.get("SSH_PORT", "22")),
                "username": os.environ.get("SSH_USER", os.environ.get("USER", "gato")),
            }
            logger.info(f"Usando configuración SSH por defecto (env): {config['hostname']}")

        def _execute():
            client = None
            try:
                client = self._get_ssh_client(config)
                stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
                
                stdout_text = stdout.read().decode('utf-8', errors='ignore').strip()
                stderr_text = stderr.read().decode('utf-8', errors='ignore').strip()
                exit_status = stdout.channel.recv_exit_status()
                
                return stdout_text, stderr_text, exit_status
            finally:
                if client:
                    client.close()

        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                stdout_text, stderr_text, exit_status = await loop.run_in_executor(pool, _execute)
            
            output = f"""📟 **Resultado Terminal (Host: {config['hostname']})**:
```bash
{command}
```

📤 **STDOUT**:
```
{stdout_text if stdout_text else '(Sin salida estándar)'}
```

📛 **STDERR**:
```
{stderr_text if stderr_text else '(Sin errores)'}
```

✅ **Status**: {exit_status} {'(Éxito)' if exit_status == 0 else '(Error)'}"""
            
            return output
            
        except paramiko.AuthenticationException:
            return f"❌ **Error de autenticación SSH**: No se pudo autenticar en {config['hostname']}@{config['username']}.\n💡 Verifica tus credenciales en Ajustes > SSH."
        except paramiko.SSHException as e:
            return f"❌ **Error SSH**: {str(e)}\n💡 Si estás en Docker, intenta usar la IP de la puerta de enlace (ej: 172.17.0.1) en lugar de localhost."
        except Exception as e:
            logger.error(f"❌ Error crítico en host_terminal_skill: {e}", exc_info=True)
            return f"❌ **Error Crítico**: {str(e)}"

    def _run(self, command: str, timeout: int = 30) -> str:
        """Soporte para ejecución síncrona (redirecciona a asíncrona)."""
        try:
            loop = asyncio.get_running_loop()
            # SkillManager suele llamar a _arun si está disponible.
            return asyncio.run(self._arun(command, timeout))
        except RuntimeError:
            return asyncio.run(self._arun(command, timeout))
