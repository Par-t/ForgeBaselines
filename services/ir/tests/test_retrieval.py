"""Unit tests for BM25 retrieval and IR metrics."""

import pytest
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.metrics import compute_map, compute_ndcg, compute_mrr, compute_recall


CORPUS = [
    "machine learning algorithms classification",
    "deep learning neural networks",
    "information retrieval bm25 ranking",
    "natural language processing text",
    "random forest decision trees",
]
DOC_IDS = ["d1", "d2", "d3", "d4", "d5"]


@pytest.fixture
def retriever():
    return BM25Retriever(CORPUS, DOC_IDS)


def test_bm25_retrieve_returns_k_results(retriever):
    results = retriever.retrieve("machine learning", k=3)
    assert len(results) == 3


def test_bm25_retrieve_most_relevant_first(retriever):
    results = retriever.retrieve("machine learning", k=5)
    assert results[0] == "d1"


def test_bm25_retrieve_clamps_to_corpus_size(retriever):
    results = retriever.retrieve("learning", k=100)
    assert len(results) == len(DOC_IDS)


def test_compute_map_perfect():
    qrels = {"q1": {"d1", "d2"}}
    results = {"q1": ["d1", "d2", "d3"]}
    assert compute_map(qrels, results) == pytest.approx(1.0)


def test_compute_map_no_relevant():
    qrels = {"q1": {"d99"}}
    results = {"q1": ["d1", "d2"]}
    assert compute_map(qrels, results) == pytest.approx(0.0)


def test_compute_map_partial():
    qrels = {"q1": {"d1", "d3"}}
    results = {"q1": ["d1", "d2", "d3"]}
    # P@1=1.0 (d1 relevant), P@3=2/3 (d3 relevant); AP = (1.0 + 2/3) / 2
    expected = (1.0 + 2 / 3) / 2
    assert compute_map(qrels, results) == pytest.approx(expected)


def test_compute_ndcg_perfect():
    qrels = {"q1": {"d1"}}
    results = {"q1": ["d1", "d2"]}
    assert compute_ndcg(qrels, results, k=10) == pytest.approx(1.0)


def test_compute_ndcg_miss():
    qrels = {"q1": {"d1"}}
    results = {"q1": ["d2", "d3"]}
    assert compute_ndcg(qrels, results, k=10) == pytest.approx(0.0)


def test_compute_mrr_first_hit():
    qrels = {"q1": {"d1"}}
    results = {"q1": ["d1", "d2"]}
    assert compute_mrr(qrels, results) == pytest.approx(1.0)


def test_compute_mrr_second_hit():
    qrels = {"q1": {"d2"}}
    results = {"q1": ["d1", "d2", "d3"]}
    assert compute_mrr(qrels, results) == pytest.approx(0.5)


def test_compute_recall_full():
    qrels = {"q1": {"d1", "d2"}}
    results = {"q1": ["d1", "d2", "d3"]}
    assert compute_recall(qrels, results, k=10) == pytest.approx(1.0)


def test_compute_recall_partial():
    qrels = {"q1": {"d1", "d2"}}
    results = {"q1": ["d1", "d3"]}
    assert compute_recall(qrels, results, k=10) == pytest.approx(0.5)


def test_compute_recall_at_k_cutoff():
    qrels = {"q1": {"d1", "d2"}}
    results = {"q1": ["d3", "d1", "d2"]}
    assert compute_recall(qrels, results, k=1) == pytest.approx(0.0)
    assert compute_recall(qrels, results, k=2) == pytest.approx(0.5)
