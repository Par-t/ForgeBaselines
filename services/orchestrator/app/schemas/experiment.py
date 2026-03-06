"""Experiment schemas."""

from typing import Dict, List, Any, Optional
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
    dataset_id: str
    status: str
    run_count: int
    created_at: str


class ExperimentListResponse(BaseModel):
    """Response for listing experiments."""
    experiments: List[ExperimentListItem]


class UnifiedExperimentListItem(BaseModel):
    """Single experiment in the unified list (classification or IR)."""
    experiment_id: str
    task_type: str  # "classification" or "ir"
    status: str
    created_at: str
    # classification only
    dataset_id: Optional[str] = None
    # IR only
    corpus_dataset_id: Optional[str] = None
    queries_dataset_id: Optional[str] = None


class UnifiedExperimentListResponse(BaseModel):
    """Response for the unified experiment list."""
    experiments: List[UnifiedExperimentListItem]
