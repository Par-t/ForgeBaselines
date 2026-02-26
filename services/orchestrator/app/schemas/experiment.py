"""Experiment schemas."""

from typing import Dict, List, Any
from pydantic import BaseModel


class RuntimeEstimateRequest(BaseModel):
    """Request for runtime estimation."""
    dataset_id: str
    model_names: List[str]


class RuntimeEstimateResponse(BaseModel):
    """Response for runtime estimation."""
    dataset_id: str
    overall_estimate: str
    per_model: Dict[str, Any]
    complexity_factors: Dict[str, Any]


class ExperimentListItem(BaseModel):
    """Single experiment in list."""
    experiment_id: str
    status: str
    run_count: int


class ExperimentListResponse(BaseModel):
    """Response for listing experiments."""
    experiments: List[ExperimentListItem]
