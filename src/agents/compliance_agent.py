"""Compliance Agent: citation-backed retrieval over regulatory documents, per architecture.md."""

from __future__ import annotations

from typing import Any

from src.services.rag_service import answer_question



def answer_compliance_question(question: str, *, top_k: int = 5) -> dict[str, Any]:
        """Answer a regulatory question strictly from retrieved RBI/SEBI/FATF evidence."""
        result = answer_question(question, top_k=top_k)
        result["agent"] = "compliance_agent"
        return result
