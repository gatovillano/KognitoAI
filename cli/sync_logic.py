import os
import sqlite3
import httpx
import time
import logging
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("KognitoSync")

def is_ignored_path(path):
    if not path:
        return True
    filename = os.path.basename(path)
    if not filename:
        return True
    if filename.startswith((".", "~$", "~")):
        return True
    if filename.endswith((".tmp", ".swp", ".bak", ".crdownload", ".part", "~", ".sb-")):
        return True
    if filename.startswith("goutputstream-"):
        return True
    if filename.lower() in ("desktop.ini", "thumbs.db", ".ds_store"):
        return True
    return False

class LocalChangeHandler(FileSystemEventHandler):
    def __init__(self, sync_manager):
        self.sync_manager = sync_manager

    def on_modified(self, event):
        if not event.is_directory:
            self.sync_manager.handle_local_change(event.src_path, "modify")

    def on_created(self, event):
        if not event.is_directory:
            self.sync_manager.handle_local_change(event.src_path, "create")
        else:
            self.sync_manager.handle_local_dir_created(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.sync_manager.handle_local_change(event.src_path, "delete")
        else:
            self.sync_manager.handle_local_dir_deleted(event.src_path)

    def on_moved(self, event):
        self.sync_manager.handle_local_move(event.src_path, event.dest_path, event.is_directory)

class KognitoSyncManager:
    def __init__(self, server_url, username, password, sync_dir, db_path):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.sync_dir = os.path.abspath(sync_dir)
        self.db_path = os.path.abspath(db_path)
        self.token = None
        self.is_running = False
        self.observer = None
        self._suppress_watchdog = False
        self._internal_moves = set()
        self._internal_moves_lock = threading.Lock()
        self._uploading_files = set()
        self._upload_lock = threading.Lock()
        self._debounce_timers = {}
        self._debounce_lock = threading.Lock()
        self.init_db()

    def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_files (
                local_path TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                workspace_id TEXT,
                folder_id TEXT,
                last_seen_mtime REAL NOT NULL,
                last_seen_updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def login(self):
        url = f"{self.server_url}/api/auth/login"
        try:
            # fastapi expects username/password form fields for standard OAuth2 login
            data = {"username": self.username, "password": self.password}
            resp = httpx.post(url, data=data)
            if resp.status_code == 200:
                self.token = resp.json().get("access_token")
                logger.info("Autenticación exitosa.")
                return True
            else:
                # Try json as backup
                resp = httpx.post(url, json=data)
                if resp.status_code == 200:
                    self.token = resp.json().get("access_token")
                    logger.info("Autenticación exitosa (JSON).")
                    return True
                logger.error(f"Error de login: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error al conectar para login: {e}")
            return False

    def get_auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def fetch_remote_workspaces(self):
        url = f"{self.server_url}/api/workspaces?limit=100"
        try:
            resp = httpx.get(url, headers=self.get_auth_headers())
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "workspaces" in data:
                    return data["workspaces"]
                elif isinstance(data, list):
                    return data
            logger.error(f"Error buscando workspaces remotos: {resp.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error buscando workspaces remotos: {e}")
            return []

    def fetch_remote_folders(self):
        url = f"{self.server_url}/api/onlyoffice/folders"
        try:
            resp = httpx.get(url, headers=self.get_auth_headers())
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"Error buscando carpetas remotas: {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error buscando carpetas remotas: {e}")
            return None

    def fetch_remote_documents(self):
        url = f"{self.server_url}/api/onlyoffice/list"
        try:
            resp = httpx.get(url, headers=self.get_auth_headers())
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"Error buscando documentos remotos: {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error buscando documentos remotos: {e}")
            return None

    def create_remote_folder(self, name, workspace_id=None, parent_id=None):
        url = f"{self.server_url}/api/onlyoffice/folders"
        data = {"name": name}
        if workspace_id:
            data["workspace_id"] = str(workspace_id)
        if parent_id:
            data["parent_id"] = str(parent_id)
        try:
            resp = httpx.post(url, headers=self.get_auth_headers(), data=data)
            if resp.status_code in [200, 201]:
                res_json = resp.json()
                new_id = str(res_json.get("id"))
                logger.info(f"Carpeta remota '{name}' creada con ID: {new_id} (workspace={workspace_id}, parent={parent_id})")
                return new_id
            logger.error(f"Error creando carpeta remota '{name}': {resp.status_code} - {resp.text}")
            return None
        except Exception as e:
            logger.error(f"Excepción creando carpeta remota '{name}': {e}")
            return None

    def build_folder_map(self, folders):
        folder_map = {}
        if folders:
            for f in folders:
                folder_map[str(f["id"])] = {
                    "id": str(f["id"]),
                    "name": f["name"],
                    "parent_id": str(f["parent_id"]) if f.get("parent_id") else None,
                    "workspace_id": str(f["workspace_id"]) if f.get("workspace_id") else None,
                    "workspace_name": f.get("workspace_name")
                }
        return folder_map

    def resolve_folder_path(self, folder_id, folder_map):
        if not folder_id:
            return ""
        parts = []
        curr_id = str(folder_id)
        visited = set()
        while curr_id and curr_id not in visited:
            visited.add(curr_id)
            folder = folder_map.get(curr_id)
            if not folder:
                break
            parts.insert(0, folder["name"])
            curr_id = str(folder["parent_id"]) if folder.get("parent_id") else None
        return os.path.join(*parts) if parts else ""

    def find_folder_by_names(self, folder_names, workspace_id, folder_map):
        """Busca el ID de la carpeta final dada la secuencia de nombres y el workspace_id."""
        if not folder_names:
            return None
        curr_parent_id = None
        for name in folder_names:
            found_id = None
            for fid, f in folder_map.items():
                f_ws = f.get("workspace_id")
                f_parent = f.get("parent_id")
                ws_match = (str(f_ws) == str(workspace_id)) if (f_ws and workspace_id) else (not f_ws and not workspace_id)
                parent_match = (str(f_parent) == str(curr_parent_id)) if (f_parent and curr_parent_id) else (not f_parent and not curr_parent_id)
                if f.get("name") == name and ws_match and parent_match:
                    found_id = str(fid)
                    break
            if not found_id:
                return None
            curr_parent_id = found_id
        return curr_parent_id

    def ensure_remote_folder_chain(self, folder_names, workspace_id, folder_map):
        """
        Garantiza que la cadena de subcarpetas exista en la nube (remoto).
        folder_names: lista de nombres de subcarpetas en orden, ej: ["Carpeta1", "Sub2"]
        workspace_id: ID del workspace (o None para Personal)
        folder_map: dict de folder_id -> folder_data
        Retorna el folder_id de la carpeta final (o None si folder_names está vacío).
        """
        if not folder_names:
            return None
            
        curr_parent_id = None
        for name in folder_names:
            found_id = None
            for fid, f in folder_map.items():
                f_ws = f.get("workspace_id")
                f_parent = f.get("parent_id")
                
                ws_match = (str(f_ws) == str(workspace_id)) if (f_ws and workspace_id) else (not f_ws and not workspace_id)
                parent_match = (str(f_parent) == str(curr_parent_id)) if (f_parent and curr_parent_id) else (not f_parent and not curr_parent_id)
                
                if f.get("name") == name and ws_match and parent_match:
                    found_id = str(fid)
                    break
            
            if found_id:
                curr_parent_id = found_id
            else:
                created_id = self.create_remote_folder(name, workspace_id=workspace_id, parent_id=curr_parent_id)
                if not created_id:
                    logger.error(f"Fallo al asegurar carpeta remota '{name}'")
                    return None
                folder_map[created_id] = {
                    "id": created_id,
                    "name": name,
                    "parent_id": curr_parent_id,
                    "workspace_id": str(workspace_id) if workspace_id else None,
                    "workspace_name": None
                }
                curr_parent_id = created_id
                
        return curr_parent_id

    def resolve_local_path_hierarchy(self, local_path, folder_map=None, workspaces=None):
        """
        Analiza la ruta local de un archivo y determina:
        1. Si necesita reubicación a Personal/ (si está en la raíz o en una carpeta que no es workspace)
        2. El workspace_id correspondiente
        3. El folder_id remoto correspondiente, creando las carpetas faltantes en el servidor si es necesario.
        Retorna (local_path_actualizado, workspace_id, folder_id, folder_map)
        """
        rel_path = os.path.relpath(local_path, self.sync_dir)
        parts = rel_path.split(os.sep)
        filename = parts[-1]

        if workspaces is None:
            workspaces = self.fetch_remote_workspaces() or []
        ws_name_to_id = {w["name"]: str(w["id"]) for w in workspaces}

        if len(parts) == 1:
            # Archivo directamente en la raíz -> Mover a Personal/filename
            personal_dir = os.path.join(self.sync_dir, "Personal")
            os.makedirs(personal_dir, exist_ok=True)
            target_path = os.path.join(personal_dir, filename)
            with self._internal_moves_lock:
                self._internal_moves.add((local_path, target_path))
                self._internal_moves.add(target_path)
            try:
                os.rename(local_path, target_path)
                logger.info(f"Archivo movido de raíz a carpeta Personal: {local_path} -> {target_path}")
                local_path = target_path
            except Exception as e:
                with self._internal_moves_lock:
                    self._internal_moves.discard((local_path, target_path))
                    self._internal_moves.discard(target_path)
                logger.error(f"No se pudo mover archivo raíz a Personal: {e}")
            rel_path = os.path.relpath(local_path, self.sync_dir)
            parts = rel_path.split(os.sep)

        elif parts[0] != "Personal" and parts[0] not in ws_name_to_id:
            # Si el primer directorio no es 'Personal' ni el nombre de un workspace existente,
            # significa que es una carpeta personal creada en la raíz (ej: ~/KognitoSync/MiCarpeta/...)
            target_path = os.path.join(self.sync_dir, "Personal", rel_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with self._internal_moves_lock:
                self._internal_moves.add((local_path, target_path))
                self._internal_moves.add(target_path)
            try:
                os.rename(local_path, target_path)
                logger.info(f"Ruta reubicada dentro de Personal: {local_path} -> {target_path}")
                local_path = target_path
            except Exception as e:
                with self._internal_moves_lock:
                    self._internal_moves.discard((local_path, target_path))
                    self._internal_moves.discard(target_path)
                logger.error(f"No se pudo reubicar bajo Personal: {e}")
            rel_path = os.path.relpath(local_path, self.sync_dir)
            parts = rel_path.split(os.sep)

        if parts[0] == "Personal":
            workspace_id = None
            folder_names = parts[1:-1]
        elif parts[0] in ws_name_to_id:
            workspace_id = ws_name_to_id[parts[0]]
            folder_names = parts[1:-1]
        else:
            workspace_id = None
            folder_names = parts[1:-1]

        if folder_map is None:
            folders = self.fetch_remote_folders() or []
            folder_map = self.build_folder_map(folders)

        folder_id = self.ensure_remote_folder_chain(folder_names, workspace_id, folder_map)
        return local_path, workspace_id, folder_id, folder_map

    def update_remote_doc_meta(self, doc_id, filename=None, workspace_id=None, folder_id=None):
        url = f"{self.server_url}/api/onlyoffice/{doc_id}/meta"
        data = {}
        if filename:
            data["filename"] = filename
        data["workspace_id"] = str(workspace_id) if workspace_id else "null"
        data["folder_id"] = str(folder_id) if folder_id else "null"
        try:
            resp = httpx.post(url, headers=self.get_auth_headers(), data=data)
            if resp.status_code == 200:
                logger.info(f"Metadatos remotos actualizados para documento ID: {doc_id}")
                return True
            logger.error(f"Error al actualizar metadatos remotos ({doc_id}): {resp.status_code} - {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Excepción al actualizar metadatos remotos ({doc_id}): {e}")
            return False

    def sync_pass(self):
        if not self.token and not self.login():
            logger.error("No se pudo iniciar sesión. Saltando ciclo de sincronización.")
            return

        logger.info("Iniciando ciclo de sincronización...")
        self._suppress_watchdog = True
        
        try:
            # 1. Obtener estado de la nube
            workspaces = self.fetch_remote_workspaces() or []
            ws_name_to_id = {w["name"]: str(w["id"]) for w in workspaces}
            ws_id_to_name = {str(w["id"]): w["name"] for w in workspaces}
            
            folders = self.fetch_remote_folders()
            if folders is None:
                logger.error("No se pudieron obtener carpetas remotas. Cancelando ciclo de sync para proteger archivos locales.")
                return
            folder_map = self.build_folder_map(folders)

            # Asegurar que todas las carpetas remotas existan localmente
            os.makedirs(os.path.join(self.sync_dir, "Personal"), exist_ok=True)
            remote_folder_dirs = {os.path.join(self.sync_dir, "Personal")}
            for f in folders:
                ws_dir = ws_id_to_name.get(str(f.get("workspace_id"))) if f.get("workspace_id") else "Personal"
                f_subpath = self.resolve_folder_path(f["id"], folder_map)
                local_folder_dir = os.path.join(self.sync_dir, ws_dir, f_subpath)
                os.makedirs(local_folder_dir, exist_ok=True)
                remote_folder_dirs.add(local_folder_dir)

            remote_docs = self.fetch_remote_documents()
            if remote_docs is None:
                logger.error("No se pudieron obtener documentos remotos. Cancelando ciclo de sync para proteger archivos locales.")
                return
            
            # Map remote docs por ruta local esperada y por document_id
            remote_by_path = {}
            remote_by_doc_id = {}
            for doc in remote_docs:
                ws_dir = doc["workspace_name"] if doc.get("workspace_name") else "Personal"
                folder_subpath = self.resolve_folder_path(doc.get("folder_id"), folder_map)
                rel_path = os.path.join(ws_dir, folder_subpath, doc["filename"])
                local_path = os.path.join(self.sync_dir, rel_path)
                remote_by_path[local_path] = doc
                remote_by_doc_id[str(doc["id"])] = (local_path, doc)

            # 2. Conectar a SQLite
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Obtener todos los registros locales
            cursor.execute("SELECT * FROM sync_files")
            local_db_records = {r["local_path"]: dict(r) for r in cursor.fetchall()}
            local_db_by_doc_id = {str(r["document_id"]): dict(r) for r in local_db_records.values() if r.get("document_id")}

            # 3. Procesar cambios de Nube -> Local (Descargar nuevos / modificados / reubicados)
            for local_path, rdoc in remote_by_path.items():
                doc_id = str(rdoc["id"])
                db_rec = local_db_records.get(local_path)
                
                # Si la ruta no coincide exactamente pero el document_id ya está en SQLite
                if not db_rec and doc_id in local_db_by_doc_id:
                    existing_rec = local_db_by_doc_id[doc_id]
                    old_path = existing_rec["local_path"]
                    if os.path.exists(old_path) and old_path != local_path:
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        try:
                            os.rename(old_path, local_path)
                            logger.info(f"Reubicando rastro local: {old_path} -> {local_path}")
                        except Exception as e:
                            logger.error(f"Error reubicando rastro local: {e}")
                    cursor.execute("""
                        UPDATE sync_files 
                        SET local_path = ?, workspace_id = ?, folder_id = ?, last_seen_updated_at = ? 
                        WHERE document_id = ?
                    """, (local_path, rdoc.get("workspace_id"), rdoc.get("folder_id"), rdoc.get("updated_at", ""), doc_id))
                    db_rec = existing_rec
                    db_rec["local_path"] = local_path

                # Caso 1: Archivo remoto es totalmente nuevo para nosotros
                if not db_rec:
                    if os.path.exists(local_path):
                        self.rename_to_conflict(local_path)
                    
                    self.download_file(rdoc["id"], local_path)
                    self.register_in_db(cursor, local_path, rdoc["id"], rdoc.get("workspace_id"), rdoc.get("folder_id"), rdoc.get("updated_at", ""))
                    
                # Caso 2: Registrado en DB local
                else:
                    # Si el archivo fue borrado localmente mientras estaba offline y el remoto no cambió
                    if not os.path.exists(local_path):
                        if rdoc.get("updated_at") == db_rec.get("last_seen_updated_at"):
                            logger.info(f"Eliminando en la nube por borrado local previo offline: {doc_id}")
                            url = f"{self.server_url}/api/onlyoffice/{doc_id}"
                            try:
                                resp = httpx.delete(url, headers=self.get_auth_headers())
                                if resp.status_code == 200:
                                    cursor.execute("DELETE FROM sync_files WHERE document_id = ?", (doc_id,))
                            except Exception as e:
                                logger.error(f"Error borrando en la nube ({doc_id}): {e}")
                            continue
                        else:
                            # Remoto cambió mientras no existía local -> descargar
                            self.download_file(rdoc["id"], local_path)
                            self.register_in_db(cursor, local_path, rdoc["id"], rdoc.get("workspace_id"), rdoc.get("folder_id"), rdoc.get("updated_at", ""))
                            continue

                    # Comprobar si el archivo remoto fue editado
                    if rdoc.get("updated_at") != db_rec.get("last_seen_updated_at"):
                        local_modified = False
                        if os.path.exists(local_path):
                            curr_mtime = os.path.getmtime(local_path)
                            if abs(curr_mtime - db_rec.get("last_seen_mtime", 0)) > 1.0:
                                local_modified = True
                        
                        if local_modified:
                            logger.warning(f"Conflicto de edición en: {local_path}. Creando copia local de conflicto.")
                            self.rename_to_conflict(local_path)
                            
                        self.download_file(rdoc["id"], local_path)
                        self.register_in_db(cursor, local_path, rdoc["id"], rdoc.get("workspace_id"), rdoc.get("folder_id"), rdoc.get("updated_at", ""))

            # 4. Procesar archivos que están en DB local pero ya NO existen en la nube
            for local_path, db_rec in list(local_db_records.items()):
                doc_id = str(db_rec.get("document_id"))

                if local_path not in remote_by_path:
                    # 4.1 Comprobar si el documento existe en la nube pero en una ruta reubicada
                    if doc_id and doc_id in remote_by_doc_id:
                        new_expected_path, rdoc = remote_by_doc_id[doc_id]
                        if os.path.exists(local_path) and local_path != new_expected_path:
                            os.makedirs(os.path.dirname(new_expected_path), exist_ok=True)
                            if not os.path.exists(new_expected_path):
                                try:
                                    os.rename(local_path, new_expected_path)
                                    logger.info(f"Archivo reubicado automáticamente: {local_path} -> {new_expected_path}")
                                except Exception as e:
                                    logger.error(f"Error reubicando archivo: {e}")
                        cursor.execute("DELETE FROM sync_files WHERE local_path = ?", (local_path,))
                        mtime = os.path.getmtime(new_expected_path) if os.path.exists(new_expected_path) else 0
                        cursor.execute("""
                            INSERT OR REPLACE INTO sync_files (local_path, document_id, workspace_id, folder_id, last_seen_mtime, last_seen_updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (new_expected_path, doc_id, rdoc.get("workspace_id"), rdoc.get("folder_id"), mtime, rdoc.get("updated_at", "")))
                        continue

                    # 4.2 El archivo fue borrado en la nube (no existe en remote_by_doc_id)
                    if os.path.exists(local_path):
                        curr_mtime = os.path.getmtime(local_path)
                        last_mtime = db_rec.get("last_seen_mtime", 0)
                        if abs(curr_mtime - last_mtime) <= 1.0:
                            # No fue modificado localmente -> BORRAR LOCALMENTE
                            try:
                                os.remove(local_path)
                                logger.info(f"Archivo eliminado localmente (borrado en la nube): {local_path}")
                            except Exception as e:
                                logger.error(f"Error al eliminar archivo local {local_path}: {e}")
                        else:
                            # Modificado localmente tras eliminación remota -> re-subir como nuevo
                            logger.info(f"Archivo modificado localmente tras eliminación remota. Re-subiendo: {local_path}")
                            self.upload_new_file(cursor, local_path, folder_map=folder_map, workspaces=workspaces)

                    cursor.execute("DELETE FROM sync_files WHERE local_path = ?", (local_path,))

            # 5. Buscar archivos locales no registrados en DB para subida
            for root, dirs, files in os.walk(self.sync_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in files:
                    if is_ignored_path(f):
                        continue
                    full_path = os.path.join(root, f)
                    
                    # Comprobar directamente en SQLite si ya está registrado
                    cursor.execute("SELECT 1 FROM sync_files WHERE local_path = ?", (full_path,))
                    if cursor.fetchone():
                        continue

                    if full_path not in local_db_records and full_path not in remote_by_path:
                        upload_res = self.upload_new_file(cursor, full_path, folder_map=folder_map, workspaces=workspaces)
                        if upload_res:
                            doc_id, resolved_path = upload_res
                            local_db_records[resolved_path] = {"document_id": doc_id, "local_path": resolved_path}

            # 6. Limpieza de carpetas locales vacías que ya no existen en la nube
            for root, dirs, files in os.walk(self.sync_dir, topdown=False):
                if root == self.sync_dir:
                    continue
                rel = os.path.relpath(root, self.sync_dir)
                parts = rel.split(os.sep)
                if len(parts) == 1 and (parts[0] == "Personal" or parts[0] in ws_name_to_id):
                    continue
                if root not in remote_folder_dirs and os.path.exists(root) and not os.listdir(root):
                    try:
                        os.rmdir(root)
                        logger.info(f"Carpeta vacía eliminada localmente (borrada en la nube): {root}")
                    except Exception as e:
                        logger.error(f"Error al eliminar carpeta vacía {root}: {e}")

            conn.commit()
            conn.close()
            logger.info("Ciclo de sincronización terminado.")
        finally:
            self._suppress_watchdog = False

    def rename_to_conflict(self, local_path):
        dir_name = os.path.dirname(local_path)
        base_name = os.path.basename(local_path)
        name_parts = os.path.splitext(base_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{name_parts[0]}_conflicto_{timestamp}{name_parts[1]}"
        new_path = os.path.join(dir_name, new_name)
        try:
            os.rename(local_path, new_path)
            logger.info(f"Archivo en conflicto renombrado a: {new_path}")
        except Exception as e:
            logger.error(f"No se pudo renombrar el conflicto {local_path}: {e}")

    def download_file(self, document_id, dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        url = f"{self.server_url}/api/onlyoffice/download/{document_id}"
        logger.info(f"Descargando archivo {document_id} a {dest_path}...")
        try:
            with httpx.stream("GET", url, headers=self.get_auth_headers()) as r:
                if r.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in r.iter_bytes():
                            f.write(chunk)
                    logger.info(f"Descarga completada para {dest_path}.")
                else:
                    logger.error(f"Fallo al descargar {document_id}: {r.status_code}")
        except Exception as e:
            logger.error(f"Error en descarga ({document_id}): {e}")

    def upload_updated_file(self, cursor, local_path, doc_id):
        if not os.path.exists(local_path) or is_ignored_path(local_path):
            return False

        try:
            curr_mtime = os.path.getmtime(local_path)
        except Exception:
            return False

        cursor.execute("SELECT last_seen_mtime FROM sync_files WHERE document_id = ?", (str(doc_id),))
        row = cursor.fetchone()
        if row and abs(curr_mtime - row[0]) < 0.1:
            return True

        logger.info(f"Actualizando contenido remoto para ID: {doc_id} ({local_path})")
        url = f"{self.server_url}/api/onlyoffice/{doc_id}"
        try:
            with open(local_path, "rb") as f:
                files = {"file": (os.path.basename(local_path), f, "application/octet-stream")}
                resp = httpx.put(url, headers=self.get_auth_headers(), files=files)
                if resp.status_code == 200:
                    res_json = resp.json()
                    updated_at = res_json.get("updated_at", datetime.now().isoformat())
                    cursor.execute("""
                        UPDATE sync_files SET last_seen_mtime = ?, last_seen_updated_at = ?
                        WHERE document_id = ?
                    """, (curr_mtime, updated_at, str(doc_id)))
                    logger.info(f"Actualizado exitosamente en el servidor (ID: {doc_id}).")
                    return True
                else:
                    logger.error(f"Error al actualizar archivo ({doc_id}): {resp.status_code} - {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Error en PUT ({doc_id}): {e}")
            return False

    def upload_new_file(self, cursor, local_path, folder_map=None, workspaces=None):
        if not os.path.exists(local_path) or is_ignored_path(local_path):
            return None

        # Bloqueo para evitar subidas concurrentes del mismo archivo
        with self._upload_lock:
            if local_path in self._uploading_files:
                logger.info(f"Subida ya en curso para {local_path}, omitiendo duplicado.")
                return None
            self._uploading_files.add(local_path)

        resolved_path = None
        try:
            # 1. Resolver la jerarquía de directorios (workspace y carpetas anidadas)
            resolved_path, workspace_id, folder_id, folder_map = self.resolve_local_path_hierarchy(
                local_path, folder_map=folder_map, workspaces=workspaces
            )
            if not os.path.exists(resolved_path) or is_ignored_path(resolved_path):
                return None

            # 2. Comprobar si tras la resolución de ruta ya está registrado en SQLite
            cursor.execute("SELECT document_id, last_seen_mtime FROM sync_files WHERE local_path = ?", (resolved_path,))
            existing = cursor.fetchone()
            if existing:
                doc_id = existing[0]
                logger.info(f"Archivo ya registrado en {resolved_path} (ID: {doc_id}). Actualizando contenido.")
                self.upload_updated_file(cursor, resolved_path, doc_id)
                return doc_id, resolved_path

            filename = os.path.basename(resolved_path)
            logger.info(f"Subiendo nuevo archivo local: {resolved_path} (workspace_id={workspace_id}, folder_id={folder_id})")
            
            url = f"{self.server_url}/api/onlyoffice/upload"
            with open(resolved_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                data = {}
                if workspace_id:
                    data["workspace_id"] = str(workspace_id)
                if folder_id:
                    data["folder_id"] = str(folder_id)
                
                resp = httpx.post(url, headers=self.get_auth_headers(), files=files, data=data)
                if resp.status_code == 200:
                    res_json = resp.json()
                    doc_id = str(res_json["id"])
                    updated_at = res_json.get("updated_at") or datetime.now().isoformat()
                    self.register_in_db(cursor, resolved_path, doc_id, workspace_id, folder_id, updated_at)
                    logger.info(f"Subido con éxito: {filename} (ID: {doc_id}, folder_id: {folder_id})")
                    return doc_id, resolved_path
                else:
                    logger.error(f"Error subiendo archivo {filename}: {resp.status_code} - {resp.text}")
                    return None
        except Exception as e:
            logger.error(f"Error en subida de {local_path}: {e}")
            return None
        finally:
            with self._upload_lock:
                self._uploading_files.discard(local_path)
                if resolved_path:
                    self._uploading_files.discard(resolved_path)

    def handle_local_change(self, local_path, change_type):
        if not self.is_running or self._suppress_watchdog:
            return

        if is_ignored_path(local_path):
            return

        with self._internal_moves_lock:
            if local_path in self._internal_moves:
                self._internal_moves.discard(local_path)
                return

        # Debounce: cancelar temporizador anterior si existe para este archivo y reiniciar
        with self._debounce_lock:
            timer = self._debounce_timers.pop(local_path, None)
            if timer:
                try:
                    timer.cancel()
                except Exception:
                    pass
            
            new_timer = threading.Timer(0.8, self._process_debounced_change, args=[local_path, change_type])
            self._debounce_timers[local_path] = new_timer
            new_timer.daemon = True
            new_timer.start()

    def _process_debounced_change(self, local_path, change_type):
        with self._debounce_lock:
            self._debounce_timers.pop(local_path, None)

        if not self.is_running or self._suppress_watchdog:
            return

        if change_type == "delete":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM sync_files WHERE local_path = ?", (local_path,))
                row = cursor.fetchone()
                if row:
                    doc_id = row[1]
                    logger.info(f"Eliminando documento remoto ID: {doc_id}")
                    url = f"{self.server_url}/api/onlyoffice/{doc_id}"
                    try:
                        resp = httpx.delete(url, headers=self.get_auth_headers())
                        if resp.status_code == 200:
                            cursor.execute("DELETE FROM sync_files WHERE local_path = ?", (local_path,))
                            logger.info("Eliminado exitosamente del servidor.")
                        else:
                            logger.error(f"Error al eliminar en servidor: {resp.status_code} - {resp.text}")
                    except Exception as e:
                        logger.error(f"Error en DELETE: {e}")
                conn.commit()
            finally:
                conn.close()
            return

        if not os.path.exists(local_path) or is_ignored_path(local_path):
            return

        # Esperar a que el archivo termine de escribirse si está creciendo
        last_size = -1
        for _ in range(5):
            try:
                sz = os.path.getsize(local_path)
                if sz == last_size:
                    break
                last_size = sz
                time.sleep(0.2)
            except Exception:
                break

        logger.info(f"Procesando cambio local estabilizado: {local_path} ({change_type})")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT document_id, last_seen_mtime FROM sync_files WHERE local_path = ?", (local_path,))
            row = cursor.fetchone()
            if row:
                doc_id = row[0]
                self.upload_updated_file(cursor, local_path, doc_id)
            else:
                self.upload_new_file(cursor, local_path)
            conn.commit()
        finally:
            conn.close()

    def handle_local_dir_created(self, dir_path):
        if not self.is_running or self._suppress_watchdog:
            return
        rel_path = os.path.relpath(dir_path, self.sync_dir)
        if rel_path == "." or rel_path.startswith("."):
            return
        logger.info(f"Directorio local creado: {dir_path}")
        try:
            parts = rel_path.split(os.sep)
            workspaces = self.fetch_remote_workspaces() or []
            ws_names = {w["name"] for w in workspaces}
            ws_id_map = {w["name"]: str(w["id"]) for w in workspaces}

            # Si el directorio se creó directamente en la raíz y no es 'Personal' ni un workspace,
            # mover el directorio completo a Personal/
            if parts[0] != "Personal" and parts[0] not in ws_names:
                target_dir = os.path.join(self.sync_dir, "Personal", rel_path)
                os.makedirs(os.path.dirname(target_dir), exist_ok=True)
                if not os.path.exists(target_dir):
                    os.rename(dir_path, target_dir)
                    logger.info(f"Directorio reubicado a Personal: {dir_path} -> {target_dir}")
                    dir_path = target_dir
                    rel_path = os.path.relpath(dir_path, self.sync_dir)
                    parts = rel_path.split(os.sep)

            if parts[0] == "Personal":
                workspace_id = None
                folder_names = parts[1:]
            elif parts[0] in ws_names:
                workspace_id = ws_id_map[parts[0]]
                folder_names = parts[1:]
            else:
                workspace_id = None
                folder_names = parts[1:]

            if folder_names:
                folders = self.fetch_remote_folders() or []
                folder_map = self.build_folder_map(folders)
                self.ensure_remote_folder_chain(folder_names, workspace_id, folder_map)
        except Exception as e:
            logger.error(f"Error al procesar creación de directorio {dir_path}: {e}")

    def handle_local_dir_deleted(self, dir_path):
        if not self.is_running or self._suppress_watchdog:
            return
        rel_path = os.path.relpath(dir_path, self.sync_dir)
        if rel_path == "." or rel_path.startswith("."):
            return
        logger.info(f"Directorio local eliminado: {dir_path}")
        try:
            parts = rel_path.split(os.sep)
            workspaces = self.fetch_remote_workspaces() or []
            ws_names = {w["name"] for w in workspaces}
            ws_id_map = {w["name"]: str(w["id"]) for w in workspaces}

            if parts[0] == "Personal":
                workspace_id = None
                folder_names = parts[1:]
            elif parts[0] in ws_names:
                workspace_id = ws_id_map[parts[0]]
                folder_names = parts[1:]
            else:
                workspace_id = None
                folder_names = parts[1:]

            if folder_names:
                folders = self.fetch_remote_folders() or []
                folder_map = self.build_folder_map(folders)
                target_folder_id = self.find_folder_by_names(folder_names, workspace_id, folder_map)
                if target_folder_id:
                    url = f"{self.server_url}/api/onlyoffice/folders/{target_folder_id}"
                    resp = httpx.delete(url, headers=self.get_auth_headers())
                    if resp.status_code == 200:
                        logger.info(f"Carpeta remota ID {target_folder_id} eliminada en servidor.")
        except Exception as e:
            logger.error(f"Error al procesar eliminación de directorio {dir_path}: {e}")

    def handle_local_move(self, src_path, dest_path, is_directory=False):
        if not self.is_running or self._suppress_watchdog:
            return

        with self._internal_moves_lock:
            if (src_path, dest_path) in self._internal_moves or dest_path in self._internal_moves:
                self._internal_moves.discard((src_path, dest_path))
                self._internal_moves.discard(dest_path)
                logger.info(f"Movimiento interno de reubicación ignorado en watcher: {src_path} -> {dest_path}")
                return

        if is_ignored_path(dest_path):
            return

        logger.info(f"Movimiento local detectado: {src_path} -> {dest_path} (is_dir={is_directory})")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if is_directory:
                cursor.execute("SELECT * FROM sync_files WHERE local_path LIKE ?", (src_path + "/%",))
                rows = cursor.fetchall()
                for row in rows:
                    old_file_path = row[0]
                    doc_id = row[1]
                    rel_inside = os.path.relpath(old_file_path, src_path)
                    new_file_path = os.path.join(dest_path, rel_inside)
                    
                    new_file_path, workspace_id, folder_id, _ = self.resolve_local_path_hierarchy(new_file_path)
                    self.update_remote_doc_meta(doc_id, filename=os.path.basename(new_file_path), workspace_id=workspace_id, folder_id=folder_id)
                    mtime = os.path.getmtime(new_file_path) if os.path.exists(new_file_path) else row[4]
                    cursor.execute("""
                        UPDATE sync_files SET local_path = ?, workspace_id = ?, folder_id = ?, last_seen_mtime = ?
                        WHERE document_id = ?
                    """, (new_file_path, workspace_id, folder_id, mtime, doc_id))
            else:
                cursor.execute("SELECT * FROM sync_files WHERE local_path = ?", (src_path,))
                row = cursor.fetchone()
                if row:
                    doc_id = row[1]
                    resolved_dest_path, workspace_id, folder_id, _ = self.resolve_local_path_hierarchy(dest_path)
                    self.update_remote_doc_meta(doc_id, filename=os.path.basename(resolved_dest_path), workspace_id=workspace_id, folder_id=folder_id)
                    mtime = os.path.getmtime(resolved_dest_path) if os.path.exists(resolved_dest_path) else row[4]
                    cursor.execute("""
                        UPDATE sync_files SET local_path = ?, workspace_id = ?, folder_id = ?, last_seen_mtime = ?
                        WHERE document_id = ?
                    """, (resolved_dest_path, workspace_id, folder_id, mtime, doc_id))
                else:
                    # Comprobar si dest_path ya estaba registrado (guardado atómico por editor)
                    cursor.execute("SELECT document_id FROM sync_files WHERE local_path = ?", (dest_path,))
                    dest_row = cursor.fetchone()
                    if dest_row:
                        doc_id = dest_row[0]
                        logger.info(f"Guardado atómico detectado para {dest_path} (ID: {doc_id}). Actualizando contenido.")
                        self.upload_updated_file(cursor, dest_path, doc_id)
                    else:
                        self.upload_new_file(cursor, dest_path)
            conn.commit()
        finally:
            conn.close()

    def register_in_db(self, cursor, local_path, doc_id, workspace_id, folder_id, updated_at):
        mtime = os.path.getmtime(local_path) if os.path.exists(local_path) else 0
        cursor.execute("""
            INSERT OR REPLACE INTO sync_files (local_path, document_id, workspace_id, folder_id, last_seen_mtime, last_seen_updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (local_path, str(doc_id), str(workspace_id) if workspace_id else None, str(folder_id) if folder_id else None, mtime, updated_at))

    def start_watching(self):
        if self.observer:
            try:
                self.observer.stop()
            except Exception:
                pass
        self.observer = Observer()
        event_handler = LocalChangeHandler(self)
        self.observer.schedule(event_handler, self.sync_dir, recursive=True)
        self.observer.start()
        logger.info(f"Iniciado monitoreo local de {self.sync_dir}")

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Monitoreo local detenido.")

    def run_sync_loop(self):
        self.is_running = True
        self.start_watching()
        
        while self.is_running:
            try:
                self.sync_pass()
            except Exception as e:
                logger.error(f"Error en ciclo de sincronización: {e}")
            time.sleep(60)

    def stop(self):
        self.is_running = False
        with self._debounce_lock:
            for timer in self._debounce_timers.values():
                try:
                    timer.cancel()
                except Exception:
                    pass
            self._debounce_timers.clear()
        self.stop_watching()
