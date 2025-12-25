"""MinIO client wrapper for saving and retrieving files.

Uses the ``minio`` Python library to interact with an S3-compatible
object store. Files are uploaded to the bucket specified in the
application settings. If the bucket does not exist, it will be
created automatically on first use.
"""

import os
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings


class MinioService:
    """Service for uploading files to MinIO."""

    def __init__(self) -> None:
        settings = get_settings()
        # Access settings defensively (pydantic field names are uppercase)
        endpoint = getattr(settings, "MINIO_ENDPOINT", None) or getattr(settings, "minio_endpoint", None)
        access_key = getattr(settings, "MINIO_ACCESS_KEY", None) or getattr(settings, "minio_access_key", None)
        secret_key = getattr(settings, "MINIO_SECRET_KEY", None) or getattr(settings, "minio_secret_key", None)
        bucket = getattr(settings, "MINIO_BUCKET", None) or getattr(settings, "minio_bucket", None)
        self._secure = bool(getattr(settings, "MINIO_SECURE", False))
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=self._secure,
        )
        self.bucket = bucket
        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as exc:
            print(f"Error creating/accessing bucket: {exc}")

    def upload_file(self, file_path: str, object_name: Optional[str] = None) -> str:
        """Upload a file to MinIO.

        Args:
            file_path: Local path to the file.
            object_name: Optional custom object name. If omitted the
                basename of the file will be used.
        Returns:
            The object name stored in the bucket.
        """
        object_name = object_name or os.path.basename(file_path)
        self.client.fput_object(self.bucket, object_name, file_path)
        return object_name

    def public_url(self, object_name: str) -> str:
        """Return a fetchable URL for the given object."""
        scheme = "https" if self._secure else "http"
        endpoint = getattr(get_settings(), "MINIO_ENDPOINT", None) or getattr(get_settings(), "minio_endpoint", "")
        endpoint = endpoint.rstrip("/")
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            base = endpoint
        else:
            base = f"{scheme}://{endpoint}"
        return f"{base}/{self.bucket}/{object_name.lstrip('/')}"
