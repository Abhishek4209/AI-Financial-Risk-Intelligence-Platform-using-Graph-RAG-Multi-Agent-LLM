
"""Grounded answer generation with source-aware financial risk evidence."""

from __future__ import annotations

import re
from typing import Any

from src.llm.guardrails import enforce_insufficient_evidence, usable_summary
from src.llm.llm_factory import get_llm
from src.llm.prompt_templates import render_rag_prompt


def _document_text(document: Any) -> str:
    """Extract text from a retrieved document."""
    return str(getattr(document, "page_content", document))


def _document_source(document: Any) -> str:
    """Return the available source name and page information."""
    metadata = getattr(document, "metadata", {}) or {}

    source = (
        metadata.get("source_file")
        or metadata.get("source")
        or metadata.get("file_path")
        or "Unknown source"
    )

    page = metadata.get("page")

    if page is not None:
        source = "%s, page %s" % (source, page)

    return str(source)


def format_context(
    documents: list[Any],
    *,
    max_chars_per_doc: int = 4000,
) -> str:
    """Format retrieved evidence with source information."""
    if not documents:
        return ""

    if max_chars_per_doc < 1:
        raise ValueError("max_chars_per_doc must be at least 1")

    context_parts = []

    for index, document in enumerate(documents, start=1):
        source = _document_source(document)
        text = _document_text(document).strip()

        if not text:
            continue

        context_parts.append(
            "[Evidence %s | Source: %s]\n%s"
            % (
                index,
                source,
                text[:max_chars_per_doc],
            )
        )

    return "\n\n".join(context_parts)


def _available_sources(documents: list[Any]) -> list[str]:
    """Return unique source references while preserving their order."""
    sources = []

    for document in documents:
        source = _document_source(document)

        if source not in sources:
            sources.append(source)

    return sources


def _is_incomplete_answer(answer: str) -> bool:
    """Detect very short or obviously fragmentary model responses."""
    if not answer:
        return True

    cleaned = answer.strip()

    if len(cleaned) < 40:
        return True

    fragment_starts = (
        "by ",
        "through ",
        "with ",
        "using ",
        "including ",
        "such as ",
        "because ",
        "and ",
        "or ",
        "which ",
        "that ",
    )

    if cleaned.lower().startswith(fragment_starts):
        return True

    return False


def _attach_missing_citations(
    answer: str,
    sources: list[str],
) -> str:
    """Append retrieved source references if the answer has no citation."""
    if not answer or not sources:
        return answer

    citation_pattern = re.compile(
        r"\[(?:Source|Evidence)\s+\d+|"
        r"\b(?:source|sources|reference|references)\s*:",
        re.IGNORECASE,
    )

    if citation_pattern.search(answer):
        return answer

    references = "\n".join(
        "- %s" % source
        for source in sources
    )

    return (
        answer.rstrip()
        + "\n\nRetrieved sources:\n"
        + references
    )


def generate_answer(
    question: str,
    documents: list[Any],
    *,
    provider: str | None = None,
) -> dict[str, Any]:
    """Generate an evidence-grounded answer with traceable source references."""
    if not documents:
        return {
            "answer": (
                "The information was not found in the available retrieved sources."
            ),
            "sources": [],
            "grounded": True,
        }

    sources = _available_sources(documents)

    context = format_context(documents)
    prompt = render_rag_prompt(question, context)

    try:
        generate = get_llm(provider)
        raw_answer = generate(prompt)
        cleaned = usable_summary(raw_answer)

        # Retry once when the model returns a fragment or an overly short answer.
        if not cleaned or _is_incomplete_answer(cleaned):
            retry_prompt = (
                prompt
                + "\n\nIMPORTANT: Your previous response was incomplete. "
                "Write a complete, self-contained answer to the user's question. "
                "Use only the supplied evidence. Explain the relevant risk "
                "management practices in clear sentences. Include the source "
                "and page information when available. Do not return a sentence "
                "fragment or invent controls that are not in the evidence."
            )

            raw_answer = generate(retry_prompt)
            cleaned = usable_summary(raw_answer)

    except Exception as exc:
        return {
            "answer": (
                "The report model is unavailable. "
                "The retrieved evidence is listed below for manual review."
            ),
            "sources": sources,
            "grounded": False,
            "error": "%s: %s" % (type(exc).__name__, exc),
        }

    if not cleaned or _is_incomplete_answer(cleaned):
        return {
            "answer": (
                "The model could not generate a complete answer from the "
                "retrieved evidence. Please review the listed source documents."
            ),
            "sources": sources,
            "grounded": False,
        }

    try:
        answer = enforce_insufficient_evidence(cleaned, documents)
    except Exception:
        answer = cleaned

    answer = _attach_missing_citations(answer, sources)

    return {
        "answer": answer,
        "sources": sources,
        "grounded": True,
    }
