"""Assemble specialist-agent outputs into reports that separate facts, evidence, and LLM text."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def render_investigation_report(context: dict[str, Any]) -> str:
    """Render a report distinguishing ML prediction, evidence, LLM explanation, and review guidance."""
    lines = [
        "## Investigation Report",
        "",
        "Generated: %s" % datetime.now(timezone.utc).isoformat(),
        "",
        "### 1. Model Prediction",
    ]

    model = context.get("model", {})
    if model:
        for key, value in model.items():
            lines.append("- %s: %s" % (key.replace("_", " "), value))
    else:
        lines.append("- No model prediction was supplied.")

    lines.extend(["", "### 2. Retrieved Evidence"])
    evidence = context.get("evidence", [])

    if evidence:
        for item in evidence:
            source = item.get("source", "Unknown source")
            if item.get("page") is not None:
                source += ", page %s" % item["page"]
            lines.append(
                "- **%s**: %s" % (source, str(item.get("text", ""))[:300])
            )
    else:
        lines.append(
            "- No regulatory or document evidence was retrieved; evidence is insufficient."
        )

    lines.extend(["", "### 3. LLM-Generated Explanation"])
    explanation = context.get("explanation")
    lines.append(
        explanation
        if explanation
        else "No analyst-support explanation was generated."
    )

    lines.extend(
        [
            "",
            "### 4. Human Review Requirement",
            "- Recommended for human review: %s"
            % context.get("human_review_required", True),
            "",
            "> This report provides explainable decision support. It does not constitute an automated "
            "lending, fraud, or compliance decision.",
        ]
    )

    return "\n".join(lines)


def build_report_record(
    case_id: str | None,
    report_type: str,
    content: str,
    generated_by: str = "report_agent",
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "report_type": report_type,
        "content": content,
        "generated_by": generated_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
