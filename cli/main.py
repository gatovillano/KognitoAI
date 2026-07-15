import os
import json
import threading
import sys
import time
from PIL import Image, ImageDraw
import customtkinter as ctk
import pystray
from pystray import MenuItem as item

# Set appearance mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Import the SyncManager
from sync_logic import KognitoSyncManager

CONFIG_PATH = os.path.expanduser("~/.config/kognito-sync/config.json")

def create_default_icon():
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse([8, 8, 56, 56], fill=(30, 41, 59))
    dc.ellipse([16, 16, 48, 48], fill=(59, 130, 246))
    dc.ellipse([24, 24, 40, 40], fill=(255, 255, 255))
    return image

class SyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kognito AI Sync")
        self.geometry("550x550")
        self.resizable(False, False)
        
        self.sync_manager = None
        self.sync_thread = None
        self.tray_icon = None
        self.tray_thread = None

        self.create_widgets()
        self.load_config()

        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def create_widgets(self):
        self.header_label = ctk.CTkLabel(self, text="Kognito AI - Sincronizador de Documentos", font=("Helvetica", 18, "bold"))
        self.header_label.pack(pady=20)

        # Server URL Frame
        self.server_frame = ctk.CTkFrame(self)
        self.server_frame.pack(fill="x", padx=30, pady=5)
        self.url_label = ctk.CTkLabel(self.server_frame, text="URL del Servidor:", width=120, anchor="w")
        self.url_label.pack(side="left", padx=10, pady=10)
        self.url_entry = ctk.CTkEntry(self.server_frame, width=280, placeholder_text="http://localhost:8000")
        self.url_entry.pack(side="left", padx=10, pady=10)

        # Username Frame
        self.user_frame = ctk.CTkFrame(self)
        self.user_frame.pack(fill="x", padx=30, pady=5)
        self.user_label = ctk.CTkLabel(self.user_frame, text="Usuario / Email:", width=120, anchor="w")
        self.user_label.pack(side="left", padx=10, pady=10)
        self.user_entry = ctk.CTkEntry(self.user_frame, width=280)
        self.user_entry.pack(side="left", padx=10, pady=10)

        # Password Frame
        self.pass_frame = ctk.CTkFrame(self)
        self.pass_frame.pack(fill="x", padx=30, pady=5)
        self.pass_label = ctk.CTkLabel(self.pass_frame, text="Contraseña:", width=120, anchor="w")
        self.pass_label.pack(side="left", padx=10, pady=10)
        self.pass_entry = ctk.CTkEntry(self.pass_frame, width=280, show="*")
        self.pass_entry.pack(side="left", padx=10, pady=10)

        # Folder Selector Frame
        self.folder_frame = ctk.CTkFrame(self)
        self.folder_frame.pack(fill="x", padx=30, pady=5)
        self.folder_label = ctk.CTkLabel(self.folder_frame, text="Carpeta de Sync:", width=120, anchor="w")
        self.folder_label.pack(side="left", padx=10, pady=10)
        self.folder_entry = ctk.CTkEntry(self.folder_frame, width=200)
        self.folder_entry.pack(side="left", padx=10, pady=10)
        self.browse_button = ctk.CTkButton(self.folder_frame, text="Buscar...", width=70, command=self.browse_folder)
        self.browse_button.pack(side="left", padx=10, pady=10)

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Estado: No Sincronizado", font=("Helvetica", 13, "bold"), text_color="gray")
        self.status_label.pack(pady=15)

        # Control Buttons
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.pack(pady=10)
        
        self.start_button = ctk.CTkButton(self.buttons_frame, text="Conectar y Sincronizar", command=self.start_sync, width=180)
        self.start_button.pack(side="left", padx=10)

        self.stop_button = ctk.CTkButton(self.buttons_frame, text="Detener", command=self.stop_sync, state="disabled", width=120)
        self.stop_button.pack(side="left", padx=10)

        # Activity logs
        self.log_textbox = ctk.CTkTextbox(self, width=490, height=120)
        self.log_textbox.pack(pady=20, padx=30)
        self.log_textbox.insert("0.0", "Cliente Kognito Sync iniciado.\n")
        self.log_textbox.configure(state="disabled")

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def browse_folder(self):
        folder = ctk.filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    self.url_entry.insert(0, config.get("server_url", ""))
                    self.user_entry.insert(0, config.get("username", ""))
                    self.pass_entry.insert(0, config.get("password", ""))
                    self.folder_entry.insert(0, config.get("sync_dir", ""))
            except Exception as e:
                self.log(f"Error al cargar config: {e}")

    def save_config(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        config = {
            "server_url": self.url_entry.get(),
            "username": self.user_entry.get(),
            "password": self.pass_entry.get(),
            "sync_dir": self.folder_entry.get()
        }
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            self.log(f"Error al guardar config: {e}")

    def start_sync(self):
        server_url = self.url_entry.get()
        username = self.user_entry.get()
        password = self.pass_entry.get()
        sync_dir = self.folder_entry.get()
        
        if not server_url or not username or not password or not sync_dir:
            self.log("Error: Por favor completa todos los campos.")
            return

        self.save_config()

        db_path = os.path.expanduser("~/.local/share/kognito-sync/metadata.db")
        self.sync_manager = KognitoSyncManager(server_url, username, password, sync_dir, db_path)

        self.log("Conectando con el servidor...")
        self.start_button.configure(state="disabled")
        
        def conn_thread():
            if self.sync_manager.login():
                self.log("Inicio de sesión correcto.")
                self.status_label.configure(text="Estado: Sincronizando", text_color="green")
                self.stop_button.configure(state="normal")
                
                # Start loop
                self.sync_thread = threading.Thread(target=self.sync_manager.run_sync_loop, daemon=True)
                self.sync_thread.start()
            else:
                self.log("Error: No se pudo conectar o iniciar sesión.")
                self.start_button.configure(state="normal")
                self.status_label.configure(text="Estado: Error de Conexión", text_color="red")
        
        threading.Thread(target=conn_thread, daemon=True).start()

    def stop_sync(self):
        if self.sync_manager:
            self.sync_manager.stop()
            self.log("Sincronización detenida.")
            self.status_label.configure(text="Estado: Detenido", text_color="orange")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def minimize_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            self.setup_tray()

    def setup_tray(self):
        image = create_default_icon()
        menu = (
            item('Abrir Configuración', self.restore_from_tray),
            item('Sincronizar ahora', self.sync_now_action),
            item('Salir', self.quit_app)
        )
        self.tray_icon = pystray.Icon("KognitoSync", image, "Kognito Sync", menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def sync_now_action(self):
        if self.sync_manager:
            self.log("Ejecutando forzado de sync...")
            threading.Thread(target=self.sync_manager.sync_pass, daemon=True).start()

    def restore_from_tray(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.deiconify()

    def quit_app(self):
        self.stop_sync()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = SyncApp()
    app.mainloop()
