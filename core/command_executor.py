import os
import pty
import select
import subprocess
import sys
import termios
import time
import tty
import queue
import logging
from typing import Optional, Generator

logger = logging.getLogger(__name__)

class CommandExecutor:
    def __init__(self):
        self.process = None

    def execute(self, command: str, cwd: Optional[str] = None, interrupt_queue: Optional[queue.Queue] = None) -> Generator[str, None, None]:
        """
        Ejecuta un comando en un pseudo-terminal (PTY), permitiendo la comunicación interactiva.
        Captura la salida del comando y la cede (yields) en tiempo real.
        """
        # Guardar la configuración original de la terminal si estamos en un TTY
        old_settings = None
        is_tty = sys.stdin.isatty()
        
        if is_tty:
            try:
                old_settings = termios.tcgetattr(sys.stdin.fileno())
                tty.setraw(sys.stdin.fileno())
            except termios.error as e:
                logger.warning(f"No se pudo configurar el modo raw de la terminal: {e}")
                is_tty = False

        master_fd, slave_fd = pty.openpty()

        try:
            # Si el comando contiene 'sudo', envolverlo con 'script -qc' para manejar la solicitud de contraseña
            if command.strip().startswith("sudo "):
                command = f"script -qc '{command}' /dev/null"
                
            # Iniciar el proceso del comando en el PTY
            self.process = subprocess.Popen(
                command,
                shell=True,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                preexec_fn=os.setsid,  # Crear una nueva sesión de proceso
                cwd=cwd
            )

            # Bucle principal de E/S
            while self.process.poll() is None:
                # Verificar interrupción
                if interrupt_queue and not interrupt_queue.empty():
                    interrupt_queue.get()
                    self.terminate()
                    yield "\n[Comando cancelado]"
                    break

                try:
                    # Esperar E/S
                    inputs = [master_fd]
                    if is_tty:
                        inputs.append(sys.stdin.fileno())
                        
                    readable_fds, _, _ = select.select(inputs, [], [], 0.1)

                    # Manejar salida
                    if master_fd in readable_fds:
                        try:
                            output = os.read(master_fd, 1024).decode(errors='replace')
                            if output:
                                if is_tty:
                                    sys.stdout.write(output)
                                    sys.stdout.flush()
                                yield output
                        except OSError:
                            break

                    # Manejar entrada (solo si es TTY)
                    if is_tty and sys.stdin.fileno() in readable_fds:
                        user_input = os.read(sys.stdin.fileno(), 1024)
                        if user_input:
                            os.write(master_fd, user_input)

                except select.error as e:
                    if e.args[0] == 4: # EINTR
                        continue
                    raise

            self.process.wait()

        finally:
            # Restaurar terminal
            if is_tty and old_settings:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
            
            os.close(master_fd)
            try:
                os.close(slave_fd)
            except:
                pass
            self.process = None

    def terminate(self):
        if self.process and self.process.poll() is None:
            import signal
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception as e:
                logger.error(f"Error al terminar proceso: {e}")
