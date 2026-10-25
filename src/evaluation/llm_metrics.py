"""Heuristic LLM output metrics; deterministic proxies, not a substitute for human review."""

from __future__ import annotations

from src.retriever.query_rewriter import extract_keywords



def answer_relevance(question: str, answer: str) -> float:
        """Keyword-overlap proxy for whether the answer addresses the question."""
        question_keywords = set(extract_keywords(question))
        if not question_keywords:
                return 0.0
        answer_keywords = set(extract_keywords(answer))
        return len(question_keywords & answer_keywords) / len(question_keywords)



def faithfulness_proxy(answer: str, context: str) -> float:
        """Keyword-overlap proxy for whether the answer's claims appear in the retrieved context."""
        answer_keywords = set(extract_keywords(answer))
        if not answer_keywords:
                return 0.0
        context_keywords = set(extract_keywords(context))
        return len(answer_keywords & context_keywords) / len(answer_keywords)



def citation_validity(answer: str, retrieved_sources: list[str]) -> bool:
        """Check that every source name mentioned in the answer was actually retrieved."""
        lowered_answer = answer.lower()
        mentioned_known_source = any(source.lower() in lowered_answer for source in retrieved_sources)
        return mentioned_known_source or "not found" in lowered_answer or "insufficient" in lowered_answer



def evaluate_llm_response(question: str, answer: str, context: str, retrieved_sources: list[str]) -> dict[str, float |
bool]:
        return {
                "answer_relevance": answer_relevance(question, answer),
                "faithfulness_proxy": faithfulness_proxy(answer, context),
                "citation_validity": citation_validity(answer, retrieved_sources),
        }
