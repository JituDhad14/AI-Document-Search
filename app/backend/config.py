import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"

for d in (RAW_DIR, PROCESSED_DIR, INDEX_DIR):
    os.makedirs(d, exist_ok=True)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

FAISS_INDEX_PATH = INDEX_DIR / "faiss_index.bin"
CHUNKS_META_PATH = INDEX_DIR / "chunks_meta.json"
