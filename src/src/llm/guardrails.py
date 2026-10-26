
"""Output guardrails: reject hallucination-shaped or unsupported LLM output."""
from __future__ import annotations

from typing import Any

INVALID_MARKERS = (
    '"feature":',
    '"shap_value":',
    '"direction":',
    "{",
    "}",
    "as an ai",
    "i cannot verify",
)

MIN_LENGTH = 15
MAX_LENGTH = 1200


def usable_summary(text: str) -> str | None:
    """Reject malformed, too-short, too-long, or disclaimer-only generated text."""
    cleaned = text.strip()
    lowered = cleaned.lower()

    if len(cleaned) < MIN_LENGTH or len(cleaned) > MAX_LENGTH:
        return None

    if any(marker in lowered for marker in INVALID_MARKERS):
        return None

    return cleaned


def citations_are_grounded(answer: str, retrieved_sources: list[str]) -> bool:
    """Check that any source name mentioned in the answer was actually retrieved."""
    if not retrieved_sources:
        return "source" not in answer.lower() and "page" not in answer.lower()

    lowered_answer = answer.lower()
    mentioned = [
        source for source in retrieved_sources
        if source.lower() in lowered_answer
    ]

    return bool(mentioned) or not any(
        keyword in lowered_answer
        for keyword in ("source:", "according to ", "per ")
    )


def enforce_insufficient_evidence(answer: str, documents: list[Any]) -> str:
    """Replace an ungrounded answer with an explicit insufficient-evidence message."""
    if documents:
        return answer

    return "The information was not found in the available retrieved sources."


def redact_internal_errors(message: str) -> str:
    """Strip stack traces or file paths before surfacing an error to API clients."""
    first_line = (
        message.strip().splitlines()[0]
        if message.strip()
        else "An internal error occurred."
    )
    return first_line[:300]
