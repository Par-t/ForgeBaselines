"""Experiment execution and results endpoints."""

import os
import uuid
import numpy as np
import pandas as pd
import httpx
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_user_id
from app.schemas.experiment import RuntimeEstimateRequest, RuntimeEstimateResponse
from app.schemas.plan import ExperimentRunRequest, ExperimentRunResponse
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
    # Load dataset and profile it
    try:
        file_path = storage.get_dataset_path(request.dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    # Profile dataset
    profile = profile_dataset(df)

    # Estimate runtime
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
    # 1. Validate dataset exists
    try:
        file_path = storage.get_dataset_path(request.dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    # 2. Validate target column
    if request.target_column not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Target column '{request.target_column}' not found in dataset. Available columns: {df.columns.tolist()}"
        )

    # 2b. Validate column_config references columns that exist
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

    # 3. Profile dataset and estimate runtime
    profile = profile_dataset(df)
    runtime_estimate = estimate_runtime(profile, request.model_names)

    # 4. Preprocess dataset
    try:
        X_train, X_test, y_train, y_test, preprocessor, label_classes = preprocess_dataset(
            df, request.target_column, request.test_size,
            column_config=request.column_config
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preprocessing failed: {str(e)}")

    # 5. Save preprocessed arrays to temp location
    experiment_id = str(uuid.uuid4())
    temp_dir = Path(f"{settings.data_path}/{user_id}/{request.dataset_id}/preprocessed/{experiment_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    X_train_path = temp_dir / "X_train.npy"
    X_test_path = temp_dir / "X_test.npy"
    y_train_path = temp_dir / "y_train.npy"
    y_test_path = temp_dir / "y_test.npy"

    np.save(X_train_path, X_train)
    np.save(X_test_path, X_test)
    np.save(y_train_path, y_train)
    np.save(y_test_path, y_test)

    # 6. Call classification service
    classification_url = os.getenv("CLASSIFICATION_SERVICE_URL", "http://classification:8001")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{classification_url}/train",
                json={
                    "X_train_path": str(X_train_path),
                    "X_test_path": str(X_test_path),
                    "y_train_path": str(y_train_path),
                    "y_test_path": str(y_test_path),
                    "model_names": request.model_names,
                    "label_classes": label_classes,
                    "user_id": user_id,
                    "experiment_id": experiment_id
                }
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Training service error: {str(e)}")

    # 7. Return experiment info
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
    # Query MLflow for experiment results
    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

    async with httpx.AsyncClient() as client:
        try:
            # MLflow uses our UUID as experiment *name*, assigns its own numeric ID
            # First: look up the numeric ID by name
            exp_response = await client.get(
                f"{mlflow_url}/api/2.0/mlflow/experiments/get-by-name",
                params={"experiment_name": experiment_id}
            )
            exp_response.raise_for_status()
            mlflow_exp_id = exp_response.json()["experiment"]["experiment_id"]

            # Then: search runs using the numeric ID
            response = await client.post(
                f"{mlflow_url}/api/2.0/mlflow/runs/search",
                json={"experiment_ids": [mlflow_exp_id], "max_results": 100}
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Experiment not found in MLflow")
            raise HTTPException(status_code=500, detail=f"MLflow query error: {str(e)}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"MLflow query error: {str(e)}")

    if "runs" not in data or not data["runs"]:
        raise HTTPException(status_code=404, detail="No results found for this experiment")

    # Extract leaderboard and label mapping from runs
    leaderboard = []
    label_classes = None

    for run in data["runs"]:
        metrics_dict = {m["key"]: m["value"] for m in run["data"]["metrics"]}
        params_dict = {p["key"]: p["value"] for p in run["data"]["params"]}

        # Extract label mapping once (same for all runs in this experiment)
        if label_classes is None and "label_classes" in params_dict:
            label_classes = params_dict["label_classes"].split(",")

        leaderboard.append({
            "model_name": run["info"]["run_name"],
            "accuracy": metrics_dict.get("accuracy", 0.0),
            "precision": metrics_dict.get("precision", 0.0),
            "recall": metrics_dict.get("recall", 0.0),
            "f1": metrics_dict.get("f1", 0.0),
            "training_time": metrics_dict.get("training_time", 0.0)
        })

    # Sort by F1 descending
    leaderboard.sort(key=lambda x: x["f1"], reverse=True)

    # Build label mapping: {0: "Iris-setosa", 1: "Iris-versicolor", ...}
    label_mapping = (
        {str(i): cls for i, cls in enumerate(label_classes)}
        if label_classes else {}
    )

    return {
        "experiment_id": experiment_id,
        "user_id": user_id,
        "status": "completed",
        "label_mapping": label_mapping,
        "leaderboard": leaderboard
    }