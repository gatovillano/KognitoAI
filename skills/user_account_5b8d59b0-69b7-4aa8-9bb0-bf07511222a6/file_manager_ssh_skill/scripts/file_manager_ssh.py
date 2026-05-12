from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
import subprocess
import os
import re

# ─────────────────────────────────────────────────────────────
# 📋 Esquema de Entrada
# ─────────────────────────────────────────────────────────────
class FileManagerSSHInput(BaseModel):
    operation: str = Field(
        description="""Operación a realizar. Opciones:
        READ: list_dir, read_file, head, tail, stat, file_type, wc, find, tree, exists
        CREATE: write_file, mkdir, cp
        UPDATE: mv, chmod, append
        DELETE: rm, rmdir, remove_recursive
        CONFIG: config""",
        default="list_dir"
    )
    path: str = Field(description="Ruta del archivo o directorio")
    options: Optional[str] = Field(default=None, description="Parámetros adicionales")
    content: Optional[str] = Field(default=None, description="Contenido para write_file o append")
    config_override: Optional[dict] = Field(default=None, description="Configuración SSH personalizada")


# ─────────────────────────────────────────────────────────────
# ⚙️ Configuración SSH (desde variables de entorno)
# ─────────────────────────────────────────────────────────────
def get_default_ssh_config() -> dict:
    """Obtiene configuración SSH por defecto desde variables de entorno."""
    return {
        "host": os.environ.get("SSH_HOST", "127.0.0.1"),
        "port": int(os.environ.get("SSH_PORT", "22")),
        "user": os.environ.get("SSH_USER", "gato"),
        "auth_method": "key",
        "ssh_key_path": os.environ.get("SSH_KEY_PATH", "/tmp/kai_id_ed25519"),
        "timeout": 30
    }


def get_ssh_config(config_override: dict = None) -> dict:
    """Obtiene la configuración SSH combinando default y override."""
    config = get_default_ssh_config()
    if config_override:
        config.update(config_override)
    return config


def sanitize_path(path: str) -> str:
    """Sanitiza la ruta para prevenir inyección de comandos."""
    path = os.path.normpath(path)
    if path.startswith('..'):
        raise ValueError("Rutas con '..' no permitidas")
    return path


def build_ssh_command(config: dict, remote_cmd: str) -> list:
    """Construye el comando SSH según el método de autenticación."""
    ssh_base = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={config.get('timeout', 30)}"
    ]
    
    # Agregar identidad SSH si existe
    if config.get("ssh_key_path"):
        ssh_base.extend(["-i", config["ssh_key_path"]])
    
    if config.get("port") != 22:
        ssh_base.extend(["-p", str(config["port"])])
    
    user_host = f"{config['user']}@{config['host']}"
    
    if config.get("auth_method") == "password" and config.get("password"):
        # Usar sshpass para contraseña
        return [
            "sshpass", "-p", config["password"],
            "ssh"
        ] + ssh_base + [user_host, remote_cmd]
    else:
        # Usar llave SSH
        return ssh_base + [user_host, remote_cmd]


def execute_ssh_command(config: dict, remote_cmd: str) -> tuple:
    """Ejecuta un comando SSH y devuelve (success, output, error)."""
    try:
        cmd = build_ssh_command(config, remote_cmd)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.get("timeout", 30)
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout: el comando tardó demasiado"
    except Exception as e:
        return False, "", f"Error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# 🛠️ Implementación de Operaciones
# ─────────────────────────────────────────────────────────────

def op_list_dir(path: str, config: dict) -> str:
    """Lista archivos en un directorio."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"ls -la --color=auto '{path}' 2>/dev/null || ls -la '{path}'")
    if not success:
        return f"❌ Error: {err}"
    return out if out else "📁 Directorio vacío o sin permisos"


def op_read_file(path: str, config: dict) -> str:
    """Lee el contenido de un archivo."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"cat '{path}' 2>&1")
    if not success:
        return f"❌ Error: {err}"
    return out if out else "📄 Archivo vacío"


def op_head(path: str, config: dict, lines: int = 10) -> str:
    """Muestra las primeras líneas de un archivo."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"head -{lines} '{path}' 2>&1")
    if not success:
        return f"❌ Error: {err}"
    return out if out else "📄 Archivo vacío"


def op_tail(path: str, config: dict, lines: int = 10) -> str:
    """Muestra las últimas líneas de un archivo."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"tail -{lines} '{path}' 2>&1")
    if not success:
        return f"❌ Error: {err}"
    return out if out else "📄 Archivo vacío"


def op_stat(path: str, config: dict) -> str:
    """Muestra información detallada de un archivo."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"stat '{path}' 2>&1")
    if not success:
        return f"❌ Error: {err}"
    return out


def op_file_type(path: str, config: dict) -> str:
    """Determina el tipo de archivo."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"file '{path}' 2>&1")
    if not success:
        return f"❌ Error: {err}"
    return out


def op_wc(path: str, config: dict) -> str:
    """Cuenta líneas, palabras y caracteres."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"wc -lwm '{path}' 2>&1")
    if not success:
        return f"❌ Error: {err}"
    return out


def op_find(path: str, config: dict, pattern: str = "*") -> str:
    """Busca archivos por nombre o patrón."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"find '{path}' -type f -name '{pattern}' 2>/dev/null | head -50")
    if not success:
        return f"❌ Error: {err}"
    return out if out else "🔍 No se encontraron archivos"


def op_tree(path: str, config: dict, depth: int = 2) -> str:
    """Muestra estructura de directorios."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"find '{path}' -maxdepth {depth} -not -path '*/\\.*' | sort | sed 's|[^/]*/|  |g'")
    if not success:
        return f"❌ Error: {err}"
    return out if out else "📁 Directorio vacío"


def op_exists(path: str, config: dict) -> str:
    """Verifica si existe un archivo o directorio."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(config, f"if [ -e '{path}' ]; then echo 'EXISTS'; else echo 'NOT_FOUND'; fi")
    return "✅ Existe" if "EXISTS" in out else "❌ No existe"


def op_write_file(path: str, config: dict, content: str) -> str:
    """Crea o sobrescribe un archivo."""
    path = sanitize_path(path)
    escaped_content = content.replace("'", "'\\'''")
    success, out, err = execute_ssh_command(
        config,
        f"echo '{escaped_content}' > '{path}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Archivo creado/modificado: {path}"
    return f"❌ Error: {err}"


def op_mkdir(path: str, config: dict, parents: bool = True) -> str:
    """Crea un directorio."""
    path = sanitize_path(path)
    flag = "-p" if parents else ""
    success, out, err = execute_ssh_command(
        config,
        f"mkdir {flag} '{path}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Directorio creado: {path}"
    return f"❌ Error: {err}"


def op_cp(path: str, config: dict, dest: str) -> str:
    """Copia archivos o directorios."""
    path = sanitize_path(path)
    dest = sanitize_path(dest)
    success, out, err = execute_ssh_command(
        config,
        f"cp -r '{path}' '{dest}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Copiado: {path} → {dest}"
    return f"❌ Error: {err}"


def op_mv(path: str, config: dict, dest: str) -> str:
    """Mueve o renombra archivos."""
    path = sanitize_path(path)
    dest = sanitize_path(dest)
    success, out, err = execute_ssh_command(
        config,
        f"mv '{path}' '{dest}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Movido: {path} → {dest}"
    return f"❌ Error: {err}"


def op_chmod(path: str, config: dict, mode: str) -> str:
    """Cambia permisos de archivo."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(
        config,
        f"chmod {mode} '{path}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Permisos cambiados: {path} ({mode})"
    return f"❌ Error: {err}"


def op_append(path: str, config: dict, content: str) -> str:
    """Agrega contenido a un archivo."""
    path = sanitize_path(path)
    escaped_content = content.replace("'", "'\\'''")
    success, out, err = execute_ssh_command(
        config,
        f"echo '{escaped_content}' >> '{path}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Contenido agregado a: {path}"
    return f"❌ Error: {err}"


def op_rm(path: str, config: dict, recursive: bool = False) -> str:
    """Elimina archivos."""
    path = sanitize_path(path)
    flag = "-rf" if recursive else "-f"
    success, out, err = execute_ssh_command(
        config,
        f"rm {flag} '{path}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Eliminado: {path}"
    return f"❌ Error: {err}"


def op_rmdir(path: str, config: dict) -> str:
    """Elimina directorios vacíos."""
    path = sanitize_path(path)
    success, out, err = execute_ssh_command(
        config,
        f"rmdir '{path}' && echo OK || echo ERROR"
    )
    if "OK" in out:
        return f"✅ Directorio eliminado: {path}"
    return f"❌ Error: {err}"


# ─────────────────────────────────────────────────────────────
# 🔧 Clase Principal de la Herramienta
# ─────────────────────────────────────────────────────────────
class FileManagerSSH(BaseTool):
    name: str = "file_manager_ssh"
    description: str = "Gestión de archivos CRUD en el host via SSH (soporta llave y contraseña)"
    args_schema: Type[BaseModel] = FileManagerSSHInput

    def _run(self, operation: str = "list_dir", path: str = ".", options: Optional[str] = None, 
             content: Optional[str] = None, config_override: Optional[dict] = None) -> str:
        """Ejecuta la operación solicitada."""
        config = get_ssh_config(config_override)
        
        operations = {
            # READ
            "list_dir": lambda: op_list_dir(path, config),
            "read_file": lambda: op_read_file(path, config),
            "head": lambda: op_head(path, config, int(options) if options else 10),
            "tail": lambda: op_tail(path, config, int(options) if options else 10),
            "stat": lambda: op_stat(path, config),
            "file_type": lambda: op_file_type(path, config),
            "wc": lambda: op_wc(path, config),
            "find": lambda: op_find(path, config, options or "*"),
            "tree": lambda: op_tree(path, config, int(options) if options else 2),
            "exists": lambda: op_exists(path, config),
            # CREATE
            "write_file": lambda: op_write_file(path, config, content or ""),
            "mkdir": lambda: op_mkdir(path, config),
            "cp": lambda: op_cp(path, config, options or ""),
            # UPDATE
            "mv": lambda: op_mv(path, config, options or ""),
            "chmod": lambda: op_chmod(path, config, options or ""),
            "append": lambda: op_append(path, config, content or ""),
            # DELETE
            "rm": lambda: op_rm(path, config, recursive=False),
            "rmdir": lambda: op_rmdir(path, config),
            "remove_recursive": lambda: op_rm(path, config, recursive=True),
        }
        
        op_key = operation.lower()
        if op_key not in operations:
            return f"❌ Operación '{operation}' no soportada. Opciones: {', '.join(operations.keys())}"
        
        return operations[op_key]()
    
    async def _arun(self, operation: str = "list_dir", path: str = ".", options: Optional[str] = None,
                    content: Optional[str] = None, config_override: Optional[dict] = None) -> str:
        """Versión asíncrona (simple wrapper)."""
        return self._run(operation, path, options, content, config_override)


if __name__ == "__main__":
    tool = FileManagerSSH()
    print("🔄 Creando archivo de prueba en el home...")
    result = tool._run(
        operation="write_file",
        path="~/test_kai.txt",
        content="✅ Este archivo fue creado por KAI via SSH"
    )
    print(result)
