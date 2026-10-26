"""HTTP text ingestion for explicitly supplied HTTPS source URLs."""
from typing import Any
from urllib.parse import urlparse
import requests
def load_url(url: str, *, timeout: float = 20.0, allowed_hosts: set[str] | None = None) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only absolute HTTPS source URLs are accepted")
    if allowed_hosts is not None and parsed.hostname.casefold() not in {host.casefold() for host in allo
wed_hosts}:
        raise ValueError("URL host is not in the configured allowlist")
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "FinancialRiskDocumentIngest/1.0"}
)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text/" not in content_type and "json" not in content_type:
        raise ValueError("URL did not return text or JSON content")
    return {"page_content": response.text, "metadata": {"source": url, "content_type": content_type}}
