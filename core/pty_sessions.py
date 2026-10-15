"""
core/pty_sessions.py

Manejador simple de sesiones PTY interactivas.
- create_session(...) crea un PTY, lanza el comando y arranca una tarea que
  lee la salida y la retransmite tanto al chat (stream_chunk) como a las
  conexiones de tipo 'terminal' (output).
- write_to_session(session_id, data) escribe datos al PTY (input del usuario).
- get_session(session_id) devuelve metadatos de la sesión en memoria.

Notas:
- Este módulo es intencionalmente ligero y orientado a un deploy MONO-PROCESO.
- En producción con múltiples instancias, reemplazar por un backend persistente
  (Redis pub/sub + worker encargado de las PTYs) es recomendado.
"""

import asyncio
import fcntl
import logging
import os
import pty
import struct
import subprocess
import termios
import uuid
from typing import Optional, Dict, Any

from core.websocket_manager import send_personal_message

logger = logging.getLogger(__name__)

PTY_READ_CHUNK = 4096
DEFAULT_SHELL = os.environ.get("TERMINAL_SHELL", "/bin/bash")

_sessions: Dict[str, Dict[str, Any]] = {}


def _set_pty_size(fd: int, cols: int = 220, rows: int = 50) -> None:
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass


async def create_session(
    command: str,
    account_id: str,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    session_id: Optional[str] = None,
    cols: int = 220,
    rows: int = 50,
    chat_task_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> str:
    """
    Crea una sesión PTY asíncrona que ejecuta `command` y retransmite la salida.
    Retorna el session_id.
    Si se provee chat_task_id, el evento tool_start lo reutiliza para que el
    frontend pueda asociar la terminal al mensaje en streaming en tiempo real
    (estilo kogniterm-desktop). Si no, usa session_id como fallback.
    """
    if session_id is None:
        session_id = uuid.uuid4().hex

    loop = asyncio.get_running_loop()

    master_fd, slave_fd = await loop.run_in_executor(None, pty.openpty)
    _set_pty_size(master_fd, cols=cols, rows=rows)

    _env = os.environ.copy()
    if env:
        _env.update(env)
    _env.update({"TERM": "xterm-256color", "LANG": "en_US.UTF-8"})

    def _start_proc():
        # Iniciar el proceso dentro del PTY
        def _child_setup():
            # Darle al hijo su propia sesión y terminal controladora para
            # que programas interactivos (sudo, ssh, passwd…) puedan abrir
            # /dev/tty y pedir passwords. Sin esto sudo falla o se cuelga
            # sin mostrar el prompt.
            try:
                os.setsid()
                fcntl.ioctl(0, termios.TIOCSCTTY, 0)
            except Exception:
                pass

        try:
            cmd_args = ["/bin/bash", "-c", command] if isinstance(command, str) else command
            proc = subprocess.Popen(
                cmd_args,
                shell=False,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=_env,
                cwd=cwd or None,
                preexec_fn=_child_setup,
            )
            # el padre no necesita el fd slave
            try:
                os.close(slave_fd)
            except Exception:
                pass
            return proc
        except Exception:
            try:
                os.close(slave_fd)
            except Exception:
                pass
            raise

    proc = await loop.run_in_executor(None, _start_proc)

    session = {
        "master_fd": master_fd,
        "proc": proc,
        "account_id": account_id,
        "task_id": session_id,
        "chat_task_id": chat_task_id,
        "thread_id": thread_id,
        "command": command,
        "cols": cols,
        "rows": rows,
        "closed": False,
        "accumulated_output": [],
        "close_event": asyncio.Event(),
    }
    _sessions[session_id] = session

    # Notificar inicio de la terminal para estado de herramientas.
    # Se envía DE INMEDIATO (antes de que el comando termine) para que el
    # frontend monte la terminal interactiva en tiempo real, estilo
    # kogniterm-desktop: desplegada, persistente y con input habilitado.
    # taskId = chat_task_id cuando se conoce, para que CommonChat lo asocie
    # al mensaje en streaming sin filtrarlo; session_task_id permite
    # correlacionar el tool_end posterior aunque el taskId difiera.
    try:
        display_cmd = command if isinstance(command, str) else " ".join(command)
        tool_start_msg: Dict[str, Any] = {
            "type": "tool_start",
            "taskId": chat_task_id or session_id,
            "tool_name": "terminal_executor",
            "message": f"Ejecutando en terminal: {display_cmd[:200]}",
            "pty_session": {"session_id": session_id, "command": display_cmd[:500]},
            "session_task_id": session_id,
        }
        if thread_id:
            tool_start_msg["thread_id"] = thread_id
        await send_personal_message(
            account_id,
            tool_start_msg,
        )
    except Exception:
        logger.exception("Error notificando inicio de sesión PTY")

    # Lanzar tarea que lee el PTY y retransmite
    asyncio.create_task(_reader_loop(session_id))

    return session_id


async def _reader_loop(session_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        return

    master_fd = session["master_fd"]
    account_id = session["account_id"]
    task_id = session.get("task_id")

    loop = asyncio.get_running_loop()
    accumulated: list[str] = []

    try:
        while True:
            chunk = await loop.run_in_executor(None, lambda: os.read(master_fd, PTY_READ_CHUNK))
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            accumulated.append(text)

            # Guardar en el historial de la sesión si aún existe
            current_session = _sessions.get(session_id)
            if current_session:
                current_session.setdefault("accumulated_output", []).append(text)

            # Enviar a clientes terminales conectados (tipo conexión: 'terminal').
            # Se etiqueta con session_id para que cada terminal embebida filtre
            # solo su sesión (varias terminales pueden coexistir en el chat).
            try:
                await send_personal_message(account_id, {"type": "output", "data": text, "session_id": session_id}, connection_type="terminal")
            except Exception:
                logger.exception("Error enviando output a conexiones 'terminal'")

    except Exception:
        logger.exception("Error en reader loop PTY")

    finally:
        # Intentar obtener returncode
        try:
            returncode = session["proc"].wait(timeout=0.1)
        except Exception:
            try:
                session["proc"].wait(timeout=1)
            except Exception:
                returncode = None

        try:
            tool_end_msg: Dict[str, Any] = {
                "type": "tool_end",
                "taskId": session.get("chat_task_id") or task_id,
                "tool_name": "terminal_executor",
                "message": f"Terminal finalizada (exit: {returncode})",
                "session_task_id": session_id,
                "pty_session": {"session_id": session_id},
            }
            if session.get("thread_id"):
                tool_end_msg["thread_id"] = session["thread_id"]
            await send_personal_message(
                account_id,
                tool_end_msg,
            )
        except Exception:
            logger.exception("Error enviando tool_end")

        try:
            os.close(master_fd)
        except Exception:
            pass

        session["closed"] = True
        
        # Activar el evento de cierre si existe
        close_event = session.get("close_event")
        if close_event:
            close_event.set()

        # Mantener la sesión en memoria durante 5 minutos para que el frontend
        # pueda recuperar el historial de salida antes de ser limpiada
        async def delayed_pop():
            await asyncio.sleep(300)
            _sessions.pop(session_id, None)
        
        asyncio.create_task(delayed_pop())


async def write_to_session(session_id: str, data: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise RuntimeError("Session not found")
    master_fd = session["master_fd"]
    loop = asyncio.get_running_loop()
    # Escribir en el PTY de forma no bloqueante
    await loop.run_in_executor(None, lambda: os.write(master_fd, data.encode("utf-8")))


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _sessions.get(session_id)


async def resize_session(session_id: str, cols: int = 80, rows: int = 24) -> None:
    """Ajusta el tamaño del PTY para una sesión existente."""
    session = _sessions.get(session_id)
    if not session:
        raise RuntimeError("Session not found")
    master_fd = session.get("master_fd")
    if master_fd is None:
        raise RuntimeError("Master FD not available for session")
    # Actualizar metadatos
    session["cols"] = cols
    session["rows"] = rows
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: _set_pty_size(master_fd, cols=cols, rows=rows))


async def close_session(session_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        return
    try:
        proc = session.get("proc")
        if proc and proc.poll() is None:
            proc.terminate()
    except Exception:
        logger.exception("Error terminando proceso PTY")
    finally:
        try:
            mfd = session.get("master_fd")
            if mfd is not None:
                os.close(mfd)
        except Exception:
            pass
        _sessions.pop(session_id, None)


async def log_pty_audit(user_id: str, command: str, exit_code: Optional[int] = 0, session_id: Optional[str] = None, ip_address: Optional[str] = None) -> None:
    """Registra comandos PTY en la tabla pty_audit_logs."""
    try:
        from core.database import SessionLocal, PTYAuditLog
        async with SessionLocal() as db:
            log_entry = PTYAuditLog(
                user_id=str(user_id),
                command=command,
                exit_code=exit_code,
                session_id=session_id,
                ip_address=ip_address
            )
            db.add(log_entry)
            await db.commit()
    except Exception as e:
        logger.error(f"Error registrando auditoría PTY: {e}")


async def cleanup_orphan_pty_sessions() -> int:
    """Termina todos los procesos PTY huérfanos o cerrados en memoria (Watchdog PTY)."""
    cleaned = 0
    to_remove = []
    for s_id, session in list(_sessions.items()):
        proc = session.get("proc")
        if not proc or proc.poll() is not None:
            to_remove.append(s_id)
            continue
        try:
            proc.terminate()
            cleaned += 1
        except Exception:
            pass
        to_remove.append(s_id)

    for s_id in to_remove:
        _sessions.pop(s_id, None)

    if cleaned > 0:
        logger.info(f"🧹 Watchdog PTY: {cleaned} sesiones huérfanas terminadas.")
    return cleaned


