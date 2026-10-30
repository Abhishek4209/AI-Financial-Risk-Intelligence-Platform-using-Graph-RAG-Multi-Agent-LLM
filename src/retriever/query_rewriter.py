"""Rule-based and optional LLM-based query rewriting for retrieval recall."""

from __future__ import annotations

import re
from typing import Callable


STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "for", "and",
    "in", "on", "what", "which", "how", "does", "do", "with",
    "their", "its", "this", "that", "by", "from", "about",
    "explain", "describe", "identify", "provide",
}

SYNONYMS = {
    "fraud": [
        "fraudulent activity",
        "fraud prevention",
        "fraud detection",
        "transaction monitoring",
    ],
    "aml": [
        "anti-money laundering",
        "money laundering prevention",
        "suspicious activity monitoring",
    ],
    "kyc": [
        "know your customer",
        "customer due diligence",
        "identity verification",
    ],
    "default": [
        "loan default",
        "credit default",
        "delinquency",
    ],
    "compliance": [
        "regulatory compliance",
        "regulatory requirements",
        "compliance controls",
    ],
    "credit": [
        "credit risk",
        "credit exposure",
        "credit loss",
        "credit underwriting",
    ],
    "liquidity": [
        "liquidity risk",
        "funding liquidity",
        "cash flow management",
    ],
    "operational": [
        "operational risk",
        "business continuity",
        "process controls",
    ],
    "regulatory": [
        "regulatory risk",
        "regulatory requirements",
        "supervisory requirements",
    ],
    "cyber": [
        "cybersecurity risk",
        "information security",
        "data security",
    ],
    "capital": [
        "capital adequacy",
        "capital requirements",
        "capital management",
    ],
    "interest": [
        "interest rate risk",
        "market risk",
        "interest rate exposure",
    ],
    "consumer": [
        "consumer lending",
        "card member risk",
        "consumer credit",
    ],
    "commercial": [
        "commercial lending",
        "business credit risk",
        "commercial credit exposure",
    ],
    "mitigation": [
        "risk mitigation",
        "risk controls",
        "risk management practices",
    ],
}


def expand_query(query: str) -> list[str]:
    """Generate focused query variations without changing the original query."""
    if not isinstance(query, str) or not query.strip():
        return []

    original = query.strip()
    lowered = original.lower()

    expansions = [original]

    for term, synonyms in SYNONYMS.items():
        pattern = rf"\b{re.escape(term)}\b"

        if re.search(pattern, lowered):
            for synonym in synonyms:
                expanded = re.sub(
                    pattern,
                    synonym,
                    original,
                    flags=re.IGNORECASE,
                )
                expansions.append(expanded)

    # Add a focused risk-management query variation.
    if any(
        term in lowered
        for term in (
            "risk",
            "fraud",
            "credit",
            "liquidity",
            "operational",
            "regulatory",
            "cyber",
        )
    ):
        expansions.append(
            f"{original} risk management policies controls and mitigation"
        )

    # Preserve order and remove duplicate queries.
    return list(dict.fromkeys(expansions))


def extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from a query."""
    if not isinstance(query, str) or not query.strip():
        return []

    tokens = re.findall(r"\w+", query.lower())

    return [
        token
        for token in tokens
        if token not in STOPWORDS and len(token) > 2
    ]


def rewrite_query_with_llm(
    query: str,
    generate: Callable[[str], str],
) -> str:
    """Rewrite a query using a supplied language-model generation function."""
    if not isinstance(query, str) or not query.strip():
        return query

    prompt = (
        "Rewrite the following financial risk and regulatory compliance "
        "question as a precise document-search query. Preserve the original "
        "meaning. Include relevant risk-management terminology. Return only "
        "the rewritten query.\n\n"
        f"Question: {query}"
    )

    try:
        rewritten = generate(prompt).strip()
    except Exception:
        return query

    return rewritten or query