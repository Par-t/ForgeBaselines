"""IR experiment schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.plan import PreprocessingConfig


class IRExperimentRunRequest(BaseModel):
    corpus_dataset_id: str = Field(..., description="Dataset ID of the corpus CSV")
    queries_dataset_id: str = Field(..., description="Dataset ID of the queries CSV")
    # Corpus column mapping
    corpus_doc_id_col: str = Field(default="doc_id", description="Column in corpus for document ID")
    text_column: str = Field(default="text", description="Column in corpus containing document text")
    # Queries column mapping
    queries_query_id_col: Optional[str] = Field(default=None, description="Column in queries for query ID; if omitted, query text is used as ID")
    queries_query_col: str = Field(default="query", description="Column in queries for query text")
    queries_doc_id_col: str = Field(default="doc_id", description="Column in queries for relevant document ID")
    queries_relevance_col: Optional[str] = Field(default=None, description="Column in queries for relevance score; not required by BM25 evaluation")
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
