import os
import sqlite3
import httpx
import time
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("KognitoSync")

class LocalChangeHandler(FileSystemEventHandler):
    def __init__(self, sync_manager):
        self.sync_manager = sync_manager

    def on_modified(self, event):
        if not event.is_directory:
            self.sync_manager.handle_local_change(event.src_path, "modify")

    def on_created(self, event):
        if not event.is_directory:
            self.sync_manager.handle_local_change(event.src_path, "create")

    def on_deleted(self, event):
        if not event.is_directory:
            self.sync_manager.handle_local_change(event.src_path, "delete")

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

    def fetch_remote_folders(self):
        url = f"{self.server_url}/api/onlyoffice/folders"
        try:
            resp = httpx.get(url, headers=self.get_auth_headers())
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Error buscando carpetas remotas: {e}")
            return []

    def fetch_remote_documents(self):
        url = f"{self.server_url}/api/onlyoffice/list"
        try:
            resp = httpx.get(url, headers=self.get_auth_headers())
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Error buscando documentos remotos: {e}")
            return []

    def build_folder_map(self, folders):
        folder_map = {}
        for f in folders:
            folder_map[f["id"]] = {
                "name": f["name"],
                "parent_id": f["parent_id"],
                "workspace_id": f["workspace_id"],
                "workspace_name": f["workspace_name"]
            }
        return folder_map

    def resolve_folder_path(self, folder_id, folder_map):
        parts = []
        curr_id = folder_id
        while curr_id:
            folder = folder_map.get(curr_id)
            if not folder:
                break
            parts.insert(0, folder["name"])
            curr_id = folder["parent_id"]
        return os.path.join(*parts) if parts else ""

    def sync_pass(self):
        if not self.token and not self.login():
            logger.error("No se pudo iniciar sesión. Saltando ciclo de sincronización.")
            return

        logger.info("Iniciando ciclo de sincronización...")
        
        # 1. Obtener estado de la nube
        folders = self.fetch_remote_folders()
        folder_map = self.build_folder_map(folders)
        remote_docs = self.fetch_remote_documents()
        
        # Map remote docs
        remote_by_path = {}
        for doc in remote_docs:
            ws_dir = doc["workspace_name"] if doc["workspace_name"] else "Personal"
            folder_subpath = self.resolve_folder_path(doc["folder_id"], folder_map)
            rel_path = os.path.join(ws_dir, folder_subpath, doc["filename"])
            local_path = os.path.join(self.sync_dir, rel_path)
            remote_by_path[local_path] = doc

        # 2. Conectar a SQLite
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener todos los registros locales
        cursor.execute("SELECT * FROM sync_files")
        local_db_records = {r["local_path"]: dict(r) for r in cursor.fetchall()}

        # 3. Procesar cambios de Nube -> Local
        for local_path, rdoc in remote_by_path.items():
            db_rec = local_db_records.get(local_path)
            
            # Caso 1: Archivo remoto es totalmente nuevo para nosotros
            if not db_rec:
                if os.path.exists(local_path):
                    # Conflicto local: existe el archivo local pero no estaba registrado.
                    # Renombramos el local y bajamos el de la nube.
                    self.rename_to_conflict(local_path)
                
                self.download_file(rdoc["id"], local_path)
                self.register_in_db(cursor, local_path, rdoc["id"], rdoc["workspace_id"], rdoc["folder_id"], rdoc["updated_at"])
                
            # Caso 2: Registrado en DB local
            else:
                # Comprobar si el archivo remoto fue editado
                if rdoc["updated_at"] != db_rec["last_seen_updated_at"]:
                    # ¿Se editó localmente también?
                    local_modified = False
                    if os.path.exists(local_path):
                        curr_mtime = os.path.getmtime(local_path)
                        if abs(curr_mtime - db_rec["last_seen_mtime"]) > 1.0: # diferencia > 1s
                            local_modified = True
                    
                    if local_modified:
                        # Conflicto: modificado en local y en nube
                        logger.warning(f"Conflicto de edición en: {local_path}. Creando copia local de conflicto.")
                        self.rename_to_conflict(local_path)
                        
                    self.download_file(rdoc["id"], local_path)
                    self.register_in_db(cursor, local_path, rdoc["id"], rdoc["workspace_id"], rdoc["folder_id"], rdoc["updated_at"])

        # 4. Procesar cambios de Local -> Nube (Archivos que están en DB o disco pero no en remoto)
        for local_path, db_rec in local_db_records.items():
            if local_path not in remote_by_path:
                # Fue borrado de la nube o nunca se subió.
                # Si estaba registrado, significa que se eliminó en la nube -> lo borramos localmente.
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        logger.info(f"Archivo eliminado localmente (borrado en la nube): {local_path}")
                    except Exception as e:
                        logger.error(f"Error borrando {local_path}: {e}")
                cursor.execute("DELETE FROM sync_files WHERE local_path = ?", (local_path,))

        # Buscar archivos locales no registrados para subida
        for root, dirs, files in os.walk(self.sync_dir):
            # Ignorar carpetas ocultas
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('~$') or f.startswith('.'):
                    continue
                full_path = os.path.join(root, f)
                if full_path not in local_db_records and full_path not in remote_by_path:
                    # Nuevo archivo local! Subir.
                    self.upload_new_file(cursor, full_path)

        conn.commit()
        conn.close()
        logger.info("Ciclo de sincronización terminado.")

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
            # Pausar temporalmente watchdog para evitar bucle de eventos al escribir
            if self.observer:
                self.observer.unschedule_all()
            
            with httpx.stream("GET", url, headers=self.get_auth_headers()) as r:
                if r.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in r.iter_bytes():
                            f.write(chunk)
                    logger.info("Descarga completada.")
                else:
                    logger.error(f"Fallo al descargar: {r.status_code}")
        except Exception as e:
            logger.error(f"Error en descarga: {e}")
        finally:
            # Reanudar watchdog
            if self.observer and self.is_running:
                self.start_watching()

    def upload_new_file(self, cursor, local_path):
        logger.info(f"Subiendo nuevo archivo local: {local_path}")
        # Determinar el workspace y folder basados en la ruta relativa
        rel_path = os.path.relpath(local_path, self.sync_dir)
        parts = rel_path.split(os.sep)
        
        workspace_name = parts[0]
        # Resolve workspace_id de Kognito AI. Si es "Personal", workspace_id = None
        workspace_id = None
        # En una versión completa se podría buscar o consultar por nombre de workspace.
        
        url = f"{self.server_url}/api/onlyoffice/upload"
        try:
            with open(local_path, "rb") as f:
                files = {"file": (os.path.basename(local_path), f, "application/octet-stream")}
                data = {}
                if workspace_id:
                    data["workspace_id"] = workspace_id
                
                resp = httpx.post(url, headers=self.get_auth_headers(), files=files, data=data)
                if resp.status_code == 200:
                    res_json = resp.json()
                    doc_id = res_json["id"]
                    updated_at = datetime.now().isoformat()
                    mtime = os.path.getmtime(local_path)
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO sync_files (local_path, document_id, workspace_id, folder_id, last_seen_mtime, last_seen_updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (local_path, doc_id, workspace_id, None, mtime, updated_at))
                    logger.info(f"Subido con éxito. ID asignado: {doc_id}")
                else:
                    logger.error(f"Error subiendo archivo: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error en subida: {e}")

    def handle_local_change(self, local_path, change_type):
        if not self.is_running:
            return
        
        filename = os.path.basename(local_path)
        if filename.startswith("~$") or filename.startswith("."):
            return
            
        logger.info(f"Cambio local detectado: {local_path} ({change_type})")
        
        # Esperar un momento corto por si el archivo está siendo escrito completamente
        time.sleep(0.5)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if change_type in ["create", "modify"]:
            cursor.execute("SELECT * FROM sync_files WHERE local_path = ?", (local_path,))
            row = cursor.fetchone()
            if row:
                doc_id = row[1]
                logger.info(f"Actualizando contenido remoto para ID: {doc_id}")
                url = f"{self.server_url}/api/onlyoffice/{doc_id}"
                try:
                    with open(local_path, "rb") as f:
                        files = {"file": (os.path.basename(local_path), f, "application/octet-stream")}
                        resp = httpx.put(url, headers=self.get_auth_headers(), files=files)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            updated_at = res_json.get("updated_at", datetime.now().isoformat())
                            mtime = os.path.getmtime(local_path)
                            cursor.execute("""
                                UPDATE sync_files SET last_seen_mtime = ?, last_seen_updated_at = ?
                                WHERE local_path = ?
                            """, (mtime, updated_at, local_path))
                            logger.info(f"Actualizado exitosamente en el servidor.")
                        else:
                            logger.error(f"Error al actualizar archivo: {resp.status_code} - {resp.text}")
                except Exception as e:
                    logger.error(f"Error en PUT: {e}")
            else:
                self.upload_new_file(cursor, local_path)
                
        elif change_type == "delete":
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
        conn.close()

    def register_in_db(self, cursor, local_path, doc_id, workspace_id, folder_id, updated_at):
        mtime = os.path.getmtime(local_path) if os.path.exists(local_path) else 0
        cursor.execute("""
            INSERT OR REPLACE INTO sync_files (local_path, document_id, workspace_id, folder_id, last_seen_mtime, last_seen_updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (local_path, doc_id, workspace_id, folder_id, mtime, updated_at))

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
        self.stop_watching()
