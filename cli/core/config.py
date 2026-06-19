"""
cli/core/config.py
Gestión de configuración persistente del CLI de KognitoAI.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".kognitocli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _get_default_api_url() -> str:
    port = 8889
    # Intenta buscar .env en el directorio padre del CLI
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_strip = line.strip()
                    if line_strip.startswith("API_PORT=") or "API_PORT" in line_strip:
                        # Si no está comentado
                        if not line_strip.startswith("#"):
                            parts = line_strip.split("=")
                            if len(parts) == 2:
                                port = int(parts[1].strip())
                                break
        except Exception:
            pass
    return f"http://localhost:{port}"


@dataclass
class CLIConfig:
    api_url: str = field(default_factory=_get_default_api_url)
    token: Optional[str] = None
    account_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    workspace_id: Optional[str] = None
    theme: str = "dark"
    last_thread_id: Optional[str] = None

    # Document defaults
    default_doc_dir: str = str(Path.home() / "Documents")

    @classmethod
    def load(cls) -> "CLIConfig":
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
                if cfg.api_url == "http://localhost:8000":
                    cfg.api_url = _get_default_api_url()
                return cfg
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
        from cli.core.auth import secure_config_file
        secure_config_file(str(CONFIG_FILE))

    @property
    def is_authenticated(self) -> bool:
        return bool(self.token and self.account_id)
