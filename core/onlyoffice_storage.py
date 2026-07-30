import os
from pathlib import Path
from typing import Union

from core.config import settings


ONLYOFFICE_DOCS_ROOT = Path(settings.onlyoffice_docs_root).resolve()
ONLYOFFICE_DOCS_ROOT.mkdir(parents=True, exist_ok=True)


def get_onlyoffice_docs_root() -> Path:
    return ONLYOFFICE_DOCS_ROOT


from typing import Union, Optional

def ensure_onlyoffice_account_dir(account_id: str, cloud_storage_path: Optional[str] = None) -> Path:
    if cloud_storage_path:
        account_dir = Path(cloud_storage_path) / "documents" / str(account_id)
    else:
        account_dir = ONLYOFFICE_DOCS_ROOT / str(account_id)
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir


def build_onlyoffice_relative_path(account_id: str, filename: str) -> str:
    return str(Path(str(account_id)) / filename)


def resolve_onlyoffice_file_path(file_path: Union[str, os.PathLike[str]]) -> Path:
    raw_path = str(file_path).strip()
    if not raw_path:
        raise ValueError("OnlyOffice file_path no puede estar vacío")

    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate.resolve()

    project_root = Path(__file__).resolve().parent.parent

    # Lista completa de raíces potenciales donde se han almacenado documentos
    candidate_roots = [
        ONLYOFFICE_DOCS_ROOT,
        Path(settings.media_root).resolve() / "documents" if hasattr(settings, "media_root") and settings.media_root else None,
        Path(settings.media_root).resolve() if hasattr(settings, "media_root") and settings.media_root else None,
        Path.home() / ".kognito" / "storage" / "onlyoffice" / "documents",
        Path.home() / "KognitoAI" / "storage" / "onlyoffice" / "documents",
        Path.home() / "KognitoAI" / "media" / "documents",
        project_root / "media" / "documents" / "documents",
        project_root / "media" / "documents",
        Path("/run/media/gato/Almacenamiento/Nueva Fototeca/kognitoalbums/documents"),
        Path("/run/media/gato/Almacenamiento/Nueva Fototeca/kognitoalbums"),
    ]

    for root in candidate_roots:
        if not root:
            continue
        try:
            resolved_root = root.resolve()
            if not resolved_root.exists():
                continue
            test_path = (resolved_root / candidate).resolve()
            test_path.relative_to(resolved_root)
            if test_path.exists():
                if not test_path.is_file():
                    raise ValueError(
                        f"La ruta resuelta no es un archivo (es un directorio): {raw_path}"
                    )
                return test_path
        except ValueError:
            pass

    # Si no existe en ningún lado, devolvemos la ruta por defecto en ONLYOFFICE_DOCS_ROOT
    resolved_onlyoffice = (ONLYOFFICE_DOCS_ROOT / candidate).resolve()
    try:
        resolved_onlyoffice.relative_to(ONLYOFFICE_DOCS_ROOT)
    except ValueError as exc:
        raise ValueError(f"OnlyOffice file_path fuera de la raíz configurada: {raw_path}") from exc

    if resolved_onlyoffice.exists() and not resolved_onlyoffice.is_file():
        raise ValueError(
            f"La ruta resuelta no es un archivo (es un directorio): {raw_path}"
        )

    return resolved_onlyoffice


