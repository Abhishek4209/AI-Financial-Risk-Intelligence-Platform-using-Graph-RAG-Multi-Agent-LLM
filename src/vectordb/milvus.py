"""Milvus vector store backend; optional for large-scale deployments."""
from __future__ import annotations
import os
from typing import Any
from src.embeddings.embedding_model import get_embedding_model
DEFAULT_COLLECTION = "financial_risk_documents"
def _connection_args() -> dict[str, str]:
    uri = os.getenv("MILVUS_URI")
    if not uri:
        raise RuntimeError("Set MILVUS_URI to connect to a Milvus instance")
    args = {"uri": uri}
    token = os.getenv("MILVUS_TOKEN")
    if token:
        args["token"] = token
    return args
def _store(collection_name: str | None) -> Any:
    try:
        from langchain_milvus import Milvus
    except ImportError as exc:
        raise RuntimeError("Install langchain-milvus and pymilvus to use the Milvus backend") from exc
    return Milvus(
        embedding_function=get_embedding_model(),
        collection_name=collection_name or os.getenv("MILVUS_COLLECTION", DEFAULT_COLLECTION),
        connection_args=_connection_args(),
    )
def add_documents(documents: list[Any], *, collection_name: str | None = None) -> int:
    if not documents:
        return 0
    store = _store(collection_name)
    store.add_documents(documents)
    return len(documents)
def similarity_search(query: str, *, top_k: int = 5, collection_name: str | None = None) -> list[Any]:
    store = _store(collection_name)
    return store.similarity_search(query, k=top_k)
