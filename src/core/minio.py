import logging

from minio import Minio

from src.core.config import settings

logger = logging.getLogger(__name__)


class MinIOClient:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        *,
        secure: bool = False,
    ) -> None:
        self.client = Minio(endpoint, access_key, secret_key, secure=secure)
        self.bucket = bucket

    def download(self, object_key: str) -> bytes:
        resp = self.client.get_object(self.bucket, object_key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def object_exists(self, object_key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, object_key)
            return True
        except Exception:
            return False


def create_minio_client() -> MinIOClient:
    return MinIOClient(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        secure=settings.minio_secure,
    )
