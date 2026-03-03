"""BM25 retriever using rank-bm25."""

from typing import List
import numpy as np
from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self, corpus_docs: List[str], doc_ids: List[str]):
        tokenized = [doc.split() for doc in corpus_docs]
        self.bm25 = BM25Okapi(tokenized)
        self.doc_ids = doc_ids

    def retrieve(self, query: str, k: int) -> List[str]:
        tokens = query.split()
        scores = self.bm25.get_scores(tokens)
        top_k_indices = np.argsort(scores)[::-1][:k]
        return [self.doc_ids[i] for i in top_k_indices]
