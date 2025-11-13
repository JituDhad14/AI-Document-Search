from typing import List
from backend.ingestion.embedder import get_model


def retrieve(query: str, indexer: object, k: int = 5) -> List[dict]:
    """Return top-k metadata entries for a query (each entry contains text + source etc.)."""
    model = get_model()
    qvec = model.encode([query])[0]

    results = indexer.search(qvec, k)
    # If you want to add scores or ids, you can modify this block to match your FaissIndexer output
    return results
