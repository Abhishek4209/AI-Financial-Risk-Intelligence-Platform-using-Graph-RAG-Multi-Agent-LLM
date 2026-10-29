
"""Validation shared by ingestion and risk prediction boundaries."""

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any


def require_columns(
    columns: Sequence[str],
    required: Sequence[str],
    *,
    source: str = "data",
) -> None:
    missing = [
        column
        for column in required
        if column not in columns
    ]

    if missing:
        raise ValueError(
            "%s is missing required columns: %s"
            % (source, ", ".join(missing))
        )


def validate_probability(
    value: float,
    *,
    field: str = "probability",
) -> float:
    result = float(value)

    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(
            "%s must be finite and between 0 and 1" % field
        )

    return result


def validate_paysim_transaction(
    transaction: Mapping[str, Any],
) -> dict[str, Any]:
    required = (
        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
    )

    require_columns(
        transaction.keys(),
        required,
        source="PaySim transaction",
    )

    result = dict(transaction)
    result["type"] = str(result["type"]).upper()

    if result["type"] not in {
        "CASH_IN",
        "CASH_OUT",
        "DEBIT",
        "PAYMENT",
        "TRANSFER",
    }:
        raise ValueError(
            "Unsupported PaySim transaction type: %s"
            % result["type"]
        )

    for field in required:
        if field == "type":
            continue

        number = float(result[field])

        if not isfinite(number) or number < 0:
            raise ValueError(
                "%s must be finite and non-negative" % field
            )

        result[field] = number

    if not result["step"].is_integer():
        raise ValueError("PaySim step must be an integer")

    return result
