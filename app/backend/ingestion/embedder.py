from typing import List
from app.backend.config import EMBEDDING_MODEL

# we lazily import the model so the module can be imported without immediately loading
_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    # convert to list for json-compat if needed
    return [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings]
