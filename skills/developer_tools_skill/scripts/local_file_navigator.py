from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
import os
import stat
import json
from pathlib import Path
from datetime import datetime


class InputSchema(BaseModel):
    action: str = Field(description="Acción a realizar: 'list', 'read', 'info', 'search'")
    path: Optional[str] = Field(default=".", description="Ruta relativa o absoluta")
    file_name: Optional[str] = Field(default=None, description="Nombre del archivo a leer (para 'read')")
    pattern: Optional[str] = Field(default=None, description="Patrón de búsqueda glob (para 'search')")
    recursive: Optional[bool] = Field(default=False, description="Búsqueda recursiva")
    max_results: Optional[int] = Field(default=50, description="Máximo de resultados")
    account_id: Optional[str] = Field(default=None, description="ID de la cuenta del usuario para obtener la configuración SSH guardada.")


class LocalFileNavigator(BaseTool):
    name: str = "local_file_navigator"
    description: str = """Navegador de archivos que puede operar tanto en local como de forma remota vía SSH.
    Cuando se configura SSH en la cuenta del usuario (ssh_host, ssh_user, local_base_path), conecta automáticamente
    al servidor remoto usando credenciales cifradas guardadas.

    Acciones disponibles:
    - 'list': Lista archivos y directorios en la ruta especificada
    - 'read': Lee el contenido completo de un archivo de texto
    - 'info': Obtiene metadatos detallados de un archivo o directorio
    - 'search': Busca archivos que coincidan con un patrón glob

    Ejemplos:
    - action='list', path='/home/gato/Proyectos'
    - action='read', path='/home/gato/Proyectos/app', file_name='main.py'
    - action='search', path='/home/gato/Proyectos', pattern='*.py', recursive=True
    """
    args_schema: Type[BaseModel] = InputSchema

    def _get_ssh_config(self, account_id: Optional[str]) -> Optional[dict]:
        """Obtiene la configuración SSH desde la base de datos del usuario."""
        if not account_id:
            return None
        try:
            import asyncio
            from core.database import SessionLocal, Account
            from core.repositories.secret_repository import SecretRepository
            import uuid

            async def _fetch():
                async with SessionLocal() as db:
                    account = await db.get(Account, uuid.UUID(account_id))
                    if not account or not account.ssh_host:
                        return None

                    repo = SecretRepository(db)
                    password = await repo.get_decrypted_secret(uuid.UUID(account_id), 'SSH_PASSWORD')
                    private_key = await repo.get_decrypted_secret(uuid.UUID(account_id), 'SSH_PRIVATE_KEY')

                    return {
                        "host": account.ssh_host,
                        "port": int(account.ssh_port or 22),
                        "username": account.ssh_user,
                        "base_path": account.local_base_path or "/",
                        "password": password,
                        "private_key": private_key,
                    }

            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _fetch())
                    return future.result(timeout=10)
            except RuntimeError:
                return asyncio.run(_fetch())

        except Exception as e:
            return None

    def _get_ssh_client(self, config: dict):
        """Crea y retorna un cliente SSH paramiko conectado."""
        import paramiko
        import io

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": config["host"],
            "port": config["port"],
            "username": config["username"],
            "timeout": 15,
        }

        if config.get("private_key"):
            try:
                key_obj = paramiko.RSAKey.from_private_key(io.StringIO(config["private_key"]))
                connect_kwargs["pkey"] = key_obj
            except Exception:
                try:
                    key_obj = paramiko.Ed25519Key.from_private_key(io.StringIO(config["private_key"]))
                    connect_kwargs["pkey"] = key_obj
                except Exception:
                    pass

        if config.get("password") and "pkey" not in connect_kwargs:
            connect_kwargs["password"] = config["password"]

        client.connect(**connect_kwargs)
        return client

    def _validate_path(self, path: str, base_path: str) -> str:
        """Valida que la ruta esté dentro del directorio base permitido."""
        resolved = os.path.normpath(os.path.join(base_path, path))
        if not resolved.startswith(os.path.normpath(base_path)):
            raise PermissionError(f"Acceso denegado: La ruta '{path}' está fuera del directorio raíz permitido '{base_path}'.")
        return resolved

    def _run(self, action: str, path: Optional[str] = None, file_name: Optional[str] = None,
             pattern: Optional[str] = None, recursive: bool = False, max_results: int = 50,
             account_id: Optional[str] = None) -> str:
        try:
            ssh_config = self._get_ssh_config(account_id)

            if ssh_config:
                return self._run_ssh(action, path or ".", file_name, pattern, recursive, max_results, ssh_config)
            else:
                return self._run_local(action, path or ".", file_name, pattern, recursive, max_results)
        except Exception as e:
            return f"❌ Error ejecutando '{action}': {str(e)}"

    # ───────────────────────── SSH MODE ─────────────────────────

    def _run_ssh(self, action, path, file_name, pattern, recursive, max_results, config):
        """Ejecuta la acción de forma remota vía SSH."""
        client = self._get_ssh_client(config)
        sftp = client.open_sftp()
        base = config["base_path"]

        try:
            safe_path = self._validate_path(path, base)

            if action == 'list':
                return self._ssh_list(sftp, safe_path)
            elif action == 'read':
                return self._ssh_read(sftp, safe_path, file_name)
            elif action == 'info':
                return self._ssh_info(sftp, safe_path)
            elif action == 'search':
                return self._ssh_search(client, safe_path, pattern, recursive, max_results)
            else:
                return f"❌ Acción '{action}' no reconocida. Use: list, read, info, search."
        finally:
            sftp.close()
            client.close()

    def _ssh_list(self, sftp, path: str) -> str:
        try:
            items = sftp.listdir_attr(path)
            result = [f"📁 Contenido remoto de: {path}", f"Total: {len(items)} elementos", ""]
            dirs, files = [], []
            for item in items:
                is_dir = stat.S_ISDIR(item.st_mode)
                if is_dir:
                    dirs.append(item)
                else:
                    files.append(item)

            if dirs:
                result.append("📂 Directorios:")
                for d in sorted(dirs, key=lambda x: x.filename):
                    result.append(f"  📁 {d.filename}/")
            if files:
                result.append("📄 Archivos:")
                for f in sorted(files, key=lambda x: x.filename):
                    size = self._format_size(f.st_size)
                    date = datetime.fromtimestamp(f.st_mtime).strftime('%Y-%m-%d %H:%M')
                    result.append(f"  📄 {f.filename} ({size}) - {date}")
            return "\n".join(result)
        except Exception as e:
            return f"❌ Error listando directorio SSH: {e}"

    def _ssh_read(self, sftp, base_path: str, file_name: Optional[str]) -> str:
        if not file_name:
            return "❌ Debes especificar 'file_name' para 'read'."
        full_path = os.path.join(base_path, file_name)
        try:
            with sftp.open(full_path, 'r') as f:
                content = f.read(15000).decode('utf-8', errors='ignore')
            if len(content) >= 15000:
                content += "\n... [contenido truncado] ..."
            return f"📖 Contenido remoto de: {full_path}\n\n{content}"
        except Exception as e:
            return f"❌ Error leyendo archivo SSH: {e}"

    def _ssh_info(self, sftp, path: str) -> str:
        try:
            attr = sftp.stat(path)
            is_dir = stat.S_ISDIR(attr.st_mode)
            info = [
                f"🔍 Información remota de: {path}",
                f"Tipo: {'Directorio' if is_dir else 'Archivo'}",
                f"Tamaño: {self._format_size(attr.st_size)}",
                f"Modificado: {datetime.fromtimestamp(attr.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
                f"Permisos: {oct(stat.S_IMODE(attr.st_mode))}",
            ]
            return "\n".join(info)
        except Exception as e:
            return f"❌ Error obteniendo info SSH: {e}"

    def _ssh_search(self, client, base_path: str, pattern: Optional[str], recursive: bool, max_results: int) -> str:
        if not pattern:
            return "❌ Debes especificar 'pattern' para 'search'."
        try:
            if recursive:
                cmd = f"find '{base_path}' -name '{pattern}' 2>/dev/null | head -{max_results}"
            else:
                cmd = f"find '{base_path}' -maxdepth 1 -name '{pattern}' 2>/dev/null | head -{max_results}"
            _, stdout, _ = client.exec_command(cmd)
            results = stdout.read().decode().strip().splitlines()
            if not results:
                return f"🔍 No se encontraron resultados para '{pattern}' en '{base_path}'"
            output = [f"🔍 Resultados para '{pattern}' en '{base_path}' (remoto):", f"Encontrados: {len(results)}", ""]
            for r in results:
                output.append(f"  📄 {r}")
            return "\n".join(output)
        except Exception as e:
            return f"❌ Error buscando en SSH: {e}"

    # ─────────────────────── LOCAL MODE ──────────────────────────

    def _run_local(self, action, path, file_name, pattern, recursive, max_results):
        """Ejecuta la acción de forma local en el sistema de archivos."""
        base_path = Path(path) if path else Path.cwd()

        if action == 'list':
            return self._list_directory(base_path)
        elif action == 'read':
            return self._read_file(base_path, file_name)
        elif action == 'info':
            return self._get_info(base_path)
        elif action == 'search':
            return self._search_files(base_path, pattern, recursive, max_results)
        else:
            return f"❌ Acción '{action}' no reconocida. Use: list, read, info, search."

    def _list_directory(self, path: Path) -> str:
        if not path.exists():
            return f"❌ La ruta '{path}' no existe."
        if not path.is_dir():
            return f"❌ '{path}' no es un directorio."
        try:
            items = list(path.iterdir())
            result = [f"📁 Contenido de: {path.absolute()}", f"Total: {len(items)} elementos", ""]
            dirs = [(i, 0) for i in items if i.is_dir()]
            files = [(i, i.stat().st_size) for i in items if i.is_file()]

            if dirs:
                result.append("📂 Directorios:")
                for item, _ in sorted(dirs, key=lambda x: x[0].name.lower()):
                    result.append(f"  📁 {item.name}/")
            if files:
                result.append("📄 Archivos:")
                for item, size in sorted(files, key=lambda x: x[0].name.lower()):
                    date = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    result.append(f"  📄 {item.name} ({self._format_size(size)}) - {date}")
            return "\n".join(result)
        except PermissionError:
            return f"❌ Permiso denegado para '{path}'"

    def _read_file(self, base_path: Path, file_name: Optional[str]) -> str:
        if not file_name:
            return "❌ Debes especificar 'file_name' para 'read'."
        file_path = base_path / file_name
        if not file_path.exists():
            return f"❌ El archivo '{file_path}' no existe."
        if not file_path.is_file():
            return f"❌ '{file_path}' no es un archivo."
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(15000)
            if len(content) >= 15000:
                content += "\n... [contenido truncado] ..."
            return f"📖 Contenido de: {file_path.absolute()}\n\n{content}"
        except Exception as e:
            return f"❌ Error leyendo archivo: {e}"

    def _get_info(self, path: Path) -> str:
        if not path.exists():
            return f"❌ La ruta '{path}' no existe."
        try:
            s = path.stat()
            return "\n".join([
                f"🔍 Información de: {path.absolute()}",
                f"Tipo: {'Directorio' if path.is_dir() else 'Archivo'}",
                f"Tamaño: {self._format_size(s.st_size)}",
                f"Creado: {datetime.fromtimestamp(s.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}",
                f"Modificado: {datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
                f"Permisos: {oct(s.st_mode)[-3:]}",
                *([ f"Extensión: {path.suffix}" ] if path.is_file() else []),
            ])
        except Exception as e:
            return f"❌ Error obteniendo información: {e}"

    def _search_files(self, base_path: Path, pattern: Optional[str], recursive: bool, max_results: int) -> str:
        if not pattern:
            return "❌ Debes especificar 'pattern' para 'search'."
        if not base_path.exists():
            return f"❌ La ruta '{base_path}' no existe."
        try:
            results = []
            iterator = base_path.rglob(pattern) if recursive else base_path.glob(pattern)
            for item in iterator:
                if len(results) >= max_results:
                    break
                results.append(item)
            if not results:
                return f"🔍 Sin resultados para '{pattern}' en '{base_path}'"
            output = [f"🔍 Resultados de búsqueda: '{pattern}'", f"Ruta: {base_path.absolute()}", f"Encontrados: {len(results)}", ""]
            for item in results:
                icon = "📁" if item.is_dir() else "📄"
                output.append(f"  {icon} {item.relative_to(base_path)}")
            return "\n".join(output)
        except Exception as e:
            return f"❌ Error en búsqueda: {e}"

    # ─────────────────────── HELPERS ──────────────────────────

    def _format_size(self, size: int) -> str:
        if size is None:
            return "? B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"