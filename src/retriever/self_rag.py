"""Self-RAG style relevance and support checks before accepting retrieved evidence."""

from __future__ import annotations

import re
from typing import Any

from src.retriever.query_rewriter import extract_keywords


RISK_CONCEPTS = {
    "credit": {
        "credit",
        "lending",
        "borrower",
        "underwriting",
        "delinquency",
        "default",
    },
    "fraud": {
        "fraud",
        "fraudulent",
        "scam",
        "suspicious",
        "transaction",
    },
    "liquidity": {
        "liquidity",
        "funding",
        "cashflow",
        "cash",
    },
    "operational": {
        "operational",
        "operations",
        "business continuity",
        "process",
    },
    "regulatory": {
        "regulatory",
        "regulation",
        "compliance",
        "supervisory",
    },
    "cyber": {
        "cyber",
        "cybersecurity",
        "security",
        "data breach",
    },
    "capital": {
        "capital",
        "adequacy",
        "capitalization",
    },
    "market": {
        "market",
        "interest",
        "rates",
        "investment",
    },
}

RISK_ACTION_TERMS = {
    "management",
    "mitigation",
    "control",
    "controls",
    "strategy",
    "strategies",
    "monitoring",
    "policy",
    "policies",
    "governance",
    "assessment",
    "exposure",
    "loss",
    "prevention",
    "protection",
}


def _document_text(document: Any) -> str:
    """Extract normalized text from a retrieved document."""
    content = getattr(document, "page_content", document)
    return str(content).lower()


def _matches_terms(terms: set[str], text: str) -> set[str]:
    """Find whole-word or phrase matches in document text."""
    return {
        term
        for term in terms
        if re.search(
            rf"(?<!\w){re.escape(term)}(?!\w)",
            text,
        )
    }


def _query_risk_categories(query: str) -> set[str]:
    """Identify risk categories explicitly mentioned in the query."""
    query_text = query.lower()
    categories = set()

    for category, terms in RISK_CONCEPTS.items():
        if _matches_terms(terms, query_text):
            categories.add(category)

    return categories


def is_relevant(
    query: str,
    document: Any,
    *,
    min_overlap: int = 1,
) -> bool:
    """Check whether a document contains query-specific financial risk evidence."""
    if not query or not query.strip():
        return False

    text = _document_text(document)
    query_keywords = set(extract_keywords(query))

    if not query_keywords:
        return False

    query_categories = _query_risk_categories(query)

    if query_categories:
        matched_categories = set()

        for category in query_categories:
            if _matches_terms(RISK_CONCEPTS[category], text):
                matched_categories.add(category)

        matched_actions = _matches_terms(RISK_ACTION_TERMS, text)

        # Require a matching risk category and a risk-management concept.
        if not matched_categories or not matched_actions:
            return False

        return True

    matched_keywords = _matches_terms(query_keywords, text)

    return len(matched_keywords) >= max(1, min_overlap)


def filter_relevant_documents(
    query: str,
    documents: list[Any],
    *,
    min_overlap: int = 1,
) -> list[Any]:
    """Return documents that pass the relevance check."""
    return [
        document
        for document in documents
        if is_relevant(
            query,
            document,
            min_overlap=min_overlap,
        )
    ]


def is_answer_supported(
    answer: str,
    documents: list[Any],
    *,
    min_overlap: int = 2,
) -> bool:
    """Check whether the generated answer shares meaningful terms with evidence."""
    if not answer or not answer.strip() or not documents:
        return False

    answer_keywords = set(extract_keywords(answer))

    if not answer_keywords:
        return False

    combined_text = " ".join(
        _document_text(document)
        for document in documents
    )

    matched_keywords = _matches_terms(answer_keywords, combined_text)

    return len(matched_keywords) >= max(1, min_overlap)


def self_rag_filter(
    query: str,
    documents: list[Any],
    *,
    min_overlap: int = 1,
) -> dict[str, Any]:
    """Return relevant documents and an explicit insufficient-evidence flag."""
    relevant = filter_relevant_documents(
        query,
        documents,
        min_overlap=min_overlap,
    )

    return {
        "documents": relevant,
        "evidence_sufficient": len(relevant) > 0,
    }