from __future__ import annotations

import json
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from src.services import risk_investigation as risk


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
    "transaction_id": "T2",
    "step": 25,
    "type": "CASH_OUT",
    "amount": 10,
    "oldbalanceOrg": 10,
    "newbalanceOrig": 0,
    "oldbalanceDest": 0,
    "newbalanceDest": 10,
}


def _install_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


class FakeModel:
    classes_ = [0, 1]

    def __init__(self, probabilities=(0.8, 0.2)):
        self.probabilities = probabilities

    def predict_proba(self, features):
        assert list(features.columns) == FEATURE_COLUMNS
        return [self.probabilities]


def _artifact(score=0.2):
    return {
        "model": FakeModel((1 - score, score)),
        "feature_columns": FEATURE_COLUMNS,
        "threshold": 0.5,
    }


def test_artifact_loading_and_feature_frame_validation(tmp_path):
    import pickle

    path = tmp_path / "artifact.pkl"
    path.write_bytes(pickle.dumps(_artifact()))
    assert risk.load_model_artifact(path)["feature_columns"] == FEATURE_COLUMNS
    with pytest.raises(FileNotFoundError):
        risk.load_model_artifact(tmp_path / "missing.pkl")
    invalid = tmp_path / "invalid.pkl"
    invalid.write_bytes(pickle.dumps({"model": object()}))
    with pytest.raises(ValueError, match="must contain"):
        risk.load_model_artifact(invalid)

    with pytest.raises(ValueError, match="Unsupported transaction type"):
        risk.build_feature_frame({**TRANSACTION, "type": "OTHER"}, FEATURE_COLUMNS)
    for key, value, message in (
        ("amount", "nan", "finite numbers"),
        ("amount", -1, "non-negative"),
        ("step", 1.5, "must be an integer"),
    ):
        with pytest.raises(ValueError, match=message):
            risk.build_feature_frame({**TRANSACTION, key: value}, FEATURE_COLUMNS)
    with pytest.raises(ValueError, match="unsupported PaySim features"):
        risk.build_feature_frame(TRANSACTION, ["unknown"])
    zero_origin = risk.build_feature_frame(
        {**TRANSACTION, "oldbalanceOrg": 0}, ["amount_to_origin_balance"]
    )
    assert zero_origin.iloc[0, 0] == 0


def test_shap_explanations_select_fraud_class_and_validate_shape(monkeypatch):
    class Explanation:
        values = np.array([[[0.1, 0.5], [0.2, -0.4], [0.3, 0.0], [0.4, -0.2]]])

    _install_module(
        monkeypatch,
        "shap",
        TreeExplainer=lambda model: lambda features: Explanation(),
    )
    features = risk.build_feature_frame(TRANSACTION, FEATURE_COLUMNS[:4])
    drivers = risk.explain_with_shap(object(), features)
    assert [item["feature"] for item in drivers] == ["step", "hour", "amount"]
    assert drivers[0]["direction"] == "increases"
    assert drivers[1]["direction"] == "decreases"
    class BadExplanation:
        values = np.array([[0.1]])

    _install_module(
        monkeypatch,
        "shap",
        TreeExplainer=lambda model: lambda data: BadExplanation(),
    )
    with pytest.raises(ValueError, match="do not match"):
        risk.explain_with_shap(object(), features)


def test_risk_report_formatting_and_retrieval_helpers(monkeypatch):
    evidence = risk._format_evidence([
        {
            "text": "mapping evidence",
            "metadata": {"source": "policy.pdf", "page": 0},
        },
        SimpleNamespace(
            page_content="x" * 2100,
            metadata={"file_path": "RBI/guidance.pdf", "organization": "RBI"},
        ),
    ])
    assert evidence[0]["source"] == "policy.pdf"
    assert evidence[0]["page"] == 1
    assert evidence[1]["source"] == "RBI/guidance.pdf"
    assert len(evidence[1]["text"]) == 2000
    assert risk._json_compatible(
        {"numpy": np.int64(2), "array": np.array([1, 2]), "tuple": (np.float64(3),)}
    ) == {"numpy": 2, "array": [1, 2], "tuple": [3.0]}
    query = risk.build_regulatory_query(TRANSACTION, 0.1234, [])
    assert "no dominant SHAP drivers" in query
    assert "0.1234" in risk.build_regulatory_query(
        TRANSACTION, 0.1234, [{"feature": str(i)} for i in range(7)]
    )
    assert risk._usable_generated_summary("  A grounded analyst summary.  ") == (
        "A grounded analyst summary."
    )
    for text in ("short", "x" * 401, '{"feature": "x"}', "Top model factors:"):
        assert risk._usable_generated_summary(text) is None

    context = {
        "transaction": TRANSACTION,
        "model": {
            "risk_level": "LOW",
            "fraud_risk_score": 0.2,
            "threshold": 0.5,
        },
        "shap_drivers": [],
        "regulatory_evidence": [],
    }
    report = risk._render_investigation_report(context, None)
    assert "No SHAP factors" in report
    assert "evidence is insufficient" in report
    assert "below its stored threshold" in report
    assert "T2" in report
    report_with_summary = risk._render_investigation_report(
        {**context, "model": {**context["model"], "risk_level": "HIGH"}},
        "Analyst summary.",
    )
    assert "Analyst summary." in report_with_summary


def test_investigation_uses_retriever_and_reports_generation_errors():
    retrieved = []
    result = risk.investigate_transaction(
        TRANSACTION,
        artifact=_artifact(0.2),
        retrieve=lambda query: retrieved.append(query) or [
            {"page_content": "guidance", "metadata": {"source_file": "RBI.pdf", "page": 0}}
        ],
        explain=lambda model, frame: [],
        generate_report=lambda context: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert len(retrieved) == 1
    assert result["model"]["risk_level"] == "BELOW_MODEL_THRESHOLD"
    assert result["human_review_required"] is False
    assert result["evidence"][0]["page"] == 1
    assert "not proof" in result["report"]
    assert result["report_summary"] is None
    assert result["report_generation_warning"].startswith("Report model unavailable")

    with pytest.raises(ValueError, match="does not contain class 1"):
        risk.investigate_transaction(
            TRANSACTION,
            artifact={
                "model": SimpleNamespace(
                    classes_=[0], predict_proba=lambda frame: [[1.0]]
                ),
                "feature_columns": FEATURE_COLUMNS,
            },
            documents=[],
            explain=lambda *args: [],
            generate_report=lambda context: "Valid generated text for this case.",
        )
    with pytest.raises(ValueError, match="RISK_REPORT_PROVIDER"):
        import os

        old = os.environ.get("RISK_REPORT_PROVIDER")
        os.environ["RISK_REPORT_PROVIDER"] = "unknown"
        try:
            risk.investigate_transaction(
                TRANSACTION,
                artifact=_artifact(),
                documents=[],
                explain=lambda *args: [],
            )
        finally:
            if old is None:
                os.environ.pop("RISK_REPORT_PROVIDER", None)
            else:
                os.environ["RISK_REPORT_PROVIDER"] = old


def test_ollama_report_serializes_context_and_rejects_bad_response(monkeypatch):
    captured = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "Grounded summary"}}

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test/")
    monkeypatch.setenv("OLLAMA_MODEL", "tiny")
    monkeypatch.setattr(
        risk.requests,
        "post",
        lambda url, **kwargs: captured.append((url, kwargs)) or Response(),
    )
    context = {"number": np.int64(3)}
    assert risk.generate_ollama_report(context) == "Grounded summary"
    assert captured[0][0] == "http://ollama.test/api/chat"
    assert json.loads(captured[0][1]["json"]["messages"][1]["content"]) == {
        "number": 3
    }

    class BadResponse(Response):
        def json(self):
            return {}

    monkeypatch.setattr(risk.requests, "post", lambda *args, **kwargs: BadResponse())
    with pytest.raises(RuntimeError, match="unexpected chat response"):
        risk.generate_ollama_report({})


def test_regulatory_indexing_html_faiss_and_pinecone_paths(monkeypatch, tmp_path):
    class FakeDocument:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    class FakeSoup:
        def __init__(self, content, features):
            self.content = content

        def get_text(self, separator):
            return "regulatory guidance"

    class FakeSplitter:
        def __init__(self, **kwargs):
            assert kwargs["chunk_size"] == 1000

        def split_documents(self, documents):
            return documents

    class FakeStore:
        def __init__(self):
            self.saved = None
            self.added = None

        def save_local(self, path):
            self.saved = path

        def add_documents(self, docs, ids=None):
            self.added = (docs, ids)

    store = FakeStore()
    _install_module(monkeypatch, "bs4", BeautifulSoup=FakeSoup)
    _install_module(monkeypatch, "langchain_core", documents=types.SimpleNamespace(Document=FakeDocument))
    _install_module(monkeypatch, "langchain_core.documents", Document=FakeDocument)
    _install_module(monkeypatch, "langchain_text_splitters", RecursiveCharacterTextSplitter=FakeSplitter)

    class FakeFAISS:
        @classmethod
        def from_documents(cls, docs, embeddings):
            store.docs = docs
            return store

    _install_module(
        monkeypatch,
        "langchain_community",
        document_loaders=types.SimpleNamespace(PyPDFLoader=object),
        vectorstores=types.SimpleNamespace(FAISS=FakeFAISS),
    )
    _install_module(monkeypatch, "langchain_community.document_loaders", PyPDFLoader=object)
    _install_module(monkeypatch, "langchain_community.vectorstores", FAISS=FakeFAISS)
    monkeypatch.setattr(risk, "_build_embeddings", lambda: "fake-embedding")
    monkeypatch.setenv("RAG_DOCUMENT_ORGANIZATIONS", "RBI")
    monkeypatch.setenv("RAG_VECTOR_BACKEND", "faiss")
    monkeypatch.setenv("LOCAL_VECTOR_STORE_PATH", str(tmp_path / "index"))
    (tmp_path / "RBI").mkdir()
    (tmp_path / "RBI" / "guidance.html").write_text("<p>rule</p>", encoding="utf-8")
    (tmp_path / "Other").mkdir()
    (tmp_path / "Other" / "ignored.html").write_text("ignored", encoding="utf-8")
    counts = risk.index_regulatory_documents(tmp_path)
    assert counts == {"documents": 1, "chunks": 1}
    assert store.saved == str(tmp_path / "index")
    assert store.docs[0].metadata["organization"] == "RBI"

    class FakePineconeStore:
        @classmethod
        def from_existing_index(cls, index_name, embedding):
            return store

    _install_module(
        monkeypatch,
        "langchain_pinecone",
        PineconeVectorStore=FakePineconeStore,
    )
    monkeypatch.setenv("RAG_VECTOR_BACKEND", "pinecone")
    monkeypatch.setenv("PINECONE_API_KEY", "local-test-key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")
    assert risk.index_regulatory_documents(tmp_path) == {"documents": 1, "chunks": 1}
    assert store.added[0][0].page_content == store.docs[0].page_content
    assert len(store.added[1][0]) == 64

    monkeypatch.setenv("RAG_VECTOR_BACKEND", "invalid")
    with pytest.raises(ValueError, match="RAG_VECTOR_BACKEND"):
        risk.index_regulatory_documents(tmp_path)
    with pytest.raises(ValueError, match="No PDF or HTML"):
        risk.index_regulatory_documents(tmp_path / "missing")


def test_regulatory_retrieval_backends_and_lazy_local_build(monkeypatch, tmp_path):
    searches = []
    expected = ["evidence"]

    class Store:
        def similarity_search(self, query, k):
            searches.append((query, k))
            return expected

    class FakeFAISS:
        @classmethod
        def load_local(cls, path, embeddings, allow_dangerous_deserialization):
            assert allow_dangerous_deserialization is True
            return Store()

    _install_module(
        monkeypatch,
        "langchain_community",
        vectorstores=types.SimpleNamespace(FAISS=FakeFAISS),
    )
    _install_module(monkeypatch, "langchain_community.vectorstores", FAISS=FakeFAISS)
    monkeypatch.setattr(risk, "_build_embeddings", lambda: "embed")
    local_path = tmp_path / "index"
    monkeypatch.setenv("LOCAL_VECTOR_STORE_PATH", str(local_path))
    build_calls = []
    monkeypatch.setattr(risk, "index_regulatory_documents", lambda: build_calls.append(True))
    assert risk.retrieve_local_faiss_evidence(" query ", 3) == expected
    assert build_calls == [True]
    assert searches == [(" query ", 3)]

    class PineconeStore:
        @classmethod
        def from_existing_index(cls, index_name, embedding):
            return Store()

    _install_module(monkeypatch, "langchain_pinecone", PineconeVectorStore=PineconeStore)
    with pytest.raises(RuntimeError, match="PINECONE_API_KEY"):
        risk.retrieve_pinecone_evidence("q")
    monkeypatch.setenv("PINECONE_API_KEY", "test")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "index")
    assert risk.retrieve_pinecone_evidence("q", 2) == expected
    monkeypatch.setenv("RAG_VECTOR_BACKEND", "pinecone")
    assert risk.retrieve_regulatory_evidence("q") == expected
    monkeypatch.setenv("RAG_VECTOR_BACKEND", "unknown")
    with pytest.raises(ValueError, match="RAG_VECTOR_BACKEND"):
        risk.retrieve_regulatory_evidence("q")
