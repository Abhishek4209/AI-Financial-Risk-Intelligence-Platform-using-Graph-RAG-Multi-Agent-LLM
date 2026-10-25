"""Rule-based and optional LLM-based query rewriting for retrieval recall."""

from __future__ import annotations

import re
from typing import Any, Callable

STOPWORDS = {"the", "a", "an", "is", "are", "of", "to", "for", "and", "in", "on", "what", "which"}
SYNONYMS = {
        "fraud": ["fraudulent activity", "suspicious transaction"],
        "aml": ["anti-money laundering", "money laundering"],
        "kyc": ["know your customer", "customer due diligence"],
        "default": ["loan default", "credit default"],
        "compliance": ["regulatory compliance", "regulatory requirement"],
}



def expand_query(query: str) -> list[str]:
        """Return the original query plus deterministic synonym expansions; never fabricates facts."""
        expansions = [query]
        lowered = query.lower()
        for term, synonyms in SYNONYMS.items():
                if term in lowered:
                        expansions.extend(re.sub(rf"\b{term}\b", synonym, lowered) for synonym in synonyms)
        return list(dict.fromkeys(expansions))



def extract_keywords(query: str) -> list[str]:
        tokens = re.findall(r"\w+", query.lower())
        return [token for token in tokens if token not in STOPWORDS and len(token) > 2]



def rewrite_query_with_llm(query: str, generate: Callable[[str], str]) -> str:
        """Use an LLM only to rephrase, never to introduce new factual claims."""
        prompt = (
                "Rewrite the following financial-risk analyst question as a single, clearer search query. "
                "Do not add facts, numbers, or assumptions that are not in the original question.\n\n"
                f"Question: {query}\nRewritten query:"
        )
        rewritten = generate(prompt).strip()
        return rewritten or query
