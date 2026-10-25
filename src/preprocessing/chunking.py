"""Text chunking with LangChain-compatible semantics and no provider dependency."""

from typing import Any



def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
        if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
                raise ValueError("Require chunk_size > 0 and 0 <= chunk_overlap < chunk_size")
        normalized = " ".join(str(text).split())
        chunks = []
        start = 0
        while start < len(normalized):
                end = min(start + chunk_size, len(normalized))
                boundary = normalized.rfind(" ", start, end)
                if end < len(normalized) and boundary > start:
                        end = boundary
                chunks.append(normalized[start:end].strip())
                if end == len(normalized):
                        break
                start = max(start + 1, end - chunk_overlap)
        return [chunk for chunk in chunks if chunk]



def split_documents(documents: list[Any], chunk_size: int = 1000, chunk_overlap: int = 150) -> list[Any]:
        try:
                from langchain_core.documents import Document
        except ImportError as exc:
                raise RuntimeError("Install langchain-core to split Document objects") from exc
        chunks = []
        for document in documents:
                for index, text in enumerate(split_text(document.page_content, chunk_size, chunk_overlap)):
                        metadata = dict(document.metadata)
                         metadata["chunk_index"] = index
                         chunks.append(Document(page_content=text, metadata=metadata))
        return chunks
