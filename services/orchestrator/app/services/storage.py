"""Storage service for dataset files."""

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile

from app.config import settings


class StorageService:
    """Handle dataset storage — local (default) or S3 (when STORAGE_BACKEND=s3)."""

    def __init__(self):
        self.base_path = Path(settings.data_path)
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

    def save_dataset_metadata(
        self, user_id: str, dataset_id: str, filename: str, rows: int, cols: int
    ) -> None:
        """Persist original filename, dimensions, and upload timestamp alongside CSV."""
        meta_path = self.base_path / user_id / dataset_id / "metadata.json"
        meta = {
            "filename": filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "rows": rows,
            "cols": cols,
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f)

    def get_dataset_metadata(self, user_id: str, dataset_id: str) -> dict:
        """Read dataset metadata. Falls back to filesystem inference on missing file."""
        meta_path = self.base_path / user_id / dataset_id / "metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                return json.load(f)
        # Legacy datasets without metadata.json
        csv_path = self.base_path / user_id / dataset_id / "dataset.csv"
        mtime = csv_path.stat().st_mtime if csv_path.exists() else 0
        return {
            "filename": f"{dataset_id}.csv",
            "uploaded_at": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            "rows": 0,
            "cols": 0,
        }

    def delete_dataset(self, user_id: str, dataset_id: str) -> None:
        """Delete entire dataset directory (CSV + preprocessed data) and S3 object."""
        local_dir = self.base_path / user_id / dataset_id
        if local_dir.exists():
            shutil.rmtree(local_dir)

        if settings.storage_backend == "s3":
            self._s3_client.delete_object(
                Bucket=settings.s3_bucket,
                Key=self._s3_key(user_id, dataset_id),
            )

    def delete_experiment(self, user_id: str, dataset_id: str, experiment_id: str) -> None:
        """Delete preprocessed experiment directory only (leaves dataset intact)."""
        exp_dir = (
            self.base_path / user_id / dataset_id / "preprocessed" / experiment_id
        )
        if exp_dir.exists():
            shutil.rmtree(exp_dir)

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
