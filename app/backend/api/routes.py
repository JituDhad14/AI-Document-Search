from fastapi import APIRouter, UploadFile, File, Query, Depends, HTTPException
import os
import numpy as np
from pydantic import BaseModel

from app.backend.ingestion.text_splitter import split_text
from app.backend.ingestion.embedder import get_model
from app.backend.vectorstore.faiss_index import FaissIndexer
from app.backend.retrieval.rag_pipeline import run_rag
from app.backend.config import FAISS_INDEX_PATH
from app.backend.ingestion.pdf_loader import load_pdf  # make sure you have this function

router = APIRouter()

INDEXER: FaissIndexer | None = None

def get_indexer() -> FaissIndexer | None:
    """Lazy load FAISS indexer from disk if not already loaded."""
    global INDEXER
    if INDEXER is None and os.path.exists(FAISS_INDEX_PATH):
        model = get_model()
        try:
            dim = model.get_sentence_embedding_dimension()
        except Exception:
            emb = model.encode(["hello"])
            dim = np.asarray(emb).shape[-1]
        INDEXER = FaissIndexer(dim=int(dim), index_path=str(FAISS_INDEX_PATH))
    return INDEXER

# ===========================
# Upload PDF endpoint
# ===========================
@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    global INDEXER
    filename = file.filename
    try:
        # Load and split text
        text = load_pdf(file.file)
        chunks = split_text(text)

        # Get embeddings
        model = get_model()
        try:
            dim = model.get_sentence_embedding_dimension()
        except Exception:
            emb = model.encode([chunks[0]])
            dim = np.asarray(emb).shape[-1]

        embeddings = model.encode(chunks, show_progress_bar=False)
        vectors = np.asarray(embeddings, dtype="float32")

        # Init or reuse FAISS index
        INDEXER = FaissIndexer(dim=int(dim), index_path=str(FAISS_INDEX_PATH))

        # Prepare metadata
        metas = [{"source": filename, "text": c} for c in chunks]

        INDEXER.add(vectors, metas)
        INDEXER.save()

        return {"status": "ok", "chunks_added": len(chunks)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ===========================
# Search endpoint
# ===========================
@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    k: int = Query(5, ge=1),
    indexer: FaissIndexer | None = Depends(get_indexer),
):
    if indexer is None or len(indexer.meta) == 0:
        raise HTTPException(status_code=404, detail="No index available. Upload documents first.")

    try:
        result = run_rag(q, indexer, k=k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ===========================
# Chat endpoint
# ===========================
class ChatQuery(BaseModel):
    query: str
    k: int = 5  # number of chunks to retrieve

@router.post("/chat")
async def chat(query: ChatQuery, indexer: FaissIndexer | None = Depends(get_indexer)):
    if indexer is None or len(indexer.meta) == 0:
        raise HTTPException(status_code=404, detail="No index available. Upload documents first.")
    try:
        # Use existing RAG pipeline
        result = run_rag(query.query, indexer, k=query.k)
        # Return the top answer
        return {"query": query.query, "answer": result.get("answer") or result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
