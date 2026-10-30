"""Parse RFC822 email files without executing or unpacking attachments."""
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any
def load_email(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError("Email file not found: %s" % source)
    with source.open("rb") as message_file:
        message = BytesParser(policy=policy.default).parse(message_file)
    bodies = [
        part.get_content() for part in message.walk()
        if part.get_content_type() == "text/plain" and not part.get_filename()
    ]
    return {
        "page_content": "\n".join(bodies),
        "metadata": {"source_file": source.name, "subject": str(message.get("subject", "")),
                     "date": str(message.get("date", "")), "from": str(message.get("from", ""))},
    }
