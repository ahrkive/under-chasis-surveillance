"""
Abstract Storage Interface
===========================
Pluggable storage backend for inspection images.
Implementations: local filesystem, AWS S3, GCS, Azure Blob.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """
        Upload data to storage.

        Args:
            key: Storage key/path (e.g., "approved/bot-001/image.jpg")
            data: Raw bytes to upload.
            content_type: MIME type.

        Returns:
            URL or path to the stored object.
        """
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download data from storage by key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete an object from storage."""
        ...

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with the given prefix."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if an object exists."""
        ...


# ── Singleton ────────────────────────────────────────────────────────────
_storage: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Get or create the singleton storage instance based on config."""
    global _storage
    if _storage is not None:
        return _storage

    settings = get_settings()
    provider = settings.storage_provider

    if provider == "local":
        from app.storage.local import LocalStorage
        _storage = LocalStorage(settings.storage_local_path)
    elif provider == "s3":
        from app.storage.s3 import S3Storage
        _storage = S3Storage(
            bucket=settings.s3_bucket_name,
            region=settings.aws_region,
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key,
        )
    elif provider == "gcs":
        from app.storage.gcs import GCSStorage
        _storage = GCSStorage(
            bucket=settings.gcs_bucket_name,
            credentials_path=settings.gcs_credentials_path,
        )
    elif provider == "azure":
        from app.storage.azure_blob import AzureBlobStorage
        _storage = AzureBlobStorage(
            connection_string=settings.azure_connection_string,
            container=settings.azure_container_name,
        )
    else:
        raise ValueError(f"Unknown storage provider: {provider}")

    logger.info("Storage initialized: provider=%s", provider)
    return _storage
