
"""End-to-end embedding pipeline: parse, clean, chunk, and embed."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.embeddings.embedding_model import embed_texts
from src.ingestion.parser import parse_file
from src.preprocessing.chunking import split_documents
from src.preprocessing.metadata import document_metadata


def build_document_chunks(
    paths: list[str | Path],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Any]:
    """Parse documents into chunks with citation metadata."""

    all_documents: list[Any] = []

    for path in paths:
        documents = parse_file(path)
        shared_metadata = document_metadata(path)

        for document in documents:
            document.metadata = {
                **shared_metadata,
                **document.metadata,
            }

        all_documents.extend(documents)

    if not all_documents:
        return []

    return split_documents(
        all_documents,
        chunk_size,
        chunk_overlap,
    )


def embed_document_chunks(
    chunks: list[Any],
    *,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Embed chunks and pair text, metadata, and vectors."""

    if not chunks:
        return []

    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts, provider=provider)

    return [
        {
            "page_content": chunk.page_content,
            "metadata": chunk.metadata,
            "embedding": vector,
        }
        for chunk, vector in zip(chunks, vectors)
    ]


def run_embedding_pipeline(
    paths: list[str | Path],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Run document parsing, chunking, and embedding."""

    chunks = build_document_chunks(
        paths,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return embed_document_chunks(
        chunks,
        provider=provider,
    )
