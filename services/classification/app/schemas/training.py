"""Training request and response schemas."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TrainRequest(BaseModel):
    """Request schema for training endpoint."""

    model_config = ConfigDict(protected_namespaces=())

    dataset_path: str = Field(..., description="Path to preprocessed dataset")
    target_column: str = Field(..., description="Name of the target column")
    model_names: List[str] = Field(..., description="List of model names to train")
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="Test split size")
    user_id: str = Field(..., description="User ID for experiment tracking")
    experiment_id: str = Field(..., description="Unique experiment identifier")


class ModelResult(BaseModel):
    """Result for a single model."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    training_time: float


class TrainResponse(BaseModel):
    """Response schema for training endpoint."""

    experiment_id: str
    user_id: str
    results: List[ModelResult]
    status: str = "completed"