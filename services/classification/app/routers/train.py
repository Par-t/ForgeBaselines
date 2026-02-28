"""Training endpoint."""

import numpy as np
from fastapi import APIRouter, HTTPException
from app.schemas.training import TrainRequest, TrainResponse, ModelResult
from app.training.runner import run_training

router = APIRouter(prefix="/train", tags=["training"])


@router.post("", response_model=TrainResponse)
async def train_models(request: TrainRequest):
    """Train classification models on preprocessed data."""
    try:
        # Load preprocessed arrays
        X_train = np.load(request.X_train_path)
        X_test = np.load(request.X_test_path)
        y_train = np.load(request.y_train_path)
        y_test = np.load(request.y_test_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Preprocessed data not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error loading data: {str(e)}")

    # Run training
    results = run_training(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        model_names=request.model_names,
        experiment_id=request.experiment_id,
        label_classes=request.label_classes,
        use_class_weight=request.use_class_weight,
    )

    # Convert to response format
    model_results = [
        ModelResult(
            model_name=r["model_name"],
            accuracy=r["accuracy"],
            precision=r["precision"],
            recall=r["recall"],
            f1=r["f1"],
            training_time=r["training_time"]
        )
        for r in results
    ]

    return TrainResponse(
        experiment_id=request.experiment_id,
        user_id=request.user_id,
        results=model_results,
        status="completed"
    )