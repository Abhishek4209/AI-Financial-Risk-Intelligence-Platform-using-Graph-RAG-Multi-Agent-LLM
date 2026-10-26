"""Self-RAG style relevance and support checks before accepting retrieved evidence."""
from __future__ import annotations
from typing import Any
from src.retriever.query_rewriter import extract_keywords
def is_relevant(query: str, document: Any, *, min_overlap: int = 1) -> bool:
    """Keyword-overlap relevance gate; a lightweight, deterministic stand-in for a trained critic."""
    query_keywords = set(extract_keywords(query))
    if not query_keywords:
        return True
    text = str(getattr(document, "page_content", document)).lower()
    overlap = sum(1 for keyword in query_keywords if keyword in text)
    return overlap >= min_overlap
def filter_relevant_documents(query: str, documents: list[Any], *, min_overlap: int = 1) -> list[Any]:
    filtered = [document for document in documents if is_relevant(query, document, min_overlap=min_overlap
)]
    return filtered
def is_answer_supported(answer: str, documents: list[Any], *, min_overlap: int = 2) -> bool:
    """Check that generated answer text shares vocabulary with the retrieved evidence."""
    if not documents:
        return False
    answer_keywords = set(extract_keywords(answer))
    if not answer_keywords:
        return False
    combined_text = " ".join(str(getattr(document, "page_content", document)).lower() for document in
 documents)
    overlap = sum(1 for keyword in answer_keywords if keyword in combined_text)
    return overlap >= min_overlap
def self_rag_filter(query: str, documents: list[Any], *, min_overlap: int = 1) -> dict[str, Any]:
    """Return relevant documents and an explicit insufficient-evidence flag."""
    relevant = filter_relevant_documents(query, documents, min_overlap=min_overlap)
    return {
        "documents": relevant,
        "evidence_sufficient": len(relevant) > 0,
    }
