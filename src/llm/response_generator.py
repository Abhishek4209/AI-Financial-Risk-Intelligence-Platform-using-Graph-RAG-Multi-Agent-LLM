
"""Grounded answer generation: LLM text is advisory, never the source of facts or citations."""

from __future__ import annotations

from typing import Any

from src.llm.guardrails import enforce_insufficient_evidence, usable_summary
from src.llm.llm_factory import get_llm
from src.llm.prompt_templates import render_rag_prompt


def _document_text(document: Any) -> str:
    return str(getattr(document, "page_content", document))


def _document_source(document: Any) -> str:
    metadata = getattr(document, "metadata", {})
    source = metadata.get("source_file") or metadata.get("source") or "Unknown source"

    if metadata.get("page") is not None:
        source = "%s, page %s" % (source, metadata["page"])

    return source


def format_context(
    documents: list[Any],
    *,
    max_chars_per_doc: int = 1200,
) -> str:
    if not documents:
        return ""

    return "\n\n".join(
        "[%s]\n%s"
        % (_document_source(document), _document_text(document)[:max_chars_per_doc])
        for document in documents
    )


def generate_answer(
    question: str,
    documents: list[Any],
    *,
    provider: str | None = None,
) -> dict[str, Any]:
    """Answer strictly from retrieved documents; state explicitly when evidence is insufficient."""
    if not documents:
        return {
            "answer": "The information was not found in the available retrieved sources.",
            "sources": [],
            "grounded": True,
        }

    context = format_context(documents)
    prompt = render_rag_prompt(question, context)
    generate = get_llm(provider)

    try:
        raw_answer = generate(prompt)
    except Exception as exc:
        return {
            "answer": (
                "The report model is unavailable; retrieved evidence is listed "
                "below for manual review."
            ),
            "sources": [_document_source(document) for document in documents],
            "grounded": False,
            "error": "%s: %s" % (type(exc).__name__, exc),
        }

    cleaned = usable_summary(raw_answer)
    answer = (
        enforce_insufficient_evidence(cleaned or "", documents)
        if cleaned
        else "The report model did not return a usable answer; review the retrieved evidence below."
    )

    return {
        "answer": answer,
        "sources": [_document_source(document) for document in documents],
        "grounded": cleaned is not None,
    }
