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
