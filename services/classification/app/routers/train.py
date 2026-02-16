"""Training endpoint."""

from fastapi import APIRouter
from app.schemas.training import TrainRequest, TrainResponse, ModelResult

router = APIRouter(prefix="/train", tags=["training"])


@router.post("", response_model=TrainResponse)
async def train_models(request: TrainRequest):
    """
    Train classification models.

    V1.0.7 will implement the full training logic with model registry.
    V1.0.8 will add MLflow logging.
    For now, returns mock results.
    """
    # Mock results for each requested model
    mock_results = []

    for model_name in request.model_names:
        # Different mock accuracies for different models
        base_accuracy = {
            "random_forest": 0.96,
            "gradient_boosting": 0.94,
            "logistic_regression": 0.91
        }.get(model_name, 0.90)

        mock_results.append(
            ModelResult(
                model_name=model_name,
                accuracy=base_accuracy,
                precision=base_accuracy - 0.01,
                recall=base_accuracy - 0.01,
                f1=base_accuracy - 0.01,
                training_time=1.5
            )
        )

    return TrainResponse(
        experiment_id=request.experiment_id,
        user_id=request.user_id,
        results=mock_results,
        status="completed"
    )