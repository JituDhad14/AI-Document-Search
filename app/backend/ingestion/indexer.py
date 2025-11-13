# app/backend/ingestion/indexer.py
import faiss
import json
import numpy as np
from pathlib import Path
from threading import Lock
from typing import List, Dict
from app.backend.ingestion.embedder import get_model
from app.backend.config import FAISS_INDEX_PATH, CHUNKS_META_PATH

class Indexer:
    """
    FAISS-based indexer for storing and retrieving document embeddings.
    Compatible with RAG pipeline.
    """

    def __init__(self, dim: int = 1536, index_path: str = None, meta_path: str = None):
        """
        Args:
            dim (int): Embedding dimension
            index_path (str): Path to FAISS index file
            meta_path (str): Path to metadata JSON file
        """
        self.dim = dim
        self.index_path = Path(index_path) if index_path else Path(FAISS_INDEX_PATH)
        self.meta_path = Path(meta_path) if meta_path else Path(CHUNKS_META_PATH)
        self.index: faiss.Index | None = None
        self.meta: List[Dict] = []
        self.model = get_model()
        self._lock = Lock()

        self.load()

    # -----------------------------
    # Reset index
    # -----------------------------
    def reset(self):
        """Clear index and metadata both in memory and on disk."""
        with self._lock:
            self.index = faiss.IndexFlatL2(self.dim)
            self.meta = []
            if self.index_path.exists():
                self.index_path.unlink()
            if self.meta_path.exists():
                self.meta_path.unlink()
        print("✅ Index and metadata reset complete.")

    # -----------------------------
    # Add vectors
    # -----------------------------
    def add(self, vectors: np.ndarray, metas: List[dict], clear_existing: bool = False):
        """
        Add vectors and metadata to FAISS index.
        Args:
            vectors: np.ndarray of shape (n, dim)
            metas: List of dicts corresponding to each vector
            clear_existing: If True, overwrite existing index and metadata
        """
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] != self.dim:
            raise ValueError(f"Vector dimension {vectors.shape[1]} does not match index dim {self.dim}")

        with self._lock:
            if clear_existing or self.index is None:
                self.index = faiss.IndexFlatL2(self.dim)
                self.meta = []

            if self.index is None:
                self.index = faiss.IndexFlatL2(self.dim)

            self.index.add(vectors)
            self.meta.extend(metas)
            print(f"✅ Indexed {len(metas)} chunks. Total chunks: {len(self.meta)}")

    # -----------------------------
    # Save index & metadata
    # -----------------------------
    def save(self):
        """Persist FAISS index and metadata to disk."""
        with self._lock:
            if self.index is not None:
                faiss.write_index(self.index, str(self.index_path))
            self.meta_path.write_text(json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # -----------------------------
    # Load index & metadata
    # -----------------------------
    def load(self):
        """Load FAISS index and metadata if available."""
        try:
            if self.index_path.exists():
                self.index = faiss.read_index(str(self.index_path))
            else:
                self.index = faiss.IndexFlatL2(self.dim)
        except Exception:
            print("⚠️ Failed to load FAISS index. Initializing empty index.")
            self.index = faiss.IndexFlatL2(self.dim)

        try:
            if self.meta_path.exists():
                self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
            else:
                self.meta = []
        except Exception:
            print("⚠️ Failed to load metadata. Starting empty.")
            self.meta = []

    # -----------------------------
    # Retrieve top-k
    # -----------------------------
    def retrieve(self, query: str, k: int = 5) -> List[dict]:
        """
        Retrieve top-k chunks similar to the query string.
        Returns list of metadata dicts.
        """
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
            if 0 <= idx < len(self.meta):
                results.append(self.meta[idx])
        return results