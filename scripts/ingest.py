"""Extract local financial documents into citation-ready JSONL chunks."""
import argparse
import csv
import json
import logging
from pathlib import Path
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".xls"}
LOGGER = logging.getLogger("financial_risk.ingest")
def split_text(text, chunk_size, overlap):
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks
def _extract_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("PDF ingestion requires pypdf; install requirements.txt") from error
    reader = PdfReader(str(path))
    return [(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
def _extract_docx(path):
    try:
        from docx import Document
    except ImportError as error:
        raise RuntimeError("DOCX ingestion requires python-docx; install requirements.txt") from error
    document = Document(str(path))
    return [(None, "\n".join(paragraph.text for paragraph in document.paragraphs))]
def _extract_csv(path):
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
        return [
            (row_number, " | ".join("%s: %s" % (key, value) for key, value in row.items() if value))
            for row_number, row in enumerate(csv.DictReader(source), start=2)
        ]
def _extract_spreadsheet(path):
    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError("Spreadsheet ingestion requires pandas and openpyxl; install requirements.txt")
 from error
    workbook = pd.ExcelFile(path)
    records = []
    for sheet in workbook.sheet_names:
        table = pd.read_excel(workbook, sheet_name=sheet)
        records.extend(
            (int(index) + 2, "Sheet %s | %s" % (sheet, " | ".join(
                "%s: %s" % (column, value) for column, value in row.items() if value is not None
            )))
            for index, row in table.iterrows()
        )
    return records
def extract_file(path):
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return [(None, path.read_text(encoding="utf-8", errors="replace"))]
    extractors = {
        ".pdf": _extract_pdf,
        ".docx": _extract_docx,
        ".csv": _extract_csv,
        ".xlsx": _extract_spreadsheet,
        ".xls": _extract_spreadsheet,
    }
    if suffix not in extractors:
        raise ValueError("Unsupported document type: %s" % path.suffix)
    return extractors[suffix](path)
def ingest(input_paths, output_path, chunk_size, overlap, organization, document_type, reporting_year):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record_count = 0
    with output_path.open("w", encoding="utf-8") as output:
        for path in input_paths:
            pages = extract_file(path)
            for page_number, text in pages:
                for chunk_index, chunk in enumerate(split_text(text, chunk_size, overlap)):
                    record = {
                        "page_content": chunk,
                        "metadata": {
                            "source_file": str(path),
                            "file_name": path.name,
                            "file_type": path.suffix.lower().lstrip("."),
                            "page": page_number,
                            "chunk_index": chunk_index,
                            "organization": organization,
                            "document_type": document_type,
                            "reporting_year": reporting_year,
                        },
                    }
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
                    record_count += 1
            LOGGER.info("Extracted %s", path)
    return record_count
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", nargs="+", help="One or more local document paths")
    source.add_argument("--input-dir", help="Recursively ingest supported documents from a directory")
    parser.add_argument("--output", default="data/processed/document_chunks.jsonl")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--organization", help="Company or regulator, for citation metadata")
    parser.add_argument("--document-type", help="For example annual_report or regulatory_circular")
    parser.add_argument("--reporting-year", type=int)
    args = parser.parse_args()
    if args.chunk_size < 1 or args.overlap < 0 or args.overlap >= args.chunk_size:
        parser.error("Require chunk-size > 0 and 0 <= overlap < chunk-size")
    if args.input:
        paths = [Path(item).expanduser().resolve() for item in args.input]
    else:
        directory = Path(args.input_dir).expanduser().resolve()
        if not directory.is_dir():
            parser.error("Input directory does not exist: %s" % directory)
        paths = sorted(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower(
) in SUPPORTED_EXTENSIONS)
    if not paths:
        parser.error("No supported documents found")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        parser.error("Input files do not exist: %s" % missing)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = ingest(
        paths, Path(args.output).expanduser().resolve(), args.chunk_size, args.overlap,
        args.organization, args.document_type, args.reporting_year,
    )
    print(json.dumps({"files": len(paths), "chunks": count, "output": str(Path(args.output).resolve(
))}, indent=2))
if __name__ == "__main__":
    main()
