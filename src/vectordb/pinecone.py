"""Pinecone vector store backend, matching the RAG_Experiments notebook."""

from __future__ import annotations

import hashlib
import os
from typing import Any

from src.embeddings.embedding_model import get_embedding_model



def _index_name() -> str:
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not os.getenv("PINECONE_API_KEY") or not index_name:
                raise RuntimeError("Set PINECONE_API_KEY and PINECONE_INDEX_NAME to use the Pinecone backend")
        return index_name



def _store() -> Any:
        try:
                from langchain_pinecone import PineconeVectorStore
        except ImportError as exc:
                raise RuntimeError("Install langchain-pinecone to use the Pinecone backend") from exc
        return PineconeVectorStore.from_existing_index(index_name=_index_name(), embedding=get_embedding_model())



def _chunk_id(document: Any) -> str:
        metadata = getattr(document, "metadata", {})
        seed = "%s|%s|%s" % (metadata.get("file_path"), metadata.get("page"), document.page_content)
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()



def add_documents(documents: list[Any]) -> int:
        if not documents:
                return 0
        store = _store()
        store.add_documents(documents, ids=[_chunk_id(document) for document in documents])
        return len(documents)



def similarity_search(query: str, *, top_k: int = 5) -> list[Any]:
        return _store().similarity_search(query, k=top_k)
