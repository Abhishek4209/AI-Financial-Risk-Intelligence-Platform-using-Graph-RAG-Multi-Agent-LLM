
"""Local FAISS vector store, matching the RAG and RAG_Experiments notebooks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.embeddings.embedding_model import get_embedding_model
from src.utils.constants import VECTOR_STORE_ROOT


def _store_path(path: str | Path | None = None) -> Path:
    """Resolve the configured local FAISS index directory."""
    return Path(
        path
        or os.getenv("LOCAL_VECTOR_STORE_PATH", str(VECTOR_STORE_ROOT))
    )


def build_faiss_store(
    documents: list[Any],
    *,
    path: str | Path | None = None,
) -> Any:
    """Create and persist a FAISS index from documents."""
    try:
        from langchain_community.vectorstores import FAISS
    except ImportError as exc:
        raise RuntimeError(
            "Install langchain-community and faiss-cpu to build a FAISS index."
        ) from exc

    if not documents:
        raise ValueError("documents must not be empty")

    store = FAISS.from_documents(documents, get_embedding_model())
    store.save_local(str(_store_path(path)))

    return store


def load_faiss_store(
    *,
    path: str | Path | None = None,
) -> Any:
    """Load an existing local FAISS index."""
    try:
        from langchain_community.vectorstores import FAISS
    except ImportError as exc:
        raise RuntimeError(
            "Install langchain-community and faiss-cpu to load a FAISS index."
        ) from exc

    store_path = _store_path(path)

    if not (store_path / "index.faiss").exists():
        raise FileNotFoundError(
            "No FAISS index found at %s; build it first" % store_path
        )

    return FAISS.load_local(
        str(store_path),
        get_embedding_model(),
        allow_dangerous_deserialization=True,
    )


def add_documents_to_faiss(
    documents: list[Any],
    *,
    path: str | Path | None = None,
) -> Any:
    """Add documents to an existing index or create a new one."""
    if not documents:
        return load_faiss_store(path=path)

    store_path = _store_path(path)

    if (store_path / "index.faiss").exists():
        store = load_faiss_store(path=path)
        store.add_documents(documents)
        store.save_local(str(store_path))
        return store

    return build_faiss_store(documents, path=path)


def similarity_search(
    query: str,
    *,
    top_k: int = 5,
    path: str | Path | None = None,
) -> list[Any]:
    """Retrieve the most relevant documents from the local FAISS index."""
    store = load_faiss_store(path=path)
    return store.similarity_search(query, k=top_k)
