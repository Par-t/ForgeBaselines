"""Dataset management endpoints."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List
import httpx
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.dependencies import get_user_id
from app.schemas.dataset import (
    DatasetUploadResponse,
    DatasetProfileResponse,
    DatasetListItem,
    DatasetListResponse,
    DeleteResponse,
)
from app.schemas.plan import SuggestColumnsResponse
from app.services.storage import storage
from app.services.profiler import profile_dataset, suggest_column_config
from app.config import settings

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """Upload a CSV dataset."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    dataset_id, file_path = storage.save_dataset(file, user_id)

    try:
        df = pd.read_csv(file_path)
        rows, cols = df.shape
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {str(e)}")

    # Persist metadata so the list endpoint doesn't re-read every CSV
    storage.save_dataset_metadata(user_id, dataset_id, file.filename, rows, cols)

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
    try:
        file_path = storage.get_dataset_path(dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    profile = profile_dataset(df)

    return DatasetProfileResponse(
        dataset_id=dataset_id,
        user_id=user_id,
        profile=profile
    )


@router.get("/{dataset_id}/suggest-columns", response_model=SuggestColumnsResponse)
async def suggest_columns(
    dataset_id: str,
    target_column: str,
    user_id: str = Depends(get_user_id)
):
    """Auto-suggest column roles based on profiling heuristics."""
    try:
        file_path = storage.get_dataset_path(dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    if target_column not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Target column '{target_column}' not found. "
                   f"Available columns: {df.columns.tolist()}"
        )

    profile = profile_dataset(df)
    column_config, column_notes = suggest_column_config(profile, target_column)

    return SuggestColumnsResponse(
        dataset_id=dataset_id,
        column_config=column_config,
        column_notes=column_notes
    )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(user_id: str = Depends(get_user_id)):
    """List all datasets for the current user."""
    user_dir = Path(settings.data_path) / user_id
    datasets = []

    if not user_dir.exists():
        return DatasetListResponse(datasets=[])

    for dataset_dir in user_dir.iterdir():
        if not dataset_dir.is_dir():
            continue
        csv_path = dataset_dir / "dataset.csv"
        if not csv_path.exists():
            continue

        dataset_id = dataset_dir.name
        meta = storage.get_dataset_metadata(user_id, dataset_id)

        # Count experiments (subdirectories in preprocessed/)
        preprocessed_dir = dataset_dir / "preprocessed"
        experiment_count = (
            sum(1 for d in preprocessed_dir.iterdir() if d.is_dir())
            if preprocessed_dir.exists()
            else 0
        )

        # If metadata lacks row/col counts (legacy), read CSV once
        rows = meta.get("rows") or 0
        cols = meta.get("cols") or 0
        if rows == 0 and cols == 0:
            try:
                df = pd.read_csv(csv_path)
                rows, cols = df.shape
            except Exception:
                pass

        datasets.append(
            DatasetListItem(
                dataset_id=dataset_id,
                filename=meta.get("filename", f"{dataset_id}.csv"),
                rows=rows,
                cols=cols,
                created_at=meta.get("uploaded_at", ""),
                experiment_count=experiment_count,
            )
        )

    # Most recently uploaded first
    datasets.sort(key=lambda d: d.created_at, reverse=True)
    return DatasetListResponse(datasets=datasets)


@router.delete("/{dataset_id}", response_model=DeleteResponse)
async def delete_dataset(dataset_id: str, user_id: str = Depends(get_user_id)):
    """Delete a dataset and all its experiments (filesystem + MLflow)."""
    # Verify ownership
    csv_path = Path(settings.data_path) / user_id / dataset_id / "dataset.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete MLflow experiments for every run under this dataset
    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    preprocessed_dir = Path(settings.data_path) / user_id / dataset_id / "preprocessed"
    if preprocessed_dir.exists():
        async with httpx.AsyncClient() as client:
            for exp_dir in preprocessed_dir.iterdir():
                if not exp_dir.is_dir():
                    continue
                await _delete_mlflow_experiment(client, mlflow_url, exp_dir.name)

    # Delete filesystem data (CSV + all preprocessed dirs)
    storage.delete_dataset(user_id, dataset_id)

    return DeleteResponse(message=f"Dataset {dataset_id} deleted")


async def _delete_mlflow_experiment(client: httpx.AsyncClient, mlflow_url: str, experiment_id: str) -> None:
    """Look up MLflow experiment by UUID name and mark it deleted. Swallows 404s."""
    try:
        resp = await client.get(
            f"{mlflow_url}/api/2.0/mlflow/experiments/get-by-name",
            params={"experiment_name": experiment_id},
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()
        mlflow_exp_id = resp.json()["experiment"]["experiment_id"]
        await client.post(
            f"{mlflow_url}/api/2.0/mlflow/experiments/delete",
            json={"experiment_id": mlflow_exp_id},
        )
    except Exception:
        # Non-fatal: MLflow cleanup best-effort
        pass
