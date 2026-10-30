
"""Hybrid retrieve-then-generate RAG service used by compliance and document Q&A."""

from __future__ import annotations

from typing import Any

from src.llm.response_generator import generate_answer
from src.retriever.query_rewriter import expand_query
from src.retriever.reranker import rerank
from src.retriever.self_rag import self_rag_filter
from src.vectordb import search as vector_search


def answer_question(
    question: str,
    *,
    top_k: int = 5,
    backend: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """Retrieve, filter for relevance, rerank, and generate a citation-grounded answer."""
    candidates: list[Any] = []
    seen_text: set[str] = set()

    for expanded in expand_query(question):
        for document in vector_search(
            expanded,
            top_k=top_k,
            backend=backend,
        ):
            if document.page_content not in seen_text:
                seen_text.add(document.page_content)
                candidates.append(document)

    filtered = self_rag_filter(question, candidates)

    if not filtered["evidence_sufficient"]:
        return {
            "answer": "The information was not found in the available retrieved sources.",
            "sources": [],
            "grounded": True,
            "evidence_sufficient": False,
        }

    top_documents = rerank(
        question,
        filtered["documents"],
        top_k=top_k,
    )

    result = generate_answer(
        question,
        top_documents,
        provider=provider,
    )
    result["evidence_sufficient"] = True

    return result
