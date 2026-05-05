from pathlib import Path
from datetime import datetime
from fastapi import UploadFile

from app.config import settings


class LocalStorageService:
    def __init__(self):
        self.base_dir = Path(settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile) -> str:
        content = await file.read()
        return self.save_bytes(file.filename, content)

    def save_bytes(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        safe_name = f"{datetime.utcnow().timestamp():.0f}_{Path(filename).stem}{suffix}"
        target = self.base_dir / safe_name
        target.write_bytes(content)
        return f"{settings.public_base_url}/uploads/{safe_name}"

    def delete_by_url(self, file_url: str) -> bool:
        try:
            name = file_url.rstrip('/').split('/')[-1]
            target = self.base_dir / name
            if target.exists():
                target.unlink()
                return True
        except Exception:
            return False
        return False


class NoRawStorageService:
    """Production-friendly mode to avoid persisting raw CV files on app disk.
    Keeps only metadata URLs/markers and returns success for delete operations.
    """

    async def save(self, file: UploadFile) -> str:
        return self.save_bytes(file.filename, b"")

    def save_bytes(self, filename: str, content: bytes) -> str:
        suffix = Path(filename or "cv").suffix.lower()
        key = f"raw-suppressed/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{Path(filename or 'cv').stem}{suffix}"
        return f"suppressed://{key}"

    def delete_by_url(self, file_url: str) -> bool:
        return True


def get_storage_service():
    mode = (settings.storage_mode or "local").strip().lower()
    if mode in {"none", "suppressed", "metadata-only"}:
        return NoRawStorageService()
    return LocalStorageService()
