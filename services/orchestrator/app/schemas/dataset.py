"""Dataset schemas."""

from typing import Dict, List, Any
from pydantic import BaseModel


class DatasetUploadResponse(BaseModel):
    """Response for dataset upload."""
    dataset_id: str
    filename: str
    rows: int
    cols: int
    user_id: str


class DatasetProfileResponse(BaseModel):
    """Response for dataset profile."""
    dataset_id: str
    user_id: str
    profile: Dict[str, Any]


class DatasetListItem(BaseModel):
    """Single dataset in list."""
    dataset_id: str
    filename: str
    rows: int
    cols: int
    created_at: str
    experiment_count: int


class DatasetListResponse(BaseModel):
    """Response for listing datasets."""
    datasets: List[DatasetListItem]


class DeleteResponse(BaseModel):
    """Generic delete confirmation."""
    message: str
