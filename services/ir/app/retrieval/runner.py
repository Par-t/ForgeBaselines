"""Orchestrate BM25 retrieval, metric computation, and MLflow logging."""

import os
from typing import List

import mlflow
import pandas as pd

from app.retrieval.bm25 import BM25Retriever
from app.retrieval.metrics import compute_map, compute_ndcg, compute_mrr, compute_recall
from app.schemas.retrieval import IRMetrics


def run_retrieval(
    corpus_path: str,
    queries_path: str,
    text_column: str,
    k_values: List[int],
    experiment_id: str,
    user_id: str,
) -> tuple[IRMetrics, int, int]:
    """Run BM25 retrieval and compute metrics.

    Returns (IRMetrics, n_docs, n_queries).
    """
    corpus_df = pd.read_csv(corpus_path)
    queries_df = pd.read_csv(queries_path)

    doc_ids = corpus_df["doc_id"].astype(str).tolist()
    corpus_texts = corpus_df[text_column].fillna("").astype(str).tolist()

    retriever = BM25Retriever(corpus_texts, doc_ids)

    # Build qrels: {query_id: set of relevant doc_ids}
    qrels = {}
    for _, row in queries_df.iterrows():
        qid = str(row["query_id"])
        qrels.setdefault(qid, set()).add(str(row["doc_id"]))

    # Retrieve for each unique query
    query_texts = queries_df.groupby("query_id")["query"].first().to_dict()
    max_k = max(k_values)
    results = {
        str(qid): retriever.retrieve(str(query), max_k)
        for qid, query in query_texts.items()
    }

    k10 = 10 if 10 in k_values else min(k_values)
    k100 = 100 if 100 in k_values else max(k_values)

    metrics = IRMetrics(
        map=compute_map(qrels, results),
        ndcg_10=compute_ndcg(qrels, results, k10),
        recall_10=compute_recall(qrels, results, k10),
        recall_100=compute_recall(qrels, results, k100),
        mrr=compute_mrr(qrels, results),
    )

    _log_to_mlflow(metrics, experiment_id, user_id, len(doc_ids), len(qrels), text_column, k_values)

    return metrics, len(doc_ids), len(qrels)


def _log_to_mlflow(
    metrics: IRMetrics,
    experiment_id: str,
    user_id: str,
    n_docs: int,
    n_queries: int,
    text_column: str,
    k_values: List[int],
) -> None:
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(f"ir_{experiment_id}")

    with mlflow.start_run(run_name="bm25"):
        mlflow.log_params({
            "model": "BM25Okapi",
            "text_column": text_column,
            "k_values": str(k_values),
            "n_docs": n_docs,
            "n_queries": n_queries,
            "user_id": user_id,
        })
        mlflow.log_metrics({
            "map": metrics.map,
            "ndcg_10": metrics.ndcg_10,
            "recall_10": metrics.recall_10,
            "recall_100": metrics.recall_100,
            "mrr": metrics.mrr,
        })
