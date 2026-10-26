"""Metadata normalization for local regulatory and financial documents."""
from pathlib import Path
from typing import Any
ORGANIZATION_HINTS = {
    "american": "American Express", "rbi": "RBI", "reserve_bank": "RBI",
    "sebi": "SEBI", "fatf": "FATF", "basel": "Basel Committee",
    "jpmorgan": "JPMorgan Chase", "chase": "JPMorgan Chase",
    "visa": "Visa", "mastercard": "Mastercard",
}
def identify_organization(filename: str | Path) -> str:
    name = Path(filename).name.casefold()
    return next((organization for hint, organization in ORGANIZATION_HINTS.items() if hint in name), "U
nknown")
def document_metadata(path: str | Path, *, organization: str | None = None, document_type: str | None = Non
e, page: int | None = None) -> dict[str, Any]:
    source = Path(path)
    result = {
        "source_file": source.name, "file_path": str(source.resolve()),
        "file_type": source.suffix.lower().lstrip("."),
        "organization": organization or identify_organization(source),
        "document_type": document_type or source.suffix.lower().lstrip("."),
    }
    if page is not None:
        result["page"] = page
    return result
