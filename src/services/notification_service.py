
"""Analyst-facing notifications for investigation cases; logs by default, webhook optional."""

from __future__ import annotations

import os
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


def notify_case_created(case: dict[str, Any]) -> None:
    logger.info(
        "Investigation case created: %s (severity=%s)",
        case.get("id"),
        case.get("severity"),
    )
    _send_webhook("case_created", case)


def notify_high_risk_prediction(prediction: dict[str, Any]) -> None:
    logger.info(
        "High-risk prediction recorded: task=%s score=%.4f",
        prediction.get("task"),
        prediction.get("probability", 0.0),
    )
    _send_webhook("high_risk_prediction", prediction)


def _send_webhook(event_type: str, payload: dict[str, Any]) -> None:
    webhook_url = os.getenv("NOTIFICATION_WEBHOOK_URL")
    if not webhook_url:
        return

    try:
        import requests

        requests.post(
            webhook_url,
            json={"event": event_type, "data": payload},
            timeout=5,
        )
    except Exception as exc:
        logger.warning("Notification webhook failed for %s: %s", event_type, exc)
