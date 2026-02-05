"""Storage service with S3 and local support.

Configure via environment variables:
- STORAGE_TYPE: "s3" or "local" (default: "local")
- AWS_ACCESS_KEY_ID: AWS access key (required for S3)
- AWS_SECRET_ACCESS_KEY: AWS secret key (required for S3)
- AWS_REGION: AWS region (default: "us-east-1")
- S3_BUCKET_NAME: S3 bucket name (required for S3)
- UPLOAD_DIR: Local upload directory (default: "uploads/documents")
"""

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

# Conditional import for S3 support
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    def upload(self, content: bytes, key: str, content_type: Optional[str] = None) -> str:
        """Upload file and return storage key."""
        pass

    @abstractmethod
    def download(self, key: str) -> bytes:
        """Download file by key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete file by key."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Get URL for file (presigned for S3, file path for local)."""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage."""

    def __init__(self, base_dir: str = "uploads/documents"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _get_full_path(self, key: str) -> str:
        """Get full path for key."""
        return os.path.join(self.base_dir, key)

    def upload(self, content: bytes, key: str, content_type: Optional[str] = None) -> str:
        """Upload file to local filesystem."""
        full_path = self._get_full_path(key)
        dir_path = os.path.dirname(full_path)
        os.makedirs(dir_path, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(content)

        return key

    def download(self, key: str) -> bytes:
        """Download file from local filesystem."""
        full_path = self._get_full_path(key)
        with open(full_path, "rb") as f:
            return f.read()

    def delete(self, key: str) -> bool:
        """Delete file from local filesystem."""
        full_path = self._get_full_path(key)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if file exists in local filesystem."""
        full_path = self._get_full_path(key)
        return os.path.exists(full_path)

    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Return local file path."""
        full_path = self._get_full_path(key)
        if os.path.exists(full_path):
            return full_path
        return None

    def get_full_path(self, key: str) -> str:
        """Get full local path for a key (for FileResponse)."""
        return self._get_full_path(key)


class S3Storage(StorageBackend):
    """AWS S3 storage."""

    def __init__(
        self,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
    ):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )

    def upload(self, content: bytes, key: str, content_type: Optional[str] = None) -> str:
        """Upload file to S3."""
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
            **extra_args,
        )
        return key

    def download(self, key: str) -> bytes:
        """Download file from S3."""
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Get presigned URL for S3 object."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError:
            return None


class StorageService:
    """Storage service that abstracts S3 and local storage.

    Usage:
        storage = StorageService()
        key = storage.upload(content, "path/to/file.pdf", "application/pdf")
        content = storage.download(key)
    """

    def __init__(self):
        self._backend: Optional[StorageBackend] = None
        self._storage_type: str = "local"
        self._initialize()

    def _initialize(self):
        """Initialize storage backend based on environment."""
        storage_type = os.getenv("STORAGE_TYPE", "local").lower()
        self._storage_type = storage_type

        if storage_type == "s3":
            # Check if boto3 is available
            if not HAS_BOTO3:
                raise ImportError(
                    "S3 storage requires boto3. Install with: pip install boto3"
                )

            # S3 requires all configs
            bucket_name = os.getenv("S3_BUCKET_NAME")
            access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            region = os.getenv("AWS_REGION", "us-east-1")

            if not all([bucket_name, access_key_id, secret_access_key]):
                raise ValueError(
                    "S3 storage requires S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, "
                    "and AWS_SECRET_ACCESS_KEY environment variables"
                )

            self._backend = S3Storage(
                bucket_name=bucket_name,
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                region=region,
            )
        else:
            # Default to local storage
            upload_dir = os.getenv("UPLOAD_DIR", "uploads/documents")
            self._backend = LocalStorage(base_dir=upload_dir)

    @property
    def storage_type(self) -> str:
        """Return current storage type."""
        return self._storage_type

    @property
    def is_s3(self) -> bool:
        """Check if using S3 storage."""
        return self._storage_type == "s3"

    @property
    def is_local(self) -> bool:
        """Check if using local storage."""
        return self._storage_type == "local"

    def upload(self, content: bytes, key: str, content_type: Optional[str] = None) -> str:
        """Upload file to storage."""
        return self._backend.upload(content, key, content_type)

    def download(self, key: str) -> bytes:
        """Download file from storage."""
        return self._backend.download(key)

    def delete(self, key: str) -> bool:
        """Delete file from storage."""
        return self._backend.delete(key)

    def exists(self, key: str) -> bool:
        """Check if file exists."""
        return self._backend.exists(key)

    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Get URL for file."""
        return self._backend.get_url(key, expires_in)

    def get_local_path(self, key: str) -> Optional[str]:
        """Get local file path (only for local storage)."""
        if self.is_local and isinstance(self._backend, LocalStorage):
            return self._backend.get_full_path(key)
        return None


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage() -> StorageService:
    """Get storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
