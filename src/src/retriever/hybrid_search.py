"""Combine BM25 and vector similarity with configurable weighted score fusion."""
from __future__ import annotations
import os
from typing import Any
from src.retriever.bm25 import build_bm25_index
from src.vectordb import search as vector_search
def _normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    low, high = min(scores), max(scores)
    if high == low:
        return [1.0 for _ in scores]
    return [(score - low) / (high - low) for score in scores]
def hybrid_search(query: str, documents: list[Any], *, top_k: int = 5, vector_weight: float | None = None)
 -> list[Any]:
    """Fuse BM25 lexical scores with vector similarity rank over a known document set."""
    if not documents:
        return []
    weight = vector_weight if vector_weight is not None else float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.5"
))
    if not 0.0 <= weight <= 1.0:
        raise ValueError("vector_weight must be between 0 and 1")
    bm25_index = build_bm25_index(documents)
    bm25_scores = _normalize(list(bm25_index.get_scores(query.lower().split())))
    vector_hits = vector_search(query, top_k=len(documents))
    vector_rank = {id(hit): 1.0 - (position / max(len(vector_hits), 1)) for position, hit in enumera
te(vector_hits)}
    vector_scores = _normalize([vector_rank.get(id(document), 0.0) for document in documents])
    fused = [weight * vector_score + (1 - weight) * bm25_score for bm25_score, vector_score in zip(bm25_s
cores, vector_scores)]
    ranked = sorted(range(len(documents)), key=lambda index: fused[index], reverse=True)
    return [documents[index] for index in ranked[:top_k]]
