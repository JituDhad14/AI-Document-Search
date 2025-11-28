import faiss
import json
import numpy as np
from pathlib import Path
from threading import Lock
from typing import List, Dict, Optional, Any

from app.backend.ingestion.embedder import get_model
from ..config import CHUNKS_META_PATH


class FaissIndexer:
    """
    FAISS index wrapper for storing embeddings and metadata.
    Supports add, save, load, retrieve, and delete_by_source.
    """

    def __init__(self, dim: int, index_path: str):
        self.dim = dim
        self.index_path = Path(index_path)
        self.meta_path = Path(CHUNKS_META_PATH)
        self.index: Optional[faiss.Index] = None
        self.meta: List[dict] = []
        self.model = get_model()  # embedding model (must implement .encode)
        self._lock = Lock()
        self.load()

    def reset(self):
        """Wipe the FAISS index and metadata in memory and on disk."""
        print(f"🚨 Index Reset: Clearing FAISS index and metadata...")
        with self._lock:
            self.index = faiss.IndexFlatL2(self.dim)
            self.meta = []

            if self.index_path.exists():
                try:
                    self.index_path.unlink()
                except Exception:
                    pass
            if self.meta_path.exists():
                try:
                    self.meta_path.unlink()
                except Exception:
                    pass
        print("✅ Index Reset Complete.")

    def add(self, vectors: np.ndarray, metas: List[dict], clear_existing: bool = False):
        """
        Add vectors (np.ndarray, shape=(n, dim)) and their metadata.
        If clear_existing is True, the old index is wiped first.
        """
        with self._lock:
            if clear_existing:
                if self.index is not None and getattr(self.index, "ntotal", 0) > 0:
                    print("⚠️ Indexer clearing existing data before adding new chunks.")
                self.index = faiss.IndexFlatL2(self.dim)
                self.meta = []

            if self.index is None:
                self.index = faiss.IndexFlatL2(self.dim)

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
            try:
                self.meta_path.write_text(json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                print("Warning: failed to save meta:", e)

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
        if self.model is None:
            raise RuntimeError("Embedding model is not initialized.")

        if self.index is None or len(self.meta) == 0:
            return []

        q_vec = self.model.encode([query], show_progress_bar=False)
        q_vec = np.asarray(q_vec, dtype="float32")
        if q_vec.ndim == 1:
            q_vec = q_vec.reshape(1, -1)

        # ensure k <= ntotal
        ntotal = int(getattr(self.index, "ntotal", 0))
        if ntotal == 0:
            return []

        D, I = self.index.search(q_vec, min(k, ntotal))

        results: List[dict] = []
        for idx in I[0]:
            if 0 <= idx < len(self.meta):
                results.append(self.meta[idx])

        return results

    # ---------------------------
    # Deletion / rebuild helpers
    # ---------------------------
    def delete_by_source(self, source_name: str) -> int:
        """
        Remove all vectors whose metadata 'source' equals source_name.
        Returns number of vectors removed.

        Strategy:
        1) Collect indices to remove.
        2) If faiss.Index supports remove_ids, attempt to use it.
        3) Otherwise, rebuild index from remaining meta by re-encoding the kept texts.
        """
        with self._lock:
            if not self.meta:
                return 0

            # indices to remove where meta.source == source_name
            to_remove = [i for i, m in enumerate(self.meta) if m.get("source") == source_name]

            if not to_remove:
                return 0

            removed_count = len(to_remove)
            print(f"FaissIndexer.delete_by_source: will remove {removed_count} chunks for source '{source_name}'")

            # Try remove_ids if available
            try:
                # faiss expects a numpy array of ids (int64)
                ids_array = np.array(to_remove, dtype=np.int64)
                # Some FAISS builds support remove_ids on Index, some don't.
                if hasattr(self.index, "remove_ids"):
                    try:
                        self.index.remove_ids(ids_array)
                        # After calling remove_ids, metadata mapping may no longer align.
                        # Easiest safe action: rebuild metadata by keeping entries not in to_remove.
                        keep_set = set(to_remove)
                        self.meta = [m for i, m in enumerate(self.meta) if i not in keep_set]
                        if hasattr(self, "vectors"):
                            self.vectors = [v for i, v in enumerate(self.vectors) if i not in keep_set]
                        # Persist
                        self.save()
                        return removed_count
                    except Exception as e:
                        print("remove_ids failed, will fallback to rebuild:", e)
                else:
                    print("Index has no remove_ids; will rebuild from remaining metadata.")
            except Exception as e:
                print("Attempt to call remove_ids raised:", e)

            # Fallback: rebuild index from remaining metadata
            keep_meta = [m for i, m in enumerate(self.meta) if i not in set(to_remove)]

            # Rebuild index using kept metadata's text fields
            rebuilt_count = self._rebuild_index_from_meta(keep_meta)
            # rebuilt_count is number of entries kept; removed_count = original - rebuilt_count
            if rebuilt_count is None:
                # Unexpected failure
                raise RuntimeError("Rebuild failed during delete_by_source")
            # Update meta and persist
            self.meta = keep_meta
            self.save()
            return removed_count

    def _rebuild_index_from_meta(self, kept_meta: List[dict]) -> Optional[int]:
        """
        Recreate self.index from kept_meta. We re-encode the chunk texts using the model.
        Returns number of kept vectors on success, None on failure.
        """
        try:
            if self.model is None:
                raise RuntimeError("Embedding model is not initialized for rebuild.")

            # Extract texts for encoding; fallback to 'text' field
            texts = [m.get("text", "") for m in kept_meta]
            if not texts:
                # Create empty index
                self.index = faiss.IndexFlatL2(self.dim)
                self.meta = []
                return 0

            # Encode in batches to avoid memory issues if many chunks
            # Choose a batch size based on memory; 512 is a safe default but you can tune
            batch_size = 512
            all_vecs = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                embs = self.model.encode(batch_texts, show_progress_bar=False)
                embs = np.asarray(embs, dtype="float32")
                if embs.ndim == 1:
                    embs = embs.reshape(1, -1)
                all_vecs.append(embs)

            if all_vecs:
                vectors = np.vstack(all_vecs)
            else:
                vectors = np.empty((0, self.dim), dtype="float32")

            # Recreate index and add vectors
            self.index = faiss.IndexFlatL2(self.dim)
            if vectors.shape[0] > 0:
                if vectors.shape[1] != self.dim:
                    raise ValueError(f"Rebuilt vectors dim {vectors.shape[1]} != index dim {self.dim}")
                self.index.add(vectors)

            # Optionally keep vectors in memory if you use that elsewhere
            try:
                self.vectors = [v for v in vectors]  # list of numpy rows; optional
            except Exception:
                self.vectors = None

            return len(kept_meta)
        except Exception as e:
            print("Error rebuilding index from meta:", e)
            return None
