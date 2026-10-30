
"""Supervisor Agent: routes requests to specialist agents."""

from __future__ import annotations

from typing import Any

from src.agents.compliance_agent import answer_compliance_question
from src.agents.finance_agent import compute_financial_ratios
from src.agents.fraud_agent import assess_transaction_fraud
from src.agents.report_agent import compile_report
from src.agents.risk_agent import assess_credit_risk


INTENT_KEYWORDS = {
    "fraud": (
        "fraud",
        "suspicious transaction",
        "transaction risk",
    ),
    "credit_risk": (
        "default",
        "credit risk",
        "loan risk",
        "creditworthiness",
    ),
    "compliance": (
        "regulation",
        "compliance",
        "rbi",
        "sebi",
        "kyc",
        "aml rule",
    ),
    "finance": (
        "ratio",
        "profitability",
        "cash flow",
        "financial statement",
    ),
}


def classify_intents(request: str) -> list[str]:
    """Detect request intents using keyword matching."""

    lowered = request.lower()

    intents = [
        intent
        for intent, keywords in INTENT_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]

    return intents or ["compliance"]


def handle_request(
    request: str,
    *,
    payload: dict[str, Any] | None = None,
    report: bool = False,
) -> dict[str, Any]:
    """Dispatch a request to the required specialist agents."""

    data = payload or {}
    intents = classify_intents(request)
    results: list[dict[str, Any]] = []

    if "fraud" in intents and "transaction" in data:
        results.append(
            assess_transaction_fraud(
                data["transaction"],
                account_id=data.get("account_id"),
            )
        )

    if "credit_risk" in intents and "applicant" in data:
        results.append(
            assess_credit_risk(
                data["applicant"],
                data.get("dataset", "taiwan"),
            )
        )

    if "finance" in intents and "statement" in data:
        results.append(
            compute_financial_ratios(data["statement"])
        )

    if "compliance" in intents:
        results.append(answer_compliance_question(request))

    response: dict[str, Any] = {
        "intents": intents,
        "results": results,
    }

    if report:
        response["report"] = compile_report(
            results,
            case_id=data.get("case_id"),
        )

    return response
