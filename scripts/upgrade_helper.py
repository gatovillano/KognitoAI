#!/usr/bin/env python3
"""
upgrade_helper.py - Gestión del ciclo de vida de extensiones durante actualizaciones.

Uso:
  python scripts/upgrade_helper.py --pre-upgrade   Desinstala extensiones activas y guarda estado.
  python scripts/upgrade_helper.py --post-upgrade  Reinstala extensiones previamente activas.
"""

import os
import sys
import json
import subprocess

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_DIR = os.path.join(REPO_DIR, "extensions")
EXT_DIR_PARENT = os.path.join(os.path.dirname(REPO_DIR), "extensions")
STATE_FILE = os.path.expanduser("~/.kognito/config/active_extensions.json")


def find_ext_install_py(ext_name: str) -> str:
    """Finds the path to install.py for a given extension name."""
    local_path = os.path.join(REPO_DIR, "extensions", ext_name, "install.py")
    if os.path.isfile(local_path):
        return local_path

    parent_path = os.path.join(EXT_DIR_PARENT, ext_name, "install.py")
    if os.path.isfile(parent_path):
        return parent_path

    return ""


def is_extension_active(ext_name: str) -> bool:
    """Checks if the extension is currently installed/active in the repository."""
    # 1. Heuristic A: backend directory exists in api/
    if os.path.isdir(os.path.join(REPO_DIR, "api", ext_name)):
        return True
    
    # 2. Heuristic B: skill directory exists in skills/
    if os.path.isdir(os.path.join(REPO_DIR, "skills", f"{ext_name}_skill")):
        return True
    if os.path.isdir(os.path.join(REPO_DIR, "skills", ext_name)):
        return True

    # 3. Heuristic C: registered in api/main.py
    main_py = os.path.join(REPO_DIR, "api", "main.py")
    if os.path.isfile(main_py):
        try:
            with open(main_py, "r", encoding="utf-8") as f:
                content = f.read()
            if ext_name in content:
                return True
        except Exception:
            pass

    return False


def get_python_bin() -> str:
    """Returns the virtual environment Python executable, or falls back to system Python."""
    candidate = os.path.join(REPO_DIR, "venv_host", "bin", "python")
    if os.path.isfile(candidate):
        return candidate
    return sys.executable


def get_installed_extensions() -> list:
    """Scans local and parent extensions/ directories for active extensions."""
    active = []
    ext_dirs = []
    
    local_ext = os.path.join(REPO_DIR, "extensions")
    if os.path.isdir(local_ext):
        ext_dirs.append(local_ext)
        
    parent_ext = EXT_DIR_PARENT
    if os.path.isdir(parent_ext):
        ext_dirs.append(parent_ext)
        
    candidates = set()
    for d in ext_dirs:
        for item in os.listdir(d):
            item_path = os.path.join(d, item)
            if os.path.isdir(item_path):
                if os.path.isfile(os.path.join(item_path, "install.py")):
                    candidates.add(item)
                    
    for ext in sorted(candidates):
        if is_extension_active(ext):
            active.append(ext)
            
    return active


def pre_upgrade():
    """
    Pre-upgrade hook:
      1. Detect active extensions.
      2. Persist their names to ~/.kognito/config/active_extensions.json.
      (No destructive uninstall is performed, keeping all extension files and code intact).
    """
    active = get_installed_extensions()

    if not active:
        print("  ✓ No se detectaron extensiones activas. Continuando con la actualización.")
        if os.path.exists(STATE_FILE):
            try:
                os.remove(STATE_FILE)
            except OSError:
                pass
        return

    print(f"  🧩 Extensiones activas detectadas: {', '.join(active)}")

    # Persist state
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(active, f)
    print(f"  💾 Estado de extensiones resguardado en: {STATE_FILE}")


def post_upgrade():
    """
    Post-upgrade hook:
      1. Read the persisted state file.
      2. Ensure component files and DB schema sync for active extensions are in place (passing --no-build).
      3. Remove the state file.
    """
    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            active = json.load(f)
    except Exception as e:
        print(f"  ❌ Error leyendo archivo de estado de extensiones ({STATE_FILE}): {e}")
        return

    if not active:
        try:
            os.remove(STATE_FILE)
        except OSError:
            pass
        return

    print(f"  🧩 Sincronizando componentes para extensiones activas: {', '.join(active)}")

    python_bin = get_python_bin()

    for ext in active:
        ext_install_py = find_ext_install_py(ext)
        if not ext_install_py:
            print(f"  ⚠️ No se encontró install.py para {ext}. Omitiendo.")
            continue

        print(f"  ⚙️  Sincronizando componentes: {ext} ...")
        try:
            result = subprocess.run(
                [python_bin, ext_install_py, "--no-build"],
                cwd=REPO_DIR,
                env=dict(os.environ, PYTHONPATH=REPO_DIR, KOGNITO_SKIP_BUILD="1"),
                check=False,
            )
            if result.returncode == 0:
                print(f"  ✓ {ext} sincronizada con éxito.")
            else:
                print(f"  ⚠️  {ext}: la sincronización terminó con código {result.returncode}.")
        except Exception as e:
            print(f"  ❌ Error al sincronizar {ext}: {e}")

    # Clean up state file
    try:
        os.remove(STATE_FILE)
    except OSError:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("--pre-upgrade", "--post-upgrade"):
        print("Uso: upgrade_helper.py [--pre-upgrade|--post-upgrade]")
        sys.exit(1)

    if sys.argv[1] == "--pre-upgrade":
        pre_upgrade()
    elif sys.argv[1] == "--post-upgrade":
        post_upgrade()
