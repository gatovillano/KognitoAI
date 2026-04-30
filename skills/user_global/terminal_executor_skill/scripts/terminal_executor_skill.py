from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import subprocess
import shlex

class InputSchema(BaseModel):
    command: str = Field(description="El comando de terminal a ejecutar.")
    timeout: int = Field(default=30, description="Timeout en segundos para la ejecución del comando (por defecto 30).")

class TerminalExecutor(BaseTool):
    name: str = "terminal_executor"
    description: str = "Ejecuta un comando de terminal y devuelve su salida estándar, error y código de retorno."
    args_schema: Type[BaseModel] = InputSchema

    def _run(self, command: str, timeout: int = 30) -> str:
        try:
            # Ejecutar el comando en shell
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = []
            output.append(f"Return code: {result.returncode}")
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            if not result.stdout and not result.stderr:
                output.append("(Sin salida)")
            return "\n".join(output)
        except subprocess.TimeoutExpired:
            return f"Error: El comando superó el timeout de {timeout} segundos."
        except Exception as e:
            return f"Error al ejecutar el comando: {e}"