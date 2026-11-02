"""Chunked analytics for the local synthetic PaySim transaction dataset."""

from __future__ import annotations

import os
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.ingestion.csv_loader import iter_csv
from src.utils.constants import PROJECT_ROOT, RAW_DATA_ROOT
from src.utils.validators import require_columns

PAYSIM_DATA_DIR = (
    RAW_DATA_ROOT / "Fraud" / "PaySim Financial Transactions"
)
DEFAULT_PAYSIM_CSV = (
    PAYSIM_DATA_DIR
    / "PS_20174392719_1491204439457_log.csv"
)
PAYSIM_REQUIRED_COLUMNS = ("type", "amount", "isFraud")
PAYSIM_CHUNK_SIZE = 100_000
PAYSIM_CACHE_TTL_SECONDS = 300

_cache_lock = threading.Lock()
_cached_signature: tuple[str, int, int] | None = None
_cached_at = 0.0
_cached_analytics: dict[str, Any] | None = None


class PaySimAnalyticsError(ValueError):
    """Raised when PaySim analytics cannot be safely calculated."""


def _configured_csv_path() -> Path:
    configured_path = os.getenv("PAYSIM_CSV_PATH")
    candidate = (
        Path(configured_path).expanduser()
        if configured_path
        else DEFAULT_PAYSIM_CSV
    )

    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate

    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise PaySimAnalyticsError(
            "The configured PaySim CSV path could not be resolved."
        ) from exc
    raw_data_directory = RAW_DATA_ROOT.resolve()
    approved_directory = PAYSIM_DATA_DIR.resolve()

    try:
        approved_directory.relative_to(raw_data_directory)
    except ValueError as exc:
        raise PaySimAnalyticsError(
            "The approved PaySim dataset directory must remain inside data/raw."
        ) from exc

    try:
        resolved.relative_to(raw_data_directory)
        resolved.relative_to(approved_directory)
    except ValueError as exc:
        raise PaySimAnalyticsError(
            "PAYSIM_CSV_PATH must point inside the approved PaySim dataset directory."
        ) from exc

    if resolved.suffix.lower() != ".csv":
        raise PaySimAnalyticsError(
            "The configured PaySim dataset must be a CSV file."
        )

    return resolved


def aggregate_paysim_csv(
    csv_path: str | Path,
    *,
    chunksize: int = PAYSIM_CHUNK_SIZE,
) -> dict[str, Any]:
    """Aggregate supported PaySim fields without loading the complete CSV."""
    source = Path(csv_path)

    if not source.is_file():
        raise PaySimAnalyticsError(
            "The configured PaySim CSV file is missing."
        )

    if chunksize < 1:
        raise ValueError("chunksize must be positive")

    try:
        header = pd.read_csv(
            source,
            nrows=0,
            encoding="utf-8-sig",
        )
        require_columns(
            header.columns,
            PAYSIM_REQUIRED_COLUMNS,
            source="PaySim CSV",
        )
    except PaySimAnalyticsError:
        raise
    except (OSError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise PaySimAnalyticsError(
            "The configured PaySim CSV is empty or cannot be parsed."
        ) from exc
    except ValueError as exc:
        raise PaySimAnalyticsError(str(exc)) from exc

    total_transactions = 0
    total_amount = 0.0
    fraud_transaction_count = 0
    fraud_transaction_amount = 0.0
    transaction_types: Counter[str] = Counter()

    try:
        chunks = iter_csv(
            source,
            chunksize=chunksize,
            required_columns=PAYSIM_REQUIRED_COLUMNS,
            usecols=list(PAYSIM_REQUIRED_COLUMNS),
            encoding="utf-8-sig",
        )

        for chunk in chunks:
            try:
                amounts = pd.to_numeric(chunk["amount"], errors="raise")
                fraud_labels = pd.to_numeric(
                    chunk["isFraud"],
                    errors="raise",
                )
            except (TypeError, ValueError) as exc:
                raise PaySimAnalyticsError(
                    "PaySim amount and isFraud values must be numeric."
                ) from exc

            if (
                amounts.isna().any()
                or not np.isfinite(amounts.to_numpy()).all()
                or (amounts < 0).any()
            ):
                raise PaySimAnalyticsError(
                    "PaySim amount values must be finite and non-negative."
                )

            if (
                fraud_labels.isna().any()
                or not fraud_labels.isin((0, 1)).all()
            ):
                raise PaySimAnalyticsError(
                    "PaySim isFraud values must contain only 0 and 1."
                )

            transaction_type = chunk["type"].astype("string").str.strip()
            if transaction_type.isna().any() or transaction_type.eq("").any():
                raise PaySimAnalyticsError(
                    "PaySim type values must not be empty."
                )

            fraud_mask = fraud_labels.eq(1)
            total_transactions += len(chunk)
            total_amount += float(amounts.sum())
            fraud_transaction_count += int(fraud_mask.sum())
            fraud_transaction_amount += float(
                amounts.loc[fraud_mask].sum()
            )
            transaction_types.update(
                transaction_type.value_counts().to_dict()
            )
    except PaySimAnalyticsError:
        raise
    except (OSError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise PaySimAnalyticsError(
            "The configured PaySim CSV contains invalid or unreadable data."
        ) from exc
    except ValueError as exc:
        raise PaySimAnalyticsError(
            "The configured PaySim CSV contains invalid data."
        ) from exc

    return {
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "fraud_transaction_count": fraud_transaction_count,
        "fraud_transaction_rate": (
            fraud_transaction_count / total_transactions
            if total_transactions
            else 0.0
        ),
        "fraud_transaction_amount": fraud_transaction_amount,
        "transaction_type_breakdown": dict(sorted(transaction_types.items())),
    }


def get_paysim_analytics() -> dict[str, Any]:
    """Return cached PaySim aggregates, refreshing at most every five minutes."""
    global _cached_at, _cached_analytics, _cached_signature

    source = _configured_csv_path()

    try:
        stat = source.stat()
    except OSError as exc:
        raise PaySimAnalyticsError(
            "The configured PaySim CSV file is missing or unreadable."
        ) from exc

    signature = (str(source), stat.st_mtime_ns, stat.st_size)
    now = time.monotonic()

    with _cache_lock:
        if (
            _cached_analytics is not None
            and _cached_signature == signature
            and now - _cached_at < PAYSIM_CACHE_TTL_SECONDS
        ):
            return dict(_cached_analytics)

        analytics = aggregate_paysim_csv(source)

        try:
            updated_stat = source.stat()
        except OSError as exc:
            raise PaySimAnalyticsError(
                "The configured PaySim CSV became unavailable during aggregation."
            ) from exc

        updated_signature = (
            str(source),
            updated_stat.st_mtime_ns,
            updated_stat.st_size,
        )
        if updated_signature != signature:
            raise PaySimAnalyticsError(
                "The PaySim CSV changed during aggregation; retry the request."
            )

        refreshed_at = datetime.now(timezone.utc).isoformat()
        result = {
            "source": "PaySim",
            "is_synthetic": True,
            "status": "available",
            **analytics,
            "refreshed_at": refreshed_at,
            "cache_ttl_seconds": PAYSIM_CACHE_TTL_SECONDS,
        }
        _cached_signature = signature
        _cached_at = time.monotonic()
        _cached_analytics = result
        return dict(result)


def clear_paysim_analytics_cache() -> None:
    """Clear the process-local cache; intended for tests and explicit refreshes."""
    global _cached_at, _cached_analytics, _cached_signature

    with _cache_lock:
        _cached_signature = None
        _cached_at = 0.0
        _cached_analytics = None
