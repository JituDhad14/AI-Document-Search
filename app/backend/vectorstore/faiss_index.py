import faiss
import json
import numpy as np
from pathlib import Path
from threading import Lock
from typing import List, Dict
# Assuming these imports are available in your environment
from app.backend.ingestion.embedder import get_model 
from ..config import CHUNKS_META_PATH 
# Note: I'm assuming 'index_path' is passed via __init__ and CHUNKS_META_PATH is a global config


class FaissIndexer:
    """
    FAISS index wrapper for storing embeddings and metadata.
    Supports add, save, load, and retrieve operations.
    """

    def __init__(self, dim: int, index_path: str):
        self.dim = dim
        self.index_path = Path(index_path)
        self.meta_path = Path(CHUNKS_META_PATH)
        self.index: faiss.Index | None = None
        self.meta: List[dict] = []
        self.model = get_model()  # embedding model
        self._lock = Lock()
        self.load()

    # 🚨 NEW FUNCTION: RESET INDEX
    def reset(self):
        """Wipe the FAISS index and metadata in memory and on disk."""
        print(f"🚨 Index Reset: Clearing FAISS index and metadata...")
        with self._lock:
            # 1. Reset in-memory data
            self.index = faiss.IndexFlatL2(self.dim)
            self.meta = []

            # 2. Delete files from disk (if they exist)
            if self.index_path.exists():
                self.index_path.unlink()
            if self.meta_path.exists():
                self.meta_path.unlink()
        print("✅ Index Reset Complete.")

    def add(self, vectors: np.ndarray, metas: List[dict], clear_existing: bool = True):
        """
        Add vectors (np.ndarray, shape=(n, dim)) and their metadata.
        If clear_existing is True, the old index is wiped first.
        """
        with self._lock:
            # 🚨 MODIFICATION: Optionally clear old data before adding new data
            if clear_existing:
                if self.index is not None and self.index.ntotal > 0:
                    print("⚠️ Indexer clearing existing data before adding new chunks.")
                self.index = faiss.IndexFlatL2(self.dim)
                self.meta = []
                
            if self.index is None:
                self.index = faiss.IndexFlatL2(self.dim)

            # Rest of original add logic
            if vectors.ndim == 1:
                vectors = vectors.reshape(1, -1)
            
            vectors = np.asarray(vectors, dtype="float32")

            if vectors.shape[1] != self.dim:
                raise ValueError(f"Vector dim {vectors.shape[1]} != index dim {self.dim}")

            self.index.add(vectors)
            self.meta.extend(metas)
            print(f"Indexed {len(metas)} new chunks. Total chunks: {len(self.meta)}")


    def save(self):
        """Persist FAISS index and metadata to disk."""
        with self._lock:
            if self.index is not None:
                faiss.write_index(self.index, str(self.index_path))
            self.meta_path.write_text(
                json.dumps(self.meta, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

    def load(self):
        """Load index and metadata from disk if exists."""
        if self.index_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
            except Exception:
                self.index = None

        if self.meta_path.exists():
            try:
                self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
            except Exception:
                self.meta = []

    def retrieve(self, query: str, k: int = 5) -> List[dict]:
        """
        Retrieve top-k most similar chunks for the query.
        Returns list of metadata dicts (with 'text' and 'source').
        """
        # Ensure we have a model to encode the query
        if self.model is None:
             raise RuntimeError("Embedding model is not initialized.")
            
        if self.index is None or len(self.meta) == 0:
            return []

        # Encode query
        q_vec = self.model.encode([query], show_progress_bar=False)
        q_vec = np.asarray(q_vec, dtype="float32")
        if q_vec.ndim == 1:
            q_vec = q_vec.reshape(1, -1)

        # Search
        D, I = self.index.search(q_vec, min(k, self.index.ntotal))

        results = []
        for idx in I[0]:
            if 0 <= idx < len(self.meta):  # Safety check
                results.append(self.meta[idx])

        return results