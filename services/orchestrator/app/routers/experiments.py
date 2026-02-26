"""Experiment execution and results endpoints."""

import csv
import io
import os
import uuid
import numpy as np
import pandas as pd
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import get_user_id
from app.schemas.experiment import RuntimeEstimateRequest, RuntimeEstimateResponse, ExperimentListItem, ExperimentListResponse
from app.schemas.plan import ExperimentRunRequest, ExperimentRunResponse
from app.schemas.dataset import DeleteResponse
from app.config import settings
from app.services.storage import storage
from app.services.profiler import profile_dataset
from app.services.runtime_estimator import estimate_runtime
from app.preprocessing.pipeline import preprocess_dataset

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/estimate", response_model=RuntimeEstimateResponse)
async def estimate_experiment_runtime(
    request: RuntimeEstimateRequest,
    user_id: str = Depends(get_user_id)
):
    """Estimate runtime for an experiment based on dataset profile."""
    try:
        file_path = storage.get_dataset_path(request.dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    profile = profile_dataset(df)
    estimate = estimate_runtime(profile, request.model_names)

    return RuntimeEstimateResponse(
        dataset_id=request.dataset_id,
        overall_estimate=estimate["overall_estimate"],
        per_model=estimate["per_model"],
        complexity_factors=estimate["complexity_factors"]
    )


@router.post("/run", response_model=ExperimentRunResponse)
async def run_experiment(
    request: ExperimentRunRequest,
    user_id: str = Depends(get_user_id)
):
    """Run a baseline experiment end-to-end."""
    try:
        file_path = storage.get_dataset_path(request.dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    if request.target_column not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Target column '{request.target_column}' not found in dataset. Available columns: {df.columns.tolist()}"
        )

    if request.column_config is not None:
        all_cols = set(df.columns)
        bad_ignore = set(request.column_config.ignore_columns) - all_cols - {request.target_column}
        bad_features = set(request.column_config.feature_columns) - all_cols - {request.target_column}
        if bad_ignore or bad_features:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "column_config references columns not found in dataset",
                    "unknown_ignore_columns": sorted(bad_ignore),
                    "unknown_feature_columns": sorted(bad_features),
                    "available_columns": df.columns.tolist()
                }
            )

    profile = profile_dataset(df)
    runtime_estimate = estimate_runtime(profile, request.model_names)

    try:
        X_train, X_test, y_train, y_test, preprocessor, label_classes = preprocess_dataset(
            df, request.target_column, request.test_size,
            column_config=request.column_config
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preprocessing failed: {str(e)}")

    experiment_id = str(uuid.uuid4())
    temp_dir = Path(f"{settings.data_path}/{user_id}/{request.dataset_id}/preprocessed/{experiment_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    np.save(temp_dir / "X_train.npy", X_train)
    np.save(temp_dir / "X_test.npy", X_test)
    np.save(temp_dir / "y_train.npy", y_train)
    np.save(temp_dir / "y_test.npy", y_test)

    classification_url = os.getenv("CLASSIFICATION_SERVICE_URL", "http://classification:8001")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{classification_url}/train",
                json={
                    "X_train_path": str(temp_dir / "X_train.npy"),
                    "X_test_path": str(temp_dir / "X_test.npy"),
                    "y_train_path": str(temp_dir / "y_train.npy"),
                    "y_test_path": str(temp_dir / "y_test.npy"),
                    "model_names": request.model_names,
                    "label_classes": label_classes,
                    "user_id": user_id,
                    "experiment_id": experiment_id
                }
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Training service error: {str(e)}")

    return ExperimentRunResponse(
        experiment_id=experiment_id,
        dataset_id=request.dataset_id,
        status="completed",
        estimated_runtime=runtime_estimate["overall_estimate"],
        models=request.model_names,
        column_config_used=request.column_config
    )


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str, user_id: str = Depends(get_user_id)):
    """Get experiment results from MLflow."""
    dataset_id = _find_dataset_id_for_experiment(experiment_id, user_id)
    if dataset_id is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    leaderboard, label_mapping = await _fetch_mlflow_results(mlflow_url, experiment_id)

    return {
        "experiment_id": experiment_id,
        "user_id": user_id,
        "status": "completed",
        "label_mapping": label_mapping,
        "leaderboard": leaderboard,
    }


@router.get("/{experiment_id}/results/download")
async def download_experiment_results(experiment_id: str, user_id: str = Depends(get_user_id)):
    """Download experiment leaderboard as a CSV file."""
    dataset_id = _find_dataset_id_for_experiment(experiment_id, user_id)
    if dataset_id is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    leaderboard, _ = await _fetch_mlflow_results(mlflow_url, experiment_id)

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["model_name", "accuracy", "precision", "recall", "f1", "training_time"],
    )
    writer.writeheader()
    for row in leaderboard:
        writer.writerow(row)

    buf.seek(0)
    filename = f"results_{experiment_id[:8]}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{experiment_id}", response_model=DeleteResponse)
async def delete_experiment(experiment_id: str, user_id: str = Depends(get_user_id)):
    """Delete an experiment (preprocessed data + MLflow runs). Leaves dataset intact."""
    dataset_id = _find_dataset_id_for_experiment(experiment_id, user_id)
    if dataset_id is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    async with httpx.AsyncClient() as client:
        from app.routers.datasets import _delete_mlflow_experiment
        await _delete_mlflow_experiment(client, mlflow_url, experiment_id)

    storage.delete_experiment(user_id, dataset_id, experiment_id)

    return DeleteResponse(message=f"Experiment {experiment_id} deleted")


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(user_id: str = Depends(get_user_id)):
    """List all experiments for the current user."""
    user_dir = Path(settings.data_path) / user_id
    experiments = []

    if not user_dir.exists():
        return ExperimentListResponse(experiments=[])

    for dataset_dir in user_dir.iterdir():
        if not dataset_dir.is_dir():
            continue
        preprocessed_dir = dataset_dir / "preprocessed"
        if not preprocessed_dir.exists():
            continue

        dataset_id = dataset_dir.name
        for exp_dir in preprocessed_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            mtime = exp_dir.stat().st_mtime
            created_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

            experiments.append(
                ExperimentListItem(
                    experiment_id=exp_dir.name,
                    dataset_id=dataset_id,
                    status="completed",
                    run_count=1,
                    created_at=created_at,
                )
            )

    experiments.sort(key=lambda e: e.created_at, reverse=True)
    return ExperimentListResponse(experiments=experiments)


# ------------------------------------------------------------------ helpers

def _find_dataset_id_for_experiment(experiment_id: str, user_id: str):
    """Return the dataset_id that owns this experiment, or None if not found."""
    user_data_dir = Path(settings.data_path) / user_id
    if not user_data_dir.exists():
        return None
    for dataset_dir in user_data_dir.iterdir():
        exp_path = dataset_dir / "preprocessed" / experiment_id
        if exp_path.exists():
            return dataset_dir.name
    return None


async def _fetch_mlflow_results(mlflow_url: str, experiment_id: str):
    """Query MLflow for leaderboard rows. Returns (leaderboard, label_mapping)."""
    async with httpx.AsyncClient() as client:
        try:
            exp_resp = await client.get(
                f"{mlflow_url}/api/2.0/mlflow/experiments/get-by-name",
                params={"experiment_name": experiment_id},
            )
            exp_resp.raise_for_status()
            mlflow_exp_id = exp_resp.json()["experiment"]["experiment_id"]

            runs_resp = await client.post(
                f"{mlflow_url}/api/2.0/mlflow/runs/search",
                json={"experiment_ids": [mlflow_exp_id], "max_results": 100},
            )
            runs_resp.raise_for_status()
            data = runs_resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Experiment not found in MLflow")
            raise HTTPException(status_code=500, detail=f"MLflow query error: {str(e)}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"MLflow query error: {str(e)}")

    if "runs" not in data or not data["runs"]:
        raise HTTPException(status_code=404, detail="No results found for this experiment")

    leaderboard = []
    label_classes = None

    for run in data["runs"]:
        metrics_dict = {m["key"]: m["value"] for m in run["data"]["metrics"]}
        params_dict = {p["key"]: p["value"] for p in run["data"]["params"]}

        if label_classes is None and "label_classes" in params_dict:
            label_classes = params_dict["label_classes"].split(",")

        leaderboard.append({
            "model_name": run["info"]["run_name"],
            "accuracy": metrics_dict.get("accuracy", 0.0),
            "precision": metrics_dict.get("precision", 0.0),
            "recall": metrics_dict.get("recall", 0.0),
            "f1": metrics_dict.get("f1", 0.0),
            "training_time": metrics_dict.get("training_time", 0.0),
        })

    leaderboard.sort(key=lambda x: x["f1"], reverse=True)
    label_mapping = (
        {str(i): cls for i, cls in enumerate(label_classes)}
        if label_classes else {}
    )
    return leaderboard, label_mapping
