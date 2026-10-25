from types import SimpleNamespace

import numpy as np
import pytest

from src.agents import compliance_agent, fraud_agent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.finance_agent import FinanceAgent
from src.agents.fraud_agent import FraudAgent
from src.agents.report_agent import ReportAgent
from src.agents.risk_agent import RiskAgent
from src.agents.supervisor import SupervisorAgent


class FakeCreditModel:
    classes_ = [0, 1]

    def predict_proba(self, frame):
        assert list(frame.columns) == ["income", "age"]
        return np.array([[0.25, 0.75]])

    def predict(self, frame):
        return np.array([1])


def test_compliance_agent_returns_retrieved_citations(monkeypatch):
    monkeypatch.setattr(
        compliance_agent,
        "query_regulatory_documents",
        lambda query, top_k, include_citations: {
            "question": query,
            "answer": "Maintain transaction monitoring controls.",
            "findings": [
                {
                    "text": "Maintain transaction monitoring controls.",
                    "source": "guidance.pdf",
                    "organization": "RBI",
                    "page": 3,
                }
            ],
            "sources": ["guidance.pdf"],
        },
    )

    result = ComplianceAgent().search("What controls apply?", top_k=1)

    assert result["findings"][0]["source"] == "guidance.pdf"
    assert result["findings"][0]["page"] == 3
    assert "Maintain transaction monitoring controls" in result["answer"]


def test_finance_agent_calculates_ratios_and_reports_missing_fields():
    result = FinanceAgent().analyze(
        {
            "net_income": 10,
            "revenue": 100,
            "total_liabilities": 40,
            "total_assets": 80,
        }
    )

    assert result["ratios"]["net_profit_margin"] == pytest.approx(0.1)
    assert result["ratios"]["debt_to_assets"] == pytest.approx(0.5)
    assert result["ratios"]["current_ratio"] is None
    assert result["missing_inputs"]["current_ratio"] == ["current_assets", "current_liabilities"]


def test_fraud_agent_delegates_to_existing_investigation(monkeypatch):
    expected = {"transaction_id": "T-1", "model": {"risk_level": "LOW"}}
    monkeypatch.setattr(fraud_agent, "investigate_transaction", lambda transaction: expected)

    assert FraudAgent().investigate({"transaction_id": "T-1"}) is expected


def test_risk_agent_uses_artifact_feature_contract():
    agent = RiskAgent(model_path="unused.pkl")
    result = agent.assess(
        {"income": 1000, "age": 40, "ignored": "extra"},
        artifact={
            "model": FakeCreditModel(),
            "feature_columns": ["income", "age"],
            "dataset": "test credit model",
            "target": "default",
        },
    )

    assert result["default_probability"] == pytest.approx(0.75)
    assert result["predicted_class"] == 1
    with pytest.raises(ValueError, match="Missing required credit-risk fields: age"):
        agent.assess(
            {"income": 1000},
            artifact={"model": FakeCreditModel(), "feature_columns": ["income", "age"]},
        )


def test_report_agent_preserves_sources_and_model_signal():
    result = ReportAgent().generate(
        {
            "compliance": {
                "findings": [{"source": "RBI.pdf", "page": 3, "text": "Monitor unusual transfers."}]
            },
            "fraud": {"risk_level": "HIGH", "report": "Review this transaction."},
        }
    )

    assert "RBI.pdf, page 3" in result["report"]
    assert "Risk Level: HIGH" in result["report"]
    assert "not proof" in result["report"]


def test_supervisor_routes_fraud_and_question_requests():
    expected_fraud = {"transaction_id": "T-2"}

    class FakeFraudAgent:
        def investigate(self, transaction):
            return expected_fraud

    class FakeComplianceAgent:
        def search(self, question, *, top_k, include_citations=True):
            return {"question": question, "top_k": top_k, "include_citations": include_citations}

    supervisor = SupervisorAgent(
        fraud_agent=FakeFraudAgent(),
        compliance_agent=FakeComplianceAgent(),
    )

    assert supervisor.run({"task": "fraud", "transaction": {"transaction_id": "T-2"}}) is expected_fraud
    assert supervisor.run({"question": "KYC requirements?", "top_k": 3}) == {
        "question": "KYC requirements?",
        "top_k": 3,
        "include_citations": True,
    }
