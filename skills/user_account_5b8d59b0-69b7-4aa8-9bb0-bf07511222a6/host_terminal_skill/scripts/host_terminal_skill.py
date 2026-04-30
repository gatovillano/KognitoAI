from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import subprocess
import asyncio
import logging

logger = logging.getLogger(__name__)

class InputSchema(BaseModel):
    command: str = Field(description="El comando de terminal a ejecutar en el host. Puede ser cualquier comando válido de Linux/Unix.")
    timeout: int = Field(default=30, description="Timeout en segundos para la ejecución del comando (por defecto 30).")

class HostTerminalTool(BaseTool):
    name: str = "host_terminal_skill"
    description: str = "Permite ejecutar comandos de sistema directamente en la máquina host a través de SSH de forma asíncrona."
    args_schema: Type[BaseModel] = InputSchema

    def _run(self, command: str, timeout: int = 30) -> str:
        """Fallback síncrono que delega en la versión asíncrona."""
        try:
            return asyncio.run(self._arun(command, timeout))
        except Exception as e:
            return f"❌ Error en ejecución síncrona: {str(e)}"

    async def _arun(self, command: str, timeout: int = 30) -> str:
        """Ejecución asíncrona real del comando SSH."""
        ssh_command = [
            "ssh",
            "-i", "/tmp/kai_id_ed25519",
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "gato@host.docker.internal",
            command
        ]
        
        logger.info(f"🚀 Ejecutando comando SSH asíncrono: {command}")
        
        try:
            # Iniciamos el proceso asíncrono
            process = await asyncio.create_subprocess_exec(
                *ssh_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Esperamos el resultado con timeout
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                return_code = process.returncode
            except asyncio.TimeoutExpired:
                process.kill()
                logger.warning(f"⏱️ Timeout alcanzado para comando: {command}")
                return f"⏱️ **Timeout**: El comando excedió los {timeout} segundos."

            stdout_text = stdout.decode().strip()
            stderr_text = stderr.decode().strip()
            
            output = f"""📟 **Resultado Terminal (Host)**:
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

✅ **Status**: {return_code} {'(Éxito)' if return_code == 0 else '(Error)'}"""
            
            return output
            
        except Exception as e:
            logger.error(f"❌ Error crítico en host_terminal_skill: {e}", exc_info=True)
            return f"❌ **Error Crítico**: {str(e)}"
