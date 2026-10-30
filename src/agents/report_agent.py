
"""Report Agent: combine specialist outputs into one structured report."""

from __future__ import annotations

from typing import Any

from src.services.report_service import (
    build_report_record,
    render_investigation_report,
)


def compile_report(
    agent_results: list[dict[str, Any]],
    *,
    case_id: str | None = None,
    report_type: str = "investigation",
) -> dict[str, Any]:
    """Merge risk, fraud, compliance, and finance agent outputs."""

    model_facts: dict[str, Any] = {}
    evidence: list[dict[str, Any]] = []
    explanations: list[str] = []
    human_review_required = False

    for result in agent_results:
        agent_name = result.get("agent", "unknown_agent")

        if "prediction" in result:
            model_facts[agent_name] = result["prediction"]
        elif "model" in result:
            model_facts[agent_name] = result["model"]

        evidence.extend(result.get("evidence", []))

        if result.get("answer"):
            explanations.append(
                "%s: %s" % (agent_name, result["answer"])
            )

        if result.get("report_summary"):
            explanations.append(
                "%s: %s" % (agent_name, result["report_summary"])
            )

        human_review_required = (
            human_review_required
            or bool(result.get("human_review_required"))
        )

    content = render_investigation_report(
        {
            "model": model_facts,
            "evidence": evidence,
            "explanation": (
                "\n".join(explanations) if explanations else None
            ),
            "human_review_required": human_review_required,
        }
    )

    return build_report_record(case_id, report_type, content)
