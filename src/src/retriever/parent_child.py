"""Parent-child retrieval: search small child chunks, return larger parent context."""
from __future__ import annotations
from typing import Any
from src.preprocessing.chunking import split_text
def build_parent_child_index(documents: list[Any], *, parent_chunk_size: int = 2000, child_chunk_size: int 
= 400) -> tuple[list[Any], list[Any]]:
    """Split each document into parent and child chunks; children carry a parent_index."""
    try:
        from langchain_core.documents import Document
    except ImportError as exc:
        raise RuntimeError("Install langchain-core to build parent-child chunks") from exc
    parents: list[Any] = []
    children: list[Any] = []
    for document in documents:
        for parent_text in split_text(document.page_content, parent_chunk_size, chunk_overlap=0):
            parent_index = len(parents)
            parents.append(Document(page_content=parent_text, metadata=dict(document.metadata)))
            for child_text in split_text(parent_text, child_chunk_size, chunk_overlap=0):
                child_metadata = dict(document.metadata)
                child_metadata["parent_index"] = parent_index
                children.append(Document(page_content=child_text, metadata=child_metadata))
    return parents, children
def resolve_parents(matched_children: list[Any], parents: list[Any]) -> list[Any]:
    """Map matched child chunks back to their parent context, preserving order and uniqueness."""
    seen: set[int] = set()
    resolved = []
    for child in matched_children:
        parent_index = child.metadata.get("parent_index")
        if parent_index is None or parent_index in seen or parent_index >= len(parents):
            continue
        seen.add(parent_index)
        resolved.append(parents[parent_index])
    return resolved
