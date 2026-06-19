# api/terminal.py
"""
WebSocket endpoint para terminal PTY interactiva en tiempo real.

Flujo:
  1. El cliente abre WS en /ws/terminal/{account_id}?token=JWT
  2. El backend crea un PTY con pty.openpty(), lanza una shell bash en el slave
  3. Toda la salida del PTY se envía al cliente como mensajes WS binarios
  4. Todo lo que el cliente envíe (texto + resize) se escribe al maestro del PTY

Protocolo de mensajes del cliente → servidor:
  - Texto/teclas:  { "type": "input",  "data": "<chars>" }
  - Resize:        { "type": "resize", "cols": N, "rows": N }

Protocolo de mensajes del servidor → cliente:
  - Salida shell:  { "type": "output", "data": "<text>" }
  - Error/cierre:  { "type": "error",  "data": "<msg>"  }
"""

import asyncio
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import termios

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from utils.security import decode_access_token
from core.websocket_manager import manager as websocket_manager
from core.pty_sessions import write_to_session, get_session, resize_session
from core.database import SessionLocal, Account
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter()

# Tamaño máximo de buffer de lectura del PTY por iteración
PTY_READ_CHUNK = 4096
# Shell a lanzar en el PTY (bash por defecto, con fallback a sh)
DEFAULT_SHELL = os.environ.get("TERMINAL_SHELL", "/bin/bash")


def _set_pty_size(fd: int, cols: int, rows: int) -> None:
    """Ajusta el tamaño de la ventana del PTY (TIOCSWINSZ)."""
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except Exception as e:
        logger.warning(f"No se pudo ajustar el tamaño del PTY: {e}")


@router.websocket("/ws/terminal/{account_id}")
async def terminal_websocket(websocket: WebSocket, account_id: str):
    """
    Terminal PTY interactiva en tiempo real sobre WebSocket.
    Autenticación mediante JWT en query-param 'token'.
    """
    # ── 1. Autenticación ──────────────────────────────────────────────────────
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token requerido")
        return

    try:
        payload = decode_access_token(token)
        if not payload or payload.get("sub") != account_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido")
            return
    except Exception as e:
        logger.warning(f"Auth error en terminal WS: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Error de autenticación")
        return

    # ── 1.5. Verificación de rol de administrador ─────────────────────────────
    # Solo los administradores pueden crear o conectarse a sesiones PTY.
    async with SessionLocal() as db:
        result = await db.execute(select(Account).where(Account.id == account_id))
        account = result.scalars().first()
        if not account or not account.is_admin:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Se requieren permisos de administrador para acceder a la terminal PTY"
            )
            return

    await websocket.accept()
    session_id = websocket.query_params.get("session_id")
    # If the client attaches to an existing PTY session, register as a terminal client and proxy inputs
    if session_id:
        # Register connection so pty_sessions can push output (connection_type='terminal')
        await websocket_manager.connect(websocket, account_id, connection_type="terminal")
        logger.info(f"Terminal cliente conectado para cuenta {account_id}, sesión {session_id}")
        session = get_session(session_id)
        if not session or session.get("account_id") != account_id:
            await websocket.send_json({"type": "error", "data": "Session not found or not authorized"})
            websocket_manager.disconnect(websocket, account_id, "terminal")
            await websocket.close()
            return
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    msg = json.loads(msg_text)
                except json.JSONDecodeError:
                    msg = {"type": "input", "data": msg_text}

                msg_type = msg.get("type", "input")

                if msg_type == "input":
                    data = msg.get("data", "")
                    if data:
                        await write_to_session(session_id, data)

                elif msg_type == "resize":
                    cols = int(msg.get("cols", 80))
                    rows = int(msg.get("rows", 24))
                    try:
                        await resize_session(session_id, cols=cols, rows=rows)
                    except Exception as e:
                        logger.warning(f"resize_session failed: {e}")

        except WebSocketDisconnect:
            logger.info(f"Terminal cliente desconectado (sesión {session_id}) para cuenta {account_id}")
        except Exception as e:
            logger.exception(f"Error en terminal WS cliente: {e}")
        finally:
            websocket_manager.disconnect(websocket, account_id, "terminal")
            return

    logger.info(f"Terminal PTY abierta para cuenta {account_id}")

    # ── 2. Crear PTY y lanzar shell ──────────────────────────────────────────
    master_fd, slave_fd = pty.openpty()

    # Ajuste de tamaño inicial razonable
    _set_pty_size(master_fd, cols=220, rows=50)

    pid = os.fork()
    if pid == 0:
        # Proceso hijo: ejecuta la shell dentro del PTY
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(master_fd)
        os.close(slave_fd)
        env = os.environ.copy()
        env.update({
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "LANG": "en_US.UTF-8",
        })
        os.execve(DEFAULT_SHELL, [DEFAULT_SHELL, "--login"], env)
        os._exit(1)  # por si execve falla

    # Proceso padre: cierra el slave y opera sobre master_fd
    os.close(slave_fd)
    # Si el cliente proporcionó un comando inicial via ?cmd=..., enviarlo al PTY
    initial_cmd = websocket.query_params.get("cmd")
    loop = asyncio.get_event_loop()
    if initial_cmd:
        try:
            # Escribir el comando en el PTY usando un executor para no bloquear el event loop
            loop.run_in_executor(None, lambda: os.write(master_fd, (initial_cmd + "\n").encode("utf-8")))
        except Exception as e:
            logger.warning(f"No se pudo enviar el comando inicial al PTY: {e}")

    # ── 3. Tarea: leer PTY → enviar al cliente ───────────────────────────────
    async def pty_to_ws():
        try:
            while True:
                try:
                    data = await loop.run_in_executor(
                        None,
                        lambda: os.read(master_fd, PTY_READ_CHUNK)
                    )
                    if not data:
                        break
                    await websocket.send_json({
                        "type": "output",
                        "data": data.decode("utf-8", errors="replace")
                    })
                except OSError:
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"Error en pty_to_ws: {e}")

    # ── 4. Tarea: recibir del cliente → escribir al PTY ─────────────────────
    async def ws_to_pty():
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    msg = json.loads(msg_text)
                except json.JSONDecodeError:
                    # Texto plano → tratar como input directo
                    msg = {"type": "input", "data": msg_text}

                msg_type = msg.get("type", "input")

                if msg_type == "input":
                    data = msg.get("data", "")
                    if data:
                        await loop.run_in_executor(
                            None,
                            lambda d=data: os.write(master_fd, d.encode("utf-8"))
                        )

                elif msg_type == "resize":
                    cols = int(msg.get("cols", 80))
                    rows = int(msg.get("rows", 24))
                    _set_pty_size(master_fd, cols, rows)

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"ws_to_pty terminada: {e}")

    # ── 5. Ejecutar ambas tareas concurrentemente ────────────────────────────
    try:
        read_task = asyncio.create_task(pty_to_ws())
        write_task = asyncio.create_task(ws_to_pty())

        done, pending = await asyncio.wait(
            [read_task, write_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    finally:
        # ── 6. Limpieza ──────────────────────────────────────────────────────
        try:
            os.kill(pid, signal.SIGTERM)
            await asyncio.sleep(0.2)
            os.waitpid(pid, os.WNOHANG)
        except Exception:
            pass
        try:
            os.close(master_fd)
        except Exception:
            pass
        logger.info(f"Terminal PTY cerrada para cuenta {account_id}")
