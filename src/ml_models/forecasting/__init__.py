
"""Baseline trend forecasting for risk scores and alert volumes."""

from __future__ import annotations

from collections.abc import Sequence


def exponential_moving_average(
    series: Sequence[float],
    *,
    alpha: float = 0.3,
) -> list[float]:
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha must be in (0, 1]")

    if not series:
        return []

    smoothed = [float(series[0])]

    for value in series[1:]:
        smoothed.append(
            alpha * float(value) + (1 - alpha) * smoothed[-1]
        )

    return smoothed


def forecast_next_periods(
    series: Sequence[float],
    *,
    periods: int = 1,
    alpha: float = 0.3,
) -> list[float]:
    """Project forward using the last smoothed level."""
    if periods < 1:
        raise ValueError("periods must be at least 1")

    smoothed = exponential_moving_average(series, alpha=alpha)

    if not smoothed:
        raise ValueError(
            "series must contain at least one observation"
        )

    return [smoothed[-1]] * periods


def trend_summary(
    series: Sequence[float],
) -> dict[str, float | str]:
    if len(series) < 2:
        raise ValueError(
            "series must contain at least two observations "
            "to summarize a trend"
        )

    first = float(series[0])
    last = float(series[-1])
    change = last - first

    if change > 0:
        direction = "increasing"
    elif change < 0:
        direction = "decreasing"
    else:
        direction = "flat"

    return {
        "first_value": first,
        "last_value": last,
        "absolute_change": change,
        "direction": direction,
        "interpretation": (
            "Descriptive trend only; "
            "not a statistically validated forecast."
        ),
    }
