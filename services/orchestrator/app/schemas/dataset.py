"""Dataset schemas."""

from pydantic import BaseModel


class DatasetUploadResponse(BaseModel):
    """Response for dataset upload."""
    dataset_id: str
    filename: str
    rows: int
    cols: int
    user_id: str