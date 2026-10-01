import numpy as np
import pytest

from src.services import risk_investigation
from src.services.risk_investigation import (
    build_feature_frame,
    generate_huggingface_report,
    investigate_transaction,
)


FEATURE_COLUMNS = [
    "step",
    "hour",
    "day",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "origin_balance_error",
    "destination_balance_error",
    "origin_zero_after",
    "destination_zero_before",
    "amount_to_origin_balance",
    "type_CASH_IN",
    "type_CASH_OUT",
    "type_DEBIT",
    "type_PAYMENT",
    "type_TRANSFER",
]
TRANSACTION = {
    "transaction_id": "T10045",
    "step": 49,
    "type": "TRANSFER",
    "amount": 850000,
    "oldbalanceOrg": 900000,
    "newbalanceOrig": 50000,
    "oldbalanceDest": 10000,
    "newbalanceDest": 860000,
}


class FakeModel:
    classes_ = [0, 1]

    def predict_proba(self, features):
        assert list(features.columns) == FEATURE_COLUMNS
        return [[0.13, 0.87]]


def test_build_feature_frame_matches_paysim_training_features():
    frame = build_feature_frame(TRANSACTION, FEATURE_COLUMNS)

    assert frame.loc[0, "hour"] == 1
    assert frame.loc[0, "day"] == 2
    assert frame.loc[0, "origin_balance_error"] == 0
    assert frame.loc[0, "destination_balance_error"] == 0
    assert frame.loc[0, "amount_to_origin_balance"] == pytest.approx(850000 / 900000)
    assert frame.loc[0, "type_TRANSFER"] == 1
    assert frame.loc[0, "type_PAYMENT"] == 0


def test_investigation_combines_score_shap_evidence_and_report():
    report_contexts = []
    result = investigate_transaction(
        TRANSACTION,
        artifact={"model": FakeModel(), "feature_columns": FEATURE_COLUMNS, "threshold": 0.8},
        documents=[
            {
                "page_content": "Monitor unusual transfers and review applicable controls.",
                "metadata": {
                    "source_file": "RBI_fraud_guidance.pdf",
                    "organization": "RBI",
                    "page": 0,
                },
            }
        ],
        explain=lambda model, features: [
            {
                "feature": "amount",
                "feature_value": 850000.0,
                "shap_value": 0.31,
                "direction": "increases",
            }
        ],
        generate_report=lambda context: report_contexts.append(context) or "Analyst review recommended.",
    )

    assert result["model"]["fraud_risk_score"] == 0.87
    assert result["model"]["risk_level"] == "HIGH"
    assert result["human_review_required"] is True
    assert result["shap_drivers"][0]["feature"] == "amount"
    assert result["evidence"][0]["source"] == "RBI_fraud_guidance.pdf"
    assert result["evidence"][0]["page"] == 1
    assert result["report_summary"] == "Analyst review recommended."
    assert "## Transaction Investigation Summary" in result["report"]
    assert "Analyst review recommended." in result["report"]
    assert "Retrieved Evidence" in result["report"]
    assert "amount" in result["retrieval_query"]
    assert report_contexts[0]["model"]["interpretation"].endswith("does not establish fraud.")


def test_build_feature_frame_rejects_non_paysim_schema():
    with pytest.raises(ValueError, match="Missing required PaySim fields"):
        build_feature_frame({"amount": 850000, "age": 25}, FEATURE_COLUMNS)


def test_malformed_generated_summary_uses_grounded_fallback():
    result = investigate_transaction(
        TRANSACTION,
        artifact={"model": FakeModel(), "feature_columns": FEATURE_COLUMNS, "threshold": 0.8},
        documents=[],
        explain=lambda model, features: [],
        generate_report=lambda context: '"feature": "amount" { malformed output',
    )

    assert result["report_summary"] is None
    assert "The model score is at or above its stored threshold" in result["report"]
    assert "evidence is insufficient" in result["report"]


def test_huggingface_report_serializes_numpy_values(monkeypatch):
    captured_prompts = []

    class FakeTokenizer:
        def __call__(self, prompt, **kwargs):
            captured_prompts.append(prompt)
            return {"input_ids": [1]}

        def decode(self, tokens, **kwargs):
            return "Grounded report"

    class FakeModel:
        def generate(self, **kwargs):
            return [[1]]

    monkeypatch.setattr(
        risk_investigation,
        "_load_huggingface_seq2seq_model",
        lambda model_name: (FakeTokenizer(), FakeModel()),
    )

    report = generate_huggingface_report(
        {
            "transaction": {"amount": np.int64(1)},
            "model": {"fraud_risk_score": np.float64(0.2)},
            "shap_drivers": [],
            "regulatory_evidence": [],
        }
    )

    assert report == "Grounded report"
    assert "amount: 1" in captured_prompts[0]
