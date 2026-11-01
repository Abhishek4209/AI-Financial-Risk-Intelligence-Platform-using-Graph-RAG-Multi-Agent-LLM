from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.agents import (
    compliance_agent,
    finance_agent,
    fraud_agent,
    report_agent,
    risk_agent,
    supervisor,
)
from src.ml_models import credit_risk, explainability, forecasting, fraud_detection


class FakeModel:
    classes_ = [0, 1]

    def __init__(self, probabilities=(0.2, 0.8)):
        self.probabilities = probabilities
        self.received = None

    def predict_proba(self, frame):
        self.received = frame.copy()
        return [self.probabilities]


def _install_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def _valid_transaction(**updates):
    return {
        "step": 25,
        "type": "TRANSFER",
        "amount": 12,
        "oldbalanceOrg": 20,
        "newbalanceOrig": 8,
        "oldbalanceDest": 3,
        "newbalanceDest": 15,
        **updates,
    }


def test_fraud_artifact_normalization_loading_and_thresholds(tmp_path, monkeypatch):
    model = FakeModel()
    artifact_path = tmp_path / "model.pkl"
    import pickle

    artifact_path.write_bytes(pickle.dumps({"model": model, "feature_columns": ["amount"]}))
    fraud_detection.load_fraud_artifact.cache_clear()
    try:
        loaded = fraud_detection.load_fraud_artifact("custom", artifact_path)
        assert loaded["model"] is not None
        assert loaded["feature_columns"] == ["amount"]
        with pytest.raises(FileNotFoundError):
            fraud_detection.load_fraud_artifact("missing", tmp_path / "missing.pkl")
    finally:
        fraud_detection.load_fraud_artifact.cache_clear()

    normalized = fraud_detection._normalize_artifact(
        SimpleNamespace(feature_names_in_=["amount"]), "custom"
    )
    assert normalized["feature_columns"] == ["amount"]
    assert normalized["threshold"] == fraud_detection.DEFAULT_PAYSIM_THRESHOLD
    with pytest.raises(ValueError, match="between 0 and 1"):
        fraud_detection._get_threshold({"threshold": 1.5})
    with pytest.raises(ValueError, match="positive class 1"):
        fraud_detection._score(
            SimpleNamespace(classes_=[0], predict_proba=lambda frame: [[1.0]]),
            pd.DataFrame({"x": [1]}),
        )


def test_fraud_predictions_validate_inputs_and_encode_ieee(monkeypatch, tmp_path):
    model = FakeModel((0.1, 0.91))
    expected_drivers = [
        {"feature": "amount", "feature_value": 5.0, "shap_value": 0.4}
    ]
    monkeypatch.setattr(
        fraud_detection,
        "explain_prediction",
        lambda model, features, top_k: expected_drivers,
    )
    paysim_artifact = {
        "model": model,
        "feature_columns": ["step", "amount", "type_TRANSFER"],
        "threshold": 0.9,
    }
    result = fraud_detection.predict_paysim_fraud_risk(
        _valid_transaction(), artifact=paysim_artifact
    )
    assert result["risk_level"] == "HIGH"
    assert result["fraud_risk_score"] == 0.91
    assert result["shap_drivers"] == expected_drivers
    assert model.received.columns.tolist() == paysim_artifact["feature_columns"]
    with pytest.raises(ValueError, match="no recorded feature_columns"):
        fraud_detection.predict_paysim_fraud_risk(
            _valid_transaction(), artifact={"model": model}
        )

    artifact = {"model": model, "feature_columns": ["amount", "missing"]}
    with pytest.raises(ValueError, match="Missing required engineered features"):
        fraud_detection.predict_fraud_risk({"amount": 5}, "custom", artifact=artifact)
    below = fraud_detection.predict_fraud_risk(
        {"amount": 5}, "custom",
        artifact={"model": model, "feature_columns": ["amount"], "threshold": 0.95},
    )
    assert below["risk_level"] == "BELOW_MODEL_THRESHOLD"
    with pytest.raises(ValueError, match="no recorded feature_columns"):
        fraud_detection.predict_fraud_risk({}, "custom", artifact={"model": model})

    class Encoder:
        def transform(self, values):
            if values != ["known"]:
                raise ValueError("unseen label")
            return ["3"]

    monkeypatch.setattr(
        fraud_detection,
        "_load_ieee_encoders",
        lambda: {"category": Encoder()},
    )
    encoded = fraud_detection._build_ieee_frame(
        {"category": "known", "amount": 5},
        ["category", "amount"],
    )
    assert encoded.iloc[0].tolist() == [3, 5]
    with pytest.raises(ValueError, match="feature 'amount' must be numeric"):
        fraud_detection._build_ieee_frame(
            {"category": "known", "amount": "invalid"},
            ["category", "amount"],
        )
    with pytest.raises(ValueError, match="Unknown category"):
        fraud_detection._build_ieee_frame(
            {"category": "bad"}, ["category"]
        )


def test_credit_artifact_paths_and_prediction_branches(tmp_path, monkeypatch):
    model = FakeModel((0.6, 0.4))
    import pickle

    artifact_file = tmp_path / "credit.pkl"
    artifact_file.write_bytes(
        pickle.dumps({"model": model, "feature_columns": ["loan_amount"]})
    )
    credit_risk.load_credit_artifact.cache_clear()
    try:
        loaded = credit_risk.load_credit_artifact("lending_club", artifact_file)
        assert loaded["feature_columns"] == ["loan_amount"]
        with pytest.raises(ValueError, match="dataset must be one of"):
            credit_risk._artifact_path("other", None)
        with pytest.raises(FileNotFoundError):
            credit_risk.load_credit_artifact("taiwan", tmp_path / "absent.pkl")
    finally:
        credit_risk.load_credit_artifact.cache_clear()

    assert [credit_risk.risk_band(x) for x in (0.8, 0.3, 0.1)] == [
        "HIGH", "MEDIUM", "LOW"
    ]
    lending = credit_risk.predict_credit_risk(
        {"loan_amount": 200},
        "lending_club",
        artifact={"model": model, "feature_columns": ["loan_amount"]},
    )
    assert lending["risk_band"] == "MEDIUM"
    assert lending["recommended_for_review"] is True
    assert model.received.iloc[0, 0] == 200
    with pytest.raises(ValueError, match="missing feature_columns"):
        credit_risk.predict_credit_risk(
            {"loan_amount": 1}, "lending_club", artifact={"model": model}
        )
    with pytest.raises(ValueError, match="dataset must"):
        credit_risk.predict_credit_risk({}, "other", artifact={"model": model})
    with pytest.raises(ValueError, match="positive class 1"):
        credit_risk.predict_credit_risk(
            {column: 1 for column in credit_risk.derive_taiwan_features.__globals__["TAIWAN_FEATURES"]},
            "taiwan",
            artifact={
                "model": SimpleNamespace(
                    classes_=[0],
                    predict_proba=lambda frame: [[1.0]],
                )
            },
        )
    with pytest.raises(ValueError, match="missing columns"):
        credit_risk.predict_credit_risk(
            {}, "taiwan", artifact={"model": model}
        )


def test_explainability_handles_tree_pipeline_and_invalid_shapes(monkeypatch):
    class FakeExplanation:
        values = np.array([[[0.8, 0.7], [0.2, -0.5]]])

    _install_module(
        monkeypatch,
        "shap",
        TreeExplainer=lambda model: lambda values: FakeExplanation(),
        LinearExplainer=lambda *args: None,
        Explainer=lambda *args: None,
    )
    features = pd.DataFrame({"first": [2], "second": [3]})
    drivers = explainability.explain_prediction(
        SimpleNamespace(feature_importances_=[1, 1]),
        features,
    )
    assert [driver["feature"] for driver in drivers] == ["first", "second"]
    assert drivers[0]["direction"] == "increases"
    assert drivers[1]["direction"] == "decreases"
    with pytest.raises(ValueError, match="at least 1"):
        explainability.explain_prediction(object(), features, top_k=0)
    with pytest.raises(ValueError, match="at least one row"):
        explainability.explain_prediction(object(), features.iloc[0:0])


def test_explainability_transforms_sparse_pipeline_and_linear_fallback(monkeypatch):
    class SparseLike:
        shape = (1, 3)

        def toarray(self):
            return np.array([[1.0, 2.0, 3.0]])

    class Transform:
        def transform(self, frame):
            return SparseLike()

        def get_feature_names_out(self):
            return ["a", "b", "c"]

    class LinearEstimator:
        def predict_proba(self, values):
            return values

    class BrokenLinear:
        def __init__(self, *args):
            raise RuntimeError("unsupported")

    class GenericExplanation:
        values = np.array([[0.3, 0.2, -0.5]])

    _install_module(
        monkeypatch,
        "shap",
        TreeExplainer=lambda model: None,
        LinearExplainer=BrokenLinear,
        Explainer=lambda *args: lambda values: GenericExplanation(),
    )
    pipeline = SimpleNamespace(
        steps=[("prep", Transform()), ("model", LinearEstimator())]
    )
    drivers = explainability.explain_prediction(
        pipeline,
        pd.DataFrame({"raw": [10]}),
        background=pd.DataFrame({"raw": [1]}),
        top_k=1,
    )
    assert [item["feature"] for item in drivers] == ["a", "c"]
    assert explainability._transform_through([], pd.DataFrame({"x": [2]}))[1] == ["x"]
    assert explainability._resolve_background([], np.ones((1, 2)), None).tolist() == [[0, 0]]
    with pytest.raises(ValueError, match="output length"):
        monkeypatch.setattr(
            explainability,
            "_compute_shap_values",
            lambda *args: np.array([1.0]),
        )
        explainability.explain_prediction(
            LinearEstimator(), pd.DataFrame({"x": [1], "y": [2]})
        )


def test_forecasting_algorithms_cover_empty_and_directional_cases():
    assert forecasting.exponential_moving_average([]) == []
    assert forecasting.exponential_moving_average([1, 3], alpha=1) == [1.0, 3.0]
    assert forecasting.exponential_moving_average([2, 4], alpha=0.5) == [2.0, 3.0]
    for alpha in (0, 1.1):
        with pytest.raises(ValueError, match="alpha"):
            forecasting.exponential_moving_average([1], alpha=alpha)
    assert forecasting.forecast_next_periods([1, 3], periods=2, alpha=1) == [3.0, 3.0]
    with pytest.raises(ValueError, match="periods"):
        forecasting.forecast_next_periods([1], periods=0)
    with pytest.raises(ValueError, match="at least one observation"):
        forecasting.forecast_next_periods([], periods=1)
    assert forecasting.trend_summary([1, 2])["direction"] == "increasing"
    assert forecasting.trend_summary([2, 1])["direction"] == "decreasing"
    assert forecasting.trend_summary([2, 2])["direction"] == "flat"
    with pytest.raises(ValueError, match="at least two"):
        forecasting.trend_summary([1])


def test_finance_agent_ratios_and_period_comparison():
    current = {
        "current_assets": 20,
        "current_liabilities": 10,
        "total_debt": 5,
        "total_equity": 10,
        "net_income": 2,
        "revenue": 8,
        "operating_cash_flow": 4,
    }
    ratios = finance_agent.compute_financial_ratios(current)
    assert ratios["current_ratio"] == 2
    assert ratios["net_profit_margin"] == 0.25
    assert finance_agent.compute_financial_ratios({})["current_ratio"] is None
    comparison = finance_agent.compare_periods(current, {})
    assert comparison["change"]["current_ratio"] is None
    assert comparison["change"]["debt_to_equity"] is None


def test_agents_and_supervisor_dispatch_all_supported_intents(monkeypatch):
    monkeypatch.setattr(
        risk_agent,
        "load_credit_artifact",
        lambda dataset: {"model": object(), "feature_columns": ["loan_amount"]},
    )
    monkeypatch.setattr(
        risk_agent,
        "predict_credit_risk",
        lambda record, dataset, artifact: {
            "recommended_for_review": True,
            "dataset": dataset,
        },
    )
    monkeypatch.setattr(
        risk_agent,
        "explain_prediction",
        lambda model, features: [{"feature": "loan_amount"}],
    )
    assessed = risk_agent.assess_credit_risk({"loan_amount": 10}, "lending_club")
    assert assessed["agent"] == "risk_agent"
    assert assessed["human_review_required"] is True
    monkeypatch.setattr(
        risk_agent,
        "explain_prediction",
        lambda *args: (_ for _ in ()).throw(RuntimeError("SHAP unavailable")),
    )
    assert risk_agent.assess_credit_risk(
        {"loan_amount": 10}, "lending_club"
    )["shap_drivers"] == []

    monkeypatch.setattr(
        fraud_agent,
        "investigate_transaction",
        lambda transaction: {"transaction_id": transaction["id"]},
    )
    from src.graph_rag import graph_query

    monkeypatch.setattr(graph_query, "fan_out_transactions", lambda account: ["out"])
    monkeypatch.setattr(graph_query, "fan_in_transactions", lambda account: ["in"])
    fraud = fraud_agent.assess_transaction_fraud({"id": "T1"}, account_id="A1")
    assert fraud["graph_evidence"] == {"fan_out": ["out"], "fan_in": ["in"]}
    monkeypatch.setattr(
        graph_query,
        "fan_out_transactions",
        lambda account: (_ for _ in ()).throw(RuntimeError("graph down")),
    )
    assert fraud_agent.assess_transaction_fraud(
        {"id": "T2"}, account_id="A1"
    )["graph_evidence_error"] == "graph down"

    monkeypatch.setattr(
        compliance_agent,
        "answer_question",
        lambda question, top_k: {"answer": "grounded"},
    )
    assert compliance_agent.answer_compliance_question("rule")["agent"] == "compliance_agent"
    monkeypatch.setattr(supervisor, "assess_transaction_fraud", lambda *args, **kwargs: {"agent": "fraud"})
    monkeypatch.setattr(supervisor, "assess_credit_risk", lambda *args: {"agent": "credit"})
    monkeypatch.setattr(supervisor, "compute_financial_ratios", lambda *args: {"agent": "finance"})
    monkeypatch.setattr(supervisor, "answer_compliance_question", lambda request: {"agent": "compliance"})
    monkeypatch.setattr(supervisor, "compile_report", lambda results, case_id=None: {"items": len(results)})
    request = "fraud credit risk financial statement compliance"
    assert supervisor.classify_intents(request) == [
        "fraud", "credit_risk", "compliance", "finance"
    ]
    response = supervisor.handle_request(
        request,
        payload={
            "transaction": {"id": "T"},
            "applicant": {"loan_amount": 10},
            "dataset": "lending_club",
            "statement": {},
            "case_id": "C1",
        },
        report=True,
    )
    assert len(response["results"]) == 4
    assert response["report"] == {"items": 4}
    assert supervisor.classify_intents("hello") == ["compliance"]
    assert supervisor.handle_request("hello", payload={})["results"][0]["agent"] == "compliance"


def test_report_agent_merges_outputs_and_empty_results():
    report = report_agent.compile_report(
        [
            {
                "agent": "risk",
                "prediction": {"risk": "HIGH"},
                "evidence": [{"source": "RBI", "text": "rules"}],
                "human_review_required": True,
            },
            {"agent": "compliance", "answer": "Review controls."},
            {"agent": "fraud", "model": {"score": 0.8}, "report_summary": "Investigate."},
        ],
        case_id="C1",
        report_type="summary",
    )
    assert report["case_id"] == "C1"
    assert report["report_type"] == "summary"
    assert "Review controls." in report["content"]
    assert report_agent.compile_report([])["content"]
