"""Retrieval quality metrics: precision@k, recall@k, MRR, and NDCG."""

from __future__ import annotations

import math
from collections.abc import Sequence



def _validate_k(k: int) -> None:
        if k < 1:
                raise ValueError("k must be at least 1")



def precision_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int) -> float:
        _validate_k(k)
        if not retrieved_ids:
                return 0.0
        top_k = retrieved_ids[:k]
        relevant_set = set(relevant_ids)
        return sum(1 for item in top_k if item in relevant_set) / len(top_k)



def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int) -> float:
        _validate_k(k)
        if not relevant_ids:
                return 0.0
        top_k = set(retrieved_ids[:k])
        return sum(1 for item in relevant_ids if item in top_k) / len(relevant_ids)



def mean_reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: Sequence[str]) -> float:
        relevant_set = set(relevant_ids)
        for rank, item in enumerate(retrieved_ids, start=1):
                if item in relevant_set:
                        return 1.0 / rank
        return 0.0



def ndcg_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int) -> float:
        _validate_k(k)
        relevant_set = set(relevant_ids)
        top_k = retrieved_ids[:k]
        dcg = sum(1.0 / math.log2(rank + 1) for rank, item in enumerate(top_k, start=1) if item in relevant_set)
        ideal_hits = min(len(relevant_set), k)
        ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
        return dcg / ideal_dcg if ideal_dcg > 0 else 0.0



def evaluate_retrieval(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], *, k: int = 5) -> dict[str, float]:
        return {
                "precision_at_k": precision_at_k(retrieved_ids, relevant_ids, k),
                "recall_at_k": recall_at_k(retrieved_ids, relevant_ids, k),
                "mrr": mean_reciprocal_rank(retrieved_ids, relevant_ids),
                "ndcg_at_k": ndcg_at_k(retrieved_ids, relevant_ids, k),
        }
