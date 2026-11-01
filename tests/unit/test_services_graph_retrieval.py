from __future__ import annotations

import importlib.util
import importlib
import sys
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.graph_rag import graph_builder, graph_query, graph_retriever, neo4j_loader
from src.llm import guardrails
from src.retriever import (
    bm25,
    parent_child,
    query_rewriter,
    reranker,
    self_rag,
)
from src.services import document_service, notification_service, rag_service, report_service
from src import vectordb


def _load_evaluation_module(name: str):
    source = Path(__file__).parents[2] / "src" / "evaluation" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"coverage_tests_{name}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retrieval_metrics = _load_evaluation_module("retrieval_metrics")
llm_metrics = _load_evaluation_module("llm_metrics")
hybrid_search_module = importlib.import_module("src.retriever.hybrid_search")


def _install_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def _doc(text, **metadata):
    return SimpleNamespace(page_content=text, metadata=metadata)


def test_retrieval_metrics_and_llm_quality_proxies():
    retrieved = ["a", "b", "c"]
    relevant = ["b", "c"]
    assert retrieval_metrics.precision_at_k(retrieved, relevant, 2) == 0.5
    assert retrieval_metrics.recall_at_k(retrieved, relevant, 2) == 0.5
    assert retrieval_metrics.mean_reciprocal_rank(retrieved, relevant) == 0.5
    assert retrieval_metrics.ndcg_at_k(retrieved, relevant, 3) > 0
    assert retrieval_metrics.evaluate_retrieval([], [], k=2) == {
        "precision_at_k": 0.0,
        "recall_at_k": 0.0,
        "mrr": 0.0,
        "ndcg_at_k": 0.0,
    }
    for function in (
        lambda: retrieval_metrics.precision_at_k([], [], 0),
        lambda: retrieval_metrics.recall_at_k([], [], 0),
        lambda: retrieval_metrics.ndcg_at_k([], [], 0),
    ):
        with pytest.raises(ValueError, match="k must be at least 1"):
            function()

    scores = llm_metrics.evaluate_llm_response(
        "How to reduce credit risk?",
        "Credit risk controls reduce losses.",
        "Credit risk controls and loss prevention.",
        ["RBI guidance"],
    )
    assert scores["answer_relevance"] > 0
    assert scores["faithfulness_proxy"] > 0
    assert scores["citation_validity"] is False
    assert llm_metrics.citation_validity(
        "According to RBI guidance", ["RBI guidance"]
    )
    assert llm_metrics.citation_validity("Insufficient evidence", [])


def test_guardrails_reject_unusable_or_ungrounded_summaries():
    assert guardrails.usable_summary("Analysts should review the transaction.") == (
        "Analysts should review the transaction."
    )
    for text in ("short", "x" * (guardrails.MAX_LENGTH + 1), '{"feature": 1}', "As an AI, generated text"):
        assert guardrails.usable_summary(text) is None

    assert guardrails.citations_are_grounded("RBI issued controls", ["RBI"])
    assert not guardrails.citations_are_grounded(
        "According to another source", ["RBI"]
    )
    assert guardrails.citations_are_grounded("No sources cited.", ["RBI"])
    assert not guardrails.citations_are_grounded("No pages cited.", [])
    assert not guardrails.citations_are_grounded("Page 2 says so.", [])
    assert guardrails.enforce_insufficient_evidence("answer", [_doc("text")]) == "answer"
    assert "not found" in guardrails.enforce_insufficient_evidence("answer", [])
    assert guardrails.redact_internal_errors(" Traceback: details\nsecond line") == "Traceback: details"
    assert guardrails.redact_internal_errors("  ") == "An internal error occurred."
    assert len(guardrails.redact_internal_errors("x" * 400)) == 300


def test_query_rewriting_and_keyword_extraction():
    expanded = query_rewriter.expand_query("Fraud controls for credit")
    assert expanded[0] == "Fraud controls for credit"
    assert "fraudulent activity controls for credit" in expanded
    assert any("risk management policies" in item for item in expanded)
    assert query_rewriter.expand_query("  ") == []
    assert query_rewriter.extract_keywords("What is AML risk?") == ["aml", "risk"]
    assert query_rewriter.extract_keywords("") == []

    captured = []
    rewritten = query_rewriter.rewrite_query_with_llm(
        "question", lambda prompt: captured.append(prompt) or " precise query "
    )
    assert rewritten == "precise query"
    assert "Question: question" in captured[0]
    assert query_rewriter.rewrite_query_with_llm("question", lambda prompt: " ") == "question"
    assert query_rewriter.rewrite_query_with_llm(
        "question", lambda prompt: (_ for _ in ()).throw(RuntimeError("offline"))
    ) == "question"
    assert query_rewriter.rewrite_query_with_llm("", lambda prompt: "unused") == ""


def test_reranker_model_and_deterministic_fallback(monkeypatch):
    documents = [
        _doc("unrelated weather"),
        _doc("fraud prevention controls"),
        _doc("fraud monitoring"),
    ]
    monkeypatch.setattr(
        reranker,
        "_get_cross_encoder",
        lambda name: SimpleNamespace(predict=lambda pairs: [0.1, 0.9, 0.4]),
    )
    assert reranker.rerank("fraud controls", documents, top_k=2) == [
        documents[1],
        documents[2],
    ]
    monkeypatch.setattr(
        reranker,
        "_get_cross_encoder",
        lambda name: SimpleNamespace(predict=lambda pairs: [1]),
    )
    assert reranker.rerank("fraud controls", documents, top_k=2) == [
        documents[1],
        documents[2],
    ]
    assert reranker.rerank("", documents, top_k=2) == documents[:2]
    assert reranker.rerank("fraud", [], top_k=2) == []
    assert reranker._fallback_rerank("   ", documents, 2) == documents[:2]


def test_self_rag_requires_topic_and_action_and_checks_support():
    query = "How should fraud controls be managed?"
    docs = [
        _doc("Fraud prevention controls monitor suspicious transactions."),
        _doc("Fraud appears in this unrelated sentence."),
        _doc("Credit risk mitigation and underwriting controls."),
    ]
    assert self_rag.is_relevant(query, docs[0])
    assert not self_rag.is_relevant(query, docs[1])
    assert not self_rag.is_relevant(query, docs[2])
    assert not self_rag.is_relevant("the and is", docs[0])
    assert self_rag.filter_relevant_documents(query, docs) == [docs[0]]
    assert self_rag.is_relevant("policy credit", _doc("policy credit lending"), min_overlap=2)
    assert self_rag.is_answer_supported(
        "Fraud controls prevent suspicious transactions", [docs[0]], min_overlap=2
    )
    assert not self_rag.is_answer_supported("   ", docs)
    assert not self_rag.is_answer_supported("Fraud controls", [])
    filtered = self_rag.self_rag_filter("zebra volcano", docs)
    assert filtered == {"documents": [], "evidence_sufficient": False}


def test_bm25_and_hybrid_search_rank_documents(monkeypatch):
    documents = [_doc("fraud risk"), _doc("credit lending"), _doc("fraud controls")]

    class FakeIndex:
        def get_scores(self, tokens):
            assert tokens == ["fraud"]
            return [0.5, 0.0, 1.0]

    monkeypatch.setattr(bm25, "build_bm25_index", lambda docs: FakeIndex())
    assert bm25.bm25_search("Fraud", documents, top_k=2) == [
        documents[2],
        documents[0],
    ]
    assert bm25.bm25_search("fraud", [], top_k=1) == []
    with pytest.raises(ValueError, match="at least 1"):
        bm25.bm25_search("fraud", documents, top_k=0)

    monkeypatch.setattr(hybrid_search_module, "build_bm25_index", lambda docs: FakeIndex())
    monkeypatch.setattr(
        hybrid_search_module,
        "vector_search",
        lambda query, top_k: [documents[1], documents[0], documents[2]],
    )
    fused = hybrid_search_module.hybrid_search(
        "fraud", documents, top_k=3, vector_weight=1
    )
    assert fused[0] is documents[1]
    assert hybrid_search_module.hybrid_search("fraud", [], top_k=1) == []
    for kwargs in ({"top_k": 0}, {"vector_weight": -0.1}, {"vector_weight": 1.1}):
        with pytest.raises(ValueError):
            hybrid_search_module.hybrid_search("fraud", documents, **kwargs)


def test_parent_child_index_and_resolution(monkeypatch):
    class FakeDocument:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    _install_module(
        monkeypatch, "langchain_core", documents=SimpleNamespace(Document=FakeDocument)
    )
    _install_module(monkeypatch, "langchain_core.documents", Document=FakeDocument)
    parents, children = parent_child.build_parent_child_index(
        [_doc("one two three four", source="policy")],
        parent_chunk_size=15,
        child_chunk_size=6,
    )
    assert len(parents) == 2
    assert [child.metadata["parent_index"] for child in children] == [0, 0, 0, 1]
    resolved = parent_child.resolve_parents(
        [children[0], children[1], children[-1], _doc("orphan")],
        parents,
    )
    assert resolved == [parents[0], parents[1]]


def test_graph_building_creates_expected_queries(monkeypatch):
    calls = []
    monkeypatch.setattr(graph_builder, "run_query", lambda *args: calls.append(args) or [])
    graph_builder.ensure_constraints()
    graph_builder.upsert_customer("C1")
    graph_builder.upsert_account("A1", "C1", {"currency": "USD"})
    graph_builder.upsert_transaction("T1", "A1", "A2", {"amount": 10})
    graph_builder.upsert_transaction("T2", "A1", None)
    graph_builder.link_document_to_customer("D1", "C1")
    count = graph_builder.build_transaction_graph([
        {"transaction_id": 1, "from_account_id": "A1", "to_account_id": "A2", "amount": 10},
        {"transaction_id": 2, "from_account_id": "A1", "amount": 20},
    ])
    assert len(calls[:4]) == 4
    assert calls[4][1] == {"id": "C1", "properties": {}}
    assert calls[5][1]["properties"] == {"currency": "USD"}
    assert len(calls) == 13
    assert count == 2


def test_graph_queries_and_optional_account_evidence(monkeypatch):
    calls = []
    monkeypatch.setattr(graph_query, "run_query", lambda query, params=None: calls.append((query, params)) or [])
    graph_query.find_connected_customers("C1", max_hops=3)
    graph_query.fan_out_transactions("A1")
    graph_query.fan_in_transactions("A1")
    graph_query.suspicious_transaction_chains("A1", max_hops=5)
    graph_query.customer_documents("C1")
    with pytest.raises(ValueError, match="max_hops"):
        graph_query.find_connected_customers("C1", max_hops=0)
    with pytest.raises(ValueError, match="max_hops"):
        graph_query.suspicious_transaction_chains("A1", max_hops=1)
    assert "$customer_id" in calls[0][0]
    assert calls[0][1] == {"customer_id": "C1"}

    graph_calls = []
    monkeypatch.setattr(graph_retriever, "find_connected_customers", lambda customer: [customer])
    monkeypatch.setattr(graph_retriever, "fan_out_transactions", lambda account: [f"out:{account}"])
    monkeypatch.setattr(graph_retriever, "fan_in_transactions", lambda account: [f"in:{account}"])
    monkeypatch.setattr(graph_retriever, "vector_search", lambda query, top_k: graph_calls.append((query, top_k)) or ["doc"])
    assert graph_retriever.retrieve_graph_evidence("C1") == {"connected_customers": ["C1"]}
    assert graph_retriever.retrieve_graph_evidence("C1", "A1") == {
        "connected_customers": ["C1"],
        "fan_out": ["out:A1"],
        "fan_in": ["in:A1"],
    }
    assert graph_retriever.retrieve_hybrid_evidence("query", "C1", top_k=2)["documents"] == ["doc"]
    assert graph_calls == [("query", 2)]


def test_neo4j_loader_queries_and_connectivity(monkeypatch):
    queries = []

    class FakeResult:
        def __iter__(self):
            return iter([SimpleNamespace(data=lambda: {"value": 2})])

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def run(self, query, parameters):
            queries.append((query, parameters))
            return FakeResult()

    class FakeDriver:
        def session(self):
            return FakeSession()

        def verify_connectivity(self):
            return None

    driver = FakeDriver()
    _install_module(
        monkeypatch,
        "neo4j",
        GraphDatabase=SimpleNamespace(
            driver=lambda uri, auth: (queries.append((uri, auth)) or driver)
        ),
    )
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-only")
    monkeypatch.setenv("NEO4J_USER", "tester")
    neo4j_loader.get_neo4j_driver.cache_clear()
    try:
        assert neo4j_loader.run_query("RETURN 1") == [{"value": 2}]
        assert queries[-1] == ("RETURN 1", {})
        assert neo4j_loader.verify_connectivity()
        assert queries[0] == ("bolt://localhost", ("tester", "test-only"))
    finally:
        neo4j_loader.get_neo4j_driver.cache_clear()


def test_document_ingestion_reports_success_empty_and_unavailable_index(monkeypatch, tmp_path):
    source = tmp_path / "policy.pdf"
    source.touch()
    chunks = [_doc("policy text")]
    monkeypatch.setattr(document_service, "build_document_chunks", lambda paths, **kwargs: chunks)
    monkeypatch.setattr(document_service, "index_documents", lambda docs, backend=None: len(docs))
    result = document_service.ingest_document(source, document_id="D1", backend="faiss")
    assert result["status"] == "indexed"
    assert result["chunks_indexed"] == 1
    assert result["document_id"] == "D1"

    monkeypatch.setattr(document_service, "build_document_chunks", lambda *args, **kwargs: [])
    empty = document_service.ingest_document(source, document_id="D2")
    assert empty["status"] == "failed"
    assert empty["error"]

    monkeypatch.setattr(document_service, "build_document_chunks", lambda *args, **kwargs: chunks)
    monkeypatch.setattr(
        document_service,
        "index_documents",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("backend unavailable")),
    )
    assert document_service.ingest_document(source)["status"] == "chunked_only"
    with pytest.raises(FileNotFoundError):
        document_service.ingest_document(tmp_path / "missing.pdf")


def test_report_rendering_and_record_fields():
    report = report_service.render_investigation_report({
        "model": {"risk_level": "HIGH"},
        "evidence": [{"source": "RBI.pdf", "page": 2, "text": "control " * 80}],
        "explanation": "Review the transfer.",
        "human_review_required": True,
    })
    assert "risk level: HIGH" in report
    assert "RBI.pdf, page 2" in report
    assert "Review the transfer." in report
    assert "does not constitute an automated" in report
    assert len(report.split("control ")[1]) <= 300
    empty_report = report_service.render_investigation_report({})
    assert "No model prediction" in empty_report
    assert "evidence is insufficient" in empty_report
    assert "No analyst-support explanation" in empty_report
    record = report_service.build_report_record(None, "case", "body")
    assert record["case_id"] is None
    assert record["generated_by"] == "report_agent"
    datetime.fromisoformat(record["created_at"])


def test_notifications_are_optional_and_webhook_failures_are_logged(monkeypatch):
    logged = []
    monkeypatch.setattr(notification_service.logger, "info", lambda *args: logged.append(args))
    monkeypatch.setattr(notification_service.logger, "warning", lambda *args: logged.append(args))
    notification_service.notify_case_created({"id": "C1", "severity": "high"})
    notification_service.notify_high_risk_prediction({"task": "fraud", "probability": 0.9})
    assert len(logged) == 2

    monkeypatch.setenv("NOTIFICATION_WEBHOOK_URL", "https://hooks.invalid/test")
    post_calls = []
    _install_module(
        monkeypatch,
        "requests",
        post=lambda *args, **kwargs: post_calls.append((args, kwargs)),
    )
    notification_service._send_webhook("case_created", {"id": "C1"})
    assert post_calls[0][1]["json"] == {
        "event": "case_created",
        "data": {"id": "C1"},
    }
    _install_module(
        monkeypatch,
        "requests",
        post=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    notification_service._send_webhook("case_created", {})
    assert len(logged) == 3


def test_rag_service_short_circuits_missing_evidence_and_generates_when_grounded(monkeypatch):
    first = _doc("Fraud prevention controls monitor unusual transfers.")
    monkeypatch.setattr(rag_service, "expand_query", lambda query: [query, query + " expanded"])
    monkeypatch.setattr(
        rag_service,
        "vector_search",
        lambda query, top_k, backend=None: [first, _doc(first.page_content), _doc("Credit unrelated")],
    )
    monkeypatch.setattr(
        rag_service,
        "self_rag_filter",
        lambda query, docs: {"documents": docs[:1], "evidence_sufficient": True},
    )
    monkeypatch.setattr(rag_service, "rerank", lambda query, docs, top_k: docs)
    monkeypatch.setattr(
        rag_service,
        "generate_answer",
        lambda query, docs, provider=None: {"answer": "grounded", "sources": ["RBI"]},
    )
    result = rag_service.answer_question("  fraud policy ", top_k=2, provider="local")
    assert result["answer"] == "grounded"
    assert result["retrieved_count"] == 2
    assert result["filtered_count"] == 1
    assert result["evidence_sufficient"] is True

    monkeypatch.setattr(
        rag_service,
        "self_rag_filter",
        lambda query, docs: {"documents": [], "evidence_sufficient": False},
    )
    insufficient = rag_service.answer_question("fraud policy")
    assert insufficient["grounded"] is True
    assert insufficient["reranked_count"] == 0
    for question, top_k in (("", 5), ("what", 0), ("what", True), (None, 5)):
        with pytest.raises(ValueError):
            rag_service.answer_question(question, top_k=top_k)


def test_vector_database_backend_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(
        vectordb.retrieval,
        "add_documents_to_faiss",
        lambda docs: calls.append(("faiss-add", docs)),
    )
    monkeypatch.setattr(
        vectordb.retrieval,
        "similarity_search",
        lambda query, top_k: calls.append(("faiss-search", query, top_k)) or ["hit"],
    )
    fake_chroma = SimpleNamespace(
        add_documents=lambda docs: calls.append(("chroma-add", docs)) or 7,
        similarity_search=lambda query, top_k: ["chroma"],
    )
    monkeypatch.setitem(vectordb._BACKENDS, "chroma", fake_chroma)
    assert vectordb.index_documents([1], backend="faiss") == 1
    assert vectordb.index_documents([1], backend="chroma") == 7
    assert vectordb.search("query", top_k=3, backend="faiss") == ["hit"]
    assert vectordb.search("query", backend="chroma") == ["chroma"]
    with pytest.raises(ValueError, match="VECTOR_DB_PROVIDER"):
        vectordb.search("query", backend="other")
