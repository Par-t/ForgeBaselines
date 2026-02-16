"""Dataset management endpoints."""

import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.dependencies import get_user_id
from app.schemas.dataset import DatasetUploadResponse, DatasetProfileResponse
from app.services.storage import storage
from app.services.profiler import profile_dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """Upload a CSV dataset."""
    # Validate file extension
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large (max 50MB)")

    # Save file
    dataset_id, file_path = storage.save_dataset(file, user_id)

    # Get row/column counts
    try:
        df = pd.read_csv(file_path)
        rows, cols = df.shape
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {str(e)}")

    return DatasetUploadResponse(
        dataset_id=dataset_id,
        filename=file.filename,
        rows=rows,
        cols=cols,
        user_id=user_id
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
async def get_dataset_profile(dataset_id: str, user_id: str = Depends(get_user_id)):
    """Get dataset profile with real statistics."""
    # Load dataset
    try:
        file_path = storage.get_dataset_path(dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    # Profile it
    profile = profile_dataset(df)

    return DatasetProfileResponse(
        dataset_id=dataset_id,
        user_id=user_id,
        profile=profile
    )