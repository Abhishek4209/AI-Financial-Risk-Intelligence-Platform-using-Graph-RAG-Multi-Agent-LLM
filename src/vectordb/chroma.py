"""Chroma vector store backend; optional alternative to the default local FAISS index."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.embeddings.embedding_model import get_embedding_model
from src.utils.constants import PROJECT_ROOT


DEFAULT_CHROMA_PATH = PROJECT_ROOT / "vector_store" / "chroma"
DEFAULT_COLLECTION = "financial_risk_documents"



def _client(path: str | Path | None, collection_name: str | None) -> Any:
        try:
                from langchain_chroma import Chroma
        except ImportError as exc:
                raise RuntimeError("Install langchain-chroma and chromadb to use the Chroma backend") from exc
        persist_directory = str(path or os.getenv("CHROMA_PERSIST_DIR", str(DEFAULT_CHROMA_PATH)))
        return Chroma(
                collection_name=collection_name or os.getenv("CHROMA_COLLECTION", DEFAULT_COLLECTION),
                embedding_function=get_embedding_model(),
                persist_directory=persist_directory,
        )



def add_documents(documents: list[Any], *, path: str | Path | None = None, collection_name: str | None = None) -> int:
        if not documents:
                return 0
        store = _client(path, collection_name)
        store.add_documents(documents)
        return len(documents)



def similarity_search(query: str, *, top_k: int = 5, path: str | Path | None = None, collection_name: str | None = None)
-> list[Any]:
        store = _client(path, collection_name)
        return store.similarity_search(query, k=top_k)
