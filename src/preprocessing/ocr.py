"""Optional OCR fallback for scanned documents."""
from pathlib import Path
def extract_image_text(image_path: str | Path, *, language: str = "eng") -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install pytesseract and Pillow to use OCR") from exc
    with Image.open(image_path) as image:
        return pytesseract.image_to_string(image, lang=language)
