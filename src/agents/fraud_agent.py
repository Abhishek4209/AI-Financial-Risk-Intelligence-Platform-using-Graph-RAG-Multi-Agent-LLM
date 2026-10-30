
"""Fraud Agent: PaySim scoring, SHAP evidence, and graph-based relationship checks."""

from __future__ import annotations

from typing import Any

from src.services.risk_investigation import investigate_transaction


def assess_transaction_fraud(
    transaction: dict[str, Any],
    *,
    account_id: str | None = None,
) -> dict[str, Any]:
    """Score a transaction and optionally attach graph relationship evidence."""

    result = investigate_transaction(transaction)
    result["agent"] = "fraud_agent"

    if account_id:
        try:
            from src.graph_rag.graph_query import (
                fan_in_transactions,
                fan_out_transactions,
            )

            result["graph_evidence"] = {
                "fan_out": fan_out_transactions(account_id),
                "fan_in": fan_in_transactions(account_id),
            }
        except RuntimeError as exc:
            result["graph_evidence_error"] = str(exc)

    return result
