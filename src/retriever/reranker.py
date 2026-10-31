"""Cross-encoder reranking to refine first-stage retrieval results."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from src.retriever.query_rewriter import extract_keywords


DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def _get_cross_encoder(model_name: str) -> Any:
    """Load and cache the configured cross-encoder."""
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "Install sentence-transformers to use reranking."
        ) from exc

    return CrossEncoder(model_name)


def _document_text(document: Any) -> str:
    """Extract document text safely."""
    return str(getattr(document, "page_content", document))


def _fallback_rerank(
    query: str,
    documents: list[Any],
    top_k: int,
) -> list[Any]:
    """Rank documents using deterministic keyword overlap."""
    query_keywords = set(extract_keywords(query))

    if not query_keywords:
        return documents[:top_k]

    scored_documents = []

    for document in documents:
        text = _document_text(document).lower()

        overlap = sum(
            1
            for keyword in query_keywords
            if keyword in text
        )

        scored_documents.append((document, overlap))

    ranked = sorted(
        scored_documents,
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        document
        for document, _ in ranked[:top_k]
    ]


def rerank(
    query: str,
    documents: list[Any],
    *,
    top_k: int = 5,
    model_name: str | None = None,
) -> list[Any]:
    """Rerank retrieved documents using a cross-encoder.

    Falls back to deterministic keyword ranking if the model
    cannot be loaded or produces invalid scores.
    """
    if not documents or top_k <= 0:
        return []

    if not isinstance(query, str) or not query.strip():
        return documents[:top_k]

    name = (
        model_name
        or os.getenv("RERANKER_MODEL", DEFAULT_RERANKER_MODEL)
    )

    pairs = [
        (query.strip(), _document_text(document))
        for document in documents
    ]

    try:
        encoder = _get_cross_encoder(name)
        scores = encoder.predict(pairs)

        if len(scores) != len(documents):
            raise ValueError(
                "Cross-encoder returned an unexpected number of scores."
            )

        ranked = sorted(
            zip(documents, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )

        return [
            document
            for document, _ in ranked[:top_k]
        ]

    except Exception:
        return _fallback_rerank(
            query.strip(),
            documents,
            top_k,
        )