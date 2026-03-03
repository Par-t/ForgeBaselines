"""IR experiment schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.plan import PreprocessingConfig


class IRExperimentRunRequest(BaseModel):
    corpus_dataset_id: str = Field(..., description="Dataset ID of the corpus CSV (doc_id, text)")
    queries_dataset_id: str = Field(..., description="Dataset ID of the queries CSV (query_id, query, doc_id, relevance)")
    text_column: str = Field(default="text", description="Column in corpus containing document text")
    k_values: List[int] = Field(default=[10, 100], description="Cutoff values for Recall and nDCG")
    preprocessing_config: Optional[PreprocessingConfig] = Field(
        default=None,
        description="Text preprocessing options. When omitted, no preprocessing is applied.",
    )


class IRExperimentRunResponse(BaseModel):
    experiment_id: str
    corpus_dataset_id: str
    queries_dataset_id: str
    status: str


class IRMetrics(BaseModel):
    map: float
    ndcg_10: float
    recall_10: float
    recall_100: float
    mrr: float


class IRResultsResponse(BaseModel):
    experiment_id: str
    user_id: str
    status: str
    metrics: IRMetrics
    n_docs: int
    n_queries: int


class IRExperimentListItem(BaseModel):
    experiment_id: str
    corpus_dataset_id: str
    queries_dataset_id: str
    status: str
    created_at: str


class IRExperimentListResponse(BaseModel):
    experiments: List[IRExperimentListItem]
