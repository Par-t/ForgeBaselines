"""IR service request/response schemas."""

from typing import List
from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    corpus_path: str
    queries_path: str
    text_column: str = "text"
    k_values: List[int] = [10, 100]
    experiment_id: str
    user_id: str


class IRMetrics(BaseModel):
    map: float
    ndcg_10: float
    recall_10: float
    recall_100: float
    mrr: float


class RetrieveResponse(BaseModel):
    experiment_id: str
    user_id: str
    metrics: IRMetrics
    n_docs: int
    n_queries: int
    status: str = "completed"
