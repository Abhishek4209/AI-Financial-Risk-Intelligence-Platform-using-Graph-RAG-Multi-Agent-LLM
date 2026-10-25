"""PDF text extraction preserving one-based page numbers for citations."""

from pathlib import Path
from typing import Any

from src.preprocessing.metadata import document_metadata



def load_pdf(path: str | Path, *, metadata: dict[str, Any] | None = None) -> list[Any]:
        source = Path(path).expanduser()
        if not source.is_file():
                raise FileNotFoundError("PDF not found: %s" % source)
        try:
                from langchain_community.document_loaders import PyPDFLoader
        except ImportError as exc:
                raise RuntimeError("Install langchain-community and pypdf to load PDFs") from exc
        documents = PyPDFLoader(str(source)).load()
        shared = document_metadata(source, document_type="PDF")
        shared.update(metadata or {})
        for document in documents:
                document.metadata.update(shared)
                document.metadata["page"] = int(document.metadata.get("page", 0)) + 1
        return documents
