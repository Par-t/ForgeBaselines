"""Storage service for dataset files."""

import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile


class StorageService:
    """Handle dataset storage (local for V1, S3 in V1.1.1)."""

    def __init__(self):
        self.base_path = Path("/app/data")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_dataset(self, file: UploadFile, user_id: str) -> Tuple[str, str]:
        """Save uploaded file. Returns (dataset_id, file_path)."""
        dataset_id = str(uuid.uuid4())
        user_dir = self.base_path / user_id / dataset_id
        user_dir.mkdir(parents=True, exist_ok=True)

        file_path = user_dir / "dataset.csv"
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        return dataset_id, str(file_path)

    def get_dataset_path(self, dataset_id: str, user_id: str) -> str:
        """Get path to dataset. Raises FileNotFoundError if missing."""
        file_path = self.base_path / user_id / dataset_id / "dataset.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset {dataset_id} not found")
        return str(file_path)


# Singleton
storage = StorageService()
