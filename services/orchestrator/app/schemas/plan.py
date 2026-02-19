"""Experiment plan schemas (V2-ready)."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


class ColumnConfig(BaseModel):
    """Column role configuration for an experiment.

    When omitted from ExperimentRunRequest, all non-target columns are used
    as features (V1 default behaviour). When provided, this config is authoritative.

    V2 usage: agent calls GET /datasets/{id}/suggest-columns to receive a pre-filled
    ColumnConfig (source="auto"), reviews it with the user, sets source="user" on
    confirmation, then passes it verbatim to POST /experiments/run.
    """

    ignore_columns: List[str] = Field(
        default_factory=list,
        description=(
            "Columns to drop before training. Typically auto-populated ID columns "
            "(monotonically increasing integers with unique_count == n_rows)."
        )
    )
    feature_columns: List[str] = Field(
        default_factory=list,
        description=(
            "Explicit feature allowlist. When empty (default), all columns except "
            "target and ignore_columns are used. When non-empty, only these columns "
            "are used as features."
        )
    )
    source: Literal["auto", "user"] = Field(
        default="auto",
        description=(
            "'auto' = produced by suggest-columns heuristics. "
            "'user' = explicitly reviewed and confirmed by user or agent."
        )
    )

    @model_validator(mode="after")
    def validate_no_overlap(self) -> "ColumnConfig":
        overlap = set(self.feature_columns) & set(self.ignore_columns)
        if overlap:
            raise ValueError(
                f"Columns cannot appear in both feature_columns and ignore_columns: {sorted(overlap)}"
            )
        return self


class SuggestColumnsResponse(BaseModel):
    """Response from GET /datasets/{dataset_id}/suggest-columns."""

    dataset_id: str
    column_config: ColumnConfig
    column_notes: dict[str, str] = Field(
        default_factory=dict,
        description="Per-column reason strings explaining why each column was flagged."
    )


class ExperimentRunRequest(BaseModel):
    """Request to run an experiment."""

    dataset_id: str = Field(..., description="ID of uploaded dataset")
    target_column: str = Field(..., description="Name of target column")
    model_names: List[str] = Field(..., description="List of model names to train")
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="Test split ratio")
    column_config: Optional[ColumnConfig] = Field(
        default=None,
        description=(
            "Optional column configuration. When omitted, all non-target columns are "
            "used as features (V1 behaviour). When provided, ignore_columns are dropped "
            "and feature_columns (if non-empty) restrict the feature set."
        )
    )


class ExperimentRunResponse(BaseModel):
    """Response from experiment run."""

    experiment_id: str
    dataset_id: str
    status: str
    estimated_runtime: str
    models: List[str]
    column_config_used: Optional[ColumnConfig] = Field(
        default=None,
        description="The ColumnConfig that was applied during preprocessing. Null if not provided."
    )
