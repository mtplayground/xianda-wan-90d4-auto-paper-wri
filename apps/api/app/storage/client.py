from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings

MAX_PRESIGNED_URL_TTL_SECONDS = 604_800


class ObjectStorageError(RuntimeError):
    pass


class ObjectStorageConfigurationError(ObjectStorageError):
    pass


class ObjectStorageKeyError(ObjectStorageError, ValueError):
    pass


@dataclass(frozen=True)
class ObjectStorageConfig:
    access_key_id: str
    secret_access_key: str
    bucket: str
    prefix: str
    endpoint: str
    region: str
    force_path_style: bool

    @classmethod
    def from_settings(cls, settings: Settings) -> "ObjectStorageConfig":
        values = {
            "S3_ACCESS_KEY_ID": settings.s3_access_key_id,
            "S3_SECRET_ACCESS_KEY": settings.s3_secret_access_key,
            "S3_BUCKET": settings.s3_bucket,
            "S3_PREFIX": settings.s3_prefix,
            "S3_ENDPOINT": settings.s3_endpoint,
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            joined = ", ".join(missing)
            raise ObjectStorageConfigurationError(
                f"Missing required object storage environment variables: {joined}"
            )
        if not settings.s3_prefix.endswith("/"):
            raise ObjectStorageConfigurationError("S3_PREFIX must end with '/'")
        return cls(
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            bucket=settings.s3_bucket,
            prefix=settings.s3_prefix,
            endpoint=settings.s3_endpoint,
            region=settings.s3_region,
            force_path_style=settings.s3_force_path_style,
        )


@dataclass(frozen=True)
class StoredObject:
    relative_key: str
    key: str
    size: int


class ObjectStorageClient:
    def __init__(
        self,
        config: ObjectStorageConfig,
        s3_client: BaseClient | None = None,
    ) -> None:
        self._config = config
        self._client = s3_client or self._build_client(config)

    @staticmethod
    def _build_client(config: ObjectStorageConfig) -> BaseClient:
        addressing_style = "path" if config.force_path_style else "auto"
        return boto3.client(
            "s3",
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            endpoint_url=config.endpoint,
            region_name=config.region,
            config=Config(s3={"addressing_style": addressing_style}),
        )

    def full_key(self, relative_key: str) -> str:
        if not relative_key:
            raise ObjectStorageKeyError("Object key must not be empty")
        if relative_key.startswith("/"):
            raise ObjectStorageKeyError("Object key must be relative")
        if any(part in {"", ".", ".."} for part in relative_key.split("/")):
            raise ObjectStorageKeyError("Object key contains an invalid path segment")
        return f"{self._config.prefix}{relative_key}"

    def upload_bytes(
        self,
        relative_key: str,
        data: bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        full_key = self.full_key(relative_key)
        params: dict[str, Any] = {
            "Bucket": self._config.bucket,
            "Key": full_key,
            "Body": data,
            "ContentLength": len(data),
        }
        if content_type:
            params["ContentType"] = content_type
        if metadata:
            params["Metadata"] = metadata
        try:
            self._client.put_object(**params)
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError("Failed to upload object") from exc
        return StoredObject(relative_key=relative_key, key=full_key, size=len(data))

    def download_bytes(self, relative_key: str) -> bytes:
        full_key = self.full_key(relative_key)
        try:
            response = self._client.get_object(Bucket=self._config.bucket, Key=full_key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError("Failed to download object") from exc

    def delete_object(self, relative_key: str) -> None:
        full_key = self.full_key(relative_key)
        try:
            self._client.delete_object(Bucket=self._config.bucket, Key=full_key)
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError("Failed to delete object") from exc

    def object_exists(self, relative_key: str) -> bool:
        full_key = self.full_key(relative_key)
        try:
            self._client.head_object(Bucket=self._config.bucket, Key=full_key)
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 404:
                return False
            raise ObjectStorageError("Failed to inspect object") from exc
        except BotoCoreError as exc:
            raise ObjectStorageError("Failed to inspect object") from exc
        return True

    def presigned_get_url(self, relative_key: str, *, expires_in: int = 3600) -> str:
        if expires_in < 1 or expires_in > MAX_PRESIGNED_URL_TTL_SECONDS:
            raise ValueError("Presigned URL expiration must be between 1 and 604800")
        full_key = self.full_key(relative_key)
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._config.bucket, "Key": full_key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError("Failed to create signed URL") from exc


@lru_cache
def get_storage_client() -> ObjectStorageClient:
    return ObjectStorageClient(ObjectStorageConfig.from_settings(get_settings()))
