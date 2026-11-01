from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.embeddings import embedding_model
from src.vectordb import chroma, milvus, pinecone, retrieval


def _install_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def _doc(text, **metadata):
    return SimpleNamespace(page_content=text, metadata=metadata)


def test_embedding_model_provider_configuration_and_calls(monkeypatch):
    class FakeEmbeddings:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def embed_documents(self, texts):
            return [[float(len(text))] for text in texts]

        def embed_query(self, text):
            return [float(len(text))]

    _install_module(
        monkeypatch,
        "langchain_huggingface",
        HuggingFaceEmbeddings=FakeEmbeddings,
    )
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", "test-embedder")
    monkeypatch.setenv("EMBEDDING_DEVICE", "cpu")
    embedding_model.get_embedding_model.cache_clear()
    try:
        huggingface = embedding_model.get_embedding_model("huggingface")
        assert huggingface.kwargs["model_name"] == "test-embedder"
        assert huggingface.kwargs["encode_kwargs"] == {"normalize_embeddings": True}
        assert embedding_model.embed_texts([]) == []
        assert embedding_model.embed_texts(["a", "abc"]) == [[1.0], [3.0]]
        assert embedding_model.embed_query("abc") == [3.0]
        assert embedding_model.get_embedding_model("huggingface") is huggingface

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            embedding_model.get_embedding_model("openai")

        _install_module(
            monkeypatch,
            "langchain_openai",
            OpenAIEmbeddings=FakeEmbeddings,
        )
        monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
        openai = embedding_model.get_embedding_model("openai", "test-openai")
        assert openai.kwargs["model"] == "test-openai"
        with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
            embedding_model.get_embedding_model("unsupported")
    finally:
        embedding_model.get_embedding_model.cache_clear()


def test_chroma_backend_uses_configured_client(monkeypatch, tmp_path):
    calls = []

    class FakeChroma:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def add_documents(self, documents):
            calls.append(("add", documents))

        def similarity_search(self, query, k):
            calls.append((query, k))
            return ["hit"]

    _install_module(monkeypatch, "langchain_chroma", Chroma=FakeChroma)
    monkeypatch.setattr(chroma, "get_embedding_model", lambda: "embedding")
    monkeypatch.setenv("CHROMA_COLLECTION", "configured")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path))
    assert chroma.add_documents([]) == 0
    assert chroma.add_documents(["doc"], collection_name="explicit") == 1
    assert calls[0] == {
        "collection_name": "explicit",
        "embedding_function": "embedding",
        "persist_directory": str(tmp_path),
    }
    assert chroma.similarity_search("query", top_k=2) == ["hit"]
    assert calls[-1] == ("query", 2)


def test_milvus_connection_and_backend_operations(monkeypatch):
    with pytest.raises(RuntimeError, match="MILVUS_URI"):
        milvus._connection_args()
    monkeypatch.setenv("MILVUS_URI", "http://localhost:19530")
    assert milvus._connection_args() == {"uri": "http://localhost:19530"}
    monkeypatch.setenv("MILVUS_TOKEN", "test-token")
    assert milvus._connection_args()["token"] == "test-token"

    calls = []

    class FakeMilvus:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def add_documents(self, documents):
            calls.append(("add", documents))

        def similarity_search(self, query, k):
            return [(query, k)]

    _install_module(monkeypatch, "langchain_milvus", Milvus=FakeMilvus)
    monkeypatch.setattr(milvus, "get_embedding_model", lambda: "embedding")
    assert milvus.add_documents([]) == 0
    assert milvus.add_documents(["doc"], collection_name="records") == 1
    assert calls[0]["connection_args"] == {
        "uri": "http://localhost:19530",
        "token": "test-token",
    }
    assert milvus.similarity_search("query", top_k=4) == [("query", 4)]


def test_pinecone_backend_generates_chunk_ids_and_validates_credentials(monkeypatch):
    with pytest.raises(RuntimeError, match="PINECONE_API_KEY"):
        pinecone._index_name()
    monkeypatch.setenv("PINECONE_API_KEY", "local-test-key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "risk")
    assert pinecone._index_name() == "risk"
    first = _doc("guidance", file_path=r"C:\RBI\policy.pdf", page=2)
    second = _doc("guidance", file_path=r"C:\RBI\policy.pdf", page=2)
    assert pinecone._chunk_id(first) == pinecone._chunk_id(second)
    assert pinecone._chunk_id(first) != pinecone._chunk_id(
        _doc("guidance", file_path="/RBI/policy.pdf", page=2)
    )

    calls = []

    class FakeStore:
        def add_documents(self, docs, ids):
            calls.append((docs, ids))

        def similarity_search(self, query, k):
            return [(query, k)]

    _install_module(
        monkeypatch,
        "langchain_pinecone",
        PineconeVectorStore=SimpleNamespace(
            from_existing_index=lambda index_name, embedding: FakeStore()
        ),
    )
    monkeypatch.setattr(pinecone, "get_embedding_model", lambda: "embedding")
    assert pinecone.add_documents([]) == 0
    assert pinecone.add_documents([first, second]) == 2
    assert calls[0][0] == [first, second]
    assert calls[0][1] == [pinecone._chunk_id(first), pinecone._chunk_id(second)]
    assert pinecone.similarity_search("query", top_k=3) == [("query", 3)]


def test_faiss_document_fingerprints_and_deduplication():
    original = _doc(
        "same text",
        source_file="12345678-1234-1234-1234-123456789abc_policy.pdf",
        page=1,
    )
    normalized = _doc("same text", source_file="policy.pdf", page=1)
    different_page = _doc("same text", source_file="policy.pdf", page=2)
    assert retrieval._document_fingerprint(original) == retrieval._document_fingerprint(normalized)
    assert retrieval._document_fingerprint(original) != retrieval._document_fingerprint(different_page)
    assert retrieval._filter_new_documents(
        [original, normalized, different_page],
        {retrieval._document_fingerprint(original)},
    ) == [different_page]
    assert retrieval._existing_fingerprints(
        SimpleNamespace(docstore=SimpleNamespace(_dict={"doc": original}))
    ) == {retrieval._document_fingerprint(original)}
    assert retrieval._existing_fingerprints(object()) == set()


def test_faiss_build_load_add_and_similarity_search(monkeypatch, tmp_path):
    calls = []
    documents = [_doc("first", source_file="a.pdf", page=1)]

    class FakeStore:
        def __init__(self):
            self.docstore = SimpleNamespace(_dict={})
            self.added = []

        def save_local(self, path):
            calls.append(("save", path))

        def add_documents(self, docs):
            self.added.extend(docs)
            calls.append(("add", docs))

        def similarity_search_with_score(self, query, k):
            return [(documents[0], 0.125)]

    store = FakeStore()

    class FakeFAISS:
        @classmethod
        def from_documents(cls, docs, embedding):
            calls.append(("build", docs, embedding))
            return store

        @classmethod
        def load_local(cls, path, embedding, allow_dangerous_deserialization):
            calls.append(("load", path, embedding, allow_dangerous_deserialization))
            return store

    _install_module(
        monkeypatch,
        "langchain_community",
        vectorstores=SimpleNamespace(FAISS=FakeFAISS),
    )
    _install_module(monkeypatch, "langchain_community.vectorstores", FAISS=FakeFAISS)
    monkeypatch.setattr(retrieval, "get_embedding_model", lambda: "embedding")
    with pytest.raises(ValueError, match="documents must not be empty"):
        retrieval.build_faiss_store([])
    assert retrieval.build_faiss_store(documents, path=tmp_path) is store
    assert calls[0] == ("build", documents, "embedding")
    assert calls[1] == ("save", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="No FAISS index"):
        retrieval.load_faiss_store(path=tmp_path)

    (tmp_path / "index.faiss").touch()
    assert retrieval.load_faiss_store(path=tmp_path) is store
    store.docstore._dict = {"existing": documents[0]}
    assert retrieval.add_documents_to_faiss(
        [_doc("first", source_file="a.pdf", page=1)], path=tmp_path
    ) is store
    assert not store.added
    new_document = _doc("second", source_file="b.pdf", page=1)
    assert retrieval.add_documents_to_faiss([new_document], path=tmp_path) is store
    assert store.added == [new_document]
    assert retrieval.add_documents_to_faiss([], path=tmp_path) is store

    with pytest.raises(ValueError, match="query must not be empty"):
        retrieval.similarity_search_with_scores("  ", path=tmp_path)
    with pytest.raises(ValueError, match="top_k must be at least 1"):
        retrieval.similarity_search_with_scores("query", top_k=0, path=tmp_path)
    scored = retrieval.similarity_search_with_scores(" query ", path=tmp_path)
    assert scored == [(documents[0], 0.125)]
    assert retrieval.similarity_search("query", path=tmp_path) == [documents[0]]
