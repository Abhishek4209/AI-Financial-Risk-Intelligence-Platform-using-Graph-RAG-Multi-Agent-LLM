"""Embedding model access; defaults match the RAG notebook’s local model."""
from __future__ import annotations
import os
from functools import lru_cache
from typing import Any
from src.utils.constants import DEFAULT_EMBEDDING_MODEL
@lru_cache(maxsize=4)
def get_embedding_model(provider: str | None = None, model_name: str | None = None) -> Any:
    """Build the configured embedding model; defaults to the notebook’s local HuggingFace model."""
    selected_provider = (provider or os.getenv("EMBEDDING_PROVIDER", "huggingface")).lower()
    if selected_provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as exc:
            raise RuntimeError("Install langchain-huggingface to create local embeddings") from exc
        return HuggingFaceEmbeddings(
            model_name=model_name or os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
            model_kwargs={"device": os.getenv("EMBEDDING_DEVICE", "cpu")},
            encode_kwargs={"normalize_embeddings": True},
        )
    if selected_provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise RuntimeError("Install langchain-openai to use OpenAI embeddings") from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY to use OpenAI embeddings")
        return OpenAIEmbeddings(model=model_name or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-
small"))
    raise ValueError("EMBEDDING_PROVIDER must be ’huggingface’ or ’openai’")
def embed_texts(texts: list[str], *, provider: str | None = None) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model(provider)
    return model.embed_documents(texts)
def embed_query(text: str, *, provider: str | None = None) -> list[float]:
    model = get_embedding_model(provider)
    return model.embed_query(text)
