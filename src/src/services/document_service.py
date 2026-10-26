"""Document ingestion orchestration: parse -> chunk -> embed -> index, per architecture.md."""
from __future__ import annotations
import uuid
from pathlib import Path
from typing import Any
from src.embeddings.embedding_pipeline import build_document_chunks
from src.utils.logger import get_logger
from src.vectordb import index_documents
logger = get_logger(__name__)
def ingest_document(path: str | Path, *, document_id: str | None = None, backend: str | None = None, chunk_
size: int = 1000, chunk_overlap: int = 150) -> dict[str, Any]:
    """Run the ingestion pipeline for one uploaded document and report its status."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError("Document not found: %s" % source)
    chunks = build_document_chunks([source], chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        return {
            "document_id": document_id or str(uuid.uuid4()),
            "status": "failed",
            "document_name": source.name,
            "chunks_indexed": 0,
            "vector_indexed": False,
            "error": "No extractable text was found in the document.",
        }
    try:
        indexed_count = index_documents(chunks, backend=backend)
        vector_indexed = True
    except RuntimeError as exc:
        logger.warning("Vector indexing unavailable for %s: %s", source, exc)
        indexed_count, vector_indexed = 0, False
    logger.info("Ingested %s chunks for %s", len(chunks), source.name)
    return {
        "document_id": document_id or str(uuid.uuid4()),
        "status": "indexed" if vector_indexed else "chunked_only",
        "document_name": source.name,
        "chunks_indexed": indexed_count,
        "vector_indexed": vector_indexed,
    }
def ingest_documents(paths: list[str | Path], *, backend: str | None = None) -> list[dict[str, Any]]:
    return [ingest_document(path, backend=backend) for path in paths]
