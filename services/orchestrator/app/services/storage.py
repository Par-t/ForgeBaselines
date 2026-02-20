"""Storage service for dataset files."""

import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile

from app.config import settings


class StorageService:
    """Handle dataset storage — local (default) or S3 (when STORAGE_BACKEND=s3)."""

    def __init__(self):
        self.base_path = Path("/app/data")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._s3 = None  # lazy-initialised boto3 client

    @property
    def _s3_client(self):
        if self._s3 is None:
            import boto3
            self._s3 = boto3.client("s3", region_name=settings.aws_default_region)
        return self._s3

    def save_dataset(self, file: UploadFile, user_id: str) -> Tuple[str, str]:
        """Save uploaded file locally, then mirror to S3 if enabled.

        Always writes locally first — pandas needs a local path to read CSVs.
        Returns (dataset_id, local_file_path).
        """
        dataset_id = str(uuid.uuid4())
        local_path = self._local_path(user_id, dataset_id)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        content = file.file.read()
        with open(local_path, "wb") as f:
            f.write(content)

        if settings.storage_backend == "s3":
            self._s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=self._s3_key(user_id, dataset_id),
                Body=content,
            )

        return dataset_id, str(local_path)

    def get_dataset_path(self, dataset_id: str, user_id: str) -> str:
        """Return local path to dataset, downloading from S3 on cache miss.

        Local cache takes priority. If the file is missing (e.g. after an EC2
        restart) and S3 is enabled, download it first.
        """
        local_path = self._local_path(user_id, dataset_id)
        if local_path.exists():
            return str(local_path)

        if settings.storage_backend == "s3":
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._s3_client.download_file(
                settings.s3_bucket,
                self._s3_key(user_id, dataset_id),
                str(local_path),
            )
            return str(local_path)

        raise FileNotFoundError(f"Dataset {dataset_id} not found")

    # ------------------------------------------------------------------ helpers

    def _local_path(self, user_id: str, dataset_id: str) -> Path:
        return self.base_path / user_id / dataset_id / "dataset.csv"

    def _s3_key(self, user_id: str, dataset_id: str) -> str:
        return f"datasets/{user_id}/{dataset_id}/dataset.csv"


# Singleton
storage = StorageService()
