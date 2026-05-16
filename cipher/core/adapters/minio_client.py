"""MinIO client wrapper (T-008)."""

from __future__ import annotations

import os

from minio import Minio


def get_minio_endpoint() -> str:
    return os.environ.get("MINIO_ENDPOINT", "localhost:9000")


def get_minio_client() -> Minio:
    return Minio(
        endpoint=get_minio_endpoint(),
        access_key=os.environ.get("MINIO_ROOT_USER", "cipher"),
        secret_key=os.environ.get("MINIO_ROOT_PASSWORD", "cipher_secret"),
        secure=False,
    )


class MinioStore:
    """MinIO object store wrapper for CIPHER artifacts."""

    BUCKET = "cipher-artifacts"

    def __init__(self, client: Minio | None = None) -> None:
        self._client = client or get_minio_client()

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self.BUCKET):
            self._client.make_bucket(self.BUCKET)

    def bucket_exists(self) -> bool:
        return self._client.bucket_exists(self.BUCKET)

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        from io import BytesIO

        self._client.put_object(
            self.BUCKET, key, BytesIO(data), len(data), content_type=content_type
        )

    def get_object(self, key: str) -> bytes:
        resp = self._client.get_object(self.BUCKET, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
