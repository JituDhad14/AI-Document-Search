from typing import List
import re


def clean_text(text: str) -> str:
    """Lightweight text cleaning"""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{2,}", "\n\n", text)  # collapse multiple newlines
    return text.strip()


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks by character count (simple)"""
    text = clean_text(text)
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(length, start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size - overlap

    # filter out very small chunks
    return [c for c in chunks if len(c) > 20]
