"""Finance Agent: deterministic financial-ratio analysis, per architecture.md."""
from __future__ import annotations
from typing import Any
def _safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator
def compute_financial_ratios(statement: dict[str, float]) -> dict[str, Any]:
    """Compute standard ratios from a financial statement; purely deterministic, no LLM involved."""
    current_assets = statement.get("current_assets", 0.0)
    current_liabilities = statement.get("current_liabilities", 0.0)
    total_debt = statement.get("total_debt", 0.0)
    total_equity = statement.get("total_equity", 0.0)
    net_income = statement.get("net_income", 0.0)
    revenue = statement.get("revenue", 0.0)
    operating_cash_flow = statement.get("operating_cash_flow", 0.0)
    return {
        "agent": "finance_agent",
        "current_ratio": _safe_divide(current_assets, current_liabilities),
        "debt_to_equity": _safe_divide(total_debt, total_equity),
        "net_profit_margin": _safe_divide(net_income, revenue),
        "return_on_equity": _safe_divide(net_income, total_equity),
        "operating_cash_flow_ratio": _safe_divide(operating_cash_flow, current_liabilities),
    }
def compare_periods(current_statement: dict[str, float], prior_statement: dict[str, float]) -> dict[str, A
ny]:
    """Compare ratio trends between two reporting periods."""
    current_ratios = compute_financial_ratios(current_statement)
    prior_ratios = compute_financial_ratios(prior_statement)
    changes = {
        key: (current_ratios[key] - prior_ratios[key])
        if isinstance(current_ratios.get(key), float) and isinstance(prior_ratios.get(key), float)
        else None
        for key in current_ratios
        if key != "agent"
    }
    return {"agent": "finance_agent", "current": current_ratios, "prior": prior_ratios, "change": changes}
