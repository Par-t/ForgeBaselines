"""IR evaluation metrics: MAP, nDCG@k, MRR, Recall@k."""

import math
from typing import Dict, List, Set


def compute_map(qrels: Dict[str, Set[str]], results: Dict[str, List[str]]) -> float:
    """Mean Average Precision."""
    aps = []
    for qid, relevant in qrels.items():
        ranked = results.get(qid, [])
        if not relevant:
            continue
        hits = 0
        precision_sum = 0.0
        for rank, doc_id in enumerate(ranked, start=1):
            if doc_id in relevant:
                hits += 1
                precision_sum += hits / rank
        aps.append(precision_sum / len(relevant))
    return float(sum(aps) / len(aps)) if aps else 0.0


def compute_ndcg(qrels: Dict[str, Set[str]], results: Dict[str, List[str]], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k."""
    ndcgs = []
    for qid, relevant in qrels.items():
        ranked = results.get(qid, [])[:k]
        dcg = sum(
            1.0 / math.log2(rank + 1)
            for rank, doc_id in enumerate(ranked, start=1)
            if doc_id in relevant
        )
        ideal_hits = min(len(relevant), k)
        idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)
    return float(sum(ndcgs) / len(ndcgs)) if ndcgs else 0.0


def compute_mrr(qrels: Dict[str, Set[str]], results: Dict[str, List[str]]) -> float:
    """Mean Reciprocal Rank."""
    rrs = []
    for qid, relevant in qrels.items():
        ranked = results.get(qid, [])
        rr = 0.0
        for rank, doc_id in enumerate(ranked, start=1):
            if doc_id in relevant:
                rr = 1.0 / rank
                break
        rrs.append(rr)
    return float(sum(rrs) / len(rrs)) if rrs else 0.0


def compute_recall(qrels: Dict[str, Set[str]], results: Dict[str, List[str]], k: int) -> float:
    """Mean Recall@k."""
    recalls = []
    for qid, relevant in qrels.items():
        if not relevant:
            continue
        retrieved = set(results.get(qid, [])[:k])
        recalls.append(len(relevant & retrieved) / len(relevant))
    return float(sum(recalls) / len(recalls)) if recalls else 0.0
