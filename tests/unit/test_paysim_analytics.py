from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api.routes import _get_exposure_under_review
from src.database.models import (
    Base,
    InvestigationCase,
    Transaction,
)
from src.services.paysim_analytics import (
    PaySimAnalyticsError,
    aggregate_paysim_csv,
    clear_paysim_analytics_cache,
    get_paysim_analytics,
)
from src.services import paysim_analytics


def _write_paysim_csv(path, records):
    pd.DataFrame.from_records(records).to_csv(path, index=False)
    return path


def test_aggregates_csv_in_chunks_and_calculates_fraud_metrics(tmp_path):
    csv_path = _write_paysim_csv(
        tmp_path / "paysim.csv",
        [
            {"type": "PAYMENT", "amount": 10.0, "isFraud": 0},
            {"type": "TRANSFER", "amount": 20.0, "isFraud": 1},
            {"type": "PAYMENT", "amount": 30.0, "isFraud": 0},
            {"type": "CASH_OUT", "amount": 40.0, "isFraud": 1},
            {"type": "PAYMENT", "amount": 50.0, "isFraud": 0},
        ],
    )

    analytics = aggregate_paysim_csv(csv_path, chunksize=2)

    assert analytics == {
        "total_transactions": 5,
        "total_amount": 150.0,
        "fraud_transaction_count": 2,
        "fraud_transaction_rate": 0.4,
        "fraud_transaction_amount": 60.0,
        "transaction_type_breakdown": {
            "CASH_OUT": 1,
            "PAYMENT": 3,
            "TRANSFER": 1,
        },
    }


def test_rejects_missing_required_columns(tmp_path):
    csv_path = _write_paysim_csv(
        tmp_path / "missing-column.csv",
        [{"transaction_type": "PAYMENT", "amount": 10, "isFraud": 0}],
    )

    with pytest.raises(PaySimAnalyticsError, match="type"):
        aggregate_paysim_csv(csv_path, chunksize=1)


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (
            {"type": "PAYMENT", "amount": "invalid", "isFraud": 0},
            "amount and isFraud values must be numeric",
        ),
        (
            {"type": "PAYMENT", "amount": 10, "isFraud": 2},
            "isFraud values must contain only 0 and 1",
        ),
    ],
)
def test_rejects_invalid_amounts_and_fraud_labels(
    tmp_path,
    record,
    message,
):
    csv_path = _write_paysim_csv(tmp_path / "invalid.csv", [record])

    with pytest.raises(PaySimAnalyticsError, match=message):
        aggregate_paysim_csv(csv_path, chunksize=1)


def test_configured_path_must_remain_inside_approved_paysim_directory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "PAYSIM_CSV_PATH",
        str(tmp_path / "outside.csv"),
    )

    with pytest.raises(PaySimAnalyticsError, match="approved PaySim"):
        get_paysim_analytics()


def test_cache_refreshes_when_source_file_changes(monkeypatch, tmp_path):
    csv_path = tmp_path / "paysim.csv"
    csv_path.write_text("first", encoding="utf-8")
    calls = []

    def fake_aggregate(path):
        calls.append(path)
        return {
            "total_transactions": len(calls),
            "total_amount": 0.0,
            "fraud_transaction_count": 0,
            "fraud_transaction_rate": 0.0,
            "fraud_transaction_amount": 0.0,
            "transaction_type_breakdown": {},
        }

    clear_paysim_analytics_cache()
    monkeypatch.setattr(
        paysim_analytics,
        "_configured_csv_path",
        lambda: csv_path.resolve(),
    )
    monkeypatch.setattr(
        paysim_analytics,
        "aggregate_paysim_csv",
        fake_aggregate,
    )

    try:
        first = get_paysim_analytics()
        second = get_paysim_analytics()
        assert first["total_transactions"] == 1
        assert second["total_transactions"] == 1
        assert len(calls) == 1

        csv_path.write_text("changed source", encoding="utf-8")
        refreshed = get_paysim_analytics()
        assert refreshed["total_transactions"] == 2
        assert len(calls) == 2
    finally:
        clear_paysim_analytics_cache()


def test_exposure_counts_each_linked_transaction_once():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        first = Transaction(
            id="transaction-one",
            amount=100.0,
            currency="USD",
            transaction_type="TRANSFER",
            occurred_at=now,
        )
        second = Transaction(
            id="transaction-two",
            amount=100.0,
            currency="USD",
            transaction_type="TRANSFER",
            occurred_at=now,
        )
        closed_transaction = Transaction(
            id="transaction-closed",
            amount=500.0,
            currency="USD",
            transaction_type="TRANSFER",
            occurred_at=now,
        )
        session.add_all(
            [
                first,
                second,
                closed_transaction,
                InvestigationCase(
                    transaction_id=first.id,
                    case_type="fraud",
                    status="open",
                    severity="high",
                    summary="First open case",
                ),
                InvestigationCase(
                    transaction_id=first.id,
                    case_type="fraud",
                    status="open",
                    severity="medium",
                    summary="Second open case for same transaction",
                ),
                InvestigationCase(
                    transaction_id=second.id,
                    case_type="fraud",
                    status="open",
                    severity="high",
                    summary="Open case for a separate equal-value transaction",
                ),
                InvestigationCase(
                    transaction_id=closed_transaction.id,
                    case_type="fraud",
                    status="closed",
                    severity="high",
                    summary="Closed case",
                ),
            ]
        )
        session.commit()

        assert _get_exposure_under_review(session) == 200.0
