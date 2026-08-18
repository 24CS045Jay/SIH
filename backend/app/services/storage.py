from pathlib import Path
from uuid import UUID

from app.core.config import get_settings


def storage_root() -> Path:
    root = Path(get_settings().storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def version_storage_path(version_id: UUID, filename: str) -> Path:
    safe_name = Path(filename).name.replace(" ", "_")
    folder = storage_root() / str(version_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / safe_name
