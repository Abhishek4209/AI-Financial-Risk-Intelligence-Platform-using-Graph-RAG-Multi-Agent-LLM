from types import SimpleNamespace

import numpy as np
import pytest

from src.embeddings.cache import EmbeddingCache
from src.evaluation.llm_metrics import evaluate_answer
from src.evaluation.retrieval_metrics import evaluate_retrieval
from src.graph_rag.graph_builder import build_entity_graph
from src.ingestion.parser import parse_file
from src.llm.guardrails import validate_grounded_response
from src.llm.response_generator import generate_grounded_response
from src.ml_models.fraud_detection import predict_fraud
from src.preprocessing.chunking import chunk_text
from src.preprocessing.cleaner import clean_text
from src.retriever.bm25 import BM25Retriever
from src.retriever.hybrid_search import reciprocal_rank_fusion
from src.retriever.reranker import rerank_documents
from src.utils.helpers import json_safe
from src.utils.validators import validate_paysim_transaction
from src.vectordb.pinecone import PineconeDocumentStore


TRANSACTION = {
    "transaction_id": "UNIT-1",
    "step": 49,
    "type": "TRANSFER",
    "amount": 850000,
    "oldbalanceOrg": 900000,
    "newbalanceOrig": 50000,
    "oldbalanceDest": 10000,
    "newbalanceDest": 860000,
}


class FakeFraudModel:
    classes_ = [0, 1]

    def predict_proba(self, frame):
        assert len(frame) == 1
        return [[0.8, 0.2]]


def test_predict_fraud_uses_model_artifact_and_returns_score():
    result = predict_fraud(
        TRANSACTION,
        artifact={
            "model": FakeFraudModel(),
            "feature_columns": ["amount", "type_TRANSFER"],
            "threshold": 0.15,
        },
    )

    assert result["transaction_id"] == "UNIT-1"
    assert result["fraud_risk_score"] == pytest.approx(0.2)
    assert result["risk_level"] == "HIGH"


def test_csv_parser_preserves_rows_and_metadata(tmp_path):
    source = tmp_path / "transactions.csv"
    source.write_text("id,amount\nT-1,12.5\nT-2,9\n", encoding="utf-8")

    documents = parse_file(source)

    assert len(documents) == 2
    assert documents[0].metadata["row_number"] == 2
    assert documents[0].metadata["record"]["id"] == "T-1"
    assert "amount: 12.5" in documents[0].page_content


def test_pinecone_store_upserts_and_retrieves_langchain_documents():
    class FakeEmbedding:
        def embed_documents(self, texts):
            return [[0.1, 0.2, 0.3] for _ in texts]

        def embed_query(self, text):
            return [0.1, 0.2, 0.3]

    class FakeIndex:
        def upsert(self, *, vectors, namespace=None):
            self.vectors = vectors
            self.namespace = namespace

        def query(self, **kwargs):
            return {"matches": [{"metadata": self.vectors[0]["metadata"]}]}

    index = FakeIndex()
    store = PineconeDocumentStore(index, FakeEmbedding(), namespace="regulations")
    document = SimpleNamespace(
        page_content="Monitor suspicious transactions.",
        metadata={"source_file": "guide.pdf", "custom": {"section": 2}},
    )

    assert store.add_documents([document], ids=["stable-id"]) == ["stable-id"]
    retrieved = store.similarity_search("transaction monitoring", k=1)

    assert index.namespace == "regulations"
    assert index.vectors[0]["metadata"]["custom"] == '{"section": 2}'
    assert retrieved[0].page_content == "Monitor suspicious transactions."
    assert retrieved[0].metadata["source_file"] == "guide.pdf"


def test_pinecone_store_batches_large_upserts(monkeypatch):
    class FakeEmbedding:
        def embed_documents(self, texts):
            return [[0.1, 0.2] for _ in texts]

    class FakeIndex:
        def __init__(self):
            self.batch_sizes = []

        def upsert(self, *, vectors, namespace=None):
            self.batch_sizes.append(len(vectors))

    index = FakeIndex()
    store = PineconeDocumentStore(index, FakeEmbedding())
    documents = [SimpleNamespace(page_content=f"document {i}", metadata={}) for i in range(130)]

    assert len(store.add_documents(documents, ids=[str(i) for i in range(130)])) == 130
    assert index.batch_sizes == [64, 64, 2]


def test_vector_backend_defaults_to_pinecone_and_requires_explicit_faiss(monkeypatch):
    from src.services.risk_investigation import _selected_vector_backend

    monkeypatch.delenv("RAG_VECTOR_BACKEND", raising=False)
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.delenv("PINECONE_INDEX_NAME", raising=False)
    assert _selected_vector_backend() == "pinecone"

    monkeypatch.setenv("RAG_VECTOR_BACKEND", "faiss")
    assert _selected_vector_backend() == "faiss"


def test_email_parser_extracts_subject_sender_and_body(tmp_path):
    source = tmp_path / "notice.eml"
    source.write_text(
        "From: compliance@example.test\nTo: analyst@example.test\n"
        "Subject: Review\nContent-Type: text/plain; charset=utf-8\n\nPlease review this case.\n",
        encoding="utf-8",
    )

    document = parse_file(source)[0]

    assert document.metadata["subject"] == "Review"
    assert document.metadata["sender"] == "compliance@example.test"
    assert "Please review this case." in document.page_content


def test_preprocessing_chunks_and_cleans_text():
    assert clean_text("  Risk\x00   evidence ") == "Risk evidence"
    chunks = chunk_text("one two three four five", chunk_size=12, overlap=3)

    assert " ".join(chunks).replace("  ", " ").startswith("one two")
    assert all(len(chunk) <= 12 for chunk in chunks)


def test_embedding_cache_is_bounded_and_returns_copies():
    cache = EmbeddingCache(max_entries=1)
    cache.set("bge", "query", [1, 2])
    vector = cache.get("bge", "query")
    vector[0] = 9
    assert cache.get("bge", "query") == [1.0, 2.0]
    cache.set("bge", "second", [3])
    assert len(cache) == 1
    assert cache.get("bge", "query") is None


def test_bm25_and_fusion_rank_relevant_items():
    first = SimpleNamespace(page_content="fraud transfer alert", metadata={"chunk_id": "1"})
    second = SimpleNamespace(page_content="customer onboarding requirements", metadata={"chunk_id": "2"})
    ranked = BM25Retriever([first, second]).retrieve("fraud alert", top_k=2)
    fused = reciprocal_rank_fusion([[first, second], [second, first]], top_k=2)

    assert ranked[0][0] is first
    assert len(fused) == 2


def test_cross_encoder_reranks_candidates_by_score():
    first = SimpleNamespace(page_content="old result", metadata={"chunk_id": "1"})
    second = SimpleNamespace(page_content="relevant result", metadata={"chunk_id": "2"})

    class FakeCrossEncoder:
        def predict(self, pairs, show_progress_bar=False):
            assert pairs == [("fraud controls", "old result"), ("fraud controls", "relevant result")]
            return [0.1, 0.9]

    ranked = rerank_documents("fraud controls", [first, second], cross_encoder=FakeCrossEncoder())

    assert ranked == [second, first]


def test_graph_builds_customer_transaction_relationship():
    graph = build_entity_graph(
        [{"customer_id": "C1", "transaction_id": "T1", "merchant_id": "M1"}]
    )

    assert len(graph["nodes"]) == 3
    assert {edge["relation"] for edge in graph["edges"]} == {"made", "paid"}


def test_guardrails_and_surface_metrics():
    rejected = validate_grounded_response("This is a fact.", [])
    accepted = validate_grounded_response("The cited document says review.", ["review"])
    fragment = validate_grounded_response("Resiliency Risk Committee TDRRC", ["Risk Committee"])
    metrics = evaluate_answer("See [RBI 2024]. Review the transfer.", evidence=["Review transfer controls."])

    assert rejected["accepted"] is False
    assert "insufficient" in rejected["text"].lower()
    assert accepted["accepted"] is True
    assert fragment["accepted"] is False
    assert fragment["reason"] == "fragmentary_response"
    assert metrics["citation_count"] == 1
    assert metrics["evidence_token_overlap"] > 0


def test_grounded_response_uses_relevant_cited_excerpt_when_llm_output_is_fragmentary():
    class FragmentaryModel:
        def invoke(self, prompt):
            return "Resiliency Risk Committee TDRRC"

    result = generate_grounded_response(
        "What controls monitor suspicious transactions?",
        [
            {
                "text": "AML/CFT programs include policies to verify customer identities and monitor and report suspicious transactions.",
                "source": "AmEx annual report",
                "page": 37,
            }
        ],
        model=FragmentaryModel(),
    )

    assert result["answer_type"] == "extractive"
    assert result["answer_accepted"] is True
    assert "monitor and report suspicious transactions" in result["answer"]
    assert result["sources"][0]["source"] == "AmEx annual report"


def test_rag_service_combines_retrieval_groups_and_sources(monkeypatch):
    from src.services import rag_service

    vector_document = SimpleNamespace(
        page_content="Review suspicious transactions.",
        metadata={"source_file": "RBI.pdf", "organization": "RBI", "page": 0},
    )
    graph_document = SimpleNamespace(
        page_content="organization: American Express; issued_by document: annual report",
        metadata={"source_file": "Neo4j knowledge graph", "entity_id": "organization:American Express"},
    )
    monkeypatch.setattr(
        rag_service,
        "retrieve_regulatory_evidence",
        lambda query, top_k: [vector_document, graph_document],
    )
    monkeypatch.setattr(
        rag_service,
        "generate_grounded_response",
        lambda question, evidence: {"question": question, "answer": "Review suspicious transactions.", "answer_accepted": True},
    )

    result = rag_service.query_regulatory_documents("How should suspicious transactions be handled?")

    assert result["retrieval"] == {"vector_bm25": 1, "graph": 1}
    assert result["sources"][0]["page"] == 1
    assert result["sources"][1]["source"] == "Neo4j knowledge graph"


def test_retrieval_metrics_and_json_safety():
    scores = evaluate_retrieval(["a", "b", "c"], ["b", "c"])
    safe = json_safe({"timestamp": np.int64(3), "invalid": float("nan")})

    assert scores["recall"] == 1.0
    assert scores["mrr"] == 0.5
    assert safe == {"timestamp": 3, "invalid": None}


def test_transaction_validator_rejects_fractional_step():
    transaction = {**TRANSACTION, "step": 1.5}

    with pytest.raises(ValueError, match="step must be an integer"):
        validate_paysim_transaction(transaction)
