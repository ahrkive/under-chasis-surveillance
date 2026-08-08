"""
Local Filesystem Storage Backend
=================================
"""

import logging
import os
from pathlib import Path

import aiofiles

from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class LocalStorage(StorageBackend):
    """Store images on the local filesystem."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorage initialized at: %s", self.base_path)

    def _full_path(self, key: str) -> Path:
        return self.base_path / key

    async def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        full_path = self._full_path(key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(str(full_path), "wb") as f:
            await f.write(data)
        logger.debug("Stored locally: %s (%d bytes)", key, len(data))
        return str(full_path)

    async def download(self, key: str) -> bytes:
        full_path = self._full_path(key)
        async with aiofiles.open(str(full_path), "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> None:
        full_path = self._full_path(key)
        try:
            os.remove(str(full_path))
        except OSError:
            pass

    async def list_keys(self, prefix: str = "") -> list[str]:
        search_path = self._full_path(prefix) if prefix else self.base_path
        keys = []
        if search_path.is_dir():
            for root, _, files in os.walk(str(search_path)):
                for f in files:
                    full = Path(root) / f
                    rel = full.relative_to(self.base_path)
                    keys.append(str(rel).replace("\\", "/"))
        return keys

    async def exists(self, key: str) -> bool:
        return self._full_path(key).exists()
