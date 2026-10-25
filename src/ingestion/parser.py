"""Dispatch local document parsing by file extension."""

from pathlib import Path
from typing import Any

from src.ingestion.email_loader import load_email
from src.ingestion.excel_loader import load_excel
from src.ingestion.pdf_loader import load_pdf



def parse_file(path: str | Path) -> list[Any]:
        source = Path(path).expanduser()
        if not source.is_file():
                raise FileNotFoundError("Document not found: %s" % source)
        suffix = source.suffix.lower()
        if suffix == ".pdf":
                return load_pdf(source)
        if suffix in {".xlsx", ".xls"}:
                frame = load_excel(source)
                try:
                        from langchain_core.documents import Document
                except ImportError as exc:
                        raise RuntimeError("Install langchain-core to convert spreadsheets to documents") from exc
                return [Document(page_content=frame.to_csv(index=False), metadata={"source_file": source.name})]
        if suffix in {".eml", ".email"}:
                record = load_email(source)
                try:
                        from langchain_core.documents import Document
                except ImportError as exc:
                        raise RuntimeError("Install langchain-core to convert emails to documents") from exc
                return [Document(page_content=record["page_content"], metadata=record["metadata"])]
        if suffix in {".txt", ".md", ".html", ".htm"}:
                text = source.read_text(encoding="utf-8", errors="replace")
                if suffix in {".html", ".htm"}:
                        try:
                                from bs4 import BeautifulSoup
                        except ImportError as exc:
                                raise RuntimeError("Install beautifulsoup4 to parse HTML documents") from exc
                        text = BeautifulSoup(text, "html.parser").get_text("\n")
                try:
                        from langchain_core.documents import Document
                except ImportError as exc:
                        raise RuntimeError("Install langchain-core to parse text documents") from exc
                return [Document(page_content=text, metadata={"source_file": source.name, "file_path": str(source)})]
        raise ValueError("Unsupported document extension: %s" % suffix)
