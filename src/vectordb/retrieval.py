
"""Local FAISS vector store for the financial risk RAG pipeline."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from src.embeddings.embedding_model import get_embedding_model
from src.utils.constants import VECTOR_STORE_ROOT


def _store_path(path: str | Path | None = None) -> Path:
    """Resolve the configured local FAISS index directory."""
    configured_path = path or os.getenv(
        "LOCAL_VECTOR_STORE_PATH",
        str(VECTOR_STORE_ROOT),
    )
    return Path(configured_path)


def _document_fingerprint(document: Any) -> str:
    """Create a stable fingerprint for a document chunk."""
    content = str(getattr(document, "page_content", ""))

    metadata = getattr(document, "metadata", {}) or {}

    source = str(
        metadata.get("source_file")
        or metadata.get("file_path")
        or metadata.get("source")
        or ""
    )

    # Normalize Windows and Unix paths.
    source = source.replace("\\", "/").split("/")[-1]

    # Remove a UUID prefix from uploaded filenames.
    source = re.sub(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}_",
        "",
        source,
    )

    page = str(metadata.get("page", ""))

    fingerprint_data = f"{source}|{page}|{content}"

    return hashlib.sha256(
        fingerprint_data.encode("utf-8")
    ).hexdigest()


def _existing_fingerprints(store: Any) -> set[str]:
    """Collect fingerprints for documents already stored in FAISS."""
    fingerprints: set[str] = set()

    docstore = getattr(store, "docstore", None)
    documents = getattr(docstore, "_dict", {})

    for document in documents.values():
        fingerprints.add(_document_fingerprint(document))

    return fingerprints


def _filter_new_documents(
    documents: list[Any],
    existing_fingerprints: set[str],
) -> list[Any]:
    """Remove duplicate chunks from the incoming batch."""
    unique_documents: list[Any] = []
    seen = set(existing_fingerprints)

    for document in documents:
        fingerprint = _document_fingerprint(document)

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        unique_documents.append(document)

    return unique_documents


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

    store_path = _store_path(path)
    store_path.mkdir(parents=True, exist_ok=True)

    store = FAISS.from_documents(
        documents,
        get_embedding_model(),
    )

    store.save_local(str(store_path))

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

    if not (store_path / "index.faiss").is_file():
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
    """Add only new document chunks to the existing FAISS index."""
    store_path = _store_path(path)

    if not documents:
        return load_faiss_store(path=path)

    if (store_path / "index.faiss").is_file():
        store = load_faiss_store(path=path)

        existing_fingerprints = _existing_fingerprints(store)

        new_documents = _filter_new_documents(
            documents,
            existing_fingerprints,
        )

        if not new_documents:
            return store

        store.add_documents(new_documents)
        store.save_local(str(store_path))

        return store

    return build_faiss_store(documents, path=path)


def similarity_search_with_scores(
    query: str,
    *,
    top_k: int = 5,
    path: str | Path | None = None,
) -> list[tuple[Any, float]]:
    """Retrieve documents with their FAISS distance scores.

    Lower L2 distance generally indicates a closer match.
    No arbitrary score threshold is applied.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    store = load_faiss_store(path=path)

    results = store.similarity_search_with_score(
        query.strip(),
        k=top_k,
    )

    return [
        (document, float(score))
        for document, score in results
    ]


def similarity_search(
    query: str,
    *,
    top_k: int = 5,
    path: str | Path | None = None,
) -> list[Any]:
    """Retrieve the most relevant documents from the local FAISS index."""
    results = similarity_search_with_scores(
        query,
        top_k=top_k,
        path=path,
    )

    return [
        document
        for document, _ in results
    ]
