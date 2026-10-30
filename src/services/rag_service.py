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
    """Retrieve, filter, rerank and generate an evidence-grounded answer."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")

    question = question.strip()

    candidates: list[Any] = []
    seen_text: set[str] = set()

    # Limit query expansion to avoid excessive repeated vector searches.
    expanded_queries = expand_query(question)[:4]

    for expanded_query in expanded_queries:
        documents = vector_search(
            expanded_query,
            top_k=top_k,
            backend=backend,
        )

        for document in documents:
            document_text = str(
                getattr(document, "page_content", document)
            ).strip()

            if document_text and document_text not in seen_text:
                seen_text.add(document_text)
                candidates.append(document)

    retrieved_count = len(candidates)

    filtered = self_rag_filter(
        question,
        candidates,
    )

    relevant_documents = filtered["documents"]
    relevant_count = len(relevant_documents)

    if not filtered["evidence_sufficient"]:
        return {
            "answer": (
                "The information was not found in the available retrieved sources."
            ),
            "sources": [],
            "grounded": True,
            "evidence_sufficient": False,
            "retrieved_count": retrieved_count,
            "filtered_count": 0,
            "reranked_count": 0,
        }

    top_documents = rerank(
        question,
        relevant_documents,
        top_k=top_k,
    )

    result = generate_answer(
        question,
        top_documents,
        provider=provider,
    )

    result["evidence_sufficient"] = True
    result["retrieved_count"] = retrieved_count
    result["filtered_count"] = relevant_count
    result["reranked_count"] = len(top_documents)

    return result