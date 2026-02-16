"""Experiment execution and results endpoints."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_user_id
from app.schemas.experiment import RuntimeEstimateRequest, RuntimeEstimateResponse
from app.services.storage import storage
from app.services.profiler import profile_dataset
from app.services.runtime_estimator import estimate_runtime

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


@router.post("/run")
async def run_experiment(user_id: str = Depends(get_user_id)):
    """
    Run a baseline experiment.

    V1.0.9 will implement the full end-to-end orchestration.
    For now, returns mock data.
    """
    return {
        "experiment_id": "mock-exp-456",
        "status": "queued",
        "user_id": user_id,
        "estimated_runtime": "1-5 min"
    }


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str, user_id: str = Depends(get_user_id)):
    """
    Get experiment results and leaderboard.

    V1.0.9 will implement the full logic with MLflow integration.
    For now, returns mock leaderboard.
    """
    return {
        "experiment_id": experiment_id,
        "user_id": user_id,
        "status": "completed",
        "leaderboard": [
            {
                "model_name": "random_forest",
                "accuracy": 0.96,
                "f1": 0.95,
                "precision": 0.96,
                "recall": 0.95
            },
            {
                "model_name": "gradient_boosting",
                "accuracy": 0.94,
                "f1": 0.93,
                "precision": 0.94,
                "recall": 0.93
            },
            {
                "model_name": "logistic_regression",
                "accuracy": 0.91,
                "f1": 0.90,
                "precision": 0.92,
                "recall": 0.89
            }
        ]
    }