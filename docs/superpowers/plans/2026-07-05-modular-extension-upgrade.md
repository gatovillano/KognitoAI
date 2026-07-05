# Mecanismo de Actualización Adaptativo para Extensiones Modulares

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a helper script (`scripts/upgrade_helper.py`) and integrate it into the `kognitoai` CLI (`cmd_upgrade`) so that active extensions are automatically uninstalled before a `git pull` and reinstalled afterwards.

**Architecture:**
- `scripts/upgrade_helper.py` scans `extensions/` for installers (`install.py`).
- Active extensions are detected if they have a matching backend subdirectory inside `api/`.
- Active extensions are serialized to `~/.kognito/config/active_extensions.json`.
- The CLI runs the helper script during pre-upgrade and post-upgrade phases of `cmd_upgrade`.

**Tech Stack:** Python 3, Bash, Git.

## Global Constraints
- Do not modify files outside the workspace directories.
- Ensure all execution paths resolve correctly relative to `REPO_DIR`.
- Maintain full compatibility with existing `install.py` options (`--uninstall`).

---

### Task 1: Create the upgrade helper script and tests

**Files:**
- Create: [upgrade_helper.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/scripts/upgrade_helper.py)
- Create: [test_upgrade_helper.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/tests/test_upgrade_helper.py)

**Interfaces:**
- Consumes: None (looks up filesystem state dynamically)
- Produces: State JSON file at `~/.kognito/config/active_extensions.json`, invokes subprocess installers.

- [ ] **Step 1: Create the helper script file**
Create the helper script in `/home/gato/Proyectos/KognitoAI/kognito-ai/scripts/upgrade_helper.py` with the following content:
```python
#!/usr/bin/env python3
import os
import sys
import json
import subprocess

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_DIR = os.path.join(REPO_DIR, "extensions")
STATE_FILE = os.path.expanduser("~/.kognito/config/active_extensions.json")

def get_installed_extensions():
    """Finds active extensions in the main Kognito AI repository."""
    active = []
    if not os.path.isdir(EXT_DIR):
        return active
    for item in os.listdir(EXT_DIR):
        item_path = os.path.join(EXT_DIR, item)
        if os.path.isdir(item_path):
            install_py = os.path.join(item_path, "install.py")
            if os.path.isfile(install_py):
                # Heuristic: check if api/<ext_name> folder exists in the main repository
                backend_dir = os.path.join(REPO_DIR, "api", item)
                if os.path.isdir(backend_dir):
                    active.append(item)
    return active

def pre_upgrade():
    """Saves active extensions and uninstalls them."""
    active = get_installed_extensions()
    if not active:
        print("  ✓ No se detectaron extensiones activas.")
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        return

    print(f"  🧩 Extensiones activas detectadas: {', '.join(active)}")
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(active, f)

    # Use virtual environment python if it exists
    python_bin = os.path.join(REPO_DIR, "venv_host", "bin", "python")
    if not os.path.isfile(python_bin):
        python_bin = sys.executable

    for ext in active:
        print(f"  🔄 Desinstalando temporalmente {ext}...")
        ext_install_py = os.path.join(EXT_DIR, ext, "install.py")
        try:
            subprocess.run(
                [python_bin, ext_install_py, "--uninstall"],
                cwd=REPO_DIR,
                env=dict(os.environ, PYTHONPATH=REPO_DIR),
                check=True
            )
            print(f"  ✓ {ext} desinstalada temporalmente.")
        except Exception as e:
            print(f"  ❌ Error al desinstalar {ext}: {e}")

def post_upgrade():
    """Re-installs extensions saved in the state file."""
    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r") as f:
            active = json.load(f)
    except Exception as e:
        print(f"  ❌ Error leyendo archivo de estado de extensiones: {e}")
        return

    if not active:
        return

    print(f"  🧩 Reinstalando extensiones: {', '.join(active)}")
    python_bin = os.path.join(REPO_DIR, "venv_host", "bin", "python")
    if not os.path.isfile(python_bin):
        python_bin = sys.executable

    for ext in active:
        ext_install_py = os.path.join(EXT_DIR, ext, "install.py")
        if os.path.isfile(ext_install_py):
            print(f"  ⚙️  Reinstalando {ext}...")
            try:
                subprocess.run(
                    [python_bin, ext_install_py],
                    cwd=REPO_DIR,
                    env=dict(os.environ, PYTHONPATH=REPO_DIR),
                    check=True
                )
                print(f"  ✓ {ext} reinstalada con éxito.")
            except Exception as e:
                print(f"  ❌ Error al reinstalar {ext}: {e}")
        else:
            print(f"  ❌ No se encontró el instalador para {ext} en {ext_install_py}")

    # Clean up state file
    try:
        os.remove(STATE_FILE)
    except Exception as e:
        pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: upgrade_helper.py [--pre-upgrade|--post-upgrade]")
        sys.exit(1)
    if sys.argv[1] == "--pre-upgrade":
        pre_upgrade()
    elif sys.argv[1] == "--post-upgrade":
        post_upgrade()
```

- [ ] **Step 2: Create unit tests**
Create the unit test file in `/home/gato/Proyectos/KognitoAI/kognito-ai/tests/test_upgrade_helper.py` with the following content:
```python
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Mock state file path during import setup
with patch('scripts.upgrade_helper.os.path.expanduser', return_value='/tmp/.kognito/config/active_extensions.json'):
    import scripts.upgrade_helper as uh

class TestUpgradeHelper(unittest.TestCase):
    @patch('scripts.upgrade_helper.os.path.isdir')
    @patch('scripts.upgrade_helper.os.listdir')
    @patch('scripts.upgrade_helper.os.path.isfile')
    def test_get_installed_extensions(self, mock_isfile, mock_listdir, mock_isdir):
        mock_listdir.return_value = ['gallery_selection_panel', 'some_file.txt']
        mock_isdir.side_effect = lambda path: 'gallery_selection_panel' in path or 'api/gallery_selection_panel' in path
        mock_isfile.side_effect = lambda path: 'install.py' in path
        
        extensions = uh.get_installed_extensions()
        self.assertEqual(extensions, ['gallery_selection_panel'])

    @patch('scripts.upgrade_helper.get_installed_extensions')
    @patch('scripts.upgrade_helper.subprocess.run')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('scripts.upgrade_helper.os.makedirs')
    @patch('scripts.upgrade_helper.os.path.exists')
    def test_pre_upgrade(self, mock_exists, mock_makedirs, mock_file, mock_run, mock_get_extensions):
        mock_get_extensions.return_value = ['gallery_selection_panel']
        uh.pre_upgrade()
        
        mock_file.assert_called_with(uh.STATE_FILE, "w")
        mock_run.assert_called_once()
        self.assertIn('--uninstall', mock_run.call_args[0][0])

    @patch('scripts.upgrade_helper.os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='["gallery_selection_panel"]')
    @patch('scripts.upgrade_helper.subprocess.run')
    @patch('scripts.upgrade_helper.os.path.isfile')
    @patch('scripts.upgrade_helper.os.remove')
    def test_post_upgrade(self, mock_remove, mock_isfile, mock_run, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        uh.post_upgrade()
        
        mock_run.assert_called_once()
        self.assertNotIn('--uninstall', mock_run.call_args[0][0])
        mock_remove.assert_called_with(uh.STATE_FILE)
```

- [ ] **Step 3: Run the unit test to verify it passes**
Run: `PYTHONPATH=. pytest tests/test_upgrade_helper.py -v`
Expected: 3 tests pass.

- [ ] **Step 4: Commit the script and tests**
Run:
```bash
git add scripts/upgrade_helper.py tests/test_upgrade_helper.py
git commit -m "feat: add upgrade helper script and tests for modular extensions"
```

---

### Task 2: Modify the CLI upgrade command to call the helper hooks

**Files:**
- Modify: [kognitoai](file:///home/gato/Proyectos/KognitoAI/kognito-ai/kognitoai)

- [ ] **Step 1: Inject the hooks into `cmd_upgrade`**
Modify `kognitoai` in `/home/gato/Proyectos/KognitoAI/kognito-ai/kognitoai` around lines 141-158.
Target Content to replace:
```bash
cmd_upgrade() {
    check_repo
    echo -e "${YELLOW}🔄 Actualizando Kognito AI desde GitHub...${NC}"
    cd "${REPO_DIR}"
    local branch
    branch=$(_detect_branch)
    git pull origin "${branch}"
    echo -e "${BLUE}🐍 Actualizando dependencias de Python...${NC}"
```
Replacement Content:
```bash
cmd_upgrade() {
    check_repo
    echo -e "${YELLOW}🔄 Actualizando Kognito AI desde GitHub...${NC}"
    cd "${REPO_DIR}"
    local branch
    branch=$(_detect_branch)

    local python_bin="./venv_host/bin/python"
    if [ ! -f "${python_bin}" ]; then
        python_bin="python3"
    fi

    if [ -f "scripts/upgrade_helper.py" ]; then
        echo -e "${BLUE}🧩 Desactivando temporalmente extensiones activas...${NC}"
        PYTHONPATH=. "${python_bin}" scripts/upgrade_helper.py --pre-upgrade
    fi

    git pull origin "${branch}"

    if [ -f "scripts/upgrade_helper.py" ]; then
        echo -e "${BLUE}🧩 Reinstalando extensiones previamente activas...${NC}"
        PYTHONPATH=. "${python_bin}" scripts/upgrade_helper.py --post-upgrade
    fi

    echo -e "${BLUE}🐍 Actualizando dependencias de Python...${NC}"
```

- [ ] **Step 2: Commit the CLI modification**
Run:
```bash
git add kognitoai
git commit -m "feat: integrate upgrade helper hooks into kognitoai upgrade CLI command"
```

---

## Verification Plan

### Automated Tests
- Run: `PYTHONPATH=. pytest tests/test_upgrade_helper.py`

### Manual Verification
1. Verify that running `kognitoai upgrade` triggers the pre-upgrade hook (displays detecting/deactivating extensions) and post-upgrade hook (displays reinstating extensions).
