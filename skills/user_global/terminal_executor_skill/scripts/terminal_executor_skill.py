"""
skills/user_global/terminal_executor_skill/scripts/terminal_executor_skill.py

Terminal executor con dos modos:
  1. SÍNCRONO (sin streaming): subprocess.run() → devuelve salida completa al agente.
     Ideal para comandos cortos y scripts que terminan rápido.

  2. PTY interactivo (streaming): lanza el comando en un PTY real y acumula la
     salida hasta que termina o agota el timeout. Útil para comandos que producen
     salida progresiva (pip install, npm install, etc.).

El agente elige el modo automáticamente:
  - streaming=False  → subprocess.run (rápido, simple)
  - streaming=True   → PTY con lectura incremental (progresivo, para comandos largos)
"""

import asyncio
import fcntl
import logging
import os
import pty
import select
import signal
import struct
import subprocess
import termios
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Constantes ────────────────────────────────────────────────────────────────
MAX_OUTPUT_CHARS = 32_000   # límite de caracteres de salida al agente
PTY_READ_CHUNK = 4_096
DEFAULT_SHELL = os.environ.get("TERMINAL_SHELL", "/bin/bash")


# ── Helpers PTY ───────────────────────────────────────────────────────────────
def _set_pty_size(fd: int, cols: int = 220, rows: int = 50) -> None:
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass


def _run_in_pty(command: str, timeout: int) -> str:
    """
    Ejecuta *command* dentro de un PTY real y acumula toda la salida.
    Retorna la salida como string (ANSI escapes incluidos → el agente puede leerlos).
    """
    master_fd, slave_fd = pty.openpty()
    _set_pty_size(master_fd)

    env = os.environ.copy()
    env.update({"TERM": "xterm-256color", "LANG": "en_US.UTF-8"})

    proc = subprocess.Popen(
        command,
        shell=True,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        env=env,
        executable=DEFAULT_SHELL,
    )
    os.close(slave_fd)

    output_chunks: list[bytes] = []
    total_bytes = 0

    try:
        while True:
            # select con timeout de 0.1 s para no bloquear indefinidamente
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if r:
                try:
                    chunk = os.read(master_fd, PTY_READ_CHUNK)
                    if not chunk:
                        break
                    output_chunks.append(chunk)
                    total_bytes += len(chunk)
                    if total_bytes > MAX_OUTPUT_CHARS * 2:
                        output_chunks.append(b"\n[... salida truncada ...]\n")
                        break
                except OSError:
                    break
            elif proc.poll() is not None:
                # Proceso terminado → leer lo que quede
                try:
                    while True:
                        r2, _, _ = select.select([master_fd], [], [], 0)
                        if not r2:
                            break
                        chunk = os.read(master_fd, PTY_READ_CHUNK)
                        if not chunk:
                            break
                        output_chunks.append(chunk)
                except OSError:
                    pass
                break
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass

    # Esperar hasta timeout
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return _format_pty_output(output_chunks, proc.returncode, timeout=True)

    return _format_pty_output(output_chunks, proc.returncode)


def _format_pty_output(chunks: list[bytes], returncode: Optional[int], timeout: bool = False) -> str:
    import re
    raw = b"".join(chunks).decode("utf-8", errors="replace")
    # Eliminar secuencias ANSI para el agente (lectura limpia)
    clean = re.sub(r"\x1b\[[0-9;]*[mGKHABCDJfsuhl]", "", raw)
    clean = re.sub(r"\x1b\].*?\x07", "", clean)
    clean = clean.replace("\r\n", "\n").replace("\r", "\n")

    parts = []
    if timeout:
        parts.append(f"⏰ Timeout alcanzado — salida parcial:")
    parts.append(clean[:MAX_OUTPUT_CHARS])
    if len(clean) > MAX_OUTPUT_CHARS:
        parts.append("\n[... salida truncada ...]")
    if returncode is not None:
        parts.append(f"\nReturn code: {returncode}")
    return "\n".join(parts)


# ── Schema ────────────────────────────────────────────────────────────────────
class InputSchema(BaseModel):
    command: str = Field(
        description="El comando de terminal a ejecutar (bash)."
    )
    timeout: int = Field(
        default=60,
        description="Timeout en segundos (por defecto 60). Usa valores mayores para instalaciones o compilaciones largas.",
    )
    streaming: bool = Field(
        default=True,
        description=(
            "Si True (por defecto), ejecuta el comando dentro de un PTY real y devuelve la salida "
            "progresiva acumulada o un terminal interactivo. Ideal para comandos con salida larga o interactiva "
            "(pip install, npm install, docker build…). "
            "Si False, usa subprocess.run() para mayor velocidad."
        ),
    )
    interactive: bool = Field(
        default=True,
        description=(
            "Si True (por defecto), inserta en la respuesta HTML un terminal PTY interactivo embebido en el chat. "
            "Al abrir el terminal, el frontend conectará por WebSocket y ejecutará el comando automáticamente."
        ),
    )
    cwd: Optional[str] = Field(
        default=None,
        description="Directorio de trabajo desde donde ejecutar el comando. Si no se indica, usa el directorio actual.",
    )


# ── Tool ──────────────────────────────────────────────────────────────────────
class TerminalExecutor(BaseTool):
    name: str = "terminal_executor"
    description: str = (
        "Ejecuta comandos de terminal (bash) en el servidor. "
        "Devuelve stdout, stderr y código de retorno. "
        "Por defecto ejecuta en modo interactivo (streaming=True, interactive=True) "
        "para mostrar un terminal interactivo en tiempo real en la interfaz de chat. "
        "Para comandos cortos y rápidos donde no se requiera interactividad, puedes establecer streaming=False, interactive=False. "
        "Puedes especificar 'cwd' para cambiar el directorio de trabajo. "
        "IMPORTANTE: este tool ejecuta comandos en el SERVIDOR, no en la máquina "
        "local del usuario."
    )
    args_schema: Type[BaseModel] = InputSchema
    # Inyectado por SkillManager: permite crear sesiones PTY ligadas a la cuenta
    account_id: Optional[str] = None

    def _create_pty_session_html(self, command: str, cwd: Optional[str] = None, account_id: Optional[str] = None) -> str:
        try:
            from core.pty_sessions import create_session
            acct = account_id or getattr(self, "account_id", None)
            if not acct:
                return "❌ Error: account_id no disponible para crear sesión PTY."

            coro = create_session(command=command, account_id=acct, cwd=cwd)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                fut = asyncio.run_coroutine_threadsafe(coro, loop)
                session_id = fut.result(timeout=10)
            else:
                session_id = asyncio.run(coro)

            import html as _html
            safe_cmd = _html.escape(command)
            return f'<div class="pty-session-placeholder" data-session-id="{session_id}" data-cmd="{safe_cmd}"></div>'
        except Exception as e:
            logger.exception(f"Error creando sesión PTY interactiva: {e}")
            return f"❌ Error al crear terminal interactiva: {e}"

    def _run(
        self,
        command: str,
        timeout: int = 60,
        streaming: bool = True,
        cwd: Optional[str] = None,
        interactive: bool = True,
        **kwargs: Any,
    ) -> str:
        if streaming:
            # --- Modo PTY: salida progresiva acumulada o terminal interactivo ---
            if interactive:
                acct = getattr(self, "account_id", None) or kwargs.get("account_id")
                return self._create_pty_session_html(command=command, cwd=cwd, account_id=acct)
            if cwd:
                command = f"cd {cwd!r} && {command}"
            return _run_in_pty(command, timeout)
        else:
            # --- Modo subprocess clásico (rápido) ---
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=cwd or None,
                    executable=DEFAULT_SHELL,
                )
                parts = [f"Return code: {result.returncode}"]
                if result.stdout:
                    out = result.stdout[:MAX_OUTPUT_CHARS]
                    if len(result.stdout) > MAX_OUTPUT_CHARS:
                        out += "\n[... salida truncada ...]"
                    parts.append(f"STDOUT:\n{out}")
                if result.stderr:
                    err = result.stderr[:MAX_OUTPUT_CHARS]
                    if len(result.stderr) > MAX_OUTPUT_CHARS:
                        err += "\n[... stderr truncado ...]"
                    parts.append(f"STDERR:\n{err}")
                if not result.stdout and not result.stderr:
                    parts.append("(Sin salida)")
                return "\n".join(parts)
            except subprocess.TimeoutExpired:
                return f"⏰ Error: El comando superó el timeout de {timeout} s."
            except Exception as e:
                return f"❌ Error al ejecutar el comando: {e}"

    async def _arun(
        self,
        command: str,
        timeout: int = 60,
        streaming: bool = True,
        cwd: Optional[str] = None,
        interactive: bool = True,
        **kwargs: Any,
    ) -> str:
        """Versión asíncrona: delega a un executor para no bloquear el event loop."""
        if streaming and interactive:
            # Modo interactivo: crear sesión PTY real y devolver placeholder HTML
            try:
                from core.pty_sessions import create_session
                acct = getattr(self, "account_id", None) or kwargs.get("account_id")
                if not acct:
                    return "❌ Error: account_id no disponible para crear sesión PTY."
                session_id = await create_session(
                    command=command,
                    account_id=acct,
                    cwd=cwd,
                )
                import html as _html
                safe_cmd = _html.escape(command)
                return (
                    f'<div class="pty-session-placeholder" '
                    f'data-session-id="{session_id}" data-cmd="{safe_cmd}"></div>'
                )
            except Exception as e:
                logger.exception(f"Error creando sesión PTY interactiva: {e}")
                return f"❌ Error al crear terminal interactiva: {e}"
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._run(command, timeout, streaming, cwd, interactive, **kwargs),
            )
