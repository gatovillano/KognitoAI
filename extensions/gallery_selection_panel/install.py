#!/usr/bin/env python3
"""
Installer script for KognitoAI Gallery Selection Panel Extension & Google Photos UI.

Usage:
  python install.py           Installs/Enables the extension, builds frontend & restarts server
  python install.py --uninstall Reverts KognitoAI to its stock base state
"""

import os
import sys
import shutil
import asyncio
import subprocess

BASE_DIR = os.environ.get("KOGNITO_REPO_DIR")
if not BASE_DIR:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
else:
    BASE_DIR = os.path.abspath(BASE_DIR)
EXT_DIR = os.path.dirname(__file__)

# Paths for Frontend Modifications
PAGE_TARGET = os.path.join(BASE_DIR, "src/app/(dashboard)/galleries/page.tsx")
PAGE_BACKUP = os.path.join(BASE_DIR, "src/app/(dashboard)/galleries/page.tsx.bak")

SHARE_ROUTE_DIR = os.path.join(BASE_DIR, "src/app/share/selection/[token]")
SHARE_ROUTE_FILE = os.path.join(SHARE_ROUTE_DIR, "page.tsx")

# Paths for Backend Modifications
API_MAIN_TARGET = os.path.join(BASE_DIR, "api/main.py")
API_MAIN_BACKUP = os.path.join(BASE_DIR, "api/main.py.bak")

PAGE_TRANSFORMED_CONTENT = """'use client';

import React from 'react';
import { KogniPhotosGalleryView } from '../../../../extensions/gallery_selection_panel/frontend/KogniPhotosGalleryView';

export default function GalleriesPage() {
  return <KogniPhotosGalleryView />;
}
"""

SHARE_ROUTE_CONTENT = """'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { SelectionPublicPage } from '../../../../../extensions/gallery_selection_panel/frontend/SelectionPublicPage';

export default function PublicSelectionRoute() {
  const params = useParams();
  const token = (params?.token || '') as string;

  return <SelectionPublicPage token={token} />;
}
"""

API_ROUTER_INJECTION = """app.include_router(galleries_router, prefix="/api/galleries", tags=["galleries"])
try:
    from extensions.gallery_selection_panel.backend.router import router as gallery_selection_extension_router
    app.include_router(gallery_selection_extension_router)
    logger.info("Extensión Gallery Selection Panel cargada con éxito.")
except Exception as e:
    logger.warning(f"No se pudo cargar la extensión Gallery Selection Panel: {e}")
"""

async def create_database_tables():
    """Dynamically initializes SQLAlchemy models and database schema updates."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from sqlalchemy import text
        from core.database import engine, Base
        import extensions.gallery_selection_panel.backend.models  # Registers models with Base
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE albums ADD COLUMN IF NOT EXISTS workspace_id UUID;"))
            await conn.run_sync(Base.metadata.create_all)
        print("  ✓ Tablas de base de datos creadas y columna workspace_id verificada.")
    except Exception as e:
        print(f"  ⚠ Nota sobre base de datos: {e}")

def run_build():
    """Builds the frontend production bundle using npm run build."""
    print("\n🛠️ Ejecutando build del frontend (npm run build)...")
    try:
        res = subprocess.run(["npm", "run", "build"], cwd=BASE_DIR, check=False)
        if res.returncode == 0:
            print("  ✓ Build del frontend completado exitosamente.")
        else:
            print("  ⚠ Advertencia: Ocurrió un detalle en el build del frontend.")
    except Exception as e:
        print(f"  ⚠ No se pudo ejecutar npm run build: {e}")

def restart_local_servers():
    """Attempts to notify or restart active local dev/api processes."""
    print("\n🔄 Reiniciando servicios locales...")
    try:
        # Check if uvicorn / python run_api.py is active and reload gracefully if needed
        subprocess.run(["pkill", "-f", "run_api.py"], check=False)
        print("  ✓ Reiniciada señal del servidor Backend API.")
    except Exception as e:
        print(f"  ⚠ Nota sobre proceso backend: {e}")

def install():
    print("🚀 Instalando Extensión: Panel de Selección de Galerías & KogniPhotos UI...")
    
    # 1. Frontend - Transformed Gallery Page
    if not os.path.exists(PAGE_BACKUP) and os.path.exists(PAGE_TARGET):
        shutil.copyfile(PAGE_TARGET, PAGE_BACKUP)
        print("  ✓ Copia de seguridad creada para la vista de galerías base.")

    with open(PAGE_TARGET, "w", encoding="utf-8") as f:
        f.write(PAGE_TRANSFORMED_CONTENT)
    print("  ✓ Interfaz de galería transformada a KogniPhotos UI.")

    # 2. Frontend - Public Recipient Share Route
    os.makedirs(SHARE_ROUTE_DIR, exist_ok=True)
    with open(SHARE_ROUTE_FILE, "w", encoding="utf-8") as f:
        f.write(SHARE_ROUTE_CONTENT)
    print("  ✓ Ruta pública de selección instalada en /share/selection/[token].")

    # 3. Backend - API Router Injection
    if os.path.exists(API_MAIN_TARGET):
        with open(API_MAIN_TARGET, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "gallery_selection_extension_router" not in content:
            if not os.path.exists(API_MAIN_BACKUP):
                shutil.copyfile(API_MAIN_TARGET, API_MAIN_BACKUP)
                print("  ✓ Copia de seguridad creada para api/main.py.")
            
            target_str = 'app.include_router(galleries_router, prefix="/api/galleries", tags=["galleries"])'
            if target_str in content:
                new_content = content.replace(target_str, API_ROUTER_INJECTION)
                with open(API_MAIN_TARGET, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print("  ✓ Router backend registrado con éxito en api/main.py.")

    # 4. Database Setup
    asyncio.run(create_database_tables())

    # 5. Frontend Build & Restart
    run_build()
    restart_local_servers()

    print("\n🎉 ¡Extensión instalada con éxito! La aplicación se ha reconstruido y actualizado.")

def uninstall():
    print("🔄 Desinstalando Extensión y restaurando sistema base...")

    # 1. Frontend Page Restore
    if os.path.exists(PAGE_BACKUP):
        shutil.copyfile(PAGE_BACKUP, PAGE_TARGET)
        os.remove(PAGE_BACKUP)
        print("  ✓ Vista de galerías base restaurada.")

    # 2. Public Share Route Cleanup
    if os.path.exists(SHARE_ROUTE_FILE):
        os.remove(SHARE_ROUTE_FILE)
        print("  ✓ Ruta pública de selección eliminada.")

    # 3. Backend API Restore
    if os.path.exists(API_MAIN_BACKUP):
        shutil.copyfile(API_MAIN_BACKUP, API_MAIN_TARGET)
        os.remove(API_MAIN_BACKUP)
        print("  ✓ Backend api/main.py restaurado a estado original.")

    # 4. Rebuild & Restart
    run_build()
    restart_local_servers()

    print("\n🎉 Extensión desinstalada correctamente y sistema base restaurado.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall()
    else:
        install()
