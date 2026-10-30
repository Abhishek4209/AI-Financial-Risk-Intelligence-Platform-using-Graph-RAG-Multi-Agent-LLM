"""Vector database backends behind a single provider-neutral interface."""
from __future__ import annotations
import os
from typing import Any
from . import chroma, milvus, pinecone, retrieval
_BACKENDS = {"faiss": retrieval, "chroma": chroma, "milvus": milvus, "pinecone": pinecone}
def _backend(name: str | None):
    selected = (name or os.getenv("VECTOR_DB_PROVIDER", "faiss")).lower()
    if selected not in _BACKENDS:
        raise ValueError("VECTOR_DB_PROVIDER must be one of %s" % sorted(_BACKENDS))
    return _BACKENDS[selected]
def index_documents(documents: list[Any], *, backend: str | None = None) -> int:
    module = _backend(backend)
    if module is retrieval:
        retrieval.add_documents_to_faiss(documents)
        return len(documents)
    return module.add_documents(documents)
def search(query: str, *, top_k: int = 5, backend: str | None = None) -> list[Any]:
    return _backend(backend).similarity_search(query, top_k=top_k)
__all__ = ["index_documents", "search", "chroma", "milvus", "pinecone", "retrieval"]
