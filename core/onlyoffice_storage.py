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

    # 1. Intentar resolver en ONLYOFFICE_DOCS_ROOT
    resolved_onlyoffice = (ONLYOFFICE_DOCS_ROOT / candidate).resolve()
    try:
        resolved_onlyoffice.relative_to(ONLYOFFICE_DOCS_ROOT)
        if resolved_onlyoffice.exists():
            if not resolved_onlyoffice.is_file():
                raise ValueError(
                    f"La ruta resuelta no es un archivo (es un directorio): {raw_path}"
                )
            return resolved_onlyoffice
    except ValueError:
        pass

    # 2. Intentar resolver en MEDIA_ROOT/documents (el almacenamiento externo)
    if hasattr(settings, "media_root") and settings.media_root:
        media_docs_root = Path(settings.media_root).resolve() / "documents"
        try:
            resolved_media = (media_docs_root / candidate).resolve()
            resolved_media.relative_to(media_docs_root)
            if resolved_media.exists():
                if not resolved_media.is_file():
                    raise ValueError(
                        f"La ruta resuelta no es un archivo (es un directorio): {raw_path}"
                    )
                return resolved_media
        except ValueError:
            pass

    # 3. Intentar resolver en el fallback local de desarrollo (media/documents/documents)
    # Buscamos de manera dinámica con respecto a la ubicación del archivo
    project_root = Path(__file__).resolve().parent.parent
    local_fallback_root = (project_root / "media" / "documents" / "documents").resolve()
    try:
        resolved_local = (local_fallback_root / candidate).resolve()
        resolved_local.relative_to(local_fallback_root)
        if resolved_local.exists():
            if not resolved_local.is_file():
                raise ValueError(
                    f"La ruta resuelta no es un archivo (es un directorio): {raw_path}"
                )
            return resolved_local
    except ValueError:
        pass

    # Si no existe en ningún lado, devolvemos la ruta por defecto en ONLYOFFICE_DOCS_ROOT
    # garantizando que pase el chequeo de límites.
    try:
        resolved_onlyoffice.relative_to(ONLYOFFICE_DOCS_ROOT)
    except ValueError as exc:
        raise ValueError(f"OnlyOffice file_path fuera de la raíz configurada: {raw_path}") from exc

    if resolved_onlyoffice.exists() and not resolved_onlyoffice.is_file():
        raise ValueError(
            f"La ruta resuelta no es un archivo (es un directorio): {raw_path}"
        )

    return resolved_onlyoffice

