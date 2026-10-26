"""BM25 lexical retrieval over local document chunks, per architecture.md’s retrieval layer."""
from __future__ import annotations
from typing import Any
def build_bm25_index(documents: list[Any]) -> Any:
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        raise RuntimeError("Install rank-bm25 to use BM25 retrieval") from exc
    if not documents:
        raise ValueError("documents must not be empty")
    tokenized = [str(getattr(document, "page_content", document)).lower().split() for document in do
cuments]
    return BM25Okapi(tokenized)
def bm25_search(query: str, documents: list[Any], *, top_k: int = 5) -> list[Any]:
    """Return the top-k documents by BM25 score for a tokenized query."""
    if not documents:
        return []
    index = build_bm25_index(documents)
    scores = index.get_scores(query.lower().split())
    ranked = sorted(range(len(documents)), key=lambda position: scores[position], reverse=True)
    return [documents[position] for position in ranked[:top_k]]
