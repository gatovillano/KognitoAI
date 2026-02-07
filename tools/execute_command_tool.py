import logging
import queue
from typing import Type, Optional, Any, Generator
from pydantic import BaseModel, Field, PrivateAttr
from langchain_core.tools import BaseTool
from core.command_executor import CommandExecutor

logger = logging.getLogger(__name__)

class ExecuteCommandTool(BaseTool):
    name: str = "execute_command"
    description: str = (
        "Ejecuta un comando bash en el sistema local y devuelve su salida en tiempo real. "
        "Úsala para realizar tareas de sistema, gestionar archivos, ejecutar scripts o consultar información del entorno. "
        "Soporta comandos interactivos."
    )
    
    class ExecuteCommandInput(BaseModel):
        command: str = Field(description="El comando bash completo a ejecutar.")

    args_schema: Type[BaseModel] = ExecuteCommandInput
    
    # Atributos privados para evitar problemas de validación con Pydantic en LangChain
    _command_executor: CommandExecutor = PrivateAttr()
    _interrupt_queue: queue.Queue = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_command_executor', CommandExecutor())
        object.__setattr__(self, '_interrupt_queue', queue.Queue())

    def _run(self, command: str) -> str:
        """
        Ejecuta el comando y acumula la salida para devolverla como resultado final a la IA.
        """
        logger.info(f"🚀 Ejecutando comando: {command}")
        full_output = ""
        try:
            for chunk in self._command_executor.execute(command, interrupt_queue=self._interrupt_queue):
                full_output += chunk
                # Aquí podríamos enviar chunks vía WebSocket si tuviéramos acceso al gestor,
                # pero por ahora devolvemos el total para que la IA lo procese.
            
            return full_output if full_output else "Comando ejecutado sin salida."
        except Exception as e:
            logger.error(f"Error ejecutando comando '{command}': {e}", exc_info=True)
            return f"Error al ejecutar el comando: {str(e)}"

    async def _arun(self, command: str) -> str:
        """
        Versión asíncrona (requerida por la arquitectura de Kognito AI).
        """
        # Ejecutamos en un thread para no bloquear el loop asíncrono de FastAPI
        import asyncio
        return await asyncio.to_thread(self._run, command)

    def get_command_generator(self, command: str) -> Generator[str, None, None]:
        """
        Devuelve un generador para streaming (útil para la CLI).
        """
        return self._command_executor.execute(command, interrupt_queue=self._interrupt_queue)
