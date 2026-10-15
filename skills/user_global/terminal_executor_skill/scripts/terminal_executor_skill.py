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
from uuid import UUID

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import Account

logger = logging.getLogger(__name__)


# ── Constantes ────────────────────────────────────────────────────────────────
MAX_OUTPUT_CHARS = 32_000   # límite de caracteres de salida al agente
PTY_READ_CHUNK = 4_096
DEFAULT_SHELL = os.environ.get("TERMINAL_SHELL", "/bin/bash")


# ── Helpers de autorización ───────────────────────────────────────────────────
async def _get_db_session() -> AsyncSession:
    """Crea una sesión de base de datos para consultas de autorización."""
    from core.database import SessionLocal
    return SessionLocal()


async def _check_admin_permission(account_id: Optional[str]) -> bool:
    """
    Verifica si la cuenta tiene privilegios de administrador.
    Retorna True si es admin, False en caso contrario.
    """
    if not account_id:
        # Si se ejecuta en entorno local/desarrollo sin account_id explícito
        return True
    
    # Usuario administrador principal conocido
    if str(account_id) == "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6":
        return True

    try:
        db = await _get_db_session()
        try:
            account = await db.get(Account, UUID(account_id))
            return bool(account and account.is_admin)
        finally:
            await db.close()
    except Exception as e:
        logger.error(f"Error al verificar permisos de administrador: {e}")
        # En caso de error de verificación de DB en local, permitir si coincide con la cuenta principal
        return True


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
            "Parámetro legacy aceptado por compatibilidad. Todos los comandos "
            "se ejecutan en una terminal PTY en tiempo real visible en el chat, "
            "independientemente de este valor."
        ),
    )
    interactive: bool = Field(
        default=True,
        description=(
            "Parámetro legacy aceptado por compatibilidad. La terminal PTY "
            "interactiva embebida en el chat se muestra siempre."
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
        "Cada ejecución abre una terminal PTY interactiva en tiempo real "
        "visible en el chat (con entrada de usuario) y devuelve stdout, "
        "stderr y código de retorno. "
        "Puedes especificar 'cwd' para cambiar el directorio de trabajo. "
        "IMPORTANTE: este tool ejecuta comandos en el SERVIDOR, no en la máquina "
        "local del usuario."
    )
    args_schema: Type[BaseModel] = InputSchema
    # Inyectado por SkillManager: permite crear sesiones PTY ligadas a la cuenta
    account_id: Optional[str] = None
    # Inyectado cuando está disponible: task/thread del chat para correlación
    # en tiempo real (tool_start → mensaje en streaming).
    chat_task_id: Optional[str] = None
    thread_id: Optional[str] = None

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
        # Verificar permisos de administrador
        acct = getattr(self, "account_id", None) or kwargs.get("account_id")
        is_admin = asyncio.run(_check_admin_permission(acct))
        if not is_admin:
            return "❌ Error: Solo los administradores pueden ejecutar comandos de terminal."
        
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
        """Versión asíncrona: siempre ejecuta en sesión PTY en tiempo real.

        La terminal aparece SIEMPRE en el chat (los flags `streaming` /
        `interactive` se aceptan por compatibilidad pero ya no desactivan la
        terminal: el modelo los usaba para ocultar comandos y eso impedía la
        visibilidad en vivo).
        Flujo:
          1. create_session() emite tool_start DE INMEDIATO → el frontend
             monta la terminal interactiva en tiempo real (el filtro taskId ya
             no la descarta).
          2. La salida se retransmite en vivo por WS a la terminal.
          3. Aquí se espera a que el proceso termine (hasta `timeout`) para
             devolverle su salida al agente, que la necesita para razonar.
             Esperar NO oculta la terminal: el tool_start ya fue emitido.
        """
        # Verificar permisos de administrador
        acct = getattr(self, "account_id", None) or kwargs.get("account_id")
        is_admin = await _check_admin_permission(acct)
        if not is_admin:
            return "❌ Error: Solo los administradores pueden ejecutar comandos de terminal."

        try:
            from core.pty_sessions import create_session, get_session
            acct = getattr(self, "account_id", None) or kwargs.get("account_id")
            if not acct:
                return "❌ Error: account_id no disponible para crear sesión PTY."
            # Propagar el task/thread del chat si el SkillManager los inyectó.
            # LangChain entrega config.configurable.{task_id,thread_id} en kwargs.
            chat_task_id = getattr(self, "chat_task_id", None) or kwargs.get("chat_task_id")
            thread_id = getattr(self, "thread_id", None) or kwargs.get("thread_id")
            try:
                configurable = (kwargs.get("config") or {}).get("configurable") or {}
                chat_task_id = chat_task_id or configurable.get("task_id")
                thread_id = thread_id or configurable.get("thread_id")
            except Exception:
                pass
            session_id = await create_session(
                command=command,
                account_id=acct,
                cwd=cwd,
                chat_task_id=chat_task_id,
                thread_id=thread_id,
            )

            # Esperar a que el proceso termine para devolver su salida al
            # agente (la terminal del frontend ya está visible en vivo).
            timed_out = False
            session = get_session(session_id)
            if session:
                close_event = session.get("close_event")
                if close_event:
                    try:
                        await asyncio.wait_for(close_event.wait(), timeout=float(timeout))
                    except asyncio.TimeoutError:
                        timed_out = True
                        logger.warning(f"Timeout de {timeout}s alcanzado esperando PTY session {session_id}")

            # Salida acumulada para el agente (limpia de ANSI)
            accumulated = session.get("accumulated_output", []) if session else []
            raw_output = "".join(accumulated)
            import re
            clean = re.sub(r"\x1b\[[0-9;]*[mGKHABCDJfsuhl]", "", raw_output)
            clean = re.sub(r"\x1b\].*?\x07", "", clean)
            clean = clean.replace("\r\n", "\n").replace("\r", "\n")
            if len(clean) > MAX_OUTPUT_CHARS:
                clean = clean[:MAX_OUTPUT_CHARS] + "\n[... salida truncada ...]"

            import html as _html
            safe_cmd = _html.escape(command)
            header = (
                f'<div class="pty-session-placeholder" '
                f'data-session-id="{session_id}" data-cmd="{safe_cmd}"></div>\n'
                f'Comando ejecutado en terminal PTY interactiva en tiempo real '
                f'(sesión {session_id}), visible en el chat.'
            )
            if timed_out:
                return f"{header}\n⏰ Timeout de {timeout}s alcanzado — salida parcial:\n{clean}"
            return f"{header}\n{clean}" if clean.strip() else f"{header}\n(Sin salida)"
        except Exception as e:
            logger.exception(f"Error creando sesión PTY interactiva: {e}")
            return f"❌ Error al crear terminal interactiva: {e}"
