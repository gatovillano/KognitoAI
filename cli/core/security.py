"""
cli/core/security.py
Sandboxing y validación de seguridad para ejecución de comandos shell
que el CLI o el agente IA puedan solicitar.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import List, Optional, Tuple

# ── Listas de control ─────────────────────────────────────────────────────────

# Comandos explícitamente bloqueados (destructivos o de alto riesgo)
BLOCKED_COMMANDS = frozenset({
    "rm", "rmdir", "mkfs", "dd", "shred", "fdisk", "parted",
    "chmod", "chown", "chattr",
    "sudo", "su", "doas",
    "passwd", "adduser", "useradd", "userdel", "usermod",
    "shutdown", "reboot", "halt", "poweroff",
    "iptables", "ufw", "firewall-cmd",
    "curl", "wget",          # pueden exfiltrar datos
    "nc", "netcat", "ncat",  # reverse shells
    "python", "python3", "perl", "ruby", "node",  # ejecución arbitraria
    "bash", "sh", "zsh", "fish", "dash",          # shell anidada
    "eval", "exec",
    "crontab",
    "at",
    "kill", "killall", "pkill",
    "mount", "umount",
    "systemctl", "service",
    "docker", "kubectl", "podman",
    "git",   # podría clonar repos maliciosos
    "pip", "pip3", "npm", "yarn",  # instalación de paquetes
})

# Comandos permitidos explícitamente (lectura, navegación, análisis)
ALLOWED_COMMANDS = frozenset({
    "ls", "ll", "la", "dir",
    "cat", "head", "tail", "less", "more",
    "grep", "rg", "find",
    "pwd", "echo", "printf",
    "wc", "sort", "uniq", "cut", "awk", "sed",
    "diff", "cmp",
    "file", "stat", "du", "df",
    "ps", "top", "htop",
    "date", "uptime",
    "env", "printenv",
    "which", "type",
    "md5sum", "sha256sum",
    "tree",
    "jq",
})

# Patrones de redirección/pipe peligrosos
DANGEROUS_PATTERNS = [
    r">\s*/etc/",          # escritura en /etc
    r">\s*/sys/",          # escritura en /sys
    r">\s*/proc/",         # escritura en /proc
    r">\s*/dev/",          # escritura en /dev
    r">\s*/boot/",         # escritura en /boot
    r"\|\s*bash",          # pipe a bash
    r"\|\s*sh\b",          # pipe a sh
    r";\s*rm\s+",          # rm tras ;
    r"&&\s*rm\s+",         # rm tras &&
    r"\$\(.*\)",           # command substitution
    r"`.*`",               # backtick execution
    r"\bexec\b",
    r"\beval\b",
    r"2>&1.*>\s*/",        # redirección de stderr a rutas del sistema
]

_DANGEROUS_RE = [re.compile(p) for p in DANGEROUS_PATTERNS]


class CommandSecurity:
    """
    Analiza comandos shell antes de ejecutarlos para detectar
    operaciones peligrosas.
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()

    def analyze(self, command: str) -> Tuple[bool, str]:
        """
        Retorna (is_safe, reason).
        is_safe=True → el comando puede ejecutarse.
        is_safe=False → razón por la que fue bloqueado.
        """
        cmd = command.strip()
        if not cmd:
            return False, "Comando vacío"

        # 1. Patrones peligrosos de redirección/substitución
        for pattern in _DANGEROUS_RE:
            if pattern.search(cmd):
                return False, f"Patrón peligroso detectado: {pattern.pattern}"

        # 2. Extraer el binario principal
        try:
            tokens = shlex.split(cmd)
        except ValueError as e:
            return False, f"Comando malformado: {e}"

        if not tokens:
            return False, "Comando vacío"

        base_cmd = Path(tokens[0]).name.lower()

        # 3. Verificar lista de bloqueo
        if base_cmd in BLOCKED_COMMANDS:
            return False, f"Comando bloqueado por política de seguridad: '{base_cmd}'"

        # 4. Si no está en la lista de permitidos, requiere confirmación
        if base_cmd not in ALLOWED_COMMANDS:
            return False, (
                f"Comando desconocido '{base_cmd}'. "
                "Solo se permiten comandos de lectura y análisis."
            )

        # 5. Verificar que no accede a rutas fuera del workspace
        for token in tokens[1:]:
            if token.startswith("/") and not token.startswith(str(self.workspace_root)):
                # Rutas absolutas fuera del workspace son sospechosas
                if any(token.startswith(p) for p in ["/etc", "/sys", "/proc", "/boot", "/root"]):
                    return False, f"Acceso denegado a ruta del sistema: {token}"

        return True, "OK"

    def safe_commands_list(self) -> List[str]:
        return sorted(ALLOWED_COMMANDS)


# ── Input sanitization ────────────────────────────────────────────────────────

def sanitize_filename(name: str, max_len: int = 128) -> str:
    """Sanitiza un nombre de archivo para evitar path traversal."""
    # Eliminar separadores de ruta y caracteres peligrosos
    safe = re.sub(r'[/\\:*?"<>|]', "_", name)
    safe = safe.strip(". ")
    safe = safe[:max_len]
    if not safe:
        safe = "documento"
    return safe


def validate_output_path(path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Valida que la ruta de salida esté dentro del directorio base
    para prevenir path traversal attacks.
    """
    base = base_dir or Path.cwd()
    target = (base / path).resolve()
    # Verificar que la ruta resultante esté dentro del base
    try:
        target.relative_to(base.resolve())
    except ValueError:
        raise ValueError(
            f"Ruta no permitida: '{path}'. "
            f"Los archivos deben guardarse dentro de: {base}"
        )
    return target


def mask_token(token: str) -> str:
    """Enmascara un token JWT para logging seguro."""
    if not token or len(token) < 20:
        return "***"
    return token[:8] + "..." + token[-4:]
