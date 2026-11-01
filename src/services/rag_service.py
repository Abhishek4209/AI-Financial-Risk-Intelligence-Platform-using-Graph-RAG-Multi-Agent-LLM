"""Hybrid retrieve-then-generate RAG service used by compliance and document Q&A."""

from __future__ import annotations

from typing import Any

from src.llm.response_generator import generate_answer
from src.retriever.query_rewriter import expand_query
from src.retriever.reranker import rerank
from src.retriever.self_rag import self_rag_filter
from src.vectordb import search as vector_search


def _format_evidence(documents: list[Any]) -> list[dict[str, Any]]:
    """Keep only source metadata that exists on the retrieved documents."""
    evidence = []

    for document in documents:
        if isinstance(document, dict):
            text = str(document.get("page_content", document.get("text", "")))
            metadata = document.get("metadata", {}) or {}
        else:
            text = str(getattr(document, "page_content", document))
            metadata = getattr(document, "metadata", {}) or {}

        page = metadata.get("page_label")
        if page is None:
            page = metadata.get("page")

        evidence.append(
            {
                "document": (
                    metadata.get("source_file")
                    or metadata.get("source")
                    or metadata.get("file_path")
                ),
                "section": metadata.get("section"),
                "page": page,
                "text": text,
            }
        )

    return evidence


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
            "question": question,
            "answer": "Insufficient evidence.",
            "evidence": [],
            "grounding_status": "Insufficient evidence",
            "limitations": ["No directly relevant evidence was retrieved."],
            "sources": [],
            "grounded": False,
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

    grounded = bool(result.get("grounded", False))
    if not grounded:
        result["answer"] = "Insufficient evidence."

    result["question"] = question
    result["evidence"] = _format_evidence(top_documents)
    result["grounding_status"] = (
        "Grounded" if grounded else "Insufficient evidence"
    )
    result["limitations"] = (
        []
        if grounded
        else ["Retrieved passages did not directly support a grounded answer."]
    )
    result["evidence_sufficient"] = grounded
    result["retrieved_count"] = retrieved_count
    result["filtered_count"] = relevant_count
    result["reranked_count"] = len(top_documents)

    return result