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
STATE_FILE = os.path.expanduser("~/.kognito/config/active_extensions.json")


def get_python_bin() -> str:
    """Returns the virtual environment Python executable, or falls back to system Python."""
    candidate = os.path.join(REPO_DIR, "venv_host", "bin", "python")
    if os.path.isfile(candidate):
        return candidate
    return sys.executable


def get_installed_extensions() -> list:
    """
    Scans the extensions/ directory for active extensions.

    An extension is considered active if:
      1. It has a subdirectory in extensions/ with an install.py file.
      2. It has a matching backend subdirectory inside api/ (e.g. api/gallery_selection_panel).
    """
    active = []
    if not os.path.isdir(EXT_DIR):
        return active

    for item in sorted(os.listdir(EXT_DIR)):
        item_path = os.path.join(EXT_DIR, item)
        if not os.path.isdir(item_path):
            continue

        install_py = os.path.join(item_path, "install.py")
        if not os.path.isfile(install_py):
            continue

        # Heuristic: active = backend directory was injected into api/
        backend_dir = os.path.join(REPO_DIR, "api", item)
        if os.path.isdir(backend_dir):
            active.append(item)

    return active


def pre_upgrade():
    """
    Pre-upgrade hook:
      1. Detect active extensions.
      2. Persist their names to ~/.kognito/config/active_extensions.json.
      3. Run each extension's install.py --uninstall to restore a clean repo state.
    """
    active = get_installed_extensions()

    if not active:
        print("  ✓ No se detectaron extensiones activas. Continuando con la actualización.")
        # Remove any stale state file
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
    print(f"  💾 Estado guardado en: {STATE_FILE}")

    python_bin = get_python_bin()

    for ext in active:
        ext_install_py = os.path.join(EXT_DIR, ext, "install.py")
        if not os.path.isfile(ext_install_py):
            print(f"  ⚠️  No se encontró install.py para {ext}. Omitiendo desinstalación.")
            continue

        print(f"  🔄 Desinstalando temporalmente: {ext} ...")
        try:
            result = subprocess.run(
                [python_bin, ext_install_py, "--uninstall"],
                cwd=REPO_DIR,
                env=dict(os.environ, PYTHONPATH=REPO_DIR),
                check=False,
            )
            if result.returncode == 0:
                print(f"  ✓ {ext} desinstalada temporalmente.")
            else:
                print(f"  ⚠️  {ext}: el desinstalador terminó con código {result.returncode}. Continuando.")
        except Exception as e:
            print(f"  ❌ Error al desinstalar {ext}: {e}")


def post_upgrade():
    """
    Post-upgrade hook:
      1. Read the persisted state file.
      2. Re-run each extension's install.py.
      3. Remove the state file.
    """
    if not os.path.exists(STATE_FILE):
        # Nothing to reinstall
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

    print(f"  🧩 Reinstalando extensiones previamente activas: {', '.join(active)}")

    python_bin = get_python_bin()

    for ext in active:
        ext_install_py = os.path.join(EXT_DIR, ext, "install.py")
        if not os.path.isfile(ext_install_py):
            print(f"  ❌ No se encontró install.py para {ext} en {ext_install_py}. Omitiendo.")
            continue

        print(f"  ⚙️  Reinstalando: {ext} ...")
        try:
            result = subprocess.run(
                [python_bin, ext_install_py],
                cwd=REPO_DIR,
                env=dict(os.environ, PYTHONPATH=REPO_DIR),
                check=False,
            )
            if result.returncode == 0:
                print(f"  ✓ {ext} reinstalada con éxito.")
            else:
                print(f"  ⚠️  {ext}: el instalador terminó con código {result.returncode}. Verifica manualmente.")
        except Exception as e:
            print(f"  ❌ Error al reinstalar {ext}: {e}")

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
