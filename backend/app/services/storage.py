from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from uuid import uuid4
import re

import httpx
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
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename or "cv").stem).strip("-._") or "cv"
        safe_name = f"{uuid4().hex}_{stem[:80]}{suffix}"
        target = self.base_dir / safe_name
        target.write_bytes(content)
        return f"local://{safe_name}"

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

    def read_by_url(self, file_url: str) -> bytes | None:
        name = Path(file_url.rstrip("/").split("/")[-1]).name
        target = (self.base_dir / name).resolve()
        if target.parent != self.base_dir.resolve() or not target.is_file():
            return None
        return target.read_bytes()


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

    def read_by_url(self, file_url: str) -> bytes | None:
        return None


class SupabaseStorageService:
    def __init__(self):
        self.base_url = settings.supabase_url.rstrip("/")
        self.key = settings.supabase_service_role_key
        self.bucket = settings.supabase_storage_bucket

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.key}", "apikey": self.key}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def save(self, file: UploadFile) -> str:
        content = await file.read()
        return self.save_bytes(file.filename, content, file.content_type)

    def save_bytes(self, filename: str, content: bytes, content_type: str | None = None) -> str:
        suffix = Path(filename or "cv").suffix.lower()
        name = Path(filename or "cv").stem.replace(" ", "-")
        path = f"{uuid4().hex}_{name[:80]}{suffix}"
        url = f"{self.base_url}/storage/v1/object/{quote(self.bucket)}/{quote(path)}"
        response = httpx.put(
            url,
            content=content,
            headers=self._headers(content_type or "application/octet-stream"),
            timeout=30,
        )
        response.raise_for_status()
        return f"supabase://{self.bucket}/{path}"

    def delete_by_url(self, file_url: str) -> bool:
        prefix = f"{self.base_url}/storage/v1/object/public/{self.bucket}/"
        marker = f"supabase://{self.bucket}/"
        if file_url.startswith(marker):
            path = file_url[len(marker):]
        elif file_url.startswith(prefix):
            path = file_url[len(prefix):]
        else:
            return False
        url = f"{self.base_url}/storage/v1/object/{quote(self.bucket)}/{path}"
        response = httpx.delete(url, headers=self._headers(), timeout=30)
        return response.is_success

    def read_by_url(self, file_url: str) -> bytes | None:
        prefix = f"{self.base_url}/storage/v1/object/public/{self.bucket}/"
        marker = f"supabase://{self.bucket}/"
        if file_url.startswith(marker):
            path = file_url[len(marker):]
        elif file_url.startswith(prefix):
            path = file_url[len(prefix):]
        else:
            return None
        response = httpx.get(f"{self.base_url}/storage/v1/object/{quote(self.bucket)}/{path}", headers=self._headers(), timeout=30)
        return response.content if response.is_success else None


def get_storage_service():
    mode = (settings.storage_mode or "local").strip().lower()
    if mode == "supabase":
        return SupabaseStorageService()
    if mode in {"none", "suppressed", "metadata-only"}:
        return NoRawStorageService()
    return LocalStorageService()
