"""Training request and response schemas."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TrainRequest(BaseModel):
    """Request schema for training endpoint."""

    model_config = ConfigDict(protected_namespaces=())

    X_train_path: str = Field(..., description="Path to preprocessed X_train (npy file)")
    X_test_path: str = Field(..., description="Path to preprocessed X_test (npy file)")
    y_train_path: str = Field(..., description="Path to preprocessed y_train (npy file)")
    y_test_path: str = Field(..., description="Path to preprocessed y_test (npy file)")
    model_names: List[str] = Field(..., description="List of model names to train")
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