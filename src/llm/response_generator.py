
"""Grounded answer generation with source-aware financial risk evidence."""

from __future__ import annotations

import re
from typing import Any

from src.llm.guardrails import enforce_insufficient_evidence, usable_summary
from src.llm.llm_factory import get_llm
from src.llm.prompt_templates import render_rag_prompt


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "has", "have", "in", "into", "is", "it", "its",
    "of", "on", "or", "that", "the", "their", "this", "to",
    "was", "were", "which", "with", "through", "using",
    "what", "how", "does", "do", "did", "can", "could",
    "should", "would", "explain", "describe", "discuss",
    "manage", "manages", "management", "american", "express",
}


CLASSIFICATION_TERMS = {
    "categorize", "categories", "category", "classify",
    "classification", "classified", "divide", "divided",
    "types", "type",
}


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
    max_chars_per_doc: int = 1800,
) -> str:
    """Format a compact evidence context with source information."""
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
            % (index, source, text[:max_chars_per_doc])
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


def _keywords(text: str) -> set[str]:
    """Extract meaningful words for evidence matching."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text.lower())

    return {
        word[:-1] if word.endswith("s") else word
        for word in words
        if word not in STOPWORDS
    }


def _is_classification_question(question: str) -> bool:
    """Identify questions asking for categories or classifications."""
    question_words = set(
        re.findall(r"\b[a-zA-Z]+\b", question.lower())
    )

    return bool(question_words.intersection(CLASSIFICATION_TERMS))


def _is_incomplete_answer(answer: str) -> bool:
    """Detect empty or obviously fragmentary model responses."""
    if not answer or not answer.strip():
        return True

    cleaned = answer.strip().lower()

    fragment_starts = (
        "by ", "through ", "with ", "using ", "including ",
        "such as ", "because ", "and ", "or ", "which ", "that ",
    )

    if cleaned.startswith(fragment_starts):
        return True

    unfinished_endings = (
        " and", " or", " with", " through", " by",
        " including", " such as", " because",
    )

    return cleaned.endswith(unfinished_endings)


def _answer_supported_by_evidence(
    answer: str,
    documents: list[Any],
) -> bool:
    """Check lexical overlap; this does not prove semantic entailment."""
    answer_terms = _keywords(answer)

    if len(answer_terms) < 2:
        return False

    evidence_text = " ".join(
        _document_text(document)
        for document in documents
    )

    evidence_terms = _keywords(evidence_text)

    if not evidence_terms:
        return False

    overlap = answer_terms.intersection(evidence_terms)
    overlap_ratio = len(overlap) / len(answer_terms)

    return len(overlap) >= 2 and overlap_ratio >= 0.50


def _extract_evidence_fallback(
    question: str,
    documents: list[Any],
) -> str | None:
    """Extract a complete relevant sentence directly from retrieved evidence."""
    question_terms = _keywords(question)

    if not question_terms:
        return None

    candidates = []

    for document_index, document in enumerate(documents):
        document_text = _document_text(document).strip()

        if not document_text:
            continue

        # Normalize line breaks so PDF-wrapped sentences remain together.
        normalized_text = re.sub(
            r"(?<![.!?])\s*\n\s*(?![A-Z])",
            " ",
            document_text,
        )
        normalized_text = re.sub(r"\s+", " ", normalized_text)

        sentences = re.split(
            r"(?<=[.!?])\s+",
            normalized_text,
        )

        for sentence_index, sentence in enumerate(sentences):
            cleaned = sentence.strip()

            if len(cleaned) < 25:
                continue

            sentence_terms = _keywords(cleaned)
            overlap = question_terms.intersection(sentence_terms)

            if len(overlap) < 2:
                continue

            lowered = cleaned.lower()

            priority_phrases = (
                "divided into",
                "broad categories",
                "classified into",
                "consist of",
                "categorized into",
            )

            priority = int(
                any(phrase in lowered for phrase in priority_phrases)
            )

            score = (
                priority,
                len(overlap) / len(question_terms),
                len(overlap),
            )

            candidates.append(
                (score, document_index, sentence_index, cleaned)
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            -item[1],
            -item[2],
        ),
        reverse=True,
    )

    return candidates[0][3]


def _attach_missing_citations(
    answer: str,
    sources: list[str],
) -> str:
    """Append retrieved source references if the answer has no citation."""
    if not answer or not sources:
        return answer

    citation_pattern = re.compile(
        r"\[(?:Source|Evidence)\s+\d+\]|"
        r"\b(?:source|sources|reference|references)\s*:",
        re.IGNORECASE,
    )

    if citation_pattern.search(answer):
        return answer

    references = "\n".join("- %s" % source for source in sources)

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
    """Generate an answer with model generation and evidence extraction fallback."""

    if not documents:
        return {
            "answer": (
                "The information was not found in the available retrieved sources."
            ),
            "sources": [],
            "grounded": False,
        }

    sources = _available_sources(documents)
    selected_documents = documents[:3]

    context = format_context(
        selected_documents,
        max_chars_per_doc=1800,
    )

    if not context.strip():
        return {
            "answer": (
                "The retrieved documents do not contain usable text. "
                "Please review the source documents manually."
            ),
            "sources": sources,
            "grounded": False,
        }

    generation_error = None
    cleaned = None

    try:
        generate = get_llm(provider)
        prompt = render_rag_prompt(question, context)

        raw_answer = generate(prompt)
        cleaned = usable_summary(raw_answer or "")

        if (
            not cleaned
            or _is_incomplete_answer(cleaned)
            or not _answer_supported_by_evidence(
                cleaned,
                selected_documents,
            )
        ):
            retry_prompt = (
                "Answer the question using only the evidence below.\n\n"
                "Question: %s\n\n"
                "Evidence:\n%s\n\n"
                "Write one or two complete sentences. "
                "Include all relevant categories or items stated "
                "in the evidence. Do not invent facts. "
                "If the answer is unavailable, say: "
                "'The information was not found in the available sources.'\n\n"
                "Answer:"
            ) % (question, context)

            raw_answer = generate(retry_prompt)
            cleaned = usable_summary(raw_answer or "")

    except Exception as exc:
        cleaned = None
        generation_error = "%s: %s" % (type(exc).__name__, exc)

    # Classification questions should prefer complete source evidence.
    if _is_classification_question(question):
        fallback_answer = _extract_evidence_fallback(
            question,
            selected_documents,
        )

        if fallback_answer:
            return {
                "answer": _attach_missing_citations(
                    fallback_answer,
                    sources,
                ),
                "sources": sources,
                "grounded": True,
                "answer_method": "evidence_extraction",
            }

    # Use source extraction when the model output fails basic checks.
    if (
        not cleaned
        or _is_incomplete_answer(cleaned)
        or not _answer_supported_by_evidence(
            cleaned,
            selected_documents,
        )
    ):
        fallback_answer = _extract_evidence_fallback(
            question,
            selected_documents,
        )

        if fallback_answer:
            return {
                "answer": _attach_missing_citations(
                    fallback_answer,
                    sources,
                ),
                "sources": sources,
                "grounded": True,
                "answer_method": "evidence_extraction",
            }

        result = {
            "answer": (
                "The model could not produce an answer that passed the "
                "basic evidence checks, and no sufficiently relevant "
                "complete sentence could be extracted from the sources. "
                "Please review the retrieved documents manually."
            ),
            "sources": sources,
            "grounded": False,
        }

        if generation_error:
            result["error"] = generation_error

        return result

    try:
        answer = enforce_insufficient_evidence(
            cleaned,
            selected_documents,
        )
    except Exception:
        answer = cleaned

    answer = _attach_missing_citations(answer, sources)

    return {
        "answer": answer,
        "sources": sources,
        "grounded": True,
        "answer_method": "llm",
    }
