import fitz  # PyMuPDF
from pathlib import Path
from app.backend.config import RAW_DIR


def load_pdf_from_path(path: str) -> str:
    """
    Load text from a PDF file path.
    If pages are image-based (scanned PDFs), this may return empty text.
    In that case, consider adding an OCR fallback (e.g., pytesseract).
    """
    doc = fitz.open(path)
    text_parts = []
    for page in doc:
        # Prefer raw text extraction
        page_text = page.get_text("text")
        if page_text:
            text_parts.append(page_text)
    doc.close()
    return "\n".join(text_parts)


def save_raw_upload(file_like, filename: str) -> str:
    """
    Save an uploaded file-like object into data/raw and return the saved path.
    Ensures directory exists and resets file pointer before reading.
    """
    dest = Path(RAW_DIR) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Rewind file if possible
    try:
        file_like.seek(0)
    except Exception:
        pass

    with open(dest, "wb") as f:
        f.write(file_like.read())

    return str(dest)
