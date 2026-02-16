"""Dataset management endpoints."""

from fastapi import APIRouter, Depends
from app.dependencies import get_user_id

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload")
async def upload_dataset(user_id: str = Depends(get_user_id)):
    """
    Upload a dataset.

    V1.0.3 will implement the full logic.
    For now, returns mock data.
    """
    return {
        "dataset_id": "mock-dataset-123",
        "filename": "example.csv",
        "rows": 150,
        "cols": 5,
        "user_id": user_id
    }


@router.get("/{dataset_id}/profile")
async def get_dataset_profile(dataset_id: str, user_id: str = Depends(get_user_id)):
    """
    Get dataset profile/statistics.

    V1.0.4 will implement the full logic.
    For now, returns mock data.
    """
    return {
        "dataset_id": dataset_id,
        "user_id": user_id,
        "summary_stats": {
            "n_rows": 150,
            "n_cols": 5,
            "numeric_cols": 4,
            "categorical_cols": 1,
            "missing_values": 0
        }
    }