"""Cross-encoder reranking to refine first-stage retrieval results."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any



@lru_cache(maxsize=1)
def _get_cross_encoder(model_name: str) -> Any:
        try:
                from sentence_transformers import CrossEncoder
        except ImportError as exc:
                raise RuntimeError("Install sentence-transformers to use reranking") from exc
        return CrossEncoder(model_name)



def rerank(query: str, documents: list[Any], *, top_k: int = 5, model_name: str | None = None) -> list[Any]:
        """Rerank documents by cross-encoder relevance; falls back to input order if unavailable."""
        if not documents:
                return []
        name = model_name or os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        try:
                encoder = _get_cross_encoder(name)
        except RuntimeError:
                return documents[:top_k]
        pairs = [(query, str(getattr(document, "page_content", document))) for document in documents]
        scores = encoder.predict(pairs)
        ranked = sorted(zip(documents, scores), key=lambda item: item[1], reverse=True)
        return [document for document, _ in ranked[:top_k]]
